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
        self.wal_file = self.data_dir / "wal.log"
        self.wal_state_file = self.data_dir / "wal_state.json"
        self.schemas: dict[str, TableSchema] = {}
        self.rows: dict[str, list[dict[str, Any]]] = {}
        self._last_applied_seq = 0
        self._next_wal_seq = 1
        self._load_state()
        self._load_wal_state()
        self._next_wal_seq = max(self._scan_wal_max_seq(), self._last_applied_seq) + 1
        self._replay_wal()

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

        self._append_wal_record(
            op="insert",
            table_name=table_name,
            pk_value=validated.get(pk_column.name) if pk_column is not None else None,
            before=None,
            after=validated,
        )
        self.rows[table_name].append(validated)
        row_offset = self._append_row(table_name, validated)
        if pk_column is not None:
            self._update_pk_index(table_name, pk_value, row_offset)
        self._mark_wal_applied()
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

    def update_by_pk(self, table_name: str, pk_value: Any, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update one row by primary key, rewrite table file, and return updated row."""
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
                self._append_wal_record(
                    op="update",
                    table_name=table_name,
                    pk_value=pk_value,
                    before=row,
                    after=validated,
                )
                self.rows[table_name][idx] = validated
                self._rewrite_table(table_name)
                if schema.primary_key is not None:
                    self.rebuild_pk_index(table_name)
                self._mark_wal_applied()
                return validated
        return None

    def delete_by_pk(self, table_name: str, pk_value: Any) -> bool:
        """Delete one row by primary key, rewrite table file, and return True if deleted."""
        schema = self.schemas.get(table_name)
        if schema is None:
            raise SchemaError(f"Table '{table_name}' does not exist")

        pk_column = schema.primary_key
        if pk_column is None:
            raise SchemaError("Table has no primary key")

        rows = self.rows.get(table_name, [])
        for idx, row in enumerate(rows):
            if row.get(pk_column.name) == pk_value:
                self._append_wal_record(
                    op="delete",
                    table_name=table_name,
                    pk_value=pk_value,
                    before=row,
                    after=None,
                )
                del self.rows[table_name][idx]
                self._rewrite_table(table_name)
                if schema.primary_key is not None:
                    self.rebuild_pk_index(table_name)
                self._mark_wal_applied()
                return True
        return False

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

    def _rewrite_table(self, table_name: str) -> None:
        table_path = self._table_file(table_name)
        temp_path = table_path.with_suffix(table_path.suffix + ".tmp")
        try:
            with temp_path.open("wb") as file_obj:
                for row in self.rows.get(table_name, []):
                    payload = (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")
                    file_obj.write(payload)
                if self.fsync_writes:
                    file_obj.flush()
                    os.fsync(file_obj.fileno())
            temp_path.replace(table_path)
        except OSError as exc:
            raise StorageError(f"Failed to rewrite table '{table_name}': {exc}") from exc

    def _append_wal_record(
        self,
        *,
        op: str,
        table_name: str,
        pk_value: Any,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> None:
        """Definition: append one WAL record before mutating table or index files.

        Why this exists:
            WAL must be written before data changes so recovery can reconstruct
            intent after a crash.

        Example:
            _append_wal_record(
                op="update",
                table_name="users",
                pk_value=1,
                before={"id": 1, "name": "Asha"},
                after={"id": 1, "name": "Rahul"},
            )

        M5.1/M5.2 intentionally use a human-readable WAL so failure analysis
        stays visible. A later milestone can replace this with a binary WAL
        format once recovery semantics are stable.
        """
        record = {
            "format": "jsonl-v1",
            "seq": self._next_wal_seq,
            "op": op,
            "table": table_name,
            "pk": pk_value,
            "before": before,
            "after": after,
        }
        payload = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
        try:
            with self.wal_file.open("ab") as file_obj:
                file_obj.write(payload)
                if self.fsync_writes:
                    file_obj.flush()
                    os.fsync(file_obj.fileno())
        except OSError as exc:
            raise StorageError(f"Failed to append WAL record: {exc}") from exc
        self._next_wal_seq += 1

    def _replay_wal(self) -> None:
        """Definition: replay WAL records on startup to repair durable state.

        Why this exists:
            A crash can happen after WAL append and before table/index mutation
            completes. Replay makes startup deterministic instead of guesswork.

        Example:
            backend = JsonFileBackend(data_dir="data")
            # startup loads schema/rows and then replays unapplied WAL records

        M5.4 adds applied-sequence tracking so startup only replays WAL records
        after the last durable applied point. Replay remains idempotent because
        a crash can still happen after data mutation and before WAL-state update.
        """
        if not self.wal_file.exists():
            return

        touched_tables: set[str] = set()
        highest_replayed_seq = self._last_applied_seq
        try:
            with self.wal_file.open("r", encoding="utf-8") as file_obj:
                for line_number, line in enumerate(file_obj, start=1):
                    payload = line.strip()
                    if not payload:
                        continue
                    record = json.loads(payload)
                    record_seq = self._record_seq(record, line_number)
                    if record_seq <= self._last_applied_seq:
                        continue
                    table_name = str(record["table"])
                    if table_name not in self.schemas:
                        continue
                    self._apply_wal_record(record)
                    touched_tables.add(table_name)
                    highest_replayed_seq = max(highest_replayed_seq, record_seq)
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            raise StorageError(f"Failed to replay WAL: {exc}") from exc

        for table_name in touched_tables:
            self._rewrite_table(table_name)
            schema = self.schemas.get(table_name)
            if schema is not None and schema.primary_key is not None:
                self.rebuild_pk_index(table_name)
        if highest_replayed_seq > self._last_applied_seq:
            self._last_applied_seq = highest_replayed_seq
            self._save_wal_state()

    def _apply_wal_record(self, record: dict[str, Any]) -> None:
        """Definition: apply one WAL record to in-memory table state.

        Why this exists:
            Replay needs a single place that interprets WAL operations and turns
            them into row-state changes.

        Example:
            _apply_wal_record(
                {
                    "op": "delete",
                    "table": "users",
                    "pk": 1,
                    "after": None,
                }
            )
        """
        op = str(record["op"])
        table_name = str(record["table"])
        pk_value = record.get("pk")
        after = record.get("after")

        if op == "insert":
            self._upsert_row_from_replay(table_name, pk_value, after)
            return

        if op == "update":
            self._upsert_row_from_replay(table_name, pk_value, after)
            return

        if op == "delete":
            row_idx = self._find_row_index_by_pk(table_name, pk_value)
            if row_idx is not None:
                del self.rows[table_name][row_idx]
            return

        raise StorageError(f"Unknown WAL operation '{op}'")

    def _upsert_row_from_replay(self, table_name: str, pk_value: Any, row: Any) -> None:
        """Definition: insert or replace a row during WAL replay.

        Why this exists:
            Recovery must be idempotent. If a row already exists, replay should
            replace it rather than create duplicates.

        Example:
            _upsert_row_from_replay(
                "users",
                1,
                {"id": 1, "name": "Rahul"},
            )
        """
        if not isinstance(row, dict):
            raise StorageError(f"Replay row for '{table_name}' must be an object")

        row_idx = self._find_row_index_by_pk(table_name, pk_value)
        if row_idx is None:
            self.rows[table_name].append(row)
        else:
            self.rows[table_name][row_idx] = row

    def _find_row_index_by_pk(self, table_name: str, pk_value: Any) -> int | None:
        """Definition: find the in-memory row position for a primary-key value.

        Example:
            idx = _find_row_index_by_pk("users", 1)
        """
        schema = self.schemas.get(table_name)
        if schema is None or schema.primary_key is None:
            return None

        pk_name = schema.primary_key.name
        rows = self.rows.get(table_name, [])
        for idx, row in enumerate(rows):
            if row.get(pk_name) == pk_value:
                return idx
        return None

    def _load_wal_state(self) -> None:
        """Definition: load last applied WAL sequence metadata from disk.

        Why this exists:
            Startup should not replay work that is already known to be durable.

        Example:
            _load_wal_state()
            assert self._last_applied_seq >= 0
        """
        if not self.wal_state_file.exists():
            self._last_applied_seq = 0
            return
        try:
            payload = json.loads(self.wal_state_file.read_text(encoding="utf-8"))
            self._last_applied_seq = int(payload.get("last_applied_seq", 0))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise StorageError(f"Failed to load WAL state: {exc}") from exc

    def _save_wal_state(self) -> None:
        """Definition: persist the last applied WAL sequence to disk.

        Example:
            self._last_applied_seq = 12
            _save_wal_state()
        """
        payload = json.dumps({"last_applied_seq": self._last_applied_seq}, sort_keys=True)
        self._atomic_write(self.wal_state_file, payload)

    def _mark_wal_applied(self) -> None:
        """Definition: mark the latest written WAL record as applied.

        Why this exists:
            After data/index mutation completes successfully, startup replay can
            skip WAL records up to this point.

        Example:
            _mark_wal_applied()
        """
        self._last_applied_seq = self._next_wal_seq - 1
        self._save_wal_state()

    def _scan_wal_max_seq(self) -> int:
        """Definition: scan WAL to discover the highest sequence number present.

        Why this exists:
            Startup must know where to continue WAL numbering after restart.

        Example:
            max_seq = _scan_wal_max_seq()
        """
        if not self.wal_file.exists():
            return 0

        max_seq = 0
        try:
            with self.wal_file.open("r", encoding="utf-8") as file_obj:
                for line_number, line in enumerate(file_obj, start=1):
                    payload = line.strip()
                    if not payload:
                        continue
                    record = json.loads(payload)
                    max_seq = max(max_seq, self._record_seq(record, line_number))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise StorageError(f"Failed to scan WAL sequence state: {exc}") from exc
        return max_seq

    def _record_seq(self, record: dict[str, Any], fallback_seq: int) -> int:
        """Definition: return the WAL sequence number for one record.

        Example:
            seq = _record_seq({"seq": 10}, 3)  # -> 10
            seq = _record_seq({}, 3)           # -> 3
        """
        seq = record.get("seq")
        return int(seq) if seq is not None else fallback_seq

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
