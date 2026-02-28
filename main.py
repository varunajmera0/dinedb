from __future__ import annotations

import json

from dinedb.models import Column
from dinedb.service import DineDBService
from dinedb.sql.engine import SqlExecutor


def main() -> None:
    service = DineDBService.from_env()
    executor = SqlExecutor(service.storage)
    print("dinedb SQL shell")
    print("Enter SQL statements terminated by ';' (multi-line supported). Ctrl+D to exit.")

    try:
        import readline  # noqa: F401
    except Exception:
        pass

    buffer: list[str] = []

    def prompt() -> str:
        return "dinedb> " if not buffer else "....> "

    def split_sql_statements(sql_text: str) -> list[str]:
        """Split SQL text on semicolons, ignoring semicolons inside single quotes."""
        statements: list[str] = []
        current: list[str] = []
        in_string = False
        i = 0
        while i < len(sql_text):
            ch = sql_text[i]
            if ch == "'":
                in_string = not in_string
                current.append(ch)
                i += 1
                continue
            if ch == ";" and not in_string:
                stmt = "".join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
                i += 1
                continue
            current.append(ch)
            i += 1
        tail = "".join(current).strip()
        if tail:
            statements.append(tail)
        return statements

    while True:
        try:
            line = input(prompt()).rstrip()
        except EOFError:
            print()
            break

        if not line.strip():
            continue

        buffer.append(line)
        sql_text = "\n".join(buffer)
        if ";" not in sql_text:
            continue

        statements = split_sql_statements(sql_text)
        buffer.clear()
        for stmt in statements:
            print(json.dumps(executor.execute(stmt + ";"), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
