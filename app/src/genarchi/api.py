"""API HTTP (contracts/api/openapi.yaml)."""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime, timedelta
from html import escape
from typing import Annotated, Literal

from fastapi import BackgroundTasks, Depends, FastAPI, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import CONTRACT_VERSION, domain
from .domain import Event, Order, Problem, Ticket, TicketStatus
from .logs import request_id_var, trace_var
from .services import ticket_purchased_event
from .wiring import Container

log = logging.getLogger("genarchi.api")
EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


# --- schémas d'entrée -----------------------------------------------------------------------------
class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    venue: str = Field(min_length=1, max_length=120)
    starts_at: datetime
    sales_open_at: datetime
    capacity: int = Field(ge=1, le=100_000)
    price_cents: int = Field(ge=0)

    @model_validator(mode="after")
    def _window(self) -> EventCreate:
        if self.starts_at.tzinfo is None or self.sales_open_at.tzinfo is None:
            raise ValueError("les dates doivent préciser leur fuseau (RFC 3339)")
        if self.sales_open_at >= self.starts_at:
            raise ValueError("sales_open_at doit précéder starts_at")
        if self.starts_at <= domain.now():
            raise ValueError("starts_at doit être dans le futur")
        return self


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    buyer_email: str = Field(max_length=254, pattern=EMAIL_RE)
    quantity: int = Field(ge=1, le=4)


class ChaosRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["crash", "unready", "latency"]
    duration_s: int = Field(default=60, ge=1, le=600)
    latency_ms: int = Field(default=1000, ge=1, le=10_000)


# --- sérialisation --------------------------------------------------------------------------------
def iso(d: datetime | None) -> str | None:
    return d.isoformat().replace("+00:00", "Z") if d else None


def event_json(e: Event) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "venue": e.venue,
        "starts_at": iso(e.starts_at),
        "sales_open_at": iso(e.sales_open_at),
        "capacity": e.capacity,
        "remaining": e.remaining,
        "price_cents": e.price_cents,
        "currency": e.currency,
        "status": e.status().value,
        "created_at": iso(e.created_at),
    }


def ticket_json(t: Ticket) -> dict:
    issued = t.status in (TicketStatus.ISSUED, TicketStatus.SCANNED)
    return {
        "id": t.id,
        "order_id": t.order_id,
        "event_id": t.event_id,
        "status": t.status.value,
        "qr_url": f"/tickets/{t.id}/qr" if issued else None,
        "issued_at": iso(t.issued_at),
        "scanned_at": iso(t.scanned_at),
    }


def order_json(o: Order) -> dict:
    return {
        "id": o.id,
        "event_id": o.event_id,
        "buyer_email": o.buyer_email,
        "quantity": o.quantity,
        "amount_cents": o.amount_cents,
        "status": o.status,
        "tickets": [ticket_json(t) for t in o.tickets],
        "created_at": iso(o.created_at),
    }


def problem_response(status: int, code: str, detail: str = "", headers: dict | None = None, **extra) -> JSONResponse:
    titles = {
        400: "Bad Request",
        401: "Unauthorized",
        404: "Not Found",
        409: "Conflict",
        422: "Unprocessable Content",
        500: "Internal Server Error",
        503: "Service Unavailable",
    }
    body = {
        "type": f"/problems/{code}",
        "title": titles.get(status, "Error"),
        "status": status,
        "code": code,
        "detail": detail,
        **extra,
    }
    return JSONResponse(body, status_code=status, media_type="application/problem+json", headers=headers)


# --- état de chaos (hooks de test du protocole T2/T4) ---------------------------------------------
class Chaos:
    def __init__(self) -> None:
        self.unready_until = 0.0
        self.latency_until = 0.0
        self.latency_ms = 0

    def unready(self) -> bool:
        return time.monotonic() < self.unready_until

    def delay(self) -> float:
        return self.latency_ms / 1000 if time.monotonic() < self.latency_until else 0.0


def _crash() -> None:
    time.sleep(0.2)
    os._exit(3)  # arrêt brutal volontaire : la plateforme doit remplacer l'instance


