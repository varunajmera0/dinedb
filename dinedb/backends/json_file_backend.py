from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dinedb.errors import ConstraintError, SchemaError, StorageError
from dinedb.models import Column, TableSchema


class JsonFileBackend:
    """Definition: backend that persists schema/rows to JSON files.

    Example:
        backend = JsonFileBackend(data_dir="data")
        backend.create_table(
            "users",
            [
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )
        backend.insert("users", [1, "Asha"])
    """

    def __init__(self, data_dir: str | Path = "data", *, fsync_writes: bool = False) -> None:
        self.data_dir = Path(data_dir)
        self.fsync_writes = fsync_writes
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.schema_file = self.data_dir / "schema.json"
        self.schemas: dict[str, TableSchema] = {}
        self.rows: dict[str, list[dict[str, Any]]] = {}
        self._load_state()

    def create_table(self, table_name: str, columns: list[Column]) -> None:
        """Create a table and persist schema metadata on disk."""
        if table_name in self.schemas:
            raise ConstraintError(f"Table '{table_name}' already exists")

        TableSchema.validate_columns(columns)
        schema = TableSchema(name=table_name, columns=columns)
        self.schemas[table_name] = schema
        self.rows[table_name] = []
        self._save_schema()
        self._table_file(table_name).touch(exist_ok=True)
        if schema.primary_key is not None:
            self._pk_index_file(table_name).write_text("{}", encoding="utf-8")

    def insert(self, table_name: str, values: list[Any]) -> dict[str, Any]:
        """Validate and append one row to table file and memory cache."""
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
        row_offset = self._append_row(table_name, validated)
        if pk_column is not None:
            self._update_pk_index(table_name, pk_value, row_offset)
        return validated

    def get_by_pk(self, table_name: str, pk_value: Any) -> dict[str, Any] | None:
        """Return a row by primary key using the PK index file."""
        row, _ = self.get_by_pk_with_index(table_name, pk_value)
        return row

    def get_by_pk_with_index(self, table_name: str, pk_value: Any) -> tuple[dict[str, Any] | None, bool]:
        """Return a row and indicate whether the PK index was used."""
        schema = self.schemas.get(table_name)
        if schema is None:
            raise SchemaError(f"Table '{table_name}' does not exist")

        pk_column = schema.primary_key
        if pk_column is None:
            return (None, False)

        index_path = self._pk_index_file(table_name)
        if not index_path.exists():
            return (None, False)

        try:
            raw = index_path.read_text(encoding="utf-8")
            index_data = json.loads(raw) if raw.strip() else {}
        except (OSError, json.JSONDecodeError) as exc:
            raise StorageError(f"Failed to load PK index for '{table_name}': {exc}") from exc

        offset = index_data.get(str(pk_value))
        if offset is None:
            return (None, True)

        table_path = self._table_file(table_name)
        try:
            with table_path.open("rb") as file_obj:
                file_obj.seek(offset)
                line = file_obj.readline()
        except OSError as exc:
            raise StorageError(f"Failed to read table '{table_name}': {exc}") from exc

        if not line:
            return (None, True)

        try:
            return (json.loads(line.decode("utf-8")), True)
        except json.JSONDecodeError as exc:
            raise StorageError(f"Failed to parse row for '{table_name}': {exc}") from exc

    def select_all(self, table_name: str) -> list[dict[str, Any]]:
        """Return all rows for a table (cached in memory)."""
        schema = self.schemas.get(table_name)
        if schema is None:
            raise SchemaError(f"Table '{table_name}' does not exist")
        return list(self.rows.get(table_name, []))

    def _load_state(self) -> None:
        if not self.schema_file.exists():
            return

        try:
            raw_schema = json.loads(self.schema_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StorageError(f"Failed to load schema file: {exc}") from exc

        for table_name, column_defs in raw_schema.items():
            columns = [
                Column(
                    name=column["name"],
                    data_type=column["data_type"],
                    is_primary_key=bool(column.get("is_primary_key", False)),
                )
                for column in column_defs
            ]
            TableSchema.validate_columns(columns)
            self.schemas[table_name] = TableSchema(name=table_name, columns=columns)
            self.rows[table_name] = self._load_rows(table_name)
            if self.schemas[table_name].primary_key is not None:
                self._ensure_pk_index(table_name)

    def _load_rows(self, table_name: str) -> list[dict[str, Any]]:
        table_path = self._table_file(table_name)
        if not table_path.exists():
            return []

        rows: list[dict[str, Any]] = []
        try:
            with table_path.open("r", encoding="utf-8") as file_obj:
                for line in file_obj:
                    payload = line.strip()
                    if not payload:
                        continue
                    rows.append(json.loads(payload))
        except (OSError, json.JSONDecodeError) as exc:
            raise StorageError(f"Failed to load table '{table_name}': {exc}") from exc

        return rows

    def _save_schema(self) -> None:
        serializable = {
            table_name: [
                {
                    "name": column.name,
                    "data_type": column.data_type,
                    "is_primary_key": column.is_primary_key,
                }
                for column in schema.columns
            ]
            for table_name, schema in self.schemas.items()
        }

        payload = json.dumps(serializable, indent=2, sort_keys=True)
        self._atomic_write(self.schema_file, payload)

    def _append_row(self, table_name: str, row: dict[str, Any]) -> int:
        table_path = self._table_file(table_name)
        payload = (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")
        try:
            with table_path.open("ab") as file_obj:
                offset = file_obj.tell()
                file_obj.write(payload)
                if self.fsync_writes:
                    file_obj.flush()
                    os.fsync(file_obj.fileno())
        except OSError as exc:
            raise StorageError(f"Failed to append row to '{table_name}': {exc}") from exc
        return offset

    def _table_file(self, table_name: str) -> Path:
        return self.data_dir / f"{table_name}.tbl"

    def _pk_index_file(self, table_name: str) -> Path:
        return self.data_dir / f"{table_name}.pk.json"

    def _atomic_write(self, path: Path, payload: str) -> None:
        temp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            temp_path.write_text(payload, encoding="utf-8")
            if self.fsync_writes:
                with temp_path.open("r+", encoding="utf-8") as file_obj:
                    file_obj.flush()
                    os.fsync(file_obj.fileno())
            temp_path.replace(path)
        except OSError as exc:
            raise StorageError(f"Failed to write file '{path.name}': {exc}") from exc

    def _update_pk_index(self, table_name: str, pk_value: Any, row_offset: int) -> None:
        index_path = self._pk_index_file(table_name)
        try:
            raw = index_path.read_text(encoding="utf-8")
            index_data = json.loads(raw) if raw.strip() else {}
        except (OSError, json.JSONDecodeError) as exc:
            raise StorageError(f"Failed to load PK index for '{table_name}': {exc}") from exc

        index_data[str(pk_value)] = row_offset
        payload = json.dumps(index_data, sort_keys=True)
        self._atomic_write(index_path, payload)

    def _ensure_pk_index(self, table_name: str) -> None:
        index_path = self._pk_index_file(table_name)
        if not index_path.exists():
            self.rebuild_pk_index(table_name)
            return

        try:
            raw = index_path.read_text(encoding="utf-8")
            index_data = json.loads(raw) if raw.strip() else {}
        except (OSError, json.JSONDecodeError):
            self.rebuild_pk_index(table_name)
            return

        rows = self.rows.get(table_name, [])
        if len(index_data) != len(rows):
            self.rebuild_pk_index(table_name)
            return

        pk_column = self.schemas[table_name].primary_key
        if pk_column is None:
            return

        for row in rows:
            if str(row.get(pk_column.name)) not in index_data:
                self.rebuild_pk_index(table_name)
                return

    def validate_pk_index(self, table_name: str) -> bool:
        schema = self.schemas.get(table_name)
        if schema is None:
            raise SchemaError(f"Table '{table_name}' does not exist")
        if schema.primary_key is None:
            return True

        index_path = self._pk_index_file(table_name)
        if not index_path.exists():
            return False

        try:
            raw = index_path.read_text(encoding="utf-8")
            index_data = json.loads(raw) if raw.strip() else {}
        except (OSError, json.JSONDecodeError):
            return False

        rows = self.rows.get(table_name, [])
        if len(index_data) != len(rows):
            return False

        pk_column = schema.primary_key
        for row in rows:
            if str(row.get(pk_column.name)) not in index_data:
                return False
        return True

    def rebuild_pk_index(self, table_name: str) -> None:
        pk_column = self.schemas[table_name].primary_key
        if pk_column is None:
            return

        index_data: dict[str, int] = {}
        table_path = self._table_file(table_name)
        try:
            with table_path.open("rb") as file_obj:
                while True:
                    offset = file_obj.tell()
                    line = file_obj.readline()
                    if not line:
                        break
                    payload = line.strip()
                    if not payload:
                        continue
                    row = json.loads(payload.decode("utf-8"))
                    pk_value = row.get(pk_column.name)
                    if pk_value is not None:
                        index_data[str(pk_value)] = offset
        except (OSError, json.JSONDecodeError) as exc:
            raise StorageError(f"Failed to rebuild PK index for '{table_name}': {exc}") from exc

        payload = json.dumps(index_data, sort_keys=True)
        self._atomic_write(self._pk_index_file(table_name), payload)
