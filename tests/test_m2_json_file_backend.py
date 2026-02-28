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
from dinedb.errors import ConstraintError, SchemaError
from dinedb.models import Column
from dinedb.storage import StorageEngine


class M2JsonFileBackendTests(unittest.TestCase):
    def _log(self, message: str) -> None:
        print(f"[M2JsonFileBackendTests] {message}")

    def test_writes_schema_file_on_create_table(self) -> None:
        self._log("checking schema and PK index files are created on CREATE TABLE")
        with tempfile.TemporaryDirectory() as tmp_dir:
            backend = JsonFileBackend(data_dir=tmp_dir)
            storage = StorageEngine(backend=backend)
            storage.create_table(
                "users",
                [
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ],
            )

            schema_path = Path(tmp_dir) / "schema.json"
            self._log(f"schema path={schema_path}")
            self.assertTrue(schema_path.exists())
            raw = json.loads(schema_path.read_text(encoding="utf-8"))
            self._log(f"schema payload={raw}")
            self.assertIn("users", raw)
            pk_index_path = Path(tmp_dir) / "users.pk.json"
            self._log(f"pk index path={pk_index_path}")
            self.assertTrue(pk_index_path.exists())

    def test_persists_rows_across_restart(self) -> None:
        self._log("checking rows and PK index survive backend restart")
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage_1 = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            storage_1.create_table(
                "users",
                [
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ],
            )
            storage_1.insert("users", [1, "Asha"])
            self._log(f"rows after first insert={storage_1._rows['users']}")
            pk_index_path = Path(tmp_dir) / "users.pk.json"
            self.assertTrue(pk_index_path.exists())
            index_payload = json.loads(pk_index_path.read_text(encoding="utf-8"))
            self._log(f"pk index payload after first insert={index_payload}")
            self.assertIn("1", index_payload)

            storage_2 = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            self._log(f"rows after reopen={storage_2._rows['users']}")
            self.assertIn("users", storage_2._schemas)
            self.assertEqual(storage_2._rows["users"], [{"id": 1, "name": "Asha"}])

            with self.assertRaisesRegex(ConstraintError, "Duplicate PRIMARY KEY"):
                storage_2.insert("users", [1, "Rahul"])

            inserted = storage_2.insert("users", [2, "Rahul"])
            self._log(f"inserted row after reopen={inserted}")
            self.assertEqual(inserted, {"id": 2, "name": "Rahul"})

            storage_3 = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            self._log(f"rows after second reopen={storage_3._rows['users']}")
            self.assertEqual(
                storage_3._rows["users"],
                [{"id": 1, "name": "Asha"}, {"id": 2, "name": "Rahul"}],
            )

    def test_insert_unknown_table_rejected(self) -> None:
        self._log("checking unknown table rejection in file backend")
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            with self.assertRaisesRegex(SchemaError, "does not exist"):
                storage.insert("users", [1, "Asha"])

    def test_fsync_flag_is_respected(self) -> None:
        self._log("checking fsync-enabled writes still insert correctly")
        with tempfile.TemporaryDirectory() as tmp_dir:
            backend = JsonFileBackend(data_dir=tmp_dir, fsync_writes=True)
            storage = StorageEngine(backend=backend)
            storage.create_table(
                "users",
                [
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ],
            )
            inserted = storage.insert("users", [1, "Asha"])
            self._log(f"inserted row with fsync enabled={inserted}")
            self.assertEqual(inserted, {"id": 1, "name": "Asha"})


if __name__ == "__main__":
    unittest.main()
