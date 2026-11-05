"""Modèle de domaine et règles métier (contracts/domain/model.md).

Aucune dépendance vers un backend : tout passe par les ports définis dans ports.py.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


def now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    # uuid4 : 122 bits d'aléa, conforme à l'exigence « non devinable » des billets.
    return f"{prefix}_{uuid.uuid4().hex}"


class EventStatus(StrEnum):
    SCHEDULED = "scheduled"
    ON_SALE = "on_sale"
    SOLD_OUT = "sold_out"
    CLOSED = "closed"


class TicketStatus(StrEnum):
    PENDING = "pending"
    ISSUED = "issued"
    SCANNED = "scanned"


@dataclass
class Event:
    id: str
    name: str
    venue: str
    starts_at: datetime
    sales_open_at: datetime
    capacity: int
    remaining: int
    price_cents: int
    created_at: datetime
    currency: str = "EUR"

    def status(self, at: datetime | None = None) -> EventStatus:
        at = at or now()
        if at >= self.starts_at:
            return EventStatus.CLOSED
        if self.remaining <= 0:
            return EventStatus.SOLD_OUT
        if at >= self.sales_open_at:
            return EventStatus.ON_SALE
        return EventStatus.SCHEDULED


@dataclass
class Ticket:
    id: str
    order_id: str
    event_id: str
    status: TicketStatus
    created_at: datetime
    qr_object: str | None = None
    issued_at: datetime | None = None
    scanned_at: datetime | None = None


@dataclass
class Order:
    id: str
    event_id: str
    buyer_email: str
    quantity: int
    amount_cents: int
    idempotency_key: str
    request_hash: str
    created_at: datetime
    tickets: list[Ticket] = field(default_factory=list)
    status: str = "confirmed"


@dataclass
class EventStats:
    event_id: str
    capacity: int
    sold: int
    remaining: int
    pending: int
    issued: int
    scanned: int


class Problem(Exception):
    """Erreur métier, traduite en application/problem+json (RFC 9457)."""

    def __init__(self, status: int, code: str, detail: str = "", **extra: object) -> None:
        super().__init__(detail or code)
        self.status = status
        self.code = code
        self.detail = detail
        self.extra = extra


def order_request_hash(event_id: str, buyer_email: str, quantity: int) -> str:
    payload = json.dumps({"e": event_id, "b": buyer_email.lower(), "q": quantity}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def order_doc_id(event_id: str, idempotency_key: str) -> str:
    """Identifiant déterministe d'une commande : la clé d'idempotence garantit l'unicité (I2)."""
    return "ord_" + hashlib.sha256(f"{event_id}\x00{idempotency_key}".encode()).hexdigest()[:32]


def qr_object_key(event_id: str, ticket_id: str) -> str:
    """Clé déterministe du QR : émettre deux fois écrit le même objet (I5)."""
    return f"tickets/{event_id}/{ticket_id}.png"


def check_sale_window(event: Event, quantity: int, at: datetime | None = None) -> None:
    at = at or now()
    if at >= event.starts_at:
        raise Problem(409, "event_closed", "l'événement a commencé")
    if at < event.sales_open_at:
        raise Problem(409, "sales_not_open", "les ventes ne sont pas encore ouvertes")
    if event.remaining <= 0:
        raise Problem(409, "sold_out", "plus aucune place")
    if event.remaining < quantity:
        raise Problem(409, "insufficient_stock", f"il reste {event.remaining} place(s)", remaining=event.remaining)


def constant_time_equals(a: str, b: str) -> bool:
    return secrets.compare_digest(a.encode(), b.encode())
