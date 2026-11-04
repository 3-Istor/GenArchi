"""Sondes, chaos et worker : ce dont les plateformes et les tests de résilience ont besoin."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from genarchi.adapters.memory import MemoryBlob, MemoryStore, NullPublisher
from genarchi.api import create_app
from genarchi.wiring import Container
from genarchi.worker import create_worker_app, ticket_id_from_event

from .conftest import ADMIN, _settings, auth


def test_readyz_and_forced_unready():
    ok = TestClient(create_app(Container(_settings(), MemoryStore(), MemoryBlob(), NullPublisher())))
    assert ok.get("/readyz").status_code == 200
    down = TestClient(
        create_app(Container(_settings(chaos_force_unready=True), MemoryStore(), MemoryBlob(), NullPublisher()))
    )
    assert down.get("/readyz").status_code == 503 and down.get("/healthz").status_code == 200


def test_chaos_unready_and_disabled():
    c = TestClient(create_app(Container(_settings(), MemoryStore(), MemoryBlob(), NullPublisher())))
    assert c.post("/internal/chaos", json={"mode": "unready", "duration_s": 30}, headers=auth(ADMIN)).status_code == 202
    assert c.get("/readyz").status_code == 503
    off = TestClient(
        create_app(Container(_settings(chaos_enabled=False), MemoryStore(), MemoryBlob(), NullPublisher()))
    )
    assert off.post("/internal/chaos", json={"mode": "unready"}, headers=auth(ADMIN)).status_code == 404


def test_worker_handles_eventarc_binary_event(make_event, container):
    from .test_contract import buy

    api = TestClient(create_app(container))
    e = make_event()
    tid = buy(api, e.id).json()["tickets"][0]["id"]
    w = TestClient(create_worker_app(container))
    headers = {
        "ce-type": "google.cloud.firestore.document.v1.created",
        "ce-id": uuid.uuid4().hex,
        "ce-subject": f"documents/tickets/{tid}",
        "content-type": "application/json",
    }
    assert w.post("/internal/events/ticket-created", content=b"{}", headers=headers).status_code == 204
    assert api.get(f"/tickets/{tid}").json()["status"] == "issued"
    # Relivraison (at-least-once) : sans effet.
    assert w.post("/internal/events/ticket-created", content=b"{}", headers=headers).status_code == 204


def test_ticket_id_parsing():
    assert ticket_id_from_event({"ce-subject": "documents/tickets/tkt_1"}, b"") == "tkt_1"
    assert ticket_id_from_event({}, b'{"subject": "tickets/tkt_2"}') == "tkt_2"
    assert ticket_id_from_event({"ce-subject": "documents/orders/x"}, b"") is None


def test_settings_refuse_missing_backend_config():
    import pytest

    with pytest.raises(ValueError, match="DATABASE_URL"):
        _settings(data_backend="postgres")
