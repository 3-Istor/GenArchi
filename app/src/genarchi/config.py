"""Configuration lue dans l'environnement (contrat d'exécution, partie C)."""

from __future__ import annotations

import os
import socket
from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", case_sensitive=False)

    platform: Literal["local", "p2", "p3"]
    port: int = 8080
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    public_base_url: str

    data_backend: Literal["postgres", "firestore", "memory"]
    database_url: str | None = None
    firestore_project: str | None = None
    firestore_database: str = "(default)"

    blob_backend: Literal["fs", "gcs", "memory"]
    blob_fs_root: str | None = None
    blob_gcs_bucket: str | None = None

    events_backend: Literal["none", "rabbitmq", "pubsub"] = "none"
    amqp_urls: str | None = None
    pubsub_project: str | None = None
    pubsub_topic_ticket_issued: str | None = None

    admin_token: str = Field(min_length=8)
    staff_token: str = Field(min_length=8)

    chaos_enabled: bool = False
    chaos_force_unready: bool = False

    instance_name: str | None = None
    zone: str | None = None
    region: str | None = None
    k_revision: str | None = None
    app_version: str = "dev"

    @model_validator(mode="after")
    def _check_backends(self) -> Settings:
        missing = []
        if self.data_backend == "postgres" and not self.database_url:
            missing.append("DATABASE_URL")
        if self.data_backend == "firestore" and not self.firestore_project:
            missing.append("FIRESTORE_PROJECT")
        if self.blob_backend == "fs" and not self.blob_fs_root:
            missing.append("BLOB_FS_ROOT")
        if self.blob_backend == "gcs" and not self.blob_gcs_bucket:
            missing.append("BLOB_GCS_BUCKET")
        if self.events_backend == "rabbitmq" and not self.amqp_urls:
            missing.append("AMQP_URLS")
        if self.events_backend == "pubsub" and not (self.pubsub_project and self.pubsub_topic_ticket_issued):
            missing.append("PUBSUB_PROJECT, PUBSUB_TOPIC_TICKET_ISSUED")
        if missing:
            raise ValueError("variables obligatoires manquantes : " + ", ".join(missing))
        self.public_base_url = self.public_base_url.rstrip("/")
        return self

    @property
    def instance(self) -> str:
        return self.instance_name or self.k_revision or socket.gethostname()

    @property
    def amqp_url_list(self) -> list[str]:
        return [u.strip() for u in (self.amqp_urls or "").split(",") if u.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


def reset_settings() -> None:
    get_settings.cache_clear()


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").lower() in {"1", "true", "yes"}
