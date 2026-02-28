from __future__ import annotations

from typing import Any

from dinedb.backends.memory_backend import InMemoryBackend
from dinedb.models import Column, TableSchema
from dinedb.storage_backend import StorageBackend


class StorageEngine:
    """Definition: storage adapter that delegates to a pluggable backend.

    This lets M2 switch from in-memory to file-backed storage without
    changing service-layer APIs.

    Example:
        storage = StorageEngine()  # default InMemoryBackend
        storage.create_table(
            "users",
            [
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )
        storage.insert("users", [1, "Asha"])
    """

    def __init__(self, backend: StorageBackend | None = None) -> None:
        """Definition: initialize storage with a provided backend.

        Example:
            storage = StorageEngine()
            custom_storage = StorageEngine(backend=InMemoryBackend())
        """
        self.backend = backend or InMemoryBackend()

    def create_table(self, table_name: str, columns: list[Column]) -> None:
        """Definition: create table via backend.

        Example:
            storage.create_table(
                "users",
                [
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ],
            )
        """
        self.backend.create_table(table_name, columns)

    def insert(self, table_name: str, values: list[Any]) -> dict[str, Any]:
        """Definition: insert row via backend.

        Example:
            storage.create_table(
                "users",
                [
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ],
            )
            inserted = storage.insert("users", [1, "Asha"])
            inserted == {"id": 1, "name": "Asha"}
        """
        return self.backend.insert(table_name, values)

    def get_by_pk(self, table_name: str, pk_value: Any) -> dict[str, Any] | None:
        """Definition: fetch one row by primary key via backend."""
        return self.backend.get_by_pk(table_name, pk_value)

    def get_by_pk_with_index(self, table_name: str, pk_value: Any) -> tuple[dict[str, Any] | None, bool]:
        """Definition: fetch one row and whether index was used."""
        return self.backend.get_by_pk_with_index(table_name, pk_value)

    def select_all(self, table_name: str) -> list[dict[str, Any]]:
        """Definition: return all rows for a table via backend.

        Example:
            rows = storage.select_all("users")
        """
        return self.backend.select_all(table_name)

    def validate_pk_index(self, table_name: str) -> bool:
        """Definition: validate PK index consistency for a table."""
        return self.backend.validate_pk_index(table_name)

    def rebuild_pk_index(self, table_name: str) -> None:
        """Definition: rebuild PK index for a table."""
        self.backend.rebuild_pk_index(table_name)

    def update_by_pk(self, table_name: str, pk_value: Any, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Definition: update one row by primary key via backend.

        Example:
            updated = storage.update_by_pk("users", 1, {"name": "Asha"})
        """
        return self.backend.update_by_pk(table_name, pk_value, updates)

    def delete_by_pk(self, table_name: str, pk_value: Any) -> bool:
        """Definition: delete one row by primary key via backend.

        Example:
            deleted = storage.delete_by_pk("users", 1)
        """
        return self.backend.delete_by_pk(table_name, pk_value)

    @property
    def _schemas(self) -> dict[str, TableSchema]:
        """Compatibility accessor for M1 examples/tests."""
        return getattr(self.backend, "schemas", {})

    @property
    def _rows(self) -> dict[str, list[dict[str, Any]]]:
        """Compatibility accessor for M1 examples/tests."""
        return getattr(self.backend, "rows", {})
