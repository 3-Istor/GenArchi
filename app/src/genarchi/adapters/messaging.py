"""Messagerie : RabbitMQ (P2) et Pub/Sub (P3)."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable

log = logging.getLogger("genarchi.messaging")

EXCHANGE = "genarchi.events"
DLX = "genarchi.dlx"
QUEUE = "tickets.issue"
DLQ = "tickets.issue.dlq"
ROUTING_PURCHASED = "ticket.purchased"
MAX_DELIVERIES = 5


def declare_topology(channel) -> None:
    """Exchange + file quorum (répliquée sur les 3 nœuds) + dead-letter après 5 livraisons."""
    channel.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)
    channel.exchange_declare(DLX, exchange_type="fanout", durable=True)
    channel.queue_declare(DLQ, durable=True, arguments={"x-queue-type": "quorum"})
    channel.queue_bind(DLQ, DLX)
    channel.queue_declare(
        QUEUE,
        durable=True,
        arguments={
            "x-queue-type": "quorum",
            "x-delivery-limit": MAX_DELIVERIES,
            "x-dead-letter-exchange": DLX,
        },
    )
    channel.queue_bind(QUEUE, EXCHANGE, routing_key=ROUTING_PURCHASED)


def _connect(urls: list[str]):
    import pika

    last: Exception | None = None
    for url in urls:  # bascule sur le nœud suivant si le premier ne répond pas
        try:
            params = pika.URLParameters(url)
            params.socket_timeout = 2
            params.blocked_connection_timeout = 5
            params.heartbeat = 30
            return pika.BlockingConnection(params)
        except Exception as exc:
            last = exc
            log.warning("rabbitmq node unreachable", extra={"url": url.split("@")[-1]})
    raise ConnectionError(f"aucun nœud RabbitMQ joignable : {last}")


class RabbitPublisher:
    """Publication persistante avec accusé du broker (publisher confirms). Thread-safe."""

    def __init__(self, urls: list[str]) -> None:
        self.urls = urls
        self._lock = threading.Lock()
        self._conn = None
        self._chan = None

    def _channel(self):
        if self._chan is None or self._chan.is_closed:
            self._conn = _connect(self.urls)
            self._chan = self._conn.channel()
            self._chan.confirm_delivery()
            declare_topology(self._chan)
        return self._chan

    def publish(self, event: dict) -> None:
        import pika

        if event.get("type") != "fr.genarchi.ticket.purchased.v1":
            return  # seul l'achat circule sur le bus en P2
        body = json.dumps(event).encode()
        props = pika.BasicProperties(
            content_type="application/cloudevents+json",
            delivery_mode=2,
            message_id=event["id"],
            headers={"ce-type": event["type"]},
        )
        with self._lock:
            for attempt in (1, 2):
                try:
                    self._channel().basic_publish(EXCHANGE, ROUTING_PURCHASED, body, props, mandatory=True)
                    return
                except Exception:
                    self._chan = None
                    if attempt == 2:
                        raise

    def close(self) -> None:
        try:
            if self._conn and self._conn.is_open:
                self._conn.close()
        except Exception:
            log.debug("close failed", exc_info=True)


def consume_forever(urls: list[str], handle: Callable[[dict], None], stop: threading.Event | None = None) -> None:
    """Consomme `tickets.issue`. Ack après traitement ; nack + remise en file sinon (dead-letter à 5)."""
    stop = stop or threading.Event()
    while not stop.is_set():
        try:
            conn = _connect(urls)
            chan = conn.channel()
            declare_topology(chan)
            chan.basic_qos(prefetch_count=10)
            log.info("consumer connected", extra={"queue": QUEUE})
            for method, _props, body in chan.consume(QUEUE, inactivity_timeout=1):
                if stop.is_set():
                    break
                if method is None:
                    continue
                try:
                    handle(json.loads(body))
                    chan.basic_ack(method.delivery_tag)
                except Exception:
                    log.exception("message handling failed, requeued")
                    chan.basic_nack(method.delivery_tag, requeue=True)
            chan.cancel()
            conn.close()
        except Exception:
            log.warning("consumer disconnected, retrying in 2s", exc_info=True)
            time.sleep(2)


class PubSubPublisher:
    """Publie `ticket.issued` (P3), consommé par l'abonnement BigQuery."""

    def __init__(self, project: str, topic: str) -> None:
        from google.cloud import pubsub_v1

        self.client = pubsub_v1.PublisherClient()
        self.topic = self.client.topic_path(project, topic)

    def publish(self, event: dict) -> None:
        if event.get("type") != "fr.genarchi.ticket.issued.v1":
            return
        data = dict(event["data"], ce_id=event["id"], ce_time=event["time"])
        self.client.publish(self.topic, json.dumps(data).encode(), **{"ce-type": event["type"]}).result(timeout=5)

    def close(self) -> None:
        return None