# --- application ----------------------------------------------------------------------------------
def create_app(c: Container) -> FastAPI:
    s = c.settings
    app = FastAPI(title="GenArchi Billetterie API", version=CONTRACT_VERSION, docs_url="/docs", redoc_url=None)
    app.state.container = c
    chaos = Chaos()

    def require(*tokens: str):
        def dep(authorization: Annotated[str | None, Header()] = None) -> None:
            given = (authorization or "").removeprefix("Bearer ").strip()
            if not given or not any(domain.constant_time_equals(given, t) for t in tokens):
                raise Problem(401, "unauthorized", "jeton absent ou invalide")

        return dep

    admin = Depends(require(s.admin_token))
    staff = Depends(require(s.staff_token, s.admin_token))

    @app.exception_handler(Problem)
    async def _problem(_req: Request, exc: Problem):
        headers = {"Retry-After": "2"} if exc.code in ("ticket_not_issued", "unavailable") else None
        return problem_response(exc.status, exc.code, exc.detail, headers, **exc.extra)

    @app.exception_handler(RequestValidationError)
    async def _invalid(_req: Request, exc: RequestValidationError):
        errors = [
            {"field": ".".join(str(p) for p in e["loc"][1:]) or str(e["loc"][0]), "message": e["msg"]}
            for e in exc.errors()
        ]
        return problem_response(422, "validation_error", "corps ou paramètres invalides", errors=errors)

    @app.exception_handler(Exception)
    async def _unexpected(_req: Request, exc: Exception):
        log.exception("unhandled error")
        return problem_response(500, "internal_error", "erreur interne")

    @app.middleware("http")
    async def _context(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        tp = request.headers.get("traceparent", "")
        cloud = request.headers.get("x-cloud-trace-context", "")
        trace = tp.split("-")[1] if tp.count("-") >= 3 else (cloud.split("/")[0] or None)
        request_id_var.set(rid)
        trace_var.set(trace)
        if (d := chaos.delay()) and request.url.path not in ("/healthz",):
            await asyncio.sleep(d)
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Served-By"] = s.instance
        if request.url.path not in ("/healthz", "/readyz"):
            log.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "http_status": response.status_code,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
        return response

    # --- sondes et identité --------------------------------------------------------------------------
    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz():
        if s.chaos_force_unready or chaos.unready():
            return JSONResponse({"status": "not_ready", "checks": {"database": "fail", "chaos": "fail"}}, 503)
        try:
            c.store.ping()
        except Exception:
            log.warning("readiness: database unreachable", exc_info=True)
            return JSONResponse({"status": "not_ready", "checks": {"database": "fail"}}, 503)
        return {"status": "ready", "checks": {"database": "ok"}}

    @app.get("/version")
    def version():
        return {
            "app_version": s.app_version,
            "contract_version": CONTRACT_VERSION,
            "platform": s.platform,
            "process": "api",
            "region": s.region,
            "zone": s.zone,
            "instance": s.instance,
            "data_backend": s.data_backend,
        }

    # --- événements ----------------------------------------------------------------------------------
    @app.get("/events")
    def list_events(
        status: Literal["scheduled", "on_sale", "sold_out", "closed"] | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        cursor: str | None = None,
    ):
        events = [e for e in c.store.list_events() if status is None or e.status().value == status]
        start = 0
        if cursor:
            try:
                last = base64.urlsafe_b64decode(cursor.encode()).decode()
                start = next(i for i, e in enumerate(events) if e.id == last) + 1
            except Exception:
                raise Problem(400, "validation_error", "curseur invalide") from None
        page = events[start : start + limit]
        nxt = base64.urlsafe_b64encode(page[-1].id.encode()).decode() if start + limit < len(events) else None
        return {"items": [event_json(e) for e in page], "next_cursor": nxt}

    @app.post("/events", status_code=201, dependencies=[admin])
    def create_event(body: EventCreate, response: Response):
        e = Event(
            domain.new_id("evt"),
            body.name,
            body.venue,
            body.starts_at,
            body.sales_open_at,
            body.capacity,
            body.capacity,
            body.price_cents,
            domain.now(),
        )
        c.store.create_event(e)
        response.headers["Location"] = f"/events/{e.id}"
        return event_json(e)

    @app.get("/events/{event_id}")
    def get_event(event_id: str):
        e = c.store.get_event(event_id)
        if e is None:
            raise Problem(404, "not_found", "événement introuvable")
        return event_json(e)

    # --- achat ---------------------------------------------------------------------------------------
    @app.post("/events/{event_id}/orders", status_code=201)
    def create_order(
        event_id: str,
        body: OrderCreate,
        response: Response,
        request: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ):
        key_ok = bool(idempotency_key) and re.fullmatch(r"[\w\-.:]{8,128}", idempotency_key or "") is not None
        if not key_ok:
            raise Problem(400, "idempotency_key_required", "en-tête Idempotency-Key requis (8 à 128 caractères)")
        rh = domain.order_request_hash(event_id, body.buyer_email, body.quantity)
        order, created = c.store.place_order(event_id, idempotency_key, body.buyer_email, body.quantity, rh)
        response.headers["Location"] = f"/orders/{order.id}"
        if not created:
            response.status_code = 200
        elif s.events_backend != "none":
            try:
                c.publisher.publish(ticket_purchased_event(order, s.platform, request.headers.get("traceparent")))
            except Exception:
                log.warning(
                    "ticket.purchased not published, issue-pending will catch up",
                    exc_info=True,
                    extra={"order_id": order.id},
                )
        log.info(
            "order placed" if created else "order replayed",
            extra={"order_id": order.id, "event_id": event_id, "quantity": order.quantity},
        )
        return order_json(order)

    @app.get("/orders/{order_id}")
    def get_order(order_id: str):
        o = c.store.get_order(order_id)
        if o is None:
            raise Problem(404, "not_found", "commande introuvable")
        return order_json(o)

    # --- billets -------------------------------------------------------------------------------------
    def _ticket_or_404(ticket_id: str) -> Ticket:
        t = c.store.get_ticket(ticket_id)
        if t is None:
            raise Problem(404, "not_found", "billet introuvable")
        return t

    @app.get("/tickets/{ticket_id}")
    def get_ticket(ticket_id: str):
        return ticket_json(_ticket_or_404(ticket_id))

    @app.get("/tickets/{ticket_id}/qr")
    def get_qr(ticket_id: str):
        t = _ticket_or_404(ticket_id)
        if t.status == TicketStatus.PENDING or not t.qr_object:
            raise Problem(409, "ticket_not_issued", "billet pas encore émis, réessayer")
        url = c.blob.signed_url(t.qr_object, 900)
        if url:
            return RedirectResponse(url, status_code=302)
        data = c.blob.get(t.qr_object)
        if data is None:
            raise Problem(503, "unavailable", "QR momentanément indisponible")
        return Response(data, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})

    @app.post("/tickets/{ticket_id}/scan", dependencies=[staff])
    def scan(ticket_id: str):
        t, already = c.store.mark_scanned(ticket_id, domain.now())
        if already:
            raise Problem(409, "already_scanned", "billet déjà scanné", scanned_at=iso(t.scanned_at))
        return ticket_json(t)

    @app.get("/t/{ticket_id}", response_class=HTMLResponse)
    def landing(ticket_id: str):
        t = _ticket_or_404(ticket_id)
        e = c.store.get_event(t.event_id)
        name = escape(e.name if e else t.event_id)
        img = (
            f'<img src="/tickets/{escape(t.id)}/qr" alt="QR code" width="240">'
            if t.qr_object
            else "<p>QR en cours d'émission…</p>"
        )
        return (
            f"<!doctype html><meta charset=utf-8><title>Billet {name}</title>"
            f"<body style='font-family:system-ui;text-align:center;padding:2rem'>"
            f"<h1>{name}</h1>{img}<p>Statut : <b>{escape(t.status.value)}</b></p>"
            f"<p><small>{escape(t.id)}</small></p></body>"
        )

    # --- admin et tests ------------------------------------------------------------------------------
    @app.get("/admin/events/{event_id}/stats", dependencies=[admin])
    def stats(event_id: str):
        st = c.store.stats(event_id)
        if st is None:
            raise Problem(404, "not_found", "événement introuvable")
        return {
            "event_id": st.event_id,
            "capacity": st.capacity,
            "sold": st.sold,
            "remaining": st.remaining,
            "tickets": {"pending": st.pending, "issued": st.issued, "scanned": st.scanned},
        }

    @app.post("/internal/chaos", status_code=202, dependencies=[admin])
    def trigger_chaos(body: ChaosRequest, background: BackgroundTasks):
        if not s.chaos_enabled:
            raise Problem(404, "not_found", "chaos désactivé sur cette instance")
        log.warning("chaos triggered", extra={"mode": body.mode, "duration_s": body.duration_s})
        if body.mode == "crash":
            background.add_task(lambda: threading.Thread(target=_crash, daemon=True).start())
        elif body.mode == "unready":
            chaos.unready_until = time.monotonic() + body.duration_s
        else:
            chaos.latency_ms = body.latency_ms
            chaos.latency_until = time.monotonic() + body.duration_s
        return {
            "mode": body.mode,
            "instance": s.instance,
            "until": iso(domain.now() + timedelta(seconds=body.duration_s)),
        }

    front = os.environ.get("FRONT_DIR")
    if front and os.path.isdir(front):  # en local seulement : en P2 Apache, en P3 le CDN servent le front
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=front, html=True), name="front")
    return app
