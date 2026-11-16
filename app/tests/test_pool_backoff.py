"""Reconnexion du pool PostgreSQL : jamais plus de 5 s entre deux tentatives, jamais d'abandon."""

import pytest

pytest.importorskip("psycopg_pool")

from genarchi.adapters.postgres import CappedAttempt


def test_backoff_is_capped_at_5s():
    a = CappedAttempt(timeout=float("inf"))
    delays = []
    for _ in range(10):
        a.update_delay(0.0)
        delays.append(a.delay)
    assert 0.9 <= delays[0] <= 1.1
    assert max(delays) == 5.0 and delays[-1] == 5.0
    assert not a.time_to_give_up(1e9)


def test_pool_module_uses_capped_attempt():
    import psycopg_pool.pool

    assert psycopg_pool.pool.AttemptWithBackoff is CappedAttempt
    # The swap only works while the pool still looks the name up when reconnecting.
    assert "AttemptWithBackoff" in psycopg_pool.pool.ConnectionPool._add_connection.__code__.co_names
