from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dinedb.sql.engine import SqlExecutor


class M4TypeValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.executor = SqlExecutor()
        self.executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")
        self.executor.execute("INSERT INTO users VALUES (1, 'Asha');")

    def test_select_where_type_mismatch(self) -> None:
        resp = self.executor.execute("SELECT * FROM users WHERE id = 'Asha';")
        self.assertFalse(resp["ok"])

    def test_update_where_type_mismatch(self) -> None:
        resp = self.executor.execute("UPDATE users SET name = 'Rahul' WHERE id = 'Asha';")
        self.assertFalse(resp["ok"])

    def test_delete_where_type_mismatch(self) -> None:
        resp = self.executor.execute("DELETE FROM users WHERE id = 'Asha';")
        self.assertFalse(resp["ok"])


if __name__ == "__main__":
    unittest.main()
