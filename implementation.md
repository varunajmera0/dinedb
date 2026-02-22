# Learning-First DB Build Kit

## Summary
This spec kit teaches database internals step-by-step using a mini Python SQL engine.  
Every milestone explains:
1. what we build,
2. what breaks,
3. how we fix it in our mini DB,
4. how production databases solve the same problem.

## Assumptions and Defaults
- Language: Python (learning-first).
- Query surface: minimal SQL first, expanded later.
- Data model: file-backed storage initially.
- Pedagogy: slow progression, no skipped steps.
- Domain examples: chosen per topic (e-commerce, food delivery, analytics, fintech, SaaS).

## Starter Deliverables
- `implementation.md`
- `notes/00-overview.md`
- `notes/01-schema-and-row-validation.md`
- `notes/02-persistence-and-file-layout.md`
- `notes/03-primary-key-index.md`
- `notes/04-query-path-parser-executor.md`
- `notes/05-crash-safety-and-atomicity.md`
- `notes/06-concurrency-and-isolation.md`
- `notes/07-page-model-and-scaling.md`
- `notes/08-productionish-roadmap.md`

## Core Interfaces and Types
### SQL AST Contracts
- `CreateTable`
- `Insert`
- `Select`

### Storage Contracts
- `create_table(table_name, columns)`
- `insert(table_name, values)`
- `select(table_name, columns, where_column=None, where_value=None, limit=None)`
- index lookup path and fallback to table scan

### Engine Contract
- `execute(sql: str) -> dict`
- response shape:
  - create: `{"ok": true, "message": "..."}`
  - insert: `{"ok": true, "row": {...}, "message": "..."}`
  - select: `{"ok": true, "rows": [...], "count": n, "message": "..."}`

### Error Taxonomy
- parse errors
- schema/constraint errors
- storage errors

## Milestone Template
Use this exact checklist format in each implementation iteration:
1. Objective
2. Internal design (data structures, control flow)
3. Problem encountered (real failure mode)
4. Our solution in mini DB
5. Real DB solution in production
6. Real-world case (company/user scenario)
7. Implementation tasks (file-by-file)
8. Acceptance checks
9. Exercise

---

## M0: Clean Baseline
### 1. Objective
Remove ambiguity and establish a consistent scaffold.

### 2. Internal Design
Create stable project paths and runtime directories:
- `dinedb/` for engine code
- `tests/` for validation
- `data/` for runtime files
- `notes/` for learning modules

### 3. Problem Encountered
Partially implemented systems create mixed assumptions and hidden bugs.

### 4. Our Solution in Mini DB
Reset to a known baseline and rebuild in explicit milestones.

### 5. Real DB Solution in Production
Teams run controlled migrations, staged rollouts, and compatibility gates.

### 6. Real-World Case
An internal data platform inherits old scripts and new services; inconsistent schema assumptions cause ingestion failures.

### 7. Implementation Tasks
- Confirm scaffold folders exist.
- Keep runtime artifacts (`data/*`) out of design docs.
- Keep milestone checklists versioned with docs.

### 8. Acceptance Checks
- Project structure matches agreed starter paths.
- Learning docs exist before new feature expansion.

### 9. Exercise
List all files that are source-of-truth for architecture decisions.  
Expected outcome: only `implementation.md` and `notes/*.md`.

---

## M1: Schema + Row Validation
### 1. Objective
Define table metadata and prevent invalid rows from entering storage.

### 2. Internal Design
- `Column(name, data_type, is_primary_key)`
- `TableSchema(name, columns)`
- validation step in insert path before persistence

### 3. Problem Encountered
Malformed rows poison reads and downstream logic.

### 4. Our Solution in Mini DB
Strict type and column validation at write time.

### 5. Real DB Solution in Production
Catalog-managed schemas and typed record encoding.

### 6. Real-World Case
E-commerce supplier feed sends `"price": "N/A"` into numeric field; analytics and search ranking fail.

### 7. Implementation Tasks
- `dinedb/models.py`: column/schema types and `validate_row`.
- `dinedb/storage.py`: call validation before append.
- `tests/test_storage.py`: invalid type and missing column cases.

### 8. Acceptance Checks
- Invalid insert rejects with deterministic error.
- Valid insert persists and remains queryable.

### 9. Exercise
Try inserting a row with an unknown column.  
Expected outcome: write is rejected before touching table file.

---

## M2: Durable Persistence
### 1. Objective
Persist schema and rows across process restarts.

### 2. Internal Design
- `data/schema.json` for table metadata
- `data/<table>.tbl` as append-only JSONL rows
- startup loads schema into memory

### 3. Problem Encountered
In-memory-only state disappears on restart.

### 4. Our Solution in Mini DB
Disk-backed schema and append protocol for row files.

### 5. Real DB Solution in Production
Persistent heap/page files and metadata catalogs.

### 6. Real-World Case
Food delivery ops updates menu; service restarts and menu silently reverts.

### 7. Implementation Tasks
- `dinedb/storage.py`: load/save schema and append rows.
- `tests/test_smoke.py`: restart engine and verify row survival.

### 8. Acceptance Checks
- Same query result before and after restart.
- Table definitions remain intact after restart.

### 9. Exercise
Insert rows, restart process, run select again.  
Expected outcome: identical dataset returned.

---

## M3: Primary Key Indexing
### 1. Objective
Avoid full scans for primary key lookups.

### 2. Internal Design
- sidecar index file: `data/<table>.pk.json`
- map `pk_value -> row byte offset`
- select path: use index for `WHERE pk = value`, else scan

