from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dinedb.sql.engine import SqlExecutor


class M4ExecutorTests(unittest.TestCase):
    def test_create_insert_select_pk(self) -> None:
        executor = SqlExecutor()
        self.assertTrue(
            executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")["ok"]
        )
        insert_resp = executor.execute("INSERT INTO users VALUES (1, 'Asha');")
        self.assertTrue(insert_resp["ok"])

        select_resp = executor.execute("SELECT * FROM users WHERE id = 1;")
        self.assertTrue(select_resp["ok"])
        self.assertEqual(select_resp["rows"], [{"id": 1, "name": "Asha"}])

    def test_select_non_pk_rejected(self) -> None:
        executor = SqlExecutor()
        executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")
        resp = executor.execute("SELECT * FROM users WHERE name = 'Asha';")
        self.assertFalse(resp["ok"])

    def test_select_projection_and_limit(self) -> None:
        executor = SqlExecutor()
        executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")
        executor.execute("INSERT INTO users VALUES (1, 'Asha');")
        resp = executor.execute("SELECT name FROM users WHERE id = 1 LIMIT 1;")
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["rows"], [{"name": "Asha"}])

    def test_select_all_rows(self) -> None:
        executor = SqlExecutor()
        executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")
        executor.execute("INSERT INTO users VALUES (1, 'Asha');")
        executor.execute("INSERT INTO users VALUES (2, 'Rahul');")
        resp = executor.execute("SELECT * FROM users;")
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["rows"], [{"id": 1, "name": "Asha"}, {"id": 2, "name": "Rahul"}])


if __name__ == "__main__":
    unittest.main()
