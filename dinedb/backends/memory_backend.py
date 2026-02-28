from __future__ import annotations

from typing import Any

from dinedb.errors import ConstraintError, SchemaError
from dinedb.models import Column, TableSchema


class InMemoryBackend:
    """Definition: backend that stores tables and rows in memory.

    Example:
        backend = InMemoryBackend()
        backend.create_table(
            "users",
            [
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )
        backend.insert("users", [1, "Asha"])
    """

    def __init__(self) -> None:
        self.schemas: dict[str, TableSchema] = {}
        self.rows: dict[str, list[dict[str, Any]]] = {}

    def create_table(self, table_name: str, columns: list[Column]) -> None:
        """Create schema entry and empty row list for a table."""
        if table_name in self.schemas:
            raise ConstraintError(f"Table '{table_name}' already exists")

        TableSchema.validate_columns(columns)
        self.schemas[table_name] = TableSchema(name=table_name, columns=columns)
        self.rows[table_name] = []

    def insert(self, table_name: str, values: list[Any]) -> dict[str, Any]:
        """Validate and append a row into an in-memory table."""
        schema = self.schemas.get(table_name)
        if schema is None:
            raise SchemaError(f"Table '{table_name}' does not exist")

        if len(values) != len(schema.columns):
            raise SchemaError(f"Expected {len(schema.columns)} values, got {len(values)}")

        row = {column.name: value for column, value in zip(schema.columns, values)}
        validated = schema.validate_row(row)

        pk_column = schema.primary_key
        if pk_column is not None:
            pk_value = validated[pk_column.name]
            for existing in self.rows[table_name]:
                if existing[pk_column.name] == pk_value:
                    raise ConstraintError(f"Duplicate PRIMARY KEY '{pk_value}'")

        self.rows[table_name].append(validated)
        return validated

    def get_by_pk(self, table_name: str, pk_value: Any) -> dict[str, Any] | None:
        """Return a row by primary key using in-memory scan."""
        schema = self.schemas.get(table_name)
        if schema is None:
            raise SchemaError(f"Table '{table_name}' does not exist")

        pk_column = schema.primary_key
        if pk_column is None:
            return None

        for row in self.rows[table_name]:
            if row.get(pk_column.name) == pk_value:
                return row
        return None

    def get_by_pk_with_index(self, table_name: str, pk_value: Any) -> tuple[dict[str, Any] | None, bool]:
        """Return a row and indicate no index was used (in-memory scan)."""
        return (self.get_by_pk(table_name, pk_value), False)

    def select_all(self, table_name: str) -> list[dict[str, Any]]:
        """Return all rows for a table (in-memory scan)."""
        schema = self.schemas.get(table_name)
        if schema is None:
            raise SchemaError(f"Table '{table_name}' does not exist")
        return list(self.rows[table_name])

    def update_by_pk(self, table_name: str, pk_value: Any, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update one row by primary key and return updated row."""
        schema = self.schemas.get(table_name)
        if schema is None:
            raise SchemaError(f"Table '{table_name}' does not exist")

        pk_column = schema.primary_key
        if pk_column is None:
            raise SchemaError("Table has no primary key")

        if pk_column.name in updates:
            raise ConstraintError("Updating primary key is not supported in M4.6")

        rows = self.rows.get(table_name, [])
        for idx, row in enumerate(rows):
            if row.get(pk_column.name) == pk_value:
                updated = {**row, **updates}
                validated = schema.validate_row(updated)
                self.rows[table_name][idx] = validated
                return validated
        return None

    def delete_by_pk(self, table_name: str, pk_value: Any) -> bool:
        """Delete one row by primary key and return True if deleted."""
        schema = self.schemas.get(table_name)
        if schema is None:
            raise SchemaError(f"Table '{table_name}' does not exist")

        pk_column = schema.primary_key
        if pk_column is None:
            raise SchemaError("Table has no primary key")

        rows = self.rows.get(table_name, [])
        for idx, row in enumerate(rows):
            if row.get(pk_column.name) == pk_value:
                del self.rows[table_name][idx]
                return True
        return False

    def validate_pk_index(self, table_name: str) -> bool:
        """In-memory backend has no separate index, so it is always consistent."""
        schema = self.schemas.get(table_name)
        if schema is None:
            raise SchemaError(f"Table '{table_name}' does not exist")
        return True

    def rebuild_pk_index(self, table_name: str) -> None:
        """No-op for in-memory backend (no persisted index)."""
        schema = self.schemas.get(table_name)
        if schema is None:
            raise SchemaError(f"Table '{table_name}' does not exist")
