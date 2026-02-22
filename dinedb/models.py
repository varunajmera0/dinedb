from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dinedb.errors import SchemaError


@dataclass(frozen=True)
class Column:
    """Definition: one table column contract.

    Example:
        Column(name="id", data_type="INT", is_primary_key=True)
    """

    name: str
    data_type: str
    is_primary_key: bool = False


@dataclass(frozen=True)
class TableSchema:
    """Definition: full schema contract for one logical table.

    Example:
        TableSchema(
            name="users",
            columns=[
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )
    """

    name: str
    columns: list[Column]

    @staticmethod
    def validate_columns(columns: list[Column]) -> None:
        """Definition: validate table-level column rules.

        Rules:
        - at least one column
        - no duplicate names
        - only supported types
        - at most one primary key

        Example:
            TableSchema.validate_columns(
                [
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ]
            )
        """
        if not columns:
            raise SchemaError("Table must have at least one column")

        seen: set[str] = set()
        primary_keys = 0
        for column in columns:
            if column.name in seen:
                raise SchemaError(f"Duplicate column '{column.name}'")
            seen.add(column.name)

            if column.data_type not in {"INT", "TEXT"}:
                raise SchemaError(f"Unsupported type '{column.data_type}'")

            if column.is_primary_key:
                primary_keys += 1

        if primary_keys > 1:
            raise SchemaError("Only one PRIMARY KEY column is supported")

    @property
    def primary_key(self) -> Column | None:
        """Definition: return the primary-key column if present.

        Example:
            schema = TableSchema(
                name="users",
                columns=[
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ],
            )
            schema.primary_key.name == "id"
        """
        for column in self.columns:
            if column.is_primary_key:
                return column
        return None

    def validate_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """Definition: validate one row against schema and normalize output.

        Example:
            schema = TableSchema(
                name="users",
                columns=[
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ],
            )
            schema.validate_row({"id": 1, "name": "Asha"})
            # returns {"id": 1, "name": "Asha"}
        """
        unknown = set(row) - {c.name for c in self.columns}
        if unknown:
            raise SchemaError(f"Unknown column(s): {sorted(unknown)}")

        validated: dict[str, Any] = {}
        for column in self.columns:
            if column.name not in row:
                raise SchemaError(f"Missing column '{column.name}'")

            value = row[column.name]
            if column.data_type == "INT":
                if not isinstance(value, int):
                    raise SchemaError(f"Column '{column.name}' must be INT")
            elif column.data_type == "TEXT":
                if not isinstance(value, str):
                    raise SchemaError(f"Column '{column.name}' must be TEXT")
            else:
                raise SchemaError(f"Unsupported type '{column.data_type}'")

            validated[column.name] = value
        return validated
