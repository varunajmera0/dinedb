from __future__ import annotations

import json

from dinedb.models import Column
from dinedb.service import DineDBService
from dinedb.sql.engine import SqlExecutor


def main() -> None:
    service = DineDBService.from_env()
    executor = SqlExecutor(service.storage)
    print("dinedb CLI (M3.7) - type .help for commands")

    while True:
        try:
            line = input("dinedb> ").strip()
        except EOFError:
            print()
            break

        if not line:
            continue

        if line in {".exit", ".quit"}:
            break

        if line == ".help":

            print(
                "\n".join(
                    [
                        "Commands:",
                        "  .demo                     create users + insert sample rows",
                        "  .validate <table>          validate PK index for table",
                        "  .reindex <table>           rebuild PK index for table",
                        "  .pk <table> <id>           direct PK lookup (check meta.index_used)",
                        "  .sql <statement>           run SQL (CREATE/INSERT/SELECT)",
                        "  .sql_demo                  run a mini SQL script (good + bad examples)",
                        "  .exit / .quit              exit",
                    ]
                )
            )
            continue

        if line == ".demo":
            result = {
                "create_table": service.create_table(
                    "users",
                    [
                        Column(name="id", data_type="INT", is_primary_key=True),
                        Column(name="name", data_type="TEXT"),
                    ],
                ),
                "insert_row_1": service.insert("users", [1, "Asha"]),
                "insert_row_2": service.insert("users", [2, "Rahul"]),
            }
            print(json.dumps(result, indent=2, sort_keys=True))
            continue

        if line.startswith(".validate "):
            table = line.split(maxsplit=1)[1]
            print(json.dumps(service.validate_pk_index(table), indent=2, sort_keys=True))
            continue

        if line.startswith(".reindex "):
            table = line.split(maxsplit=1)[1]
            print(json.dumps(service.rebuild_pk_index(table), indent=2, sort_keys=True))
            continue

        if line.startswith(".pk"):
            line_split = line.split(maxsplit=2)
            if len(line_split) < 3:
                print("usage: .pk <table> <id>")
                continue
            table = line_split[1]
            value = line_split[2]
            pk_value = int(value) if value.isdigit() else value
            print(json.dumps(service.get_by_pk(table, pk_value), indent=2, sort_keys=True))
            continue

        if line.startswith(".sql "):
            sql = line.split(" ", 1)[1]
            print(json.dumps(executor.execute(sql), indent=2, sort_keys=True))
            continue

        if line == ".sql_demo":
            demo_sql = [
                "CREATE TABLE users (id INT PRIMARY KEY, name TEXT);",
                "INSERT INTO users VALUES (1, 'Asha');",
                "SELECT * FROM users WHERE id = 1;",
                "SELECT * FROM users WHERE name = 'Asha';",
            ]
            for stmt in demo_sql:
                print(f"SQL> {stmt}")
                print(json.dumps(executor.execute(stmt), indent=2, sort_keys=True))
            continue

        upper = line.upper()
        if upper.startswith("SELECT ") or upper.startswith("INSERT ") or upper.startswith("CREATE "):
            print(json.dumps(executor.execute(line), indent=2, sort_keys=True))
            continue

        print("unknown command, type .help")


if __name__ == "__main__":
    main()
