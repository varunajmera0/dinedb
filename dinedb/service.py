from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from dinedb.backends import JsonFileBackend
from dinedb.errors import ConstraintError, DatabaseError, SchemaError, StorageError
from dinedb.models import Column
from dinedb.storage import StorageEngine


class DineDBService:
    """Definition: stable service API that returns structured success/error payloads.

    Example:
        service = DineDBService()
        result = service.create_table(
            "users",
            [
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )
        # {"ok": True, "message": "Table 'users' created"}
    """

    def __init__(
        self,
        storage: StorageEngine | None = None,
        *,
        persistent: bool = False,
        data_dir: str | Path = "data",
        fsync_writes: bool = False,
    ) -> None:
        """Definition: initialize service with configurable storage mode.

        Example:
            service = DineDBService()
            service_with_shared_storage = DineDBService(StorageEngine())
            persistent_service = DineDBService(persistent=True, data_dir="data")
        """
        self._init_error: Exception | None = None
        if storage is not None:
            self.storage = storage
        elif persistent:
            try:
                self.storage = StorageEngine(
                    backend=JsonFileBackend(data_dir=data_dir, fsync_writes=fsync_writes)
                )
            except Exception as exc:  # noqa: BLE001
                self._init_error = exc
                self.storage = StorageEngine()
        else:
            self.storage = StorageEngine()

    @classmethod
    def from_env(cls) -> "DineDBService":
        """Definition: build service using environment-based config.

        Env vars:
            DINEDB_PERSISTENT: "1"/"true"/"yes" enables persistence.
            DINEDB_DATA_DIR: path for data files (default: "data").
            DINEDB_FSYNC: "1"/"true"/"yes" enables fsync writes.

        Example:
            export DINEDB_PERSISTENT=1
            export DINEDB_DATA_DIR=/tmp/dinedb
            export DINEDB_FSYNC=1
            service = DineDBService.from_env()
        """
        persistent = _env_bool("DINEDB_PERSISTENT", default=False)
        fsync_writes = _env_bool("DINEDB_FSYNC", default=False)
        data_dir = os.getenv("DINEDB_DATA_DIR", "data")
        return cls(persistent=persistent, data_dir=data_dir, fsync_writes=fsync_writes)

    def create_table(self, table_name: str, columns: list[Column]) -> dict[str, Any]:
        """Definition: create table and return a structured response payload.

        Example:
            response = service.create_table(
                "users",
                [Column(name="id", data_type="INT", is_primary_key=True)],
            )
            # {"ok": True, "message": "Table 'users' created"}
        """
        meta = self._response_meta(operation="create_table")
        if self._init_error is not None:
            return self._error_payload(self._init_error, meta=meta)
        try:
            self.storage.create_table(table_name, columns)
            return {
                "ok": True,
                "message": f"Table '{table_name}' created",
                "meta": meta,
            }
        except Exception as exc:  # noqa: BLE001
            return self._error_payload(exc, meta=meta)

    def insert(self, table_name: str, values: list[Any]) -> dict[str, Any]:
        """Definition: insert row and return structured success/error payload.

        Example:
            response = service.insert("users", [1, "Asha"])
            # {"ok": True, "message": "1 row inserted", "row": {...}}
        """
        meta = self._response_meta(operation="insert")
        if self._init_error is not None:
            return self._error_payload(self._init_error, meta=meta)
        try:
            row = self.storage.insert(table_name, values)
            return {"ok": True, "message": "1 row inserted", "row": row, "meta": meta}
        except Exception as exc:  # noqa: BLE001
            return self._error_payload(exc, meta=meta)

    def get_by_pk(self, table_name: str, pk_value: Any) -> dict[str, Any]:
        """Definition: fetch one row by primary key and return structured payload.

        Example:
            response = service.get_by_pk("users", 1)
            # {"ok": True, "row": {...}, "meta": {...}}
        """
        meta = self._response_meta(operation="get_by_pk")
        if self._init_error is not None:
            return self._error_payload(self._init_error, meta=meta)
        try:
            row, index_used = self.storage.get_by_pk_with_index(table_name, pk_value)
            meta = {**meta, "index_used": index_used}
            return {"ok": True, "row": row, "meta": meta}
        except Exception as exc:  # noqa: BLE001
            return self._error_payload(exc, meta=meta)

    def validate_pk_index(self, table_name: str) -> dict[str, Any]:
        """Definition: validate PK index consistency and return structured payload.

        Example:
            response = service.validate_pk_index("users")
            # {"ok": True, "valid": True, "meta": {...}}
        """
        meta = self._response_meta(operation="validate_pk_index")
        if self._init_error is not None:
            return self._error_payload(self._init_error, meta=meta)
        try:
            valid = self.storage.validate_pk_index(table_name)
            return {"ok": True, "valid": valid, "meta": meta}
        except Exception as exc:  # noqa: BLE001
            return self._error_payload(exc, meta=meta)

    def rebuild_pk_index(self, table_name: str) -> dict[str, Any]:
        """Definition: rebuild PK index and return structured payload.

        Example:
            response = service.rebuild_pk_index("users")
            # {"ok": True, "message": "PK index rebuilt", "meta": {...}}
        """
        meta = self._response_meta(operation="rebuild_pk_index")
        if self._init_error is not None:
            return self._error_payload(self._init_error, meta=meta)
        try:
            self.storage.rebuild_pk_index(table_name)
            return {"ok": True, "message": "PK index rebuilt", "meta": meta}
        except Exception as exc:  # noqa: BLE001
            return self._error_payload(exc, meta=meta)
    def _response_meta(self, operation: str) -> dict[str, str]:
        """Definition: create consistent response metadata for traceability.

        Example:
            {"operation": "insert", "trace_id": "...", "timestamp_utc": "..."}
        """
        return {
            "operation": operation,
            "trace_id": str(uuid4()),
            "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    def _error_payload(self, exc: Exception, meta: dict[str, str]) -> dict[str, Any]:
        """Definition: normalize exceptions into stable error objects.

        Example:
            {
                "ok": False,
                "error": {
                    "code": "SCHEMA_ERROR",
                    "message": "...",
                },
                "meta": {
                    "operation": "insert",
                    "trace_id": "f2f5...",
                    "timestamp_utc": "2026-02-21T20:00:00.000000Z",
                }
            }
        """
        if isinstance(exc, ConstraintError):
            code = "CONSTRAINT_ERROR"
        elif isinstance(exc, SchemaError):
            code = "SCHEMA_ERROR"
        elif isinstance(exc, StorageError):
            code = "STORAGE_ERROR"
        elif isinstance(exc, DatabaseError):
            code = "DATABASE_ERROR"
        else:
            code = "INTERNAL_ERROR"

        return {
            "ok": False,
            "error": {
                "code": code,
                "message": str(exc),
            },
            "meta": meta,
        }


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
