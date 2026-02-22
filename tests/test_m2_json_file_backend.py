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
    def test_writes_schema_file_on_create_table(self) -> None:
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
            self.assertTrue(schema_path.exists())
            raw = json.loads(schema_path.read_text(encoding="utf-8"))
            self.assertIn("users", raw)
            pk_index_path = Path(tmp_dir) / "users.pk.json"
            self.assertTrue(pk_index_path.exists())

    def test_persists_rows_across_restart(self) -> None:
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
            pk_index_path = Path(tmp_dir) / "users.pk.json"
            self.assertTrue(pk_index_path.exists())
            index_payload = json.loads(pk_index_path.read_text(encoding="utf-8"))
            self.assertIn("1", index_payload)

            storage_2 = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            self.assertIn("users", storage_2._schemas)
            self.assertEqual(storage_2._rows["users"], [{"id": 1, "name": "Asha"}])

            with self.assertRaisesRegex(ConstraintError, "Duplicate PRIMARY KEY"):
                storage_2.insert("users", [1, "Rahul"])

            inserted = storage_2.insert("users", [2, "Rahul"])
            self.assertEqual(inserted, {"id": 2, "name": "Rahul"})

            storage_3 = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            self.assertEqual(
                storage_3._rows["users"],
                [{"id": 1, "name": "Asha"}, {"id": 2, "name": "Rahul"}],
            )

    def test_insert_unknown_table_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            with self.assertRaisesRegex(SchemaError, "does not exist"):
                storage.insert("users", [1, "Asha"])

    def test_fsync_flag_is_respected(self) -> None:
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
            self.assertEqual(inserted, {"id": 1, "name": "Asha"})


if __name__ == "__main__":
    unittest.main()
