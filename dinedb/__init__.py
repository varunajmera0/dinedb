"""Definition: public API exports for dinedb M1.

Example:
    from dinedb import Column, StorageEngine

    storage = StorageEngine()
    storage.create_table(
        "users",
        [
            Column(name="id", data_type="INT", is_primary_key=True),
            Column(name="name", data_type="TEXT"),
        ],
    )
"""

from dinedb.errors import ConstraintError, DatabaseError, SchemaError, StorageError
from dinedb.backends import JsonFileBackend
from dinedb.models import Column, TableSchema
from dinedb.service import DineDBService
from dinedb.storage import StorageEngine

__all__ = [
    "Column",
    "ConstraintError",
    "DatabaseError",
    "DineDBService",
    "JsonFileBackend",
    "SchemaError",
    "StorageEngine",
    "StorageError",
    "TableSchema",
]
