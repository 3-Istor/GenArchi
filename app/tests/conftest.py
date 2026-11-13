"""Fixtures : la même suite tourne sur chaque backend disponible (contrat d'exécution, A4)."""

from __future__ import annotations

import os
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from genarchi import domain
from genarchi.adapters.memory import MemoryBlob, MemoryStore, NullPublisher
from genarchi.api import create_app
from genarchi.config import Settings
from genarchi.wiring import Container

ADMIN, STAFF = "admin-token-test", "staff-token-test"
OPENAPI = Path(__file__).resolve().parents[2] / "contracts" / "api" / "openapi.yaml"


def _settings(**kw) -> Settings:
    base = dict(
        platform="local",
        public_base_url="http://testserver",
        data_backend="memory",
        blob_backend="memory",
        events_backend="none",
        admin_token=ADMIN,
        staff_token=STAFF,
        chaos_enabled=True,
    )
    base.update(kw)
    return Settings(**base)


def _postgres_store():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL non défini")
    from genarchi.adapters.postgres import PostgresStore

    store = PostgresStore(url)
    store.migrate()
    with store.pool.connection() as c:
        c.execute("TRUNCATE tickets, orders, events CASCADE")
    return store


def _firestore_store():
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        pytest.skip("FIRESTORE_EMULATOR_HOST non défini")
    from genarchi.adapters.firestore import FirestoreStore

    # Un projet par test : isolation totale dans l'émulateur.
    return FirestoreStore(f"test-{uuid.uuid4().hex[:10]}")


BACKENDS = {"memory": MemoryStore, "postgres": _postgres_store, "firestore": _firestore_store}


@pytest.fixture(params=list(BACKENDS), ids=list(BACKENDS))
def store(request):
    s = BACKENDS[request.param]()
    yield s
    s.close()


@pytest.fixture
def container(store) -> Container:
    return Container(_settings(), store, MemoryBlob(), NullPublisher())


@pytest.fixture
def client(container) -> TestClient:
    return TestClient(create_app(container), raise_server_exceptions=False)


@pytest.fixture(scope="session")
def openapi_spec():
    import json

    from openapi_core import Config, OpenAPI

    config = Config(extra_media_type_deserializers={"application/problem+json": json.loads})
    return OpenAPI.from_dict(yaml.safe_load(OPENAPI.read_text()), config=config)


@pytest.fixture
def make_event(container):
    def _make(
        capacity: int = 100,
        opens_in: timedelta = -timedelta(minutes=1),
        starts_in: timedelta = timedelta(days=10),
        price_cents: int = 2500,
    ) -> domain.Event:
        at = domain.now()
        e = domain.Event(
            domain.new_id("evt"), "Gala", "EPITA", at + starts_in, at + opens_in, capacity, capacity, price_cents, at
        )
        container.store.create_event(e)
        return e

    return _make


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
