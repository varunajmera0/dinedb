from __future__ import annotations

from typing import Any

from dinedb.errors import DatabaseError, SchemaError
from dinedb.models import Column, TableSchema
from dinedb.sql.sql_parser import CreateTable, Insert, Select, parse
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
            if isinstance(ast, CreateTable):
                columns = [Column(name=n, data_type=t, is_primary_key=pk) for n, t, pk in ast.columns]
                self.storage.create_table(ast.table_name, columns)
                return {"ok": True, "message": f"Table '{ast.table_name}' created"}

            if isinstance(ast, Insert):
                row = self.storage.insert(ast.table_name, ast.values)
                return {"ok": True, "message": "1 row inserted", "row": row}

            if isinstance(ast, Select):
                return self._execute_select(ast)

            return {"ok": False, "error": {"code": "UNSUPPORTED", "message": "Unsupported AST"}}
        except DatabaseError as exc:
            return {"ok": False, "error": {"code": "EXEC_ERROR", "message": str(exc)}}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": {"code": "INTERNAL_ERROR", "message": str(exc)}}

    def _execute_select(self, ast: Select) -> dict[str, Any]:
        """Definition: execute a SELECT AST (limited to pk equality for now).

        Dry run example:
            Select(table_name="users", columns=["name"], where_column="id", where_value=1)
            -> find PK column -> get_by_pk -> project columns
        """
        schema = self._schema_for(ast.table_name)
        if schema is None:
            raise SchemaError(f"Table '{ast.table_name}' does not exist")

        rows: list[dict[str, Any]] = []
        if ast.where_column is not None:
            pk = schema.primary_key
            if pk is None or ast.where_column != pk.name:
                raise SchemaError("Only WHERE on primary key is supported in M4.3")
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

    def _schema_for(self, table_name: str) -> TableSchema | None:
        """Definition: fetch schema from storage backend (M4.3 uses backend cache).

        Example:
            schema = executor._schema_for("users")
            # -> TableSchema(...) or None if missing
        """
        return self.storage._schemas.get(table_name)
