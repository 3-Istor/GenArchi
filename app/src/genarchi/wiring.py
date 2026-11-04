"""Assemble les adaptateurs selon la configuration."""

from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .ports import BlobStore, Publisher, Store
from .services import TicketIssuer


@dataclass
class Container:
    settings: Settings
    store: Store
    blob: BlobStore
    publisher: Publisher

    def issuer(self, publisher: Publisher | None = None) -> TicketIssuer:
        return TicketIssuer(
            self.store, self.blob, publisher or self.publisher, self.settings.public_base_url, self.settings.platform
        )

    def close(self) -> None:
        self.publisher.close()
        self.store.close()


def build_store(s: Settings) -> Store:
    if s.data_backend == "postgres":
        from .adapters.postgres import PostgresStore

        return PostgresStore(s.database_url or "")
    if s.data_backend == "firestore":
        from .adapters.firestore import FirestoreStore

        return FirestoreStore(s.firestore_project or "", s.firestore_database)
    from .adapters.memory import MemoryStore

    return MemoryStore()


def build_blob(s: Settings) -> BlobStore:
    if s.blob_backend == "fs":
        from .adapters.blob import FsBlob

        return FsBlob(s.blob_fs_root or "")
    if s.blob_backend == "gcs":
        from .adapters.blob import GcsBlob

        return GcsBlob(s.blob_gcs_bucket or "")
    from .adapters.memory import MemoryBlob

    return MemoryBlob()


def build_publisher(s: Settings) -> Publisher:
    if s.events_backend == "rabbitmq":
        from .adapters.messaging import RabbitPublisher

        return RabbitPublisher(s.amqp_url_list)
    if s.events_backend == "pubsub":
        from .adapters.messaging import PubSubPublisher

        return PubSubPublisher(s.pubsub_project or "", s.pubsub_topic_ticket_issued or "")
    from .adapters.memory import NullPublisher

    return NullPublisher()


def build(s: Settings) -> Container:
    return Container(s, build_store(s), build_blob(s), build_publisher(s))
