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


class M3PkServiceTests(unittest.TestCase):
    def test_service_get_by_pk_success(self) -> None:
        service = DineDBService()
        service.create_table(
            "users",
            [
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )
        service.insert("users", [1, "Asha"])

        response = service.get_by_pk("users", 1)
        self.assertTrue(response["ok"])
        self.assertEqual(response["row"], {"id": 1, "name": "Asha"})
        self.assertEqual(response["meta"]["operation"], "get_by_pk")
        self.assertFalse(response["meta"]["index_used"])

    def test_service_get_by_pk_missing_row(self) -> None:
        service = DineDBService()
        service.create_table(
            "users",
            [
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )
        response = service.get_by_pk("users", 999)
        self.assertTrue(response["ok"])
        self.assertIsNone(response["row"])

    def test_service_get_by_pk_persistent_backend(self) -> None:
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

            service_reopen = DineDBService(persistent=True, data_dir=tmp_dir)
            response = service_reopen.get_by_pk("users", 1)
            self.assertTrue(response["ok"])
            self.assertEqual(response["row"], {"id": 1, "name": "Asha"})
            self.assertTrue(response["meta"]["index_used"])


if __name__ == "__main__":
    unittest.main()
