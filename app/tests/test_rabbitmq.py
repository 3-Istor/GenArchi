"""Chaîne P2 complète : achat -> file quorum RabbitMQ -> consommateur -> QR émis."""

from __future__ import annotations

import os
import threading
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from genarchi.adapters.memory import MemoryBlob, MemoryStore
from genarchi.api import create_app
from genarchi.wiring import Container

from .conftest import _settings

pytestmark = pytest.mark.rabbitmq


@pytest.fixture
def amqp_url():
    url = os.environ.get("TEST_AMQP_URL")
    if not url:
        pytest.skip("TEST_AMQP_URL non défini")
    return url


def test_purchase_flows_through_rabbitmq(amqp_url):
    from genarchi.adapters.messaging import RabbitPublisher, consume_forever
    from genarchi.domain import Event, new_id, now

    settings = _settings(events_backend="rabbitmq", amqp_urls=f"amqp://bad-host:1/,{amqp_url}")
    store, blob = MemoryStore(), MemoryBlob()
    publisher = RabbitPublisher(settings.amqp_url_list)  # le premier nœud est injoignable : bascule
    c = Container(settings, store, blob, publisher)
    api = TestClient(create_app(c))
    at = now()
    from datetime import timedelta

    e = Event(new_id("evt"), "Gala", "EPITA", at + timedelta(days=1), at - timedelta(minutes=1), 10, 10, 100, at)
    store.create_event(e)
    r = api.post(
        f"/events/{e.id}/orders",
        json={"buyer_email": "a@b.co", "quantity": 3},
        headers={"Idempotency-Key": uuid.uuid4().hex},
    )
    assert r.status_code == 201
    ids = [t["id"] for t in r.json()["tickets"]]

    stop = threading.Event()
    issuer = c.issuer()

    def handle(event):
        for tid in event["data"]["ticket_ids"]:
            if store.get_ticket(tid):  # la file est partagée entre tests : ignorer les billets inconnus
                issuer.issue(tid)

    th = threading.Thread(target=consume_forever, args=(settings.amqp_url_list, handle, stop), daemon=True)
    th.start()
    deadline = time.time() + 20
    while time.time() < deadline and {api.get(f"/tickets/{i}").json()["status"] for i in ids} != {"issued"}:
        time.sleep(0.2)
    stop.set()
    th.join(timeout=5)
    publisher.close()
    assert {api.get(f"/tickets/{i}").json()["status"] for i in ids} == {"issued"}
