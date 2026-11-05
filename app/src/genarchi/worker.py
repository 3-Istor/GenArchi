"""Worker HTTP (P3) : reçoit les CloudEvents Firestore livrés par Eventarc."""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from . import CONTRACT_VERSION
from .domain import Problem
from .wiring import Container

log = logging.getLogger("genarchi.worker")


def ticket_id_from_event(headers, body: bytes) -> str | None:
    """Mode binaire (Eventarc) : `ce-subject: documents/tickets/<id>`. Mode structuré : champ `subject`."""
    subject = headers.get("ce-subject")
    if not subject and body:
        try:
            subject = json.loads(body).get("subject")
        except ValueError:
            subject = None
    if not subject:
        return None
    parts = subject.strip("/").split("/")
    return parts[-1] if len(parts) >= 2 and parts[-2] == "tickets" else None


def create_worker_app(c: Container) -> FastAPI:
    s = c.settings
    app = FastAPI(title="GenArchi worker", version=CONTRACT_VERSION, docs_url=None, redoc_url=None)
    issuer = c.issuer()

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz():
        try:
            c.store.ping()
        except Exception:
            return JSONResponse({"status": "not_ready", "checks": {"database": "fail"}}, 503)
        return {"status": "ready", "checks": {"database": "ok"}}

    @app.get("/version")
    def version():
        return {
            "app_version": s.app_version,
            "contract_version": CONTRACT_VERSION,
            "platform": s.platform,
            "process": "worker",
            "region": s.region,
            "zone": s.zone,
            "instance": s.instance,
            "data_backend": s.data_backend,
        }

    @app.post("/internal/events/ticket-created")
    async def ticket_created(request: Request):
        body = await request.body()
        tid = ticket_id_from_event(request.headers, body)
        if tid is None:
            log.warning("event ignored: no ticket id", extra={"ce_type": request.headers.get("ce-type")})
            return Response(status_code=204)  # message illisible : inutile de le relivrer
        try:
            t = issuer.issue(tid)
        except Problem as p:
            if p.status == 404:
                return Response(status_code=204)
            raise
        except Exception:
            log.exception("issue failed, the event will be redelivered", extra={"ticket_id": tid})
            return JSONResponse({"code": "unavailable"}, status_code=503)
        log.info("event handled", extra={"ticket_id": t.id, "ce_id": request.headers.get("ce-id")})
        return Response(status_code=204)

    return app
