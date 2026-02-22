from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dinedb.models import Column
from dinedb.service import DineDBService


class M13StructuredResponseTests(unittest.TestCase):
    def test_create_table_success_payload(self) -> None:
        service = DineDBService()
        response = service.create_table(
            "users",
            [
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )

        self.assertTrue(response["ok"])
        self.assertIn("created", response["message"])
        self.assertEqual(response["meta"]["operation"], "create_table")
        self.assertRegex(response["meta"]["trace_id"], r"^[0-9a-f-]{36}$")
        self.assertRegex(response["meta"]["timestamp_utc"], r"^\d{4}-\d{2}-\d{2}T")

    def test_insert_success_payload(self) -> None:
        service = DineDBService()
        service.create_table(
            "users",
            [
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )

        response = service.insert("users", [1, "Asha"])
        self.assertTrue(response["ok"])
        self.assertEqual(response["row"], {"id": 1, "name": "Asha"})
        self.assertEqual(response["meta"]["operation"], "insert")
        self.assertRegex(response["meta"]["trace_id"], r"^[0-9a-f-]{36}$")
        self.assertRegex(response["meta"]["timestamp_utc"], r"^\d{4}-\d{2}-\d{2}T")

    def test_schema_error_code_mapping(self) -> None:
        service = DineDBService()
        response = service.insert("users", [1, "Asha"])
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "SCHEMA_ERROR")
        self.assertIn("does not exist", response["error"]["message"])
        self.assertEqual(response["meta"]["operation"], "insert")
        self.assertRegex(response["meta"]["trace_id"], r"^[0-9a-f-]{36}$")
        self.assertRegex(
            response["meta"]["timestamp_utc"],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
        )

    def test_constraint_error_code_mapping(self) -> None:
        service = DineDBService()
        service.create_table(
            "users",
            [
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )
        service.insert("users", [1, "Asha"])

        duplicate_response = service.insert("users", [1, "Rahul"])
        self.assertFalse(duplicate_response["ok"])
        self.assertEqual(duplicate_response["error"]["code"], "CONSTRAINT_ERROR")
        self.assertIn("Duplicate PRIMARY KEY", duplicate_response["error"]["message"])
        self.assertEqual(duplicate_response["meta"]["operation"], "insert")
        self.assertRegex(duplicate_response["meta"]["trace_id"], r"^[0-9a-f-]{36}$")

    def test_create_table_error_includes_operation_and_observability_fields(self) -> None:
        service = DineDBService()
        service.create_table(
            "users",
            [Column(name="id", data_type="INT", is_primary_key=True)],
        )

        duplicate_table_response = service.create_table(
            "users",
            [Column(name="id", data_type="INT", is_primary_key=True)],
        )
        self.assertFalse(duplicate_table_response["ok"])
        self.assertEqual(duplicate_table_response["error"]["code"], "CONSTRAINT_ERROR")
        self.assertEqual(duplicate_table_response["meta"]["operation"], "create_table")
        self.assertRegex(duplicate_table_response["meta"]["trace_id"], r"^[0-9a-f-]{36}$")
        self.assertIsNotNone(
            re.match(
                r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
                duplicate_table_response["meta"]["timestamp_utc"],
            )
        )


if __name__ == "__main__":
    unittest.main()
