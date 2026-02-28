from __future__ import annotations

import threading
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dinedb.sql.engine import SqlExecutor


class M6TransactionControlTests(unittest.TestCase):
    def setUp(self) -> None:
        SqlExecutor._writer_gate = threading.Lock()
        SqlExecutor._writer_owner = None

    def _log(self, message: str) -> None:
        print(f"[M6TransactionControlTests] {message}")

    def test_begin_commit_flow(self) -> None:
        self._log("checking BEGIN -> COMMIT transaction state flow")
        executor = SqlExecutor()

        begin_resp = executor.execute("BEGIN;")
        self._log(f"begin response={begin_resp}")
        self.assertTrue(begin_resp["ok"])
        self.assertTrue(begin_resp["transaction_active"])

        commit_resp = executor.execute("COMMIT;")
        self._log(f"commit response={commit_resp}")
        self.assertTrue(commit_resp["ok"])
        self.assertFalse(commit_resp["transaction_active"])

    def test_begin_rollback_flow(self) -> None:
        self._log("checking BEGIN -> ROLLBACK transaction state flow")
        executor = SqlExecutor()

        executor.execute("BEGIN;")
        rollback_resp = executor.execute("ROLLBACK;")
        self._log(f"rollback response={rollback_resp}")
        self.assertTrue(rollback_resp["ok"])
        self.assertFalse(rollback_resp["transaction_active"])

    def test_nested_begin_rejected(self) -> None:
        self._log("checking nested BEGIN rejection")
        executor = SqlExecutor()

        first_begin = executor.execute("BEGIN;")
        second_begin = executor.execute("BEGIN;")
        self._log(f"first begin={first_begin}")
        self._log(f"second begin={second_begin}")
        self.assertTrue(first_begin["ok"])
        self.assertFalse(second_begin["ok"])
        self.assertEqual(second_begin["error"]["code"], "EXEC_ERROR")

    def test_second_executor_begin_rejected_while_writer_active(self) -> None:
        self._log("checking second executor cannot BEGIN while first writer is active")
        executor_a = SqlExecutor()
        executor_b = SqlExecutor()

        begin_a = executor_a.execute("BEGIN;")
        begin_b = executor_b.execute("BEGIN;")
        self._log(f"executor_a begin={begin_a}")
        self._log(f"executor_b begin={begin_b}")

        self.assertTrue(begin_a["ok"])
        self.assertFalse(begin_b["ok"])
        self.assertEqual(begin_b["error"]["code"], "EXEC_ERROR")

        commit_a = executor_a.execute("COMMIT;")
        self._log(f"executor_a commit={commit_a}")
        self.assertTrue(commit_a["ok"])

    def test_second_executor_write_rejected_while_writer_active(self) -> None:
        self._log("checking second executor cannot write while first transaction holds writer gate")
        shared_executor = SqlExecutor()
        shared_executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")

        executor_a = SqlExecutor(storage=shared_executor.storage)
        executor_b = SqlExecutor(storage=shared_executor.storage)

        begin_a = executor_a.execute("BEGIN;")
        write_b = executor_b.execute("INSERT INTO users VALUES (1, 'Asha');")
        self._log(f"executor_a begin={begin_a}")
        self._log(f"executor_b write={write_b}")

        self.assertTrue(begin_a["ok"])
        self.assertFalse(write_b["ok"])
        self.assertEqual(write_b["error"]["code"], "EXEC_ERROR")

        rollback_a = executor_a.execute("ROLLBACK;")
        self._log(f"executor_a rollback={rollback_a}")
        self.assertTrue(rollback_a["ok"])

    def test_second_executor_select_rejected_while_writer_active(self) -> None:
        self._log("checking second executor cannot read while first transaction holds writer gate")
        shared_executor = SqlExecutor()
        shared_executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")
        shared_executor.execute("INSERT INTO users VALUES (1, 'Asha');")

        executor_a = SqlExecutor(storage=shared_executor.storage)
        executor_b = SqlExecutor(storage=shared_executor.storage)

        begin_a = executor_a.execute("BEGIN;")
        select_b = executor_b.execute("SELECT * FROM users WHERE id = 1;")
        self._log(f"executor_a begin={begin_a}")
        self._log(f"executor_b select={select_b}")

        self.assertTrue(begin_a["ok"])
        self.assertFalse(select_b["ok"])
        self.assertEqual(select_b["error"]["code"], "EXEC_ERROR")

        commit_a = executor_a.execute("COMMIT;")
        select_after_commit = executor_b.execute("SELECT * FROM users WHERE id = 1;")
        self._log(f"executor_a commit={commit_a}")
        self._log(f"executor_b select after commit={select_after_commit}")
        self.assertTrue(commit_a["ok"])
        self.assertTrue(select_after_commit["ok"])

    def test_same_executor_can_read_inside_its_transaction(self) -> None:
        self._log("checking transaction owner can still read inside its own transaction")
        executor = SqlExecutor()
        executor.execute("CREATE TABLE users (id INT PRIMARY KEY, name TEXT);")
        executor.execute("INSERT INTO users VALUES (1, 'Asha');")

        begin_resp = executor.execute("BEGIN;")
        select_resp = executor.execute("SELECT * FROM users WHERE id = 1;")
        rollback_resp = executor.execute("ROLLBACK;")
        self._log(f"begin response={begin_resp}")
        self._log(f"select response={select_resp}")
        self._log(f"rollback response={rollback_resp}")

        self.assertTrue(begin_resp["ok"])
        self.assertTrue(select_resp["ok"])
        self.assertEqual(select_resp["rows"], [{"id": 1, "name": "Asha"}])
        self.assertTrue(rollback_resp["ok"])

    def test_commit_without_begin_rejected(self) -> None:
        self._log("checking COMMIT without active transaction rejection")
        executor = SqlExecutor()
        resp = executor.execute("COMMIT;")
        self._log(f"commit without begin response={resp}")
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "EXEC_ERROR")

    def test_rollback_without_begin_rejected(self) -> None:
        self._log("checking ROLLBACK without active transaction rejection")
        executor = SqlExecutor()
        resp = executor.execute("ROLLBACK;")
        self._log(f"rollback without begin response={resp}")
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "EXEC_ERROR")


if __name__ == "__main__":
    unittest.main()
