# Why Persistence Changes a Script Into a Database

## The Lame Analogy
If a cashier remembers sales in their head, the shop has no books. The moment the cashier leaves, the business loses its history.

Persistence is the ledger.

## The Technical Bridge
RAM is fast and volatile. Disk is slower and durable. The database exists to bridge those two realities.

The core challenge we face here is not just “how do I write bytes to disk?” The real challenge is:
- how do I preserve truth across restart
- how do I define when a write is actually durable
- how do I keep metadata, rows, and indexes from drifting apart
- how do I do all this without turning every write into random I/O

A beginner stores rows in a Python list. A database stores rows in structures that survive restart, process death, and deployment churn.

That is the first real step from script to system.

## Minimal Layout
A learning-first layout can be:
- `schema.json` for table metadata
- `<table>.tbl` for append-only rows

This is simple enough to inspect manually and realistic enough to teach durability.

It is not how mature engines usually store data internally, but it teaches the right instincts:
- metadata is separate from row storage
- row order matters
- restart reconstruction is part of the storage design

## Concrete Example
Write:

```sql
CREATE TABLE users (id INT PRIMARY KEY, name TEXT);
INSERT INTO users VALUES (1, 'Asha');
```

Restart the process.

If the row still exists, persistence works.
If it disappears, you built an in-memory cache, not a database.

That is the first durability test every storage engine must pass.

## What Breaks in Production
At small scale, persistence failure looks like “data disappeared after restart.”

At larger scale, the failures are nastier:
- metadata says a table exists, but the file is missing
- a row append succeeded, but the index update did not
- the process acknowledged success before data was actually durable
- the row file is intact, but restart logic reconstructs stale in-memory state
- appending works, but update/delete rewrites are slow and fragile

This is why durable persistence is not just “write to a file.” It is write ordering, flush policy, and recovery discipline.

## The Pro Definition
Persistence is durable state management across process lifetime.

In practical terms, that means:
- on-disk representation
- restart reconstruction
- an explicit contract for when data is considered durable
- a stable separation between logical state and physical representation

## Senior Insight
At scale, the real performance issue is not “disk is slow.” The real issue is access pattern:
- sequential writes are throughput-friendly
- random rewrites are expensive
- block devices prefer larger contiguous operations
- read amplification can dominate even when the data size looks modest

That is why append-only layouts are attractive early on. They fit the hardware better than scattered rewrites.

But there is a cost:
- appends are easy
- updates are awkward
- deletes create logical fragmentation
- compaction or rewrite work eventually becomes necessary

This is the classic storage-engine tradeoff. You can simplify the write path now, but you will pay later when the data shape becomes richer.

## Tradeoffs
- JSONL append is simple and debuggable
- but updates and scans are inefficient
- file growth is easy, compaction is not
- metadata is transparent, but not space-efficient

Alternative approaches:

### 1. Page-based binary layout
Better long-term performance and closer to real row stores.

Downside:
- harder to inspect
- harder to teach early

### 2. Embedded engine delegation
Use SQLite or another mature backend and focus only on SQL and API layers.

Downside:
- you learn how to use a database, not how a database works

### 3. In-memory only
Great for demo speed and terrible for durability learning.

Why choose JSONL first:
- lower cognitive load
- easy to inspect by hand
- ideal for learning durability basics before page design

## Why We Choose This Now and What Comes Later
For this phase, JSONL files are the correct compromise:
- easy to inspect after every write
- easy to reason about during failures
- low ceremony while the storage contract is still forming

Later, when durability semantics are stable, the engine should evolve toward:
- page-based storage
- stronger metadata discipline
- WAL-backed recovery
- checkpointing and compaction

So JSONL is not the destination. It is the teaching scaffold that makes the later storage-engine leap understandable.

## How It Maps to Our Toy Database
We store:
- schema in one metadata file
- rows in one append-oriented file per table
- optional index state separately

That separation is educational because it lets you see that metadata, data, and access paths can drift apart if you do not enforce discipline.

It also makes restart logic concrete:
- load schema
- load rows
- rebuild or validate index state

That restart path is part of the storage engine. It is not a helper utility.

## A Useful Mental Model
Persistence is not a file write.

Persistence is a promise:
"If I acknowledged this operation, I can reconstruct the correct state later."

That promise becomes more expensive as the database grows, which is why durability design has to start early.

## Bottom Line
Persistence is the first moment your system starts acting like a database instead of a script.
