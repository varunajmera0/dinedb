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
from dinedb.service import DineDBService
from dinedb.storage import StorageEngine


class M3PkIndexValidateTests(unittest.TestCase):
    def test_validate_and_rebuild_pk_index(self) -> None:
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
            raw = json.loads(index_path.read_text(encoding="utf-8"))
            raw.pop("2", None)
            index_path.write_text(json.dumps(raw), encoding="utf-8")

            self.assertFalse(storage.validate_pk_index("users"))

            storage.rebuild_pk_index("users")
            self.assertTrue(storage.validate_pk_index("users"))

            index_payload = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertIn("1", index_payload)
            self.assertIn("2", index_payload)

    def test_service_validate_and_rebuild_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = DineDBService(persistent=True, data_dir=tmp_dir)
            service.create_table(
                "users",
                [
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ],
            )
            service.insert("users", [1, "Asha"])

            index_path = Path(tmp_dir) / "users.pk.json"
            index_path.write_text("{not valid json", encoding="utf-8")

            validate_resp = service.validate_pk_index("users")
            self.assertTrue(validate_resp["ok"])
            self.assertFalse(validate_resp["valid"])

            rebuild_resp = service.rebuild_pk_index("users")
            self.assertTrue(rebuild_resp["ok"])
            self.assertIn("rebuilt", rebuild_resp["message"])

            validate_resp_2 = service.validate_pk_index("users")
            self.assertTrue(validate_resp_2["ok"])
            self.assertTrue(validate_resp_2["valid"])


if __name__ == "__main__":
    unittest.main()
