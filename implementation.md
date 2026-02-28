# Learning-First DB Build Kit

## Summary
This spec kit teaches database internals step-by-step using a mini Python SQL engine.  
Every milestone follows the same architectural framework:
1) Lame Analogy (hook),  
2) Technical Bridge (why before how),  
3) Senior Implementation Roadmap (pro definition + senior insight + bottom line),  
then tasks, checks, and exercises.

## Tradeoff Rule (Mandatory)
Every feature must explicitly document:
- **Primary tradeoff** (what we gain vs what we lose),
- **Alternative approach** (what a different design would optimize),
- **Why we chose this** (given learning vs production constraints).

## Assumptions and Defaults
- Language: Python (learning-first).
- Query surface: minimal SQL first, expanded later.
- Data model: file-backed storage initially.
- Pedagogy: slow progression, no skipped steps.
- Domain examples: chosen per topic (e-commerce, food delivery, analytics, fintech, SaaS).

## Deliverables
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
- `Update`
- `Delete`

### Storage Contracts
- `create_table(table_name, columns)`
- `insert(table_name, values)`
- `select_all(table_name)`
- `get_by_pk(table_name, pk_value)`
- `update_by_pk(table_name, pk_value, updates)`
- `delete_by_pk(table_name, pk_value)`

### Engine Contract
- `execute(sql: str) -> dict`
- create: `{"ok": true, "message": "..."}`
- insert: `{"ok": true, "row": {...}, "message": "..."}`
- select: `{"ok": true, "rows": [...], "count": n}`
- update: `{"ok": true, "updated": 0|1, "row": {...}|null}`
- delete: `{"ok": true, "deleted": 0|1}`

### Error Taxonomy
- parse errors
- schema/constraint errors
- storage errors

## Major Database Features (Production Map)
- **Storage engine:** page model, buffer pool, free-space tracking, compression.
- **Indexing:** secondary/composite indexes, B+Tree/LSM variants.
- **Query engine:** optimizer, joins, aggregations, sorting, window functions, views/CTEs.
- **Transactions:** WAL, checkpoints, crash recovery, rollback.
- **Concurrency:** locks/MVCC, isolation levels, deadlock handling.
- **Ops:** backups/PITR, replication, monitoring, query plans/explain.

## What Real Databases Have
When people say "real database," they usually mean an engine that combines several layers at once:
- **Logical layer:** SQL parser, semantic validation, query planning, relational operators.
- **Storage layer:** durable files, page layout, buffer manager, free-space management.
- **Access-path layer:** primary and secondary indexes, ordered/range access, index maintenance.
- **Transaction layer:** WAL, checkpoints, recovery, rollback, commit protocol.
- **Concurrency layer:** locks or MVCC, isolation levels, deadlock handling.
- **Operational layer:** backup/restore, PITR, metrics, explain plans, replication, failover.

The important architectural point is that these are not optional decorations. They are the layers that turn "data in files" into a reliable database system.

## Real Database Core Features We Intend to Implement
This project will not stop at the toy-DB layer. The planned implementation set includes the core features that make a database trustworthy and useful:
- **Schema and constraints:** typed rows, PK enforcement, validation at write time.
- **Durable storage:** persistent metadata and row files.
- **Primary-key indexing:** direct lookup path instead of full scans.
- **SQL path:** tokenizer, parser, AST, executor.
- **Crash safety:** WAL, replay on startup, checkpoints/applied-state tracking.
- **Rollback foundation:** undo/redo-aware recovery model.
- **Concurrency control:** single-writer first, then stronger locking/isolation.
- **Relational execution:** joins as an advanced SQL milestone.
- **Storage-engine evolution:** page model, free-space tracking, buffer-manager concepts.

This means we are not only studying these features. We intend to build a meaningful subset of them directly in `dinedb`.

## Real Database Features We Will Likely Describe But Not Fully Implement
Some production features are important to understand, but are currently outside the realistic scope of this learning-first engine:
- full cost-based optimizer
- replication and failover
- PITR and backup tooling
- full MVCC implementation
- distributed consensus
- deep security model (roles, authz, encryption)

