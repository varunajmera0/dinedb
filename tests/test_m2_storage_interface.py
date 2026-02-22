from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dinedb.models import Column
from dinedb.storage import StorageEngine


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def create_table(self, table_name: str, columns: list[Column]) -> None:
        self.calls.append(("create_table", table_name, len(columns)))

    def insert(self, table_name: str, values: list[Any]) -> dict[str, Any]:
        self.calls.append(("insert", table_name, tuple(values)))
        return {"table": table_name, "values": list(values)}


class M2StorageInterfaceTests(unittest.TestCase):
    def test_default_backend_behaves_like_m1(self) -> None:
        storage = StorageEngine()
        storage.create_table(
            "users",
            [
                Column(name="id", data_type="INT", is_primary_key=True),
                Column(name="name", data_type="TEXT"),
            ],
        )

        inserted = storage.insert("users", [1, "Asha"])
        self.assertEqual(inserted, {"id": 1, "name": "Asha"})
        self.assertIn("users", storage._schemas)
        self.assertEqual(storage._rows["users"], [{"id": 1, "name": "Asha"}])

    def test_custom_backend_is_pluggable(self) -> None:
        fake_backend = FakeBackend()
        storage = StorageEngine(backend=fake_backend)

        storage.create_table("events", [Column(name="id", data_type="INT")])
        inserted = storage.insert("events", [101])

        self.assertEqual(
            fake_backend.calls,
            [
                ("create_table", "events", 1),
                ("insert", "events", (101,)),
            ],
        )
        self.assertEqual(inserted, {"table": "events", "values": [101]})


if __name__ == "__main__":
    unittest.main()
