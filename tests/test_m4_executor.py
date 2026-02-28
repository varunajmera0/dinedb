from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dinedb.sql.engine import SqlExecutor


class M4ExecutorTests(unittest.TestCase):
    def _log(self, message: str) -> None:
        print(f"[M4ExecutorTests] {message}")

    def test_create_insert_select_pk(self) -> None:
        self._log("checking CREATE -> INSERT -> SELECT by primary key")
        executor = SqlExecutor()
        self.assertTrue(
            executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")["ok"]
        )
        insert_resp = executor.execute("INSERT INTO users VALUES (1, 'Asha');")
        self.assertTrue(insert_resp["ok"])
        self._log(f"insert response={insert_resp}")

        select_resp = executor.execute("SELECT * FROM users WHERE id = 1;")
        self.assertTrue(select_resp["ok"])
        self._log(f"select response={select_resp}")
        self.assertEqual(select_resp["rows"], [{"id": 1, "name": "Asha"}])

    def test_select_non_pk_rejected(self) -> None:
        self._log("checking executor rejects non-PK WHERE lookups")
        executor = SqlExecutor()
        executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")
        resp = executor.execute("SELECT * FROM users WHERE name = 'Asha';")
        self._log(f"non-PK select response={resp}")
        self.assertFalse(resp["ok"])

    def test_select_projection_and_limit(self) -> None:
        self._log("checking projection and LIMIT handling")
        executor = SqlExecutor()
        executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")
        executor.execute("INSERT INTO users VALUES (1, 'Asha');")
        resp = executor.execute("SELECT name FROM users WHERE id = 1 LIMIT 1;")
        self.assertTrue(resp["ok"])
        self._log(f"projection response={resp}")
        self.assertEqual(resp["rows"], [{"name": "Asha"}])

    def test_select_all_rows(self) -> None:
        self._log("checking full table SELECT path")
        executor = SqlExecutor()
        executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")
        executor.execute("INSERT INTO users VALUES (1, 'Asha');")
        executor.execute("INSERT INTO users VALUES (2, 'Rahul');")
        resp = executor.execute("SELECT * FROM users;")
        self.assertTrue(resp["ok"])
        self._log(f"select-all response={resp}")
        self.assertEqual(resp["rows"], [{"id": 1, "name": "Asha"}, {"id": 2, "name": "Rahul"}])


if __name__ == "__main__":
    unittest.main()
