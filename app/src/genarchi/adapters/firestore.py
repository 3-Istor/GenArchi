"""Store Firestore (Platform 3).

Le stock d'un événement est réparti sur N « shards » (events/{id}/stock/{k}) : un achat ne
verrouille qu'un shard, ce qui évite le document chaud lors de l'ouverture des ventes. Les
garanties I1 (pas de survente) et I2 (idempotence) restent assurées par les transactions.
"""

from __future__ import annotations

import logging
import random
import time
from datetime import datetime

from google.api_core import exceptions as gexc
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from .. import domain
from ..domain import Event, EventStats, Order, Problem, Ticket, TicketStatus

log = logging.getLogger("genarchi.firestore")
TX_ATTEMPTS = 25
CAS_ATTEMPTS = 40


def shard_count(capacity: int) -> int:
    """Un shard par tranche de 10 places, entre 1 et 32 : assez pour absorber l'ouverture des ventes."""
    return max(1, min(32, capacity // 10))


def _ticket(d: dict, tid: str) -> Ticket:
    return Ticket(
        tid,
        d["order_id"],
        d["event_id"],
        TicketStatus(d["status"]),
        d["created_at"],
        d.get("qr_object"),
        d.get("issued_at"),
        d.get("scanned_at"),
    )


class FirestoreStore:
    def __init__(self, project: str, database: str = "(default)") -> None:
        self.db = firestore.Client(project=project, database=database)

    def close(self) -> None:
        self.db.close()

    def ping(self) -> None:
        self.db.collection("events").limit(1).get(timeout=2)

    # --- événements -------------------------------------------------------------------------------
    def _stock(self, event_id: str):
        return self.db.collection("events").document(event_id).collection("stock")

    def _remaining(self, event_id: str, shards: int) -> int:
        refs = [self._stock(event_id).document(str(k)) for k in range(shards)]
        return sum((s.to_dict() or {}).get("remaining", 0) for s in self.db.get_all(refs))

    def _event(self, snap) -> Event:
        d = snap.to_dict()
        return Event(
            snap.id,
            d["name"],
            d["venue"],
            d["starts_at"],
            d["sales_open_at"],
            d["capacity"],
            self._remaining(snap.id, d["shards"]),
            d["price_cents"],
            d["created_at"],
        )

    def create_event(self, event: Event) -> Event:
        n = shard_count(event.capacity)
        batch = self.db.batch()
        batch.set(
            self.db.collection("events").document(event.id),
            {
                "name": event.name,
                "venue": event.venue,
                "starts_at": event.starts_at,
                "sales_open_at": event.sales_open_at,
                "capacity": event.capacity,
                "price_cents": event.price_cents,
                "created_at": event.created_at,
                "shards": n,
            },
        )
        base, extra = divmod(event.remaining, n)
        for k in range(n):
            batch.set(self._stock(event.id).document(str(k)), {"remaining": base + (1 if k < extra else 0)})
        batch.commit()
        return event

    def get_event(self, event_id: str) -> Event | None:
        snap = self.db.collection("events").document(event_id).get()
        return self._event(snap) if snap.exists else None

    def list_events(self) -> list[Event]:
        snaps = self.db.collection("events").order_by("starts_at").stream()
        return sorted((self._event(s) for s in snaps), key=lambda e: (e.starts_at, e.id))

    # --- achat --------------------------------------------------------------------------------------
    def place_order(self, event_id, idempotency_key, buyer_email, quantity, request_hash):
        """Achat sans verrou (compare-and-swap) : lecture des shards, puis un lot atomique conditionné.

        - chaque shard est mis à jour à condition de ne pas avoir changé depuis sa lecture ;
        - la commande est *créée* (condition « n'existe pas ») : une clé d'idempotence rejouée échoue
          proprement et l'on relit la commande existante (I2) ;
        - un conflit sur un shard relance l'algorithme sur un autre shard (I1 : jamais de survente).
        """
        oid = domain.order_doc_id(event_id, idempotency_key)
        order_ref = self.db.collection("orders").document(oid)
        replay = self._replay(oid, request_hash)
        if replay:
            return replay, False
        ev = self.db.collection("events").document(event_id).get()
        if not ev.exists:
            raise Problem(404, "not_found", "événement introuvable")
        e = ev.to_dict()  # immuable après création : dates, prix, nombre de shards
        at = domain.now()
        if at >= e["starts_at"]:
            raise Problem(409, "event_closed", "l'événement a commencé")
        if at < e["sales_open_at"]:
            raise Problem(409, "sales_not_open", "les ventes ne sont pas encore ouvertes")
        amount = quantity * e["price_cents"]
        refs = [self._stock(event_id).document(str(k)) for k in range(e["shards"])]

        for attempt in range(CAS_ATTEMPTS):
            snaps = [sn for sn in self.db.get_all(refs) if sn.exists]
            left = {sn.id: (sn, (sn.to_dict() or {}).get("remaining", 0)) for sn in snaps}
            total = sum(v for _, v in left.values())
            if total == 0:
                raise Problem(409, "sold_out", "plus aucune place")
            if total < quantity:
                raise Problem(409, "insufficient_stock", f"il reste {total} place(s)", remaining=total)
            take = self._pick(left, quantity)

            tickets = [Ticket(domain.new_id("tkt"), oid, event_id, TicketStatus.PENDING, at) for _ in range(quantity)]
            batch = self.db.batch()
            for sn, n in take:
                batch.update(
                    sn.reference,
                    {"remaining": left[sn.id][1] - n},
                    option=self.db.write_option(last_update_time=sn.update_time),
                )
            batch.create(
                order_ref,
                {
                    "event_id": event_id,
                    "buyer_email": buyer_email,
                    "quantity": quantity,
                    "amount_cents": amount,
                    "idempotency_key": idempotency_key,
                    "request_hash": request_hash,
                    "created_at": at,
                    "ticket_ids": [t.id for t in tickets],
                },
            )
            for t in tickets:
                batch.create(
                    self.db.collection("tickets").document(t.id),
                    {
                        "order_id": oid,
                        "event_id": event_id,
                        "status": t.status.value,
                        "created_at": at,
                        "qr_object": None,
                        "issued_at": None,
                        "scanned_at": None,
                    },
                )
            try:
                batch.commit()
                return Order(
                    oid, event_id, buyer_email, quantity, amount, idempotency_key, request_hash, at, tickets
                ), True
            except gexc.Conflict:  # la commande existe déjà : rejeu concurrent de la même clé
                replay = self._replay(oid, request_hash)
                if replay:
                    return replay, False
            except (gexc.FailedPrecondition, gexc.Aborted):  # un shard a bougé : on relit et on recommence
                time.sleep(random.uniform(0, 0.02) * (attempt + 1))
        raise Problem(503, "unavailable", "trop de concurrence, réessayer")

    @staticmethod
    def _pick(left: dict, quantity: int) -> list[tuple[object, int]]:
        """Un shard au hasard parmi ceux qui suffisent ; sinon plusieurs shards (stock fragmenté)."""
        enough = [sn for sn, v in left.values() if v >= quantity]
        if enough:
            return [(random.choice(enough), quantity)]
        take, need = [], quantity
        for sn, v in sorted(left.values(), key=lambda x: -x[1]):
            if need == 0:
                break
            if v:
                n = min(v, need)
                take.append((sn, n))
                need -= n
        return take

    def _replay(self, oid: str, request_hash: str) -> Order | None:
        existing = self.get_order(oid)
        if existing is None:
            return None
        if existing.request_hash != request_hash:
            raise Problem(409, "idempotency_conflict", "clé déjà utilisée avec un autre corps")
        return existing

    def _order_from(self, oid: str, d: dict, tickets: list[Ticket] | None) -> Order:
        return Order(
            oid,
            d["event_id"],
            d["buyer_email"],
            d["quantity"],
            d["amount_cents"],
            d["idempotency_key"],
            d["request_hash"],
            d["created_at"],
            tickets or [],
        )

    def get_order(self, order_id: str) -> Order | None:
        snap = self.db.collection("orders").document(order_id).get()
        if not snap.exists:
            return None
        d = snap.to_dict()
        refs = [self.db.collection("tickets").document(t) for t in d.get("ticket_ids", [])]
        tickets = [_ticket(s.to_dict(), s.id) for s in self.db.get_all(refs) if s.exists]
        return self._order_from(order_id, d, sorted(tickets, key=lambda t: t.id))

    # --- billets ------------------------------------------------------------------------------------
    def get_ticket(self, ticket_id: str) -> Ticket | None:
        snap = self.db.collection("tickets").document(ticket_id).get()
        return _ticket(snap.to_dict(), snap.id) if snap.exists else None

    def list_pending(self, older_than: datetime, limit: int) -> list[Ticket]:
        q = (
            self.db.collection("tickets")
            .where(filter=FieldFilter("status", "==", "pending"))
            .where(filter=FieldFilter("created_at", "<=", older_than))
            .order_by("created_at")
            .limit(limit)
        )
        return [_ticket(s.to_dict(), s.id) for s in q.stream()]

    def mark_issued(self, ticket_id: str, qr_object: str, at: datetime) -> tuple[Ticket, bool]:
        ref = self.db.collection("tickets").document(ticket_id)

        @firestore.transactional
        def run(tx):
            snap = ref.get(transaction=tx)
            if not snap.exists:
                raise Problem(404, "not_found", "billet introuvable")
            d = snap.to_dict()
            if d["status"] != TicketStatus.PENDING.value:
                return _ticket(d, ticket_id), False
            d.update(status=TicketStatus.ISSUED.value, qr_object=qr_object, issued_at=at)
            tx.update(ref, {"status": d["status"], "qr_object": qr_object, "issued_at": at})
            return _ticket(d, ticket_id), True

        return run(self.db.transaction(max_attempts=TX_ATTEMPTS))

    def mark_scanned(self, ticket_id: str, at: datetime) -> tuple[Ticket, bool]:
        ref = self.db.collection("tickets").document(ticket_id)

        @firestore.transactional
        def run(tx):
            snap = ref.get(transaction=tx)
            if not snap.exists:
                raise Problem(404, "not_found", "billet introuvable")
            d = snap.to_dict()
            if d["status"] == TicketStatus.PENDING.value:
                raise Problem(409, "ticket_not_issued", "billet pas encore émis")
            if d["status"] == TicketStatus.SCANNED.value:
                return _ticket(d, ticket_id), True
            d.update(status=TicketStatus.SCANNED.value, scanned_at=at)
            tx.update(ref, {"status": d["status"], "scanned_at": at})
            return _ticket(d, ticket_id), False

        return run(self.db.transaction(max_attempts=TX_ATTEMPTS))

    def stats(self, event_id: str) -> EventStats | None:
        e = self.get_event(event_id)
        if e is None:
            return None

        def count(status: str) -> int:
            q = (
                self.db.collection("tickets")
                .where(filter=FieldFilter("event_id", "==", event_id))
                .where(filter=FieldFilter("status", "==", status))
            )
            return int(q.count().get()[0][0].value)

        return EventStats(
            event_id,
            e.capacity,
            e.capacity - e.remaining,
            e.remaining,
            count("pending"),
            count("issued"),
            count("scanned"),
        )