## What Production Databases Do Later
After the learning-first milestones, production engines like PostgreSQL, InnoDB, SQL Server, and Oracle go much further in the same areas:
- **Concurrency expansion:** row/page/table locks, lock manager, deadlock detection, deadlock resolution.
- **MVCC and visibility:** snapshot reads, transaction IDs, undo segments or vacuum-driven cleanup.
- **Isolation-level contracts:** Read Committed, Repeatable Read, Serializable, predicate locking in stricter engines.
- **Recovery depth:** binary WAL/redo records, checksums, torn-page detection, full checkpoints, group commit.
- **Query planning:** cost-based optimizer, join reordering, statistics, cardinality estimation, plan caching.
- **Storage-engine depth:** slotted pages, buffer pool eviction, background flush, compaction or vacuum.
- **Operational controls:** backup/restore, PITR, replication, failover, metrics, explain plans.

The senior architectural point is that these are not separate topics. They are the production-grade continuations of the same milestone chain:
- `M5` grows into deeper recovery and commit protocol
- `M6` grows into serious concurrency control and isolation levels
- later SQL milestones grow into joins, optimizer rules, and statistics-driven planning

Real database examples:
- **PostgreSQL**: MVCC, WAL, checkpoints, vacuum, cost-based optimizer, replication.
- **InnoDB**: redo + undo, row locks, MVCC, purge/cleanup, buffer pool, crash recovery.

Real-world examples:
- **Banking** needs stronger isolation and recovery semantics.
- **E-commerce** needs optimizer and indexing depth as query shapes grow.
- **Ride-hailing / food delivery** needs high write concurrency with correct state transitions.

## Core Features → Milestones Mapping
- **JOINs** → **M4.9** (advanced SQL path, join execution).
- **Locks / Isolation** → **M6** (concurrency control).
- **ACID**
  - **A + D** → **M5** (WAL + recovery)
  - **I** → **M6** (locks/MVCC)
  - **C** → **M1 + M5/M6** (constraints + transactional guarantees)
- **Rollback** → **M5** (undo via WAL)
- **Recovery** → **M5** (WAL replay + checkpoints)

---

## M0: Clean Baseline
### Lame Analogy (Hook)
Clearing a messy desk before you start a project so you don’t confuse old notes with new work.

### Technical Bridge (Why)
Mixed assumptions cause hidden bugs. At scale, ambiguity is the root of inconsistent behavior.

### Senior Implementation Roadmap
**Pro Definition:** Establish a stable scaffold and source of truth.  
**Senior Insight:** If the scaffolding changes mid-stream, every later milestone inherits risk.  
**Bottom Line:** A clean baseline prevents systemic drift.

### Implementation Tasks (file-by-file)
- Ensure `dinedb/`, `tests/`, `data/`, `notes/` exist.
- Keep runtime artifacts out of design docs.

### Acceptance Checks
- Project structure matches agreed starter paths.
- Learning docs exist before new feature expansion.

### Exercise
List all files that are source-of-truth for architecture decisions.  
Expected outcome: only `implementation.md` and `notes/*.md`.

---

## M1: Schema + Row Validation
### Lame Analogy (Hook)
A restaurant menu with strict order rules so the kitchen doesn’t receive nonsense.

### Technical Bridge (Why)
Garbage in leads to garbage out. Data integrity must be enforced at the boundary.

### Senior Implementation Roadmap
**Pro Definition:** Type enforcement and constraint validation at write time.  
**Senior Insight:** Strict schemas reduce flexibility but prevent corruption early.  
**Bottom Line:** Bad data poisons everything else.

### Implementation Tasks
- `dinedb/models.py`: `Column`, `TableSchema`, `validate_row`.
- `dinedb/storage.py`: enforce validation before persistence.

### Acceptance Checks
- Invalid insert rejects with deterministic error.
- Valid insert persists and remains queryable.

