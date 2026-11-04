"""Logs JSON sur stdout, une ligne par événement (contrat d'exécution, A5)."""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
trace_var: ContextVar[str | None] = ContextVar("trace", default=None)
_STD = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def __init__(self, platform: str, process: str, instance: str, project: str | None = None) -> None:
        super().__init__()
        self.base = {"platform": platform, "process": process, "instance": instance}
        self.project = project

    def format(self, record: logging.LogRecord) -> str:
        out = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat().replace("+00:00", "Z"),
            "severity": record.levelname,
            "message": record.getMessage(),
            **self.base,
        }
        rid, trace = request_id_var.get(), trace_var.get()
        if rid:
            out["request_id"] = rid
        if trace:
            out["trace_id"] = trace
            if self.project:
                out["logging.googleapis.com/trace"] = f"projects/{self.project}/traces/{trace}"
        for k, v in vars(record).items():
            if k not in _STD and not k.startswith("_"):
                out[k] = v
        if record.exc_info:
            out["exception"] = self.formatException(record.exc_info)
        return json.dumps(out, default=str, ensure_ascii=False)


def setup(level: str, platform: str, process: str, instance: str, project: str | None = None) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(platform, process, instance, project))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    for noisy in ("uvicorn.access", "pika", "urllib3", "google"):
        logging.getLogger(noisy).setLevel("WARNING")
