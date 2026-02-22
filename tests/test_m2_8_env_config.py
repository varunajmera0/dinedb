from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dinedb.models import Column
from dinedb.service import DineDBService


class M28EnvConfigTests(unittest.TestCase):
    def test_from_env_defaults_to_in_memory(self) -> None:
        os.environ.pop("DINEDB_PERSISTENT", None)
        os.environ.pop("DINEDB_DATA_DIR", None)
        os.environ.pop("DINEDB_FSYNC", None)

        service = DineDBService.from_env()
        service.create_table(
            "users",
            [
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )
        service.insert("users", [1, "Asha"])

        fresh_service = DineDBService.from_env()
        response = fresh_service.insert("users", [2, "Rahul"])
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "SCHEMA_ERROR")

    def test_from_env_enables_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.environ["DINEDB_PERSISTENT"] = "1"
            os.environ["DINEDB_DATA_DIR"] = tmp_dir
            os.environ["DINEDB_FSYNC"] = "1"

            service_1 = DineDBService.from_env()
            service_1.create_table(
                "users",
                [
                    Column(name="id", data_type="INT", is_primary_key=True),
                    Column(name="name", data_type="TEXT"),
                ],
            )
            service_1.insert("users", [1, "Asha"])

            service_2 = DineDBService.from_env()
            response = service_2.insert("users", [1, "Asha"])
            self.assertFalse(response["ok"])
            self.assertEqual(response["error"]["code"], "CONSTRAINT_ERROR")

        os.environ.pop("DINEDB_PERSISTENT", None)
        os.environ.pop("DINEDB_DATA_DIR", None)
        os.environ.pop("DINEDB_FSYNC", None)


if __name__ == "__main__":
    unittest.main()
