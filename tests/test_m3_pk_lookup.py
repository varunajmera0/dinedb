from __future__ import annotations

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


class M3PrimaryKeyLookupTests(unittest.TestCase):
    def test_in_memory_pk_lookup(self) -> None:
        storage = StorageEngine()
        storage.create_table(
            "users",
            [
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )
        storage.insert("users", [1, "Asha"])
        storage.insert("users", [2, "Rahul"])

        self.assertEqual(storage.get_by_pk("users", 2), {"id": 2, "name": "Rahul"})
        self.assertIsNone(storage.get_by_pk("users", 999))

    def test_json_file_pk_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            storage.create_table(
                "users",
                [
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ],
            )
            storage.insert("users", [1, "Asha"])
            storage.insert("users", [2, "Rahul"])

            storage_reopen = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            self.assertEqual(storage_reopen.get_by_pk("users", 1), {"id": 1, "name": "Asha"})
            self.assertIsNone(storage_reopen.get_by_pk("users", 999))

    def test_pk_index_rebuilds_on_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            storage.create_table(
                "users",
                [
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ],
            )
            storage.insert("users", [1, "Asha"])
            storage.insert("users", [2, "Rahul"])

            index_path = Path(tmp_dir) / "users.pk.json"
            index_path.write_text("{not valid json", encoding="utf-8")

            storage_reopen = StorageEngine(backend=JsonFileBackend(data_dir=tmp_dir))
            self.assertEqual(storage_reopen.get_by_pk("users", 2), {"id": 2, "name": "Rahul"})


if __name__ == "__main__":
    unittest.main()
