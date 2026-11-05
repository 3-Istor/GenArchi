"""Point d'entrée : `genarchi <sous-commande>` (contrat d'exécution, A1)."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from datetime import timedelta

from . import domain
from .config import get_settings
from .logs import setup
from .wiring import build

log = logging.getLogger("genarchi.cli")


def _container(process: str):
    try:
        s = get_settings()
    except Exception as exc:  # contrat : refuser de démarrer avec un message explicite
        print(f"configuration invalide : {exc}", file=sys.stderr)
        sys.exit(2)
    setup(s.log_level, s.platform, process, s.instance, s.firestore_project)
    return build(s)


def _serve(app, port: int) -> None:
    import uvicorn

    # timeout_graceful_shutdown : sortie en moins de 10 s après SIGTERM.
    uvicorn.run(
        app,
        host="0.0.0.0",  # noqa: S104 - écoute de conteneur ou de VM derrière un LB
        port=port,
        log_config=None,
        access_log=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
        timeout_graceful_shutdown=8,
    )


def cmd_serve_api(_a) -> None:
    from .api import create_app

    c = _container("api")
    _serve(create_app(c), c.settings.port)


def cmd_serve_worker(_a) -> None:
    from .worker import create_worker_app

    c = _container("worker")
    _serve(create_worker_app(c), c.settings.port)


def cmd_consume(_a) -> None:
    from .adapters.messaging import consume_forever

    c = _container("consumer")
    issuer = c.issuer()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())

    def handle(event: dict) -> None:
        for tid in event.get("data", {}).get("ticket_ids", []):
            issuer.issue(tid)

    consume_forever(c.settings.amqp_url_list, handle, stop)


def cmd_issue_pending(a) -> None:
    c = _container("issue-pending")
    n = c.issuer().issue_pending(a.older_than, a.limit)
    log.info("issue-pending done", extra={"issued": n})
    print(n)


def cmd_migrate(_a) -> None:
    c = _container("migrate")
    if hasattr(c.store, "migrate"):
        applied = c.store.migrate()
        log.info("migrations applied", extra={"applied": applied})
    else:
        log.info("nothing to migrate for this backend")


def cmd_seed(a) -> None:
    c = _container("seed")
    at = domain.now()
    e = domain.Event(
        domain.new_id("evt"),
        a.name,
        a.venue,
        at + timedelta(days=30),
        at - timedelta(minutes=1),
        a.capacity,
        a.capacity,
        a.price_cents,
        at,
    )
    c.store.create_event(e)
    print(e.id)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="genarchi")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("serve-api").set_defaults(fn=cmd_serve_api)
    sub.add_parser("serve-worker").set_defaults(fn=cmd_serve_worker)
    sub.add_parser("consume").set_defaults(fn=cmd_consume)
    ip = sub.add_parser("issue-pending")
    ip.add_argument("--older-than", type=int, default=120, help="âge minimal en secondes")
    ip.add_argument("--limit", type=int, default=500)
    ip.set_defaults(fn=cmd_issue_pending)
    sub.add_parser("migrate").set_defaults(fn=cmd_migrate)
    sd = sub.add_parser("seed")
    sd.add_argument("--name", default="Gala GenArchi")
    sd.add_argument("--venue", default="EPITA, Le Kremlin-Bicêtre")
    sd.add_argument("--capacity", type=int, default=5000)
    sd.add_argument("--price-cents", type=int, default=2500)
    sd.set_defaults(fn=cmd_seed)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
