"""Store PostgreSQL (Platform 2). Toutes les garanties reposent sur des transactions ACID."""

from __future__ import annotations

import logging
from datetime import datetime
from importlib import resources

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .. import domain
from ..domain import Event, EventStats, Order, Problem, Ticket, TicketStatus

log = logging.getLogger("genarchi.postgres")
MIGRATION_LOCK = 4242_0001


def _event(r: dict) -> Event:
    return Event(
        r["id"],
        r["name"],
        r["venue"],
        r["starts_at"],
        r["sales_open_at"],
        r["capacity"],
        r["remaining"],
        r["price_cents"],
        r["created_at"],
    )


def _ticket(r: dict) -> Ticket:
    return Ticket(
        r["id"],
        r["order_id"],
        r["event_id"],
        TicketStatus(r["status"]),
        r["created_at"],
        r["qr_object"],
        r["issued_at"],
        r["scanned_at"],
    )


class PostgresStore:
    def __init__(self, dsn: str, min_size: int = 1, max_size: int = 10) -> None:
        # Timeouts du contrat : 2 s pour se connecter et pour chaque requête.
        self.pool = ConnectionPool(
            dsn,
            min_size=min_size,
            max_size=max_size,
            open=True,
            timeout=5,
            kwargs={
                "row_factory": dict_row,
                "connect_timeout": 2,
                "options": "-c statement_timeout=2000 -c lock_timeout=2000",
            },
        )

    def close(self) -> None:
        self.pool.close()

    def ping(self) -> None:
        with self.pool.connection(timeout=1) as c:
            c.execute("SELECT 1")

    def migrate(self) -> list[str]:
        applied = []
        with self.pool.connection() as c:
            c.execute("SELECT pg_advisory_lock(%s)", (MIGRATION_LOCK,))
            try:
                c.execute(
                    "CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY, "
                    "applied_at timestamptz NOT NULL DEFAULT now())"
                )
                done = {r["version"] for r in c.execute("SELECT version FROM schema_migrations")}
                files = sorted(p for p in resources.files("genarchi.migrations").iterdir() if p.name.endswith(".sql"))
                for f in files:
                    if f.name in done:
                        continue
                    with c.transaction():
                        c.execute(f.read_text())
                        c.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (f.name,))
                    applied.append(f.name)
            finally:
                c.execute("SELECT pg_advisory_unlock(%s)", (MIGRATION_LOCK,))
        return applied

    def create_event(self, event: Event) -> Event:
        with self.pool.connection() as c:
            c.execute(
                "INSERT INTO events (id, name, venue, starts_at, sales_open_at, capacity, remaining, "
                "price_cents, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    event.id,
                    event.name,
                    event.venue,
                    event.starts_at,
                    event.sales_open_at,
                    event.capacity,
                    event.remaining,
                    event.price_cents,
                    event.created_at,
                ),
            )
        return event

    def get_event(self, event_id: str) -> Event | None:
        with self.pool.connection() as c:
            r = c.execute("SELECT * FROM events WHERE id = %s", (event_id,)).fetchone()
        return _event(r) if r else None

    def list_events(self) -> list[Event]:
        with self.pool.connection() as c:
            rows = c.execute("SELECT * FROM events ORDER BY starts_at, id").fetchall()
        return [_event(r) for r in rows]

    def place_order(self, event_id, idempotency_key, buyer_email, quantity, request_hash):
        oid = domain.order_doc_id(event_id, idempotency_key)
        at = domain.now()
        with self.pool.connection() as c:
            try:
                with c.transaction():
                    event = c.execute("SELECT * FROM events WHERE id = %s", (event_id,)).fetchone()
                    if event is None:
                        raise Problem(404, "not_found", "événement introuvable")
                    # La contrainte UNIQUE (event_id, idempotency_key) sérialise deux requêtes avec la
                    # même clé : la seconde attend la première puis ne trouve rien à insérer.
                    inserted = c.execute(
                        "INSERT INTO orders (id, event_id, buyer_email, quantity, amount_cents, "
                        "idempotency_key, request_hash, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
                        "ON CONFLICT (event_id, idempotency_key) DO NOTHING RETURNING id",
                        (
                            oid,
                            event_id,
                            buyer_email,
                            quantity,
                            quantity * event["price_cents"],
                            idempotency_key,
                            request_hash,
                            at,
                        ),
                    ).fetchone()
                    if inserted is None:
                        raise _Replay()
                    # Décrément conditionnel : jamais de survente, même sous forte concurrence (I1).
                    updated = c.execute(
                        "UPDATE events SET remaining = remaining - %s WHERE id = %s AND remaining >= %s "
                        "AND now() >= sales_open_at AND now() < starts_at RETURNING remaining",
                        (quantity, event_id, quantity),
                    ).fetchone()
                    if updated is None:
                        fresh = _event(c.execute("SELECT * FROM events WHERE id = %s", (event_id,)).fetchone())
                        domain.check_sale_window(fresh, quantity)
                        raise Problem(409, "sold_out", "plus aucune place")
                    tickets = []
                    for _ in range(quantity):
                        t = Ticket(domain.new_id("tkt"), oid, event_id, TicketStatus.PENDING, at)
                        c.execute(
                            "INSERT INTO tickets (id, order_id, event_id, status, created_at) VALUES (%s,%s,%s,%s,%s)",
                            (t.id, oid, event_id, t.status.value, at),
                        )
                        tickets.append(t)
                order = Order(
                    oid,
                    event_id,
                    buyer_email,
                    quantity,
                    quantity * event["price_cents"],
                    idempotency_key,
                    request_hash,
                    at,
                    tickets,
                )
                return order, True
            except _Replay:
                existing = self.get_order(oid)
                if existing is None:  # pragma: no cover - la ligne vient d'être vue par la contrainte
                    raise Problem(503, "unavailable", "commande en cours d'écriture, réessayer") from None
                if existing.request_hash != request_hash:
                    raise Problem(409, "idempotency_conflict", "clé déjà utilisée avec un autre corps") from None
                return existing, False

    def get_order(self, order_id: str) -> Order | None:
        with self.pool.connection() as c:
            r = c.execute("SELECT * FROM orders WHERE id = %s", (order_id,)).fetchone()
            if r is None:
                return None
            ts = c.execute("SELECT * FROM tickets WHERE order_id = %s ORDER BY id", (order_id,)).fetchall()
        return Order(
            r["id"],
            r["event_id"],
            r["buyer_email"],
            r["quantity"],
            r["amount_cents"],
            r["idempotency_key"],
            r["request_hash"],
            r["created_at"],
            [_ticket(t) for t in ts],
        )

    def get_ticket(self, ticket_id: str) -> Ticket | None:
        with self.pool.connection() as c:
            r = c.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,)).fetchone()
        return _ticket(r) if r else None

    def list_pending(self, older_than: datetime, limit: int) -> list[Ticket]:
        with self.pool.connection() as c:
            rows = c.execute(
                "SELECT * FROM tickets WHERE status = 'pending' AND created_at <= %s ORDER BY created_at LIMIT %s",
                (older_than, limit),
            ).fetchall()
        return [_ticket(r) for r in rows]

    def mark_issued(self, ticket_id: str, qr_object: str, at: datetime) -> tuple[Ticket, bool]:
        with self.pool.connection() as c:
            r = c.execute(
                "UPDATE tickets SET status = 'issued', qr_object = %s, issued_at = %s "
                "WHERE id = %s AND status = 'pending' RETURNING *",
                (qr_object, at, ticket_id),
            ).fetchone()
            if r:
                return _ticket(r), True
            r = c.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,)).fetchone()
        if r is None:
            raise Problem(404, "not_found", "billet introuvable")
        return _ticket(r), False

    def mark_scanned(self, ticket_id: str, at: datetime) -> tuple[Ticket, bool]:
        with self.pool.connection() as c:
            r = c.execute(
                "UPDATE tickets SET status = 'scanned', scanned_at = %s "
                "WHERE id = %s AND status = 'issued' RETURNING *",
                (at, ticket_id),
            ).fetchone()
            if r:
                return _ticket(r), False
            r = c.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,)).fetchone()
        if r is None:
            raise Problem(404, "not_found", "billet introuvable")
        t = _ticket(r)
        if t.status == TicketStatus.PENDING:
            raise Problem(409, "ticket_not_issued", "billet pas encore émis")
        return t, True

    def stats(self, event_id: str) -> EventStats | None:
        e = self.get_event(event_id)
        if e is None:
            return None
        with self.pool.connection() as c:
            rows = c.execute(
                "SELECT status, count(*) AS n FROM tickets WHERE event_id = %s GROUP BY status", (event_id,)
            ).fetchall()
        n = {r["status"]: r["n"] for r in rows}
        return EventStats(
            event_id,
            e.capacity,
            e.capacity - e.remaining,
            e.remaining,
            n.get("pending", 0),
            n.get("issued", 0),
            n.get("scanned", 0),
        )


class _Replay(Exception):
    """Clé d'idempotence déjà utilisée : on relit la commande existante hors transaction."""


__all__ = ["PostgresStore", "psycopg"]
