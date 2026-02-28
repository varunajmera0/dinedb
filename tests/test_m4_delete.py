from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dinedb.sql.engine import SqlExecutor


class M4DeleteTests(unittest.TestCase):
    def test_delete_by_pk(self) -> None:
        executor = SqlExecutor()
        executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")
        executor.execute("INSERT INTO users VALUES (1, 'Asha');")
        resp = executor.execute("DELETE FROM users WHERE id = 1;")
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["deleted"], 1)

    def test_delete_missing_row(self) -> None:
        executor = SqlExecutor()
        executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")
        resp = executor.execute("DELETE FROM users WHERE id = 999;")
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["deleted"], 0)


if __name__ == "__main__":
    unittest.main()