### 3. Problem Encountered
Point lookups degrade linearly with table size.

### 4. Our Solution in Mini DB
Maintain PK index during insert and use direct seek on lookup.

### 5. Real DB Solution in Production
B+Tree or LSM index structures with buffer caching.

### 6. Real-World Case
Rider/order support lookup in peak traffic times out because every request scans large files.

### 7. Implementation Tasks
- `dinedb/storage.py`: create/read/write PK index file.
- `dinedb/storage.py`: implement indexed lookup path.
- `tests/test_storage.py`: verify index hit correctness.

### 8. Acceptance Checks
- Duplicate PK insert is rejected.
- `WHERE pk = ...` returns correct row without full scan fallback.

### 9. Exercise
Manually inspect index file after inserts.  
Expected outcome: each PK maps to a stable row location.

---

## M4: SQL Path (Parser -> AST -> Executor)
### 1. Objective
Translate SQL text into deterministic execution behavior.

### 2. Internal Design
- parser builds AST nodes (`CreateTable`, `Insert`, `Select`)
- engine dispatches AST to storage actions
- stable output payload contract

### 3. Problem Encountered
Loose parsing causes ambiguous behavior and hard-to-debug failures.

### 4. Our Solution in Mini DB
Constrained grammar and explicit parse errors.

### 5. Real DB Solution in Production
Parser, optimizer, and execution plan tree.

### 6. Real-World Case
Analytics team runs slightly malformed SQL; inconsistent parser behavior creates trust issues in dashboards.

### 7. Implementation Tasks
- `dinedb/sql.py`: parse supported SQL subset.
- `dinedb/engine.py`: map AST to storage methods.
- `main.py`: CLI loop and structured result output.
- `tests/test_parser.py`: valid/invalid statement coverage.

### 8. Acceptance Checks
- Supported SQL forms parse and execute.
- Unsupported SQL returns deterministic parse errors.

### 9. Exercise
Run one valid and one invalid query.  
Expected outcome: valid query returns rows; invalid query returns precise parse error.

---

## M5: Crash Safety Basics
### 1. Objective
Prevent corrupt metadata/index files from partial writes.

### 2. Internal Design
- write temp file first
- `fsync` temp file where practical
- atomic rename to target path

### 3. Problem Encountered
Crash during write leaves truncated JSON index or schema file.

### 4. Our Solution in Mini DB
Atomic replace discipline for metadata and index writes.

### 5. Real DB Solution in Production
WAL, checkpoints, and recovery replay.

### 6. Real-World Case
Checkout service crashes mid-write; orders acknowledged but metadata partially persisted.

### 7. Implementation Tasks
- `dinedb/storage.py`: atomic write helper for JSON files.
- `tests/test_storage.py`: simulate interrupted metadata write path.

### 8. Acceptance Checks
- No partially written JSON files after simulated interruption.
- Restart still loads prior consistent state.

### 9. Exercise
Force a failure before rename in test harness.  
Expected outcome: original file remains valid and readable.

---

## M6: Concurrency Model
### 1. Objective
Define safe behavior when multiple operations run concurrently.

### 2. Internal Design
- single-writer guard
- readers allowed with deterministic visibility model
- explicit lock acquisition/release boundaries

### 3. Problem Encountered
Concurrent writes can cause lost updates and corrupted indexes.

### 4. Our Solution in Mini DB
Serialize writes and document read consistency guarantees.

### 5. Real DB Solution in Production
Lock managers and MVCC snapshot isolation.

### 6. Real-World Case
Banking app posts two simultaneous balance updates; one update is silently overwritten.

### 7. Implementation Tasks
- `dinedb/storage.py`: add writer lock strategy.
- `tests/test_storage.py`: concurrent write contention tests.

### 8. Acceptance Checks
- No lost updates in simulated concurrent writes.
- Rejected writes return clear contention errors or retry signals.

### 9. Exercise
Run two writer threads updating same key.  
Expected outcome: deterministic serialization, no corrupted state.

---

## M7: Storage Evolution (JSONL -> Page Model)
### 1. Objective
Design migration path from simple file format to scalable page-based storage.

### 2. Internal Design
- define page abstraction (header, slots, payload)
- free-space tracking strategy
- compatibility boundary for old row format

### 3. Problem Encountered
JSONL offsets and full-file scans fail at scale.

### 4. Our Solution in Mini DB
Plan page-based I/O and controlled migration stages.

### 5. Real DB Solution in Production
Buffer manager, slotted pages, vacuum/compaction, background maintenance.

### 6. Real-World Case
SaaS logging workload with hot keys produces poor locality and high read amplification.

### 7. Implementation Tasks
- `notes/07-page-model-and-scaling.md`: page structure and migration design.
- `implementation.md`: acceptance gates for format transition.

### 8. Acceptance Checks
- Page format spec is testable and backward compatibility path is explicit.
- Migration plan includes rollback strategy.

### 9. Exercise
Sketch one page layout with two variable-length rows and slot directory.  
Expected outcome: offsets and free space boundaries are unambiguous.

---

## Test Matrix (Cross-Milestone)
1. Schema creation success/failure
2. Type validation failures
3. PK uniqueness enforcement
4. Persistence across restart
5. Indexed lookup vs scan correctness
6. Deterministic parser errors
7. Crash-safety simulation for metadata/index rewrite
8. Single-writer concurrency behavior

## Sequencing / Handoff
1. Keep `implementation.md` as the execution checklist.
2. Study and complete `notes/00` through `notes/04`.
3. Continue with `notes/05` through `notes/08`.
4. For each implementation step, use milestone acceptance checks before moving ahead.