### Exercise
Insert a row with an unknown column.  
Expected outcome: write is rejected before touching table file.

---

## M2: Durable Persistence
### Lame Analogy (Hook)
Writing receipts in a ledger so the records survive after you leave the counter.

### Technical Bridge (Why)
Memory is volatile. Without disk persistence, restarts destroy state.

### Senior Implementation Roadmap
**Pro Definition:** Stable on-disk state for schema and data.  
**Senior Insight:** Sequential I/O beats random I/O for throughput.  
**Bottom Line:** Without persistence, you don’t have a database.

### Implementation Tasks
- `dinedb/backends/json_file_backend.py`: schema + append-only rows.
- `dinedb/storage.py`: backend abstraction.

### Acceptance Checks
- Same query result before and after restart.
- Table definitions remain intact after restart.

### Exercise
Insert rows, restart process, run select again.  
Expected outcome: identical dataset returned.

---

## M3: Primary Key Indexing
### Lame Analogy (Hook)
A phonebook vs flipping every page for one name.

### Technical Bridge (Why)
Full scans scale linearly. That’s fatal for latency.

### Senior Implementation Roadmap
**Pro Definition:** PK index mapping `key -> row location`.  
**Senior Insight:** Indexes accelerate reads but increase write cost.  
**Bottom Line:** Predictable read latency is mandatory.

### Implementation Tasks
- `dinedb/backends/json_file_backend.py`: PK index file.
- `dinedb/storage.py`: indexed lookup path.

### Acceptance Checks
- Duplicate PK insert is rejected.
- `WHERE pk = ...` returns correct row without full scan.

### Exercise
Inspect index file after inserts.  
Expected outcome: each PK maps to a stable row location.

---

## M4: SQL Path (Parser → AST → Executor)
### Lame Analogy (Hook)
A waiter translating spoken orders into clear tickets the kitchen understands.

### Technical Bridge (Why)
Text is ambiguous. A deterministic AST prevents misinterpretation.

### Senior Implementation Roadmap
**Pro Definition:** Tokenize → parse → AST → execution dispatch.  
**Senior Insight:** Parser ambiguity destroys trust in results.  
**Bottom Line:** The SQL path is the human-to-engine contract.

### Implementation Tasks
**M4.1 Tokenizer**
- `dinedb/sql/sql_parser.py`: `TokenType`, `Token`, `tokenize`.

**M4.2 Parser → AST**
- `dinedb/sql/sql_parser.py`: `CreateTable`, `Insert`, `Select`, `Update`, `Delete`.

**M4.3 Executor**
- `dinedb/sql/engine.py`: map AST to storage methods.
- `dinedb/storage.py`: `select_all`, `update_by_pk`, `delete_by_pk`.

**M4.4 CLI Integration**
- `main.py`: SQL shell execution path.

**M4.5 Hardening**
- deterministic parse errors
- WHERE type validation
- semicolon-in-string handling

### Acceptance Checks
- Supported SQL forms parse and execute.
- Unsupported SQL returns deterministic errors.

### Exercise
Run one valid and one invalid query.  
Expected outcome: valid query returns rows; invalid query returns precise parse error.

---

## M5: Crash Safety Basics
### Lame Analogy (Hook)
Writing orders in a log before cooking them so you can recover after a mistake.

### Technical Bridge (Why)
Writes are not atomic. Crashes can corrupt files mid-write.

### Senior Implementation Roadmap
**Pro Definition:** WAL and atomic metadata writes.  
**Senior Insight:** WAL adds write amplification but makes recovery deterministic.  
**Bottom Line:** Crash recovery is non-negotiable.

### Tradeoffs & Alternatives
- **Tradeoff:** JSONL WAL is easy to inspect but slower and larger than binary WAL.
- **Alternative:** start directly with binary WAL for better space efficiency and faster parsing.
- **Why we chose this:** M5.1/M5.2 use JSONL WAL so intent and failure paths stay visible while recovery semantics are still being learned. Binary WAL is a later production-oriented step after replay/checkpoint behavior is stable.

