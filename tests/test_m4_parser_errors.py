from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dinedb.sql.engine import SqlExecutor


class M4ParserErrorTests(unittest.TestCase):
    def test_empty_sql_rejected(self) -> None:
        executor = SqlExecutor()
        resp = executor.execute("")
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "PARSE_ERROR")

    def test_unknown_statement_rejected(self) -> None:
        executor = SqlExecutor()
        resp = executor.execute("UPDATE users SET name = 'Asha';")
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "PARSE_ERROR")

    def test_missing_table_name_rejected(self) -> None:
        executor = SqlExecutor()
        resp = executor.execute("SELECT * FROM ;")
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "PARSE_ERROR")


if __name__ == "__main__":
    unittest.main()
