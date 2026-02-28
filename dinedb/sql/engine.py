from __future__ import annotations

import threading
from typing import Any

from dinedb.errors import ConcurrencyError, DatabaseError, SchemaError
from dinedb.models import Column, TableSchema
from dinedb.sql.sql_parser import (
    Begin,
    Commit,
    CreateTable,
    Delete,
    Insert,
    Rollback,
    Select,
    Update,
    parse,
)
from dinedb.storage import StorageEngine


class SqlExecutor:
    """Definition: execute parsed SQL ASTs against storage.

    Example:
        executor = SqlExecutor()
        executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")
        executor.execute("INSERT INTO users VALUES (1, 'Asha');")
        executor.execute("SELECT * FROM users WHERE id = 1;")
    """

    def __init__(self, storage: StorageEngine | None = None) -> None:
        """Definition: initialize with a storage engine.

        Example:
            executor = SqlExecutor()
        """
        self.storage = storage or StorageEngine()
        self._in_transaction = False

    def execute(self, sql: str) -> dict[str, Any]:
        """Definition: parse SQL and execute, returning structured result.

        Dry run example:
            SQL: SELECT * FROM users WHERE id = 1;
            Steps:
              1) parse -> Select(table_name="users", columns=["*"], where_column="id", where_value=1)
              2) if WHERE is on PK -> use get_by_pk
              3) format output
        """
        try:
            ast = parse(sql)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": {"code": "PARSE_ERROR", "message": str(exc)}}

        try:
            temporary_write_lock = False

            if isinstance(ast, CreateTable):
                temporary_write_lock = self._ensure_write_access()
                columns = [Column(name=n, data_type=t, is_primary_key=pk) for n, t, pk in ast.columns]
                self.storage.create_table(ast.table_name, columns)
                return {"ok": True, "message": f"Table '{ast.table_name}' created"}

            if isinstance(ast, Insert):
                temporary_write_lock = self._ensure_write_access()
                row = self.storage.insert(ast.table_name, ast.values)
                return {"ok": True, "message": "1 row inserted", "row": row}

            if isinstance(ast, Select):
                return self._execute_select(ast)

            if isinstance(ast, Update):
                temporary_write_lock = self._ensure_write_access()
                return self._execute_update(ast)

            if isinstance(ast, Delete):
                temporary_write_lock = self._ensure_write_access()
                return self._execute_delete(ast)

            if isinstance(ast, Begin):
                return self._execute_begin()

            if isinstance(ast, Commit):
                return self._execute_commit()

            if isinstance(ast, Rollback):
                return self._execute_rollback()

            return {"ok": False, "error": {"code": "UNSUPPORTED", "message": "Unsupported AST"}}
        except DatabaseError as exc:
            return {"ok": False, "error": {"code": "EXEC_ERROR", "message": str(exc)}}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": {"code": "INTERNAL_ERROR", "message": str(exc)}}
        finally:
            if "temporary_write_lock" in locals() and temporary_write_lock:
                self._release_write_access()

    def _execute_select(self, ast: Select) -> dict[str, Any]:
        """Definition: execute a SELECT AST (limited to pk equality for now).

        Dry run example:
            Select(table_name="users", columns=["name"], where_column="id", where_value=1)
            -> find PK column -> get_by_pk -> project columns
        """
        self._ensure_read_access()
        schema = self._schema_for(ast.table_name)
        if schema is None:
            raise SchemaError(f"Table '{ast.table_name}' does not exist")

        rows: list[dict[str, Any]] = []
        if ast.where_column is not None:
            pk = schema.primary_key
            if pk is None or ast.where_column != pk.name:
                raise SchemaError("Only WHERE on primary key is supported in M4.3")
            self._validate_value_type(pk, ast.where_value, context="WHERE")
            row = self.storage.get_by_pk(ast.table_name, ast.where_value)
            if row is not None:
                rows = [row]
        else:
            rows = self.storage.select_all(ast.table_name)

        if ast.columns != ["*"]:
            rows = [{col: row[col] for col in ast.columns} for row in rows]

        if ast.limit is not None:
            rows = rows[: ast.limit]

        return {"ok": True, "rows": rows, "count": len(rows)}

    def _ensure_read_access(self) -> None:
        """Definition: enforce the current committed-read rule for SELECT.

        Example:
            executor_a.execute("BEGIN;")
            executor_b.execute("SELECT * FROM users;")
            -> rejected until executor_a commits or rolls back

        Why this exists:
            M6.3 must prevent other executors from observing state that may be in the
            middle of an active write transaction. Until M6.4 adds transaction-local
            buffers, the safest honest rule is to reject outside reads during an active
            writer transaction.
        """
        owner = self.__class__._writer_owner
        if owner is not None and owner != id(self):
            raise ConcurrencyError("Committed-read rule: another writer transaction is active")

    def _execute_update(self, ast: Update) -> dict[str, Any]:
        """Definition: execute UPDATE AST (single row by PK only).

        Dry run example:
            Update(table_name="users", assignments={"name": "Asha"}, where_column="id", where_value=1)
            -> validate PK column -> update_by_pk -> return updated row
        """
        schema = self._schema_for(ast.table_name)
        if schema is None:
            raise SchemaError(f"Table '{ast.table_name}' does not exist")

        pk = schema.primary_key
        if pk is None or ast.where_column != pk.name:
            raise SchemaError("Only WHERE on primary key is supported in M4.6")
        self._validate_value_type(pk, ast.where_value, context="WHERE")

        for col in ast.assignments:
            if col not in schema.column_map:
                raise SchemaError(f"Unknown column '{col}'")

        updated = self.storage.update_by_pk(ast.table_name, ast.where_value, ast.assignments)
        return {"ok": True, "updated": 1 if updated else 0, "row": updated}

    def _execute_delete(self, ast: Delete) -> dict[str, Any]:
        """Definition: execute DELETE AST (single row by PK only).

        Dry run example:
            Delete(table_name="users", where_column="id", where_value=1)
            -> validate PK column -> delete_by_pk -> return deleted count
        """
        schema = self._schema_for(ast.table_name)
        if schema is None:
            raise SchemaError(f"Table '{ast.table_name}' does not exist")

        pk = schema.primary_key
        if pk is None or ast.where_column != pk.name:
            raise SchemaError("Only WHERE on primary key is supported in M4.7")
        self._validate_value_type(pk, ast.where_value, context="WHERE")

        deleted = self.storage.delete_by_pk(ast.table_name, ast.where_value)
        return {"ok": True, "deleted": 1 if deleted else 0}

    def _execute_begin(self) -> dict[str, Any]:
        """Definition: start a transaction state in the executor.

        Example:
            BEGIN;
            -> {"ok": True, "message": "Transaction started", "transaction_active": True}
        """
        if self._in_transaction:
            raise SchemaError("Transaction already active")
        self._acquire_writer_gate()
        self._in_transaction = True
        return {"ok": True, "message": "Transaction started", "transaction_active": True}

    def _execute_commit(self) -> dict[str, Any]:
        """Definition: end the current transaction successfully.

        Example:
            COMMIT;
            -> {"ok": True, "message": "Transaction committed", "transaction_active": False}
        """
        if not self._in_transaction:
            raise SchemaError("No active transaction to commit")
        self._in_transaction = False
        self._release_writer_gate()
        return {"ok": True, "message": "Transaction committed", "transaction_active": False}

    def _execute_rollback(self) -> dict[str, Any]:
        """Definition: abort the current transaction state.

        Example:
            ROLLBACK;
            -> {"ok": True, "message": "Transaction rolled back", "transaction_active": False}
        """
        if not self._in_transaction:
            raise SchemaError("No active transaction to roll back")
        self._in_transaction = False
        self._release_writer_gate()
        return {"ok": True, "message": "Transaction rolled back", "transaction_active": False}

    def _ensure_write_access(self) -> bool:
        """Definition: ensure the executor has the single-writer right before a write.

        Example:
            INSERT outside BEGIN acquires a temporary writer slot.
            UPDATE inside BEGIN reuses the already-held writer slot.
        """
        if self._in_transaction:
            if self.__class__._writer_owner != id(self):
                raise ConcurrencyError("Active transaction does not own the writer gate")
            return False
        self._acquire_writer_gate()
        return True

    def _acquire_writer_gate(self) -> None:
        """Definition: acquire the process-wide writer gate without blocking.

        Example:
            executor_a.execute("BEGIN;")  # acquires writer gate
            executor_b.execute("BEGIN;")  # raises ConcurrencyError until executor_a ends
        """
        cls = self.__class__
        if cls._writer_owner == id(self):
            return
        acquired = cls._writer_gate.acquire(blocking=False)
        if not acquired:
            raise ConcurrencyError("Another writer is already active")
        cls._writer_owner = id(self)

    def _release_write_access(self) -> None:
        """Definition: release a temporary single-statement writer slot.

        Example:
            INSERT outside BEGIN acquires write access for one statement and releases it here.
        """
        self._release_writer_gate()

    def _release_writer_gate(self) -> None:
        """Definition: release the process-wide writer gate if this executor owns it.

        Example:
            COMMIT or ROLLBACK releases the writer gate held since BEGIN.
        """
        cls = self.__class__
        if cls._writer_owner != id(self):
            return
        cls._writer_owner = None
        cls._writer_gate.release()

    def _validate_value_type(self, column: Column, value: Any, *, context: str) -> None:
        """Definition: enforce type checks for single values (e.g., WHERE id = ...).

        Example:
            _validate_value_type(Column("id","INT"), 1, context="WHERE")  # ok
        """
        if column.data_type == "INT" and not isinstance(value, int):
            raise SchemaError(f"{context} value for '{column.name}' must be INT")
        if column.data_type == "TEXT" and not isinstance(value, str):
            raise SchemaError(f"{context} value for '{column.name}' must be TEXT")

    def _schema_for(self, table_name: str) -> TableSchema | None:
        """Definition: fetch schema from storage backend (M4.3 uses backend cache).

        Example:
            schema = executor._schema_for("users")
            # -> TableSchema(...) or None if missing
        """
        return self.storage._schemas.get(table_name)
    _writer_gate = threading.Lock()
    _writer_owner: int | None = None
