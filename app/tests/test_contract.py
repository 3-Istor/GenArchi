"""Tests de contrat C1 à C13 (contracts/tests/acceptance.md), sur chaque backend."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from openapi_core.testing import MockRequest, MockResponse

from genarchi import CONTRACT_VERSION

from .conftest import ADMIN, STAFF, auth


def key() -> str:
    return uuid.uuid4().hex


def check(spec, method: str, path: str, resp, path_pattern: str | None = None) -> None:
    """C1 : chaque réponse est conforme à contracts/api/openapi.yaml."""
    req = MockRequest("http://localhost:8080", method.lower(), path)
    mime = resp.headers.get("content-type", "application/json").split(";")[0]
    spec.validate_response(req, MockResponse(resp.content, status_code=resp.status_code, content_type=mime))


def buy(client, event_id: str, qty: int = 1, k: str | None = None, email: str = "alice@example.com"):
    return client.post(
        f"/events/{event_id}/orders",
        json={"buyer_email": email, "quantity": qty},
        headers={"Idempotency-Key": k or key()},
    )


def test_c2_version(client, openapi_spec):
    r = client.get("/version")
    assert r.status_code == 200 and r.json()["contract_version"] == CONTRACT_VERSION
    check(openapi_spec, "get", "/version", r)


def test_c3_create_and_buy(client, make_event, openapi_spec):
    e = make_event(capacity=10)
    r = buy(client, e.id, qty=2)
    assert r.status_code == 201, r.text
    check(openapi_spec, "post", f"/events/{e.id}/orders", r)
    body = r.json()
    assert body["quantity"] == 2 and body["amount_cents"] == 5000
    assert [t["status"] for t in body["tickets"]] == ["pending", "pending"]
    ev = client.get(f"/events/{e.id}")
    check(openapi_spec, "get", f"/events/{e.id}", ev)
    assert ev.json()["remaining"] == 8
    lst = client.get("/events")
    check(openapi_spec, "get", "/events", lst)
    assert any(x["id"] == e.id for x in lst.json()["items"])


def test_c4_no_overselling_under_concurrency(client, make_event):
    # C4 : capacité 100, 200 achats d'un billet en parallèle -> exactement 100 succès.
    e = make_event(capacity=100)
    with ThreadPoolExecutor(max_workers=25) as pool:
        codes = list(pool.map(lambda _: buy(client, e.id).status_code, range(200)))
    assert codes.count(201) == 100, codes
    assert codes.count(409) == 100
    assert client.get(f"/events/{e.id}").json()["remaining"] == 0
    stats = client.get(f"/admin/events/{e.id}/stats", headers=auth(ADMIN)).json()
    assert stats["sold"] == 100 and stats["tickets"]["pending"] == 100


def test_c5_idempotent_purchase_in_parallel(client, make_event):
    e = make_event(capacity=10)
    k = key()
    with ThreadPoolExecutor(max_workers=5) as pool:
        resps = list(pool.map(lambda _: buy(client, e.id, qty=2, k=k), range(5)))
    assert sorted(r.status_code for r in resps) == [200, 200, 200, 200, 201]
    assert len({r.json()["id"] for r in resps}) == 1
    assert client.get(f"/events/{e.id}").json()["remaining"] == 8


def test_c6_c7_idempotency_errors(client, make_event, openapi_spec):
    e = make_event()
    k = key()
    assert buy(client, e.id, qty=1, k=k).status_code == 201
    r = buy(client, e.id, qty=3, k=k)
    assert r.status_code == 409 and r.json()["code"] == "idempotency_conflict"
    check(openapi_spec, "post", f"/events/{e.id}/orders", r)
    r = client.post(f"/events/{e.id}/orders", json={"buyer_email": "a@b.co", "quantity": 1})
    assert r.status_code == 400 and r.json()["code"] == "idempotency_key_required"
    check(openapi_spec, "post", f"/events/{e.id}/orders", r)


def test_c8_c9_c10_issue_qr_and_scan(client, container, make_event, openapi_spec):
    e = make_event()
    t = buy(client, e.id).json()["tickets"][0]
    r = client.post(f"/tickets/{t['id']}/scan", headers=auth(STAFF))
    assert r.status_code == 409 and r.json()["code"] == "ticket_not_issued"  # C10
    r = client.get(f"/tickets/{t['id']}/qr")
    assert r.status_code == 409 and r.headers["retry-after"]
    container.issuer().issue(t["id"])
    got = client.get(f"/tickets/{t['id']}")
    check(openapi_spec, "get", f"/tickets/{t['id']}", got)
    assert got.json()["status"] == "issued" and got.json()["qr_url"]
    qr = client.get(f"/tickets/{t['id']}/qr")
    assert qr.status_code == 200 and qr.content[:8] == b"\x89PNG\r\n\x1a\n"  # C8
    first = client.post(f"/tickets/{t['id']}/scan", headers=auth(STAFF))
    assert first.status_code == 200 and first.json()["status"] == "scanned"
    check(openapi_spec, "post", f"/tickets/{t['id']}/scan", first)
    second = client.post(f"/tickets/{t['id']}/scan", headers=auth(STAFF))
    assert second.status_code == 409 and second.json()["code"] == "already_scanned"  # C9
    assert second.json()["scanned_at"] == first.json()["scanned_at"]


def test_c11_sales_window(client, make_event):
    early = make_event(opens_in=timedelta(hours=1))
    assert buy(client, early.id).json()["code"] == "sales_not_open"
    soon = make_event(starts_in=timedelta(seconds=1), opens_in=-timedelta(hours=1))
    import time

    time.sleep(1.2)
    assert buy(client, soon.id).json()["code"] == "event_closed"


def test_c12_auth_required(client, make_event, openapi_spec):
    e = make_event()
    r = client.get(f"/admin/events/{e.id}/stats")
    assert r.status_code == 401 and r.json()["code"] == "unauthorized"
    check(openapi_spec, "get", f"/admin/events/{e.id}/stats", r)
    t = buy(client, e.id).json()["tickets"][0]
    assert client.post(f"/tickets/{t['id']}/scan", headers=auth("wrong-token")).status_code == 401
    future = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    body = {
        "name": "X",
        "venue": "Y",
        "starts_at": future,
        "sales_open_at": datetime.now(UTC).isoformat(),
        "capacity": 5,
        "price_cents": 0,
    }
    assert client.post("/events", json=body).status_code == 401
    created = client.post("/events", json=body, headers=auth(ADMIN))
    assert created.status_code == 201
    check(openapi_spec, "post", "/events", created)


def test_c13_issuing_is_idempotent(client, container, make_event):
    e = make_event()
    tid = buy(client, e.id).json()["tickets"][0]["id"]
    issuer = container.issuer()
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda _: issuer.issue(tid), range(3)))
    first = client.get(f"/tickets/{tid}").json()["issued_at"]
    issuer.issue(tid)
    assert client.get(f"/tickets/{tid}").json()["issued_at"] == first
    published = [p for p in container.publisher.published if p["type"] == "fr.genarchi.ticket.issued.v1"]
    assert len(published) == 1


def test_insufficient_stock_and_sold_out(client, make_event):
    e = make_event(capacity=3)
    assert buy(client, e.id, qty=2).status_code == 201
    r = buy(client, e.id, qty=2)
    assert r.json()["code"] == "insufficient_stock" and r.json()["remaining"] == 1
    assert buy(client, e.id, qty=1).status_code == 201
    assert buy(client, e.id).json()["code"] == "sold_out"


def test_issue_pending_catches_up(container, client, make_event):
    e = make_event()
    ids = [t["id"] for t in buy(client, e.id, qty=3).json()["tickets"]]
    assert container.issuer().issue_pending(older_than_seconds=0, limit=10) == 3
    assert {client.get(f"/tickets/{i}").json()["status"] for i in ids} == {"issued"}


@pytest.mark.parametrize(
    "body",
    [
        {"buyer_email": "pas-un-email", "quantity": 1},
        {"buyer_email": "a@b.co", "quantity": 5},
        {"buyer_email": "a@b.co", "quantity": 1, "extra": True},
    ],
)
def test_validation_errors(client, make_event, openapi_spec, body):
    e = make_event()
    r = client.post(f"/events/{e.id}/orders", json=body, headers={"Idempotency-Key": key()})
    assert r.status_code == 422 and r.json()["code"] == "validation_error"
    check(openapi_spec, "post", f"/events/{e.id}/orders", r)
