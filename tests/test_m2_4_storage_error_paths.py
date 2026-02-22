from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dinedb.backends.json_file_backend import JsonFileBackend
from dinedb.errors import StorageError
from dinedb.models import Column


class M24StorageErrorPathTests(unittest.TestCase):
    def test_atomic_write_replaces_schema_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            backend = JsonFileBackend(data_dir=tmp_dir)
            backend.create_table(
                "users",
                [
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ],
            )

            schema_path = Path(tmp_dir) / "schema.json"
            self.assertTrue(schema_path.exists())
            self.assertFalse(schema_path.with_suffix(".json.tmp").exists())

    def test_corrupt_schema_file_raises_storage_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            schema_path = Path(tmp_dir) / "schema.json"
            schema_path.write_text("{not: valid json", encoding="utf-8")

            with self.assertRaisesRegex(StorageError, "Failed to load schema file"):
                JsonFileBackend(data_dir=tmp_dir)

    def test_corrupt_table_file_raises_storage_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            schema_path = Path(tmp_dir) / "schema.json"
            schema_path.write_text(
                '{"users": [{"name": "id", "data_type": "INT", "is_primary_key": true}]}',
                encoding="utf-8",
            )
            table_path = Path(tmp_dir) / "users.tbl"
            table_path.write_text("{not json}\n", encoding="utf-8")

            with self.assertRaisesRegex(StorageError, "Failed to load table 'users'"):
                JsonFileBackend(data_dir=tmp_dir)


if __name__ == "__main__":
    unittest.main()