### Implementation Tasks
- `M5.1`: define JSONL WAL record format in the file backend.
- `M5.2`: enforce log-before-data ordering for `INSERT`, `UPDATE`, `DELETE`.
- `M5.3`: replay WAL on startup by applying full WAL idempotently and rewriting touched tables/indexes.
- `M5.4`: checkpoint / applied-LSN tracking.
- `M5.5`: consider binary WAL once semantics are stable and JSONL inspection is no longer the priority.
- atomic metadata/index writes (temp + rename).

### M5.3 Tradeoff
- **Tradeoff:** full startup replay is simple and correct for a learning engine, but startup cost grows with log size.
- **Alternative:** applied-LSN tracking plus checkpoints to bound replay cost.
- **Why we chose this:** replay semantics must be correct before replay cost is optimized.

### M5.4 Tradeoff
- **Tradeoff:** applied-sequence tracking reduces replay work but adds more metadata that itself must stay consistent.
- **Alternative:** replay the full WAL on every startup and accept slower boots.
- **Why we chose this:** once replay semantics are correct, bounding startup time is the next reliability concern.
- **Real database example:** PostgreSQL uses WAL positions and checkpoints to narrow recovery; InnoDB uses redo-log progress and checkpoint metadata for the same reason.
- **Real-world example:** payment or ordering systems need recovery that is not only correct, but also fast enough to bring service back online under incident pressure.

### M5.5 Tradeoff
- **Tradeoff:** crash simulation tests are awkward and slower than happy-path tests, but they are the only honest way to validate recovery behavior.
- **Alternative:** trust code inspection and standard tests only.
- **Why we chose this:** recovery code must be proven against broken state, not just reasoned about.
- **Real database example:** serious engines like PostgreSQL and InnoDB are validated heavily around crash boundaries because recovery bugs destroy trust.
- **Real-world example:** payments, banking, ride-hailing, and ordering systems depend on post-crash correctness, not just normal-path correctness.

### Acceptance Checks
- No partial JSON files after simulated interruption.
- Restart still loads prior consistent state.

### Exercise
Simulate crash before rename; verify recovery path.

---

## M6: Concurrency + Isolation
### Lame Analogy (Hook)
Two cooks grabbing the same plate unless rules exist.

### Technical Bridge (Why)
Concurrent writes cause lost updates and inconsistent reads.

### Senior Implementation Roadmap
**Pro Definition:** locking or MVCC to isolate transactions.  
**Senior Insight:** locks are simpler but reduce throughput; MVCC costs space.  
**Bottom Line:** Without isolation, correctness collapses under load.

### Implementation Tasks
- **M6.1:** transaction boundaries: `BEGIN`, `COMMIT`, `ROLLBACK`, executor transaction state
- **M6.2:** single-writer rule
- **M6.3:** committed-read rule
- **M6.4:** transaction-local write buffer
- **M6.5:** rollback semantics
- **M6.6:** isolation and overlap tests

### Acceptance Checks
- Concurrent operations do not corrupt data.
- Isolation level is documented and enforced.
- One executor holding `BEGIN` blocks another writer from `BEGIN`/write statements.
- One executor holding `BEGIN` blocks other executors' `SELECT` until commit or rollback.

### Exercise
Demonstrate lost update without locks, then fix.

---

## M7: Page Model + Scaling
### Lame Analogy (Hook)
Filing cabinets with labeled folders instead of loose papers.

### Technical Bridge (Why)
Disks are block-addressed; byte-level writes are an illusion.

### Senior Implementation Roadmap
**Pro Definition:** page layout, buffer pool, free-space tracking.  
**Senior Insight:** buffer pool policy dominates performance.  
**Bottom Line:** This is where I/O performance is won or lost.

### Implementation Tasks
- page file format
- buffer pool + eviction
- free-space management

### Acceptance Checks
- Reads/writes go through page layer.
- Hot pages remain cached under load.

### Exercise
Measure latency before and after caching a hot page.
