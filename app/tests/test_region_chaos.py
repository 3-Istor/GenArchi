"""Panne de région P3 : drapeau chaos/<région> relu par /readyz (au plus toutes les 5 s)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from genarchi.adapters.memory import MemoryBlob, MemoryStore, NullPublisher
from genarchi.api import RegionFlag, create_app
from genarchi.cli import chaos_region
from genarchi.wiring import Container

from .conftest import _settings


def _client(store, region="europe-west1") -> TestClient:
    app = create_app(Container(_settings(region=region), store, MemoryBlob(), NullPublisher()))
    return TestClient(app, raise_server_exceptions=False)


def test_readyz_unready_while_own_region_flag_is_active():
    store = MemoryStore()
    chaos_region(store, "europe-west1", 600, datetime.now(UTC))
    r = _client(store).get("/readyz")
    assert r.status_code == 503 and r.json()["checks"]["chaos"] == "fail"


def test_readyz_ignores_other_region_and_expired_flags():
    other = MemoryStore()
    chaos_region(other, "europe-west4", 600, datetime.now(UTC))
    assert _client(other).get("/readyz").status_code == 200
    expired = MemoryStore()
    chaos_region(expired, "europe-west1", 600, datetime.now(UTC) - timedelta(seconds=601))
    assert _client(expired).get("/readyz").status_code == 200


def test_readyz_without_region_ignores_flags():
    store = MemoryStore()
    chaos_region(store, "europe-west1", 600, datetime.now(UTC))
    assert _client(store, region=None).get("/readyz").status_code == 200


def test_flag_read_error_keeps_api_ready():
    class Broken(MemoryStore):
        def unready_until(self, region):
            raise RuntimeError("firestore down")

    assert _client(Broken()).get("/readyz").status_code == 200


def test_malformed_flag_keeps_api_ready():
    store = MemoryStore()
    store.chaos["europe-west1"] = "2030-01-01T00:00:00Z"  # written by hand as a string
    assert _client(store).get("/readyz").status_code == 200


def test_read_error_keeps_an_active_flag():
    class Flaky(MemoryStore):
        fail = False

        def unready_until(self, region):
            if self.fail:
                raise RuntimeError("firestore blip")
            return super().unready_until(region)

    store, now = Flaky(), [100.0]
    chaos_region(store, "europe-west1", 600, datetime.now(UTC))
    flag = RegionFlag(store, "europe-west1", clock=lambda: now[0])
    assert flag.unready() is True
    store.fail, now[0] = True, now[0] + 5.0
    assert flag.unready() is True


def test_region_flag_rereads_at_most_every_5s():
    store, now = MemoryStore(), [100.0]
    flag = RegionFlag(store, "europe-west1", clock=lambda: now[0])
    assert flag.unready() is False
    chaos_region(store, "europe-west1", 600, datetime.now(UTC))
    now[0] += 4.9
    assert flag.unready() is False
    now[0] += 0.2
    assert flag.unready() is True


def test_store_roundtrip(store):
    if not hasattr(store, "set_unready_until"):
        pytest.skip("drapeau de région : P3 seulement")
    until = datetime(2030, 1, 1, tzinfo=UTC)
    assert store.unready_until("europe-west1") is None
    store.set_unready_until("europe-west1", until)
    assert store.unready_until("europe-west1") == until
    assert store.unready_until("europe-west4") is None
