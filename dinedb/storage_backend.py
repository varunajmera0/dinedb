from __future__ import annotations

from typing import Any, Protocol

from dinedb.models import Column


class StorageBackend(Protocol):
    """Definition: pluggable backend contract used by StorageEngine.

    Example:
        class CustomBackend:
            def create_table(self, table_name: str, columns: list[Column]) -> None:
                ...

            def insert(self, table_name: str, values: list[Any]) -> dict[str, Any]:
                ...
    """

    def create_table(self, table_name: str, columns: list[Column]) -> None:
        """Create a table in backend storage."""

    def insert(self, table_name: str, values: list[Any]) -> dict[str, Any]:
        """Insert one row and return stored row payload."""

    def get_by_pk(self, table_name: str, pk_value: Any) -> dict[str, Any] | None:
        """Return a row by primary key if present."""

    def get_by_pk_with_index(self, table_name: str, pk_value: Any) -> tuple[dict[str, Any] | None, bool]:
        """Return a row and whether an index was used."""

    def select_all(self, table_name: str) -> list[dict[str, Any]]:
        """Return all rows in a table (full scan)."""

    def validate_pk_index(self, table_name: str) -> bool:
        """Return True if the PK index is consistent with table data."""

    def rebuild_pk_index(self, table_name: str) -> None:
        """Rebuild the PK index for a table."""

    def update_by_pk(self, table_name: str, pk_value: Any, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update one row by primary key and return updated row."""

    def delete_by_pk(self, table_name: str, pk_value: Any) -> bool:
        """Delete one row by primary key and return True if deleted."""
