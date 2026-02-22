from __future__ import annotations


class DatabaseError(Exception):
    """Base exception for dinedb."""

    pass


class StorageError(DatabaseError):
    """Storage-layer error.

    Example:
        Raised when storage state is unreadable or write path fails.
    """

    pass


class SchemaError(StorageError, ValueError):
    """Schema mismatch error.

    Example:
        Column 'id' must be INT.
    """

    pass


class ConstraintError(StorageError, ValueError):
    """Constraint violation error.

    Example:
        Duplicate PRIMARY KEY '1'.
    """

    pass
