from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dinedb.errors import ConstraintError, SchemaError
from dinedb.models import Column, TableSchema
from dinedb.storage import StorageEngine


class M1SchemaValidationTests(unittest.TestCase):
    def _log(self, message: str) -> None:
        print(f"[M1SchemaValidationTests] {message}")

    def test_create_table_rejects_empty_columns(self) -> None:
        self._log("checking that CREATE TABLE rejects an empty column list")
        storage = StorageEngine()
        with self.assertRaisesRegex(SchemaError, "at least one column"):
            storage.create_table("users", [])

    def test_create_table_rejects_duplicate_columns(self) -> None:
        self._log("checking duplicate column name validation")
        storage = StorageEngine()
        columns = [
            Column(name="id", data_type="INT", is_primary_key=True),
            Column(name="id", data_type="TEXT"),
        ]
        with self.assertRaisesRegex(SchemaError, "Duplicate column"):
            storage.create_table("users", columns)

    def test_create_table_rejects_unsupported_type(self) -> None:
        self._log("checking unsupported type rejection")
        storage = StorageEngine()
        columns = [Column(name="created_at", data_type="TIMESTAMP")]
        with self.assertRaisesRegex(SchemaError, "Unsupported type"):
            storage.create_table("users", columns)

    def test_create_table_rejects_multiple_primary_keys(self) -> None:
        self._log("checking multiple primary key rejection")
        storage = StorageEngine()
        columns = [
            Column(name="id", data_type="INT", is_primary_key=True),
            Column(name="email", data_type="TEXT", is_primary_key=True),
        ]
        with self.assertRaisesRegex(SchemaError, "Only one PRIMARY KEY"):
            storage.create_table("users", columns)

    def test_insert_rejects_wrong_value_count(self) -> None:
        self._log("checking insert arity validation")
        storage = StorageEngine()
        storage.create_table(
            "users",
            [
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )
        with self.assertRaisesRegex(SchemaError, "Expected 2 values, got 1"):
            storage.insert("users", [1])

    def test_insert_rejects_type_mismatch(self) -> None:
        self._log("checking insert type validation")
        storage = StorageEngine()
        storage.create_table(
            "users",
            [
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )
        with self.assertRaisesRegex(SchemaError, "must be INT"):
            storage.insert("users", ["1", "Asha"])

    def test_insert_rejects_duplicate_primary_key(self) -> None:
        self._log("checking duplicate primary key rejection")
        storage = StorageEngine()
        storage.create_table(
            "users",
            [
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )
        storage.insert("users", [1, "Asha"])
        with self.assertRaisesRegex(ConstraintError, "Duplicate PRIMARY KEY"):
            storage.insert("users", [1, "Sam"])

    def test_table_schema_validate_row_rejects_unknown_column(self) -> None:
        self._log("checking unknown column rejection during row validation")
        schema = TableSchema(
            name="users",
            columns=[
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )
        with self.assertRaisesRegex(SchemaError, "Unknown column"):
            schema.validate_row({"id": 1, "name": "Asha", "extra": "x"})

    def test_create_table_rejects_duplicate_table_name(self) -> None:
        self._log("checking duplicate table creation rejection")
        storage = StorageEngine()
        columns = [Column(name="id", data_type="INT", is_primary_key=True)]
        storage.create_table("users", columns)
        with self.assertRaisesRegex(ConstraintError, "already exists"):
            storage.create_table("users", columns)

    def test_insert_rejects_unknown_table(self) -> None:
        self._log("checking insert into unknown table rejection")
        storage = StorageEngine()
        with self.assertRaisesRegex(SchemaError, "does not exist"):
            storage.insert("users", [1])


if __name__ == "__main__":
    unittest.main()
