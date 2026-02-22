from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dinedb.models import Column
from dinedb.service import DineDBService


class M23ServicePersistenceTests(unittest.TestCase):
    def test_service_reports_storage_error_with_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            schema_path = Path(tmp_dir) / "schema.json"
            schema_path.write_text("{not: valid json", encoding="utf-8")

            service = DineDBService(persistent=True, data_dir=tmp_dir)
            response = service.create_table(
                "users",
                [Column(name="id", data_type="INT", is_primary_key=True)],
            )

            self.assertFalse(response["ok"])
            self.assertEqual(response["error"]["code"], "STORAGE_ERROR")
            self.assertEqual(response["meta"]["operation"], "create_table")
            self.assertIn("trace_id", response["meta"])
            self.assertIn("timestamp_utc", response["meta"])

    def test_service_persistent_mode_survives_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service_1 = DineDBService(
                persistent=True,
                data_dir=tmp_dir,
                fsync_writes=True,
            )
            create_resp = service_1.create_table(
                "users",
                [
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ],
            )
            insert_resp = service_1.insert("users", [1, "Asha"])

            self.assertTrue(create_resp["ok"])
            self.assertTrue(insert_resp["ok"])
            self.assertEqual(insert_resp["meta"]["operation"], "insert")
            self.assertIn("trace_id", insert_resp["meta"])
            self.assertIn("timestamp_utc", insert_resp["meta"])

            service_2 = DineDBService(
                persistent=True,
                data_dir=tmp_dir,
                fsync_writes=True,
            )
            duplicate_resp = service_2.insert("users", [1, "Rahul"])
            self.assertFalse(duplicate_resp["ok"])
            self.assertEqual(duplicate_resp["error"]["code"], "CONSTRAINT_ERROR")
            self.assertEqual(duplicate_resp["meta"]["operation"], "insert")
            self.assertIn("trace_id", duplicate_resp["meta"])
            self.assertIn("timestamp_utc", duplicate_resp["meta"])

            insert_resp_2 = service_2.insert("users", [2, "Rahul"])
            self.assertTrue(insert_resp_2["ok"])
            self.assertEqual(insert_resp_2["row"], {"id": 2, "name": "Rahul"})
            self.assertEqual(insert_resp_2["meta"]["operation"], "insert")

    def test_service_default_mode_stays_in_memory(self) -> None:
        service_1 = DineDBService()
        service_1.create_table(
            "users",
            [
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )
        service_1.insert("users", [1, "Asha"])

        service_2 = DineDBService()
        missing_table_resp = service_2.insert("users", [1, "Asha"])
        self.assertFalse(missing_table_resp["ok"])
        self.assertEqual(missing_table_resp["error"]["code"], "SCHEMA_ERROR")


if __name__ == "__main__":
    unittest.main()
