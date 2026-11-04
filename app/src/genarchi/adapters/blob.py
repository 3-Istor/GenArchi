"""Stockage des QR : système de fichiers (P2, NFS) ou Cloud Storage (P3)."""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import timedelta
from pathlib import Path

log = logging.getLogger("genarchi.blob")


class FsBlob:
    """Écriture atomique (fichier temporaire + rename) : un lecteur ne voit jamais un PNG tronqué."""

    def __init__(self, root: str) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root.resolve() not in p.parents:
            raise ValueError(f"clé hors du stockage : {key}")
        return p

    def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def get(self, key: str) -> bytes | None:
        path = self._path(key)
        return path.read_bytes() if path.exists() else None

    def signed_url(self, key: str, ttl_seconds: int) -> str | None:
        return None


class GcsBlob:
    def __init__(self, bucket: str) -> None:
        from google.cloud import storage

        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        blob = self.bucket.blob(key)
        blob.cache_control = "private, max-age=3600"
        blob.upload_from_string(data, content_type=content_type, timeout=5)

    def get(self, key: str) -> bytes | None:
        blob = self.bucket.blob(key)
        try:
            return blob.download_as_bytes(timeout=5)
        except Exception:
            return None

    def signed_url(self, key: str, ttl_seconds: int) -> str | None:
        """URL signée V4. Sur Cloud Run, la signature passe par l'API IAM (signBlob) du compte de service."""
        try:
            import google.auth
            from google.auth.transport.requests import Request

            creds, _ = google.auth.default()
            creds.refresh(Request())
            email = getattr(creds, "service_account_email", None)
            kwargs = {"service_account_email": email, "access_token": creds.token} if email else {}
            return self.bucket.blob(key).generate_signed_url(
                version="v4", expiration=timedelta(seconds=ttl_seconds), method="GET", **kwargs
            )
        except Exception:
            log.warning("signed url failed, falling back to streaming", exc_info=True)
            return None
