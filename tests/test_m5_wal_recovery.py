from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dinedb.backends.json_file_backend import JsonFileBackend
from dinedb.models import Column
from dinedb.storage import StorageEngine


class M5WalRecoveryTests(unittest.TestCase):
    def _log(self, message: str) -> None:
        print(f"[M5WalRecoveryTests] {message}")

    def _read_wal_records(self, tmp_dir: str) -> list[dict[str, object]]:
        wal_path = Path(tmp_dir) / "wal.log"
        if not wal_path.exists():
            return []
        return [
            json.loads(line)
            for line in wal_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _log_wal_state(self, tmp_dir: str) -> None:
        records = self._read_wal_records(tmp_dir)
        seqs = [record.get("seq") for record in records]
        self._log(f"wal records count={len(records)} seqs={seqs}")

    def _log_rows(self, label: str, rows: list[dict[str, object]]) -> None:
        self._log(f"{label}: rows={rows}")

    def test_replays_insert_when_wal_exists_but_table_write_missing(self) -> None:
        self._log("starting insert-replay scenario")
        with tempfile.TemporaryDirectory() as tmp_dir:
            self._log(f"using temp dir: {tmp_dir}")
            storage = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            self._log("creating users table")
            storage.create_table(
                "users",
                [
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ],
            )

            backend = storage.backend
            row = {"id": 1, "name": "Asha"}
            self._log("writing WAL record without table mutation to simulate crash boundary")
            backend._append_wal_record(
                op="insert",
                table_name="users",
                pk_value=1,
                before=None,
                after=row,
            )
            self._log_wal_state(tmp_dir)
            self._log_rows("before restart", backend.rows["users"])

            self._log("restarting backend and expecting WAL replay to restore row")
            recovered = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            self._log_rows("after replay", recovered._rows["users"])
            self.assertEqual(recovered._rows["users"], [row])
            self.assertTrue(recovered.validate_pk_index("users"))
            self._log("insert replay scenario passed")

    def test_replay_is_idempotent_when_data_was_written_but_wal_state_is_stale(self) -> None:
        self._log("starting idempotent replay scenario")
        with tempfile.TemporaryDirectory() as tmp_dir:
            self._log(f"using temp dir: {tmp_dir}")
            storage = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            self._log("creating users table and inserting durable row")
            storage.create_table(
                "users",
                [
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ],
            )
            storage.insert("users", [1, "Asha"])
            self._log_rows("durable rows before forcing stale state", storage._rows["users"])
            self._log_wal_state(tmp_dir)

            wal_state_path = Path(tmp_dir) / "wal_state.json"
            self._log("forcing stale wal_state.json to simulate crash before applied-state update")
            wal_state_path.write_text(json.dumps({"last_applied_seq": 0}), encoding="utf-8")

            self._log("restarting backend and expecting replay to avoid duplicate row")
            recovered = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            self._log_rows("after idempotent replay", recovered._rows["users"])
            self._log_wal_state(tmp_dir)
            self.assertEqual(recovered._rows["users"], [{"id": 1, "name": "Asha"}])
            self.assertTrue(recovered.validate_pk_index("users"))
            self._log("idempotent replay scenario passed")

    def test_replays_delete_when_wal_exists_but_delete_did_not_finish(self) -> None:
        self._log("starting delete-replay scenario")
        with tempfile.TemporaryDirectory() as tmp_dir:
            self._log(f"using temp dir: {tmp_dir}")
            storage = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            self._log("creating users table and inserting seed row")
            storage.create_table(
                "users",
                [
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ],
            )
            storage.insert("users", [1, "Asha"])

            backend = storage.backend
            self._log("writing delete WAL record without completing delete to simulate crash")
            backend._append_wal_record(
                op="delete",
                table_name="users",
                pk_value=1,
                before={"id": 1, "name": "Asha"},
                after=None,
            )
            self._log_wal_state(tmp_dir)
            self._log_rows("before restart", backend.rows["users"])

            wal_state_path = Path(tmp_dir) / "wal_state.json"
            self._log("setting last_applied_seq before delete record so restart must replay delete")
            wal_state_path.write_text(json.dumps({"last_applied_seq": 1}), encoding="utf-8")

            self._log("restarting backend and expecting WAL replay to remove row")
            recovered = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            self._log_rows("after replay", recovered._rows["users"])
            self._log_wal_state(tmp_dir)
            self.assertEqual(recovered._rows["users"], [])
            self.assertTrue(recovered.validate_pk_index("users"))
            self._log("delete replay scenario passed")


if __name__ == "__main__":
    unittest.main()
