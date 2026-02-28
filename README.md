# Dinedb

Learning-first database internals project focused on how real databases work: schema validation, persistence, indexing, SQL execution, crash recovery, and early transaction/isolation mechanics. Current stage: **M6.3 (committed-read rule)**.

## What’s Implemented So Far

- **M1: Schema + row validation**
  - Column metadata, type checks, PK metadata, and constraint errors.
- **M2: Durable persistence**
  - Pluggable storage backend (in-memory + JSON file backend).
  - Schema persistence and append-only row files.
  - Optional `fsync` for safer writes.
- **M3: Primary key indexing**
  - PK index file (`*.pk.json`) with offset lookup.
  - Index validation and rebuild tools.
- **M4: SQL path (tokenizer → parser → AST → executor)**
  - Minimal SQL: `CREATE`, `INSERT`, `SELECT`, `UPDATE`, `DELETE`.
  - Deterministic parse errors and executor dispatch.
  - `SELECT * FROM table;` and `SELECT ... WHERE pk = ...`.
- **M5: Crash safety basics**
  - JSONL WAL (`wal.log`) with write-ahead discipline.
  - WAL replay on startup.
  - Applied-state tracking via `wal_state.json`.
  - Crash simulation tests.
- **M6: Concurrency and isolation (early)**
  - `BEGIN`, `COMMIT`, `ROLLBACK`.
  - Single-writer rule.
  - Committed-read rule: other executors cannot read while an active writer transaction is open.

## What This Project Is Trying To Teach

This project is about understanding why databases are hard:
- how bad data is rejected before it poisons storage
- how state survives process restarts
- how indexes trade write cost for read speed
- how SQL text becomes executable operations
- how WAL and recovery repair crash-damaged state
- how transactions and isolation start shaping concurrent behavior

The goal is not just "run SQL." The goal is to understand the internal layers behind systems like PostgreSQL, InnoDB, and SQLite.

## Run (in-memory)

```bash
python main.py
```

## Run (persistent)

Use env vars to enable persistence and durability options:

```bash
export DINEDB_PERSISTENT=1
export DINEDB_DATA_DIR=./data
export DINEDB_FSYNC=1
python main.py
```

## Requirements

No external dependencies. Python 3.10+ is enough.

## Env Vars

- `DINEDB_PERSISTENT`: `1|true|yes|on` to enable file-backed storage.
- `DINEDB_DATA_DIR`: path for data files (`schema.json`, `*.tbl`).
- `DINEDB_FSYNC`: `1|true|yes|on` to force fsync on writes (slower, safer).

## CLI Notes

- SQL-only shell. Enter statements directly; each must end with `;` (multi-line supported).
- Exit with Ctrl+D.
- Current transaction statements:
  - `BEGIN;`
  - `COMMIT;`
  - `ROLLBACK;`

Example:
```text
CREATE TABLE users (id INT PRIMARY KEY, name TEXT);
INSERT INTO users VALUES (1, 'Asha');
BEGIN;
UPDATE users SET name = 'Rahul' WHERE id = 1;
COMMIT;
SELECT * FROM users WHERE id = 1;
DELETE FROM users WHERE id = 1;
```

## Current Limits

These parts are intentionally still incomplete:
- no transaction-local write buffer yet
- no real rollback of staged writes yet
- no row-level locking or MVCC
- no joins yet
- no page model / buffer manager yet

So `BEGIN/COMMIT/ROLLBACK` and isolation are present in early form, but not yet production-grade.

## Next Plan

- **M6.4:** transaction-local write buffer.
- **M6.5:** rollback semantics.
- **M6.6:** isolation/concurrency tests.
- **M4.9 later:** joins.
- **M7:** storage evolution toward a page model and free-space tracking.
