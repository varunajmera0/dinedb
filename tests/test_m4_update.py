from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dinedb.sql.engine import SqlExecutor


class M4UpdateTests(unittest.TestCase):
    def test_update_by_pk(self) -> None:
        executor = SqlExecutor()
        executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")
        executor.execute("INSERT INTO users VALUES (1, 'Asha');")
        resp = executor.execute("UPDATE users SET name = 'Rahul' WHERE id = 1;")
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["updated"], 1)
        self.assertEqual(resp["row"], {"id": 1, "name": "Rahul"})

    def test_update_missing_row(self) -> None:
        executor = SqlExecutor()
        executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")
        resp = executor.execute("UPDATE users SET name = 'Rahul' WHERE id = 999;")
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["updated"], 0)
        self.assertIsNone(resp["row"])

    def test_update_pk_rejected(self) -> None:
        executor = SqlExecutor()
        executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")
        executor.execute("INSERT INTO users VALUES (1, 'Asha');")
        resp = executor.execute("UPDATE users SET id = 2 WHERE id = 1;")
        self.assertFalse(resp["ok"])


if __name__ == "__main__":
    unittest.main()
