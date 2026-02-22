# Dinedb

Database internals project focused on how real databases work: schema validation, persistence, indexing, and a minimal SQL path (tokenizer → parser → AST → executor). Current stage: **M4.x (SQL parser + executor)**.

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
  - Minimal SQL: `CREATE`, `INSERT`, `SELECT`.
  - Deterministic parse errors and executor dispatch.
  - `SELECT * FROM table;` and `SELECT ... WHERE pk = ...`.

## Run (in-memory)

```bash
.venv/bin/python main.py
```

## Run (persistent)

Use env vars to enable persistence and durability options:

```bash
export DINEDB_PERSISTENT=1
export DINEDB_DATA_DIR=./data
export DINEDB_FSYNC=1
.venv/bin/python main.py
```

## Requirements

No external dependencies. Python 3.10+ is enough.

## Env Vars

- `DINEDB_PERSISTENT`: `1|true|yes|on` to enable file-backed storage.
- `DINEDB_DATA_DIR`: path for data files (`schema.json`, `*.tbl`).
- `DINEDB_FSYNC`: `1|true|yes|on` to force fsync on writes (slower, safer).

## CLI Notes

- `.pk <table> <id>` returns a structured response that includes `meta.index_used`.
  - `true` means the PK index file was used.
  - `false` means a scan path was used (in-memory backend).
- `.sql <statement>` runs SQL via the executor (CREATE/INSERT/SELECT).
- You can also paste SQL directly (must start with `CREATE`, `INSERT`, or `SELECT`).
- `.sql_demo` runs a mini SQL script showing one successful and one rejected query.

Example:
```text
.sql CREATE TABLE users (id INT PRIMARY KEY, name TEXT);
.sql INSERT INTO users VALUES (1, 'Asha');
.sql SELECT * FROM users WHERE id = 1;
```

## Next Plan

- **M4 (finish):** more parser errors + executor coverage (projection/limit, stricter validation).
- **M5:** crash safety basics (atomic metadata/index writes).
- **M6:** concurrency model (single-writer rule + lock discipline).
- **M7:** storage evolution toward a page model and free-space tracking.