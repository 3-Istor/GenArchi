"""Cas d'usage, communs à toutes les plateformes."""

from __future__ import annotations

import io
import logging
from datetime import timedelta

import segno

from . import domain
from .domain import Problem, Ticket, TicketStatus
from .ports import BlobStore, Publisher, Store

log = logging.getLogger("genarchi.services")


def cloud_event(event_type: str, source: str, subject: str, data: dict, traceparent: str | None = None) -> dict:
    """Enveloppe CloudEvents 1.0, mode structuré (contracts/events/README.md)."""
    ce = {
        "specversion": "1.0",
        "id": domain.new_id("ce"),
        "source": source,
        "type": event_type,
        "time": domain.now().isoformat().replace("+00:00", "Z"),
        "datacontenttype": "application/json",
        "subject": subject,
        "data": data,
    }
    if traceparent:
        ce["traceparent"] = traceparent
    return ce


def ticket_purchased_event(order: domain.Order, platform: str, traceparent: str | None = None) -> dict:
    return cloud_event(
        "fr.genarchi.ticket.purchased.v1",
        f"//genarchi/{platform}/api",
        f"orders/{order.id}",
        {
            "order_id": order.id,
            "event_id": order.event_id,
            "ticket_ids": [t.id for t in order.tickets],
            "quantity": order.quantity,
            "amount_cents": order.amount_cents,
            "buyer_email": order.buyer_email,
            "purchased_at": order.created_at.isoformat().replace("+00:00", "Z"),
        },
        traceparent,
    )


def render_qr_png(content: str) -> bytes:
    buf = io.BytesIO()
    segno.make(content, error="m").save(buf, kind="png", scale=8, border=2)
    return buf.getvalue()


class TicketIssuer:
    """Émission d'un billet : QR écrit, billet passé `issued`. Idempotente (I5)."""

    def __init__(
        self, store: Store, blob: BlobStore, publisher: Publisher, public_base_url: str, platform: str
    ) -> None:
        self.store = store
        self.blob = blob
        self.publisher = publisher
        self.public_base_url = public_base_url
        self.platform = platform

    def issue(self, ticket_id: str) -> Ticket:
        ticket = self.store.get_ticket(ticket_id)
        if ticket is None:
            raise Problem(404, "not_found", f"billet {ticket_id} introuvable")
        if ticket.status != TicketStatus.PENDING:
            return ticket  # déjà émis : rien à refaire
        key = domain.qr_object_key(ticket.event_id, ticket.id)
        self.blob.put(key, render_qr_png(f"{self.public_base_url}/t/{ticket.id}"), "image/png")
        issued, changed = self.store.mark_issued(ticket.id, key, domain.now())
        if changed:  # une seule publication même si deux livraisons arrivent en même temps
            self._publish_issued(issued)
        log.info("ticket issued", extra={"ticket_id": issued.id, "event_id": issued.event_id})
        return issued

    def _publish_issued(self, ticket: Ticket) -> None:
        event = cloud_event(
            "fr.genarchi.ticket.issued.v1",
            f"//genarchi/{self.platform}/worker",
            f"tickets/{ticket.id}",
            {
                "ticket_id": ticket.id,
                "order_id": ticket.order_id,
                "event_id": ticket.event_id,
                "qr_object": ticket.qr_object,
                "issued_at": ticket.issued_at.isoformat().replace("+00:00", "Z") if ticket.issued_at else None,
            },
        )
        try:
            self.publisher.publish(event)
        except Exception:  # la publication est un bonus (stats) : jamais bloquante
            log.warning("ticket.issued not published", exc_info=True, extra={"ticket_id": ticket.id})

    def issue_pending(self, older_than_seconds: int, limit: int) -> int:
        cutoff = domain.now() - timedelta(seconds=older_than_seconds)
        done = 0
        for ticket in self.store.list_pending(cutoff, limit):
            try:
                self.issue(ticket.id)
                done += 1
            except Exception:
                log.exception("issue failed", extra={"ticket_id": ticket.id})
        return done
