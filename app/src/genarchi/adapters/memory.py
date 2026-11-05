"""Adaptateurs en mémoire, pour les tests unitaires (DATA_BACKEND=memory)."""

from __future__ import annotations

import threading
from dataclasses import replace
from datetime import datetime

from .. import domain
from ..domain import Event, EventStats, Order, Problem, Ticket, TicketStatus


class MemoryStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.events: dict[str, Event] = {}
        self.orders: dict[str, Order] = {}
        self.tickets: dict[str, Ticket] = {}

    def ping(self) -> None:
        return None

    def create_event(self, event: Event) -> Event:
        with self._lock:
            self.events[event.id] = replace(event)
        return event

    def get_event(self, event_id: str) -> Event | None:
        with self._lock:
            e = self.events.get(event_id)
            return replace(e) if e else None

    def list_events(self) -> list[Event]:
        with self._lock:
            return sorted((replace(e) for e in self.events.values()), key=lambda e: (e.starts_at, e.id))

    def place_order(self, event_id, idempotency_key, buyer_email, quantity, request_hash):
        oid = domain.order_doc_id(event_id, idempotency_key)
        with self._lock:
            existing = self.orders.get(oid)
            if existing:
                if existing.request_hash != request_hash:
                    raise Problem(409, "idempotency_conflict", "clé déjà utilisée avec un autre corps")
                return self._order_copy(existing), False
            event = self.events.get(event_id)
            if event is None:
                raise Problem(404, "not_found", "événement introuvable")
            domain.check_sale_window(event, quantity)
            event.remaining -= quantity
            at = domain.now()
            order = Order(
                oid, event_id, buyer_email, quantity, quantity * event.price_cents, idempotency_key, request_hash, at
            )
            for _ in range(quantity):
                t = Ticket(domain.new_id("tkt"), oid, event_id, TicketStatus.PENDING, at)
                self.tickets[t.id] = t
                order.tickets.append(t)
            self.orders[oid] = order
            return self._order_copy(order), True

    def _order_copy(self, order: Order) -> Order:
        return replace(order, tickets=[replace(self.tickets[t.id]) for t in order.tickets])

    def get_order(self, order_id: str) -> Order | None:
        with self._lock:
            o = self.orders.get(order_id)
            return self._order_copy(o) if o else None

    def get_ticket(self, ticket_id: str) -> Ticket | None:
        with self._lock:
            t = self.tickets.get(ticket_id)
            return replace(t) if t else None

    def list_pending(self, older_than: datetime, limit: int) -> list[Ticket]:
        with self._lock:
            pending = [
                t for t in self.tickets.values() if t.status == TicketStatus.PENDING and t.created_at <= older_than
            ]
            return [replace(t) for t in sorted(pending, key=lambda t: t.created_at)[:limit]]

    def mark_issued(self, ticket_id: str, qr_object: str, at: datetime) -> tuple[Ticket, bool]:
        with self._lock:
            t = self.tickets[ticket_id]
            if t.status != TicketStatus.PENDING:
                return replace(t), False
            t.status, t.qr_object, t.issued_at = TicketStatus.ISSUED, qr_object, at
            return replace(t), True

    def mark_scanned(self, ticket_id: str, at: datetime) -> tuple[Ticket, bool]:
        with self._lock:
            t = self.tickets.get(ticket_id)
            if t is None:
                raise Problem(404, "not_found", "billet introuvable")
            if t.status == TicketStatus.PENDING:
                raise Problem(409, "ticket_not_issued", "billet pas encore émis")
            if t.status == TicketStatus.SCANNED:
                return replace(t), True
            t.status, t.scanned_at = TicketStatus.SCANNED, at
            return replace(t), False

    def stats(self, event_id: str) -> EventStats | None:
        with self._lock:
            e = self.events.get(event_id)
            if e is None:
                return None
            ts = [t for t in self.tickets.values() if t.event_id == event_id]
            count = lambda s: sum(1 for t in ts if t.status == s)  # noqa: E731
            return EventStats(
                event_id,
                e.capacity,
                e.capacity - e.remaining,
                e.remaining,
                count(TicketStatus.PENDING),
                count(TicketStatus.ISSUED),
                count(TicketStatus.SCANNED),
            )

    def close(self) -> None:
        return None


class MemoryBlob:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    def get(self, key: str) -> bytes | None:
        return self.objects.get(key)

    def signed_url(self, key: str, ttl_seconds: int) -> str | None:
        return None


class NullPublisher:
    def __init__(self) -> None:
        self.published: list[dict] = []

    def publish(self, event: dict) -> None:
        self.published.append(event)

    def close(self) -> None:
        return None
