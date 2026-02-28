# Why Indexing Is Expensive and Still Non-Negotiable

## The Lame Analogy
Without a phonebook, you find a number by reading every page.

That is a full table scan.

## The Technical Bridge
The core challenge we face here is latency growth. Without an index, point lookup cost rises linearly with table size. That is manageable at 100 rows and disastrous at 10 million.

A beginner sees indexing as a performance bonus. A database engineer sees it as a latency survival tool.

The physical reality matters here:
- storage reads are not free
- scans burn bandwidth
- repeated point lookups amplify I/O cost
- the same query can be trivial or painful depending on access path

An index changes the physical work, not the SQL text.

## What an Index Really Does
An index maps a key to a row location:

```text
id -> byte offset
1  -> 0
2  -> 37
3  -> 74
```

Instead of scanning the table, the engine jumps directly to the row.

That is the essential abstraction:
- logical query says “find row with id = 2”
- physical index says “jump here”

## Concrete Example
Query:

```sql
SELECT * FROM users WHERE id = 2;
```

Without index:
- read row 1
- compare
- read row 2
- compare
- continue until match

With index:
- read index
- get offset
- seek directly to row

The logical query is identical. The physical work is radically different.

## What Breaks in Production
Indexing failures are usually consistency failures:
- row exists but index entry is missing
- index entry exists but points to stale offset
- duplicate key slips through because validation and index maintenance are out of order
- write path updates table and index separately and crashes in the middle

This is why index maintenance is part of the write path, not a background convenience feature.

Another production problem is key design:
- monotonic IDs cluster writes nicely in B+Trees
- random UUIDs spread writes across the tree
- that increases page churn and write amplification

Correctness remains intact, but the operational profile changes.

## The Pro Definition
An index is a read-optimized access path that trades write cost for lower lookup latency.

That trade is central to database design. Read speed is purchased with:
- more storage
- more maintenance work
- more write I/O
- more consistency obligations

## Senior Insight
Indexes are not free. Every write now becomes:
- write data
- write index
- maintain consistency
- recover correctly after crashes

At scale, this becomes a bottleneck because heavy indexing shifts the system from read latency problems to write amplification problems.

This is why “just add an index” is a beginner answer and “what is the workload mix?” is the senior answer.

## Alternatives
### 1. No index
Simplest possible engine.

Problem:
- every point lookup becomes a scan
- latency grows with data size

### 2. Sidecar JSON index
Excellent for learning because it is transparent and easy to inspect.

Problem:
- not scalable enough for serious workloads
- weak crash semantics without WAL

### 3. B+Tree
Classic OLTP index.

Strength:
- balanced read performance
- supports ordered access and range scans

### 4. LSM tree
Great for write-heavy systems.

Strength:
- write-optimized

Problem:
- different read and compaction tradeoffs

## Why We Choose This Now and What Comes Later
For this project, a sidecar PK index is the right first step because it exposes the core idea directly:
- logical key
- physical row location
- maintenance cost on writes

Later, if the engine matures, this should evolve toward:
- B+Tree pages for ordered access
- secondary indexes
- composite keys
- crash-safe index maintenance under WAL

That evolution matters. The current format teaches the access-path concept. The later format teaches how production engines scale it.

## How It Maps to Our Toy Database
Our toy database uses a sidecar PK file mapping:

```text
pk -> file offset
```

That is intentionally primitive, but it teaches the core idea clearly:
an index is a shortcut into storage, not a second copy of the table.

It also exposes the real maintenance burden:
- inserts must update the index
- updates and deletes may require rebuilds or rewrites
- corruption detection matters

## A Useful Mental Model
An index is not “extra metadata.”

It is a second physical structure with its own correctness rules.

That is why database engineers care so much about:
- index build order
- index corruption
- index rebuild cost
- index choice per workload

## Bottom Line
Indexing is expensive because it duplicates work. It is mandatory because full scans do not scale.
