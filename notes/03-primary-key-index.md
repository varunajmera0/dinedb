# 03 Primary Key Index

## Outline
- What we build
- Internal focus
- Failure example
- Debugging path
- Mini DB solution
- Production counterpart
- Exercise

## What We Build
A primary-key sidecar index that maps key to row location.

## Why We Added It
Full scans are too slow for `WHERE pk = ...`. Once the table grows, lookup time becomes linear
and user-facing systems (support tools, order lookup, profile fetch) slow down.

## What Problem We Are Solving
- Fast point lookups by primary key.
- Predictable latency under growth.

## Where This Can Fail (Real-World Tradeoffs)
In production, PK indexes are usually B+Trees. How the key is generated changes write behavior:
- **Monotonic IDs (auto-increment)**: inserts land at the right-most leaf; low page splits.
- **Random UUIDs**: inserts spread across the tree; more page splits and rebalancing.
This does not break correctness, but it increases write amplification and can hurt throughput.

Proper usage depends on workload:
- For write-heavy workloads, monotonic or time-ordered keys reduce B+Tree churn.
- For distributed uniqueness, UUIDs avoid coordination but cost more index maintenance.

## Disadvantages (Why Indexing Is Expensive)
- **Extra writes**: every insert/update also writes the index.
- **More I/O**: index files must be read/updated in addition to table files.
- **Crash recovery cost**: if index is corrupted or missing, it must be rebuilt from table data.
- **Space overhead**: index files can be large and add storage cost.
 
In our mini DB, we also pay this cost:
- We write `<table>.pk.json` on every insert.
- If the index file is corrupted, we rebuild it by scanning `<table>.tbl`.

## Example (Index Used vs Scan)
When you call:
```
service.get_by_pk("users", 2)
```
We return metadata indicating whether the PK index was used:
```json
{
  "ok": true,
  "row": {"id": 2, "name": "Rahul"},
  "meta": {"operation": "get_by_pk", "index_used": true}
}
```

## Internal Focus
- `data/<table>.pk.json` stores `pk -> byte_offset`.
- Insert updates index after row append.
- `SELECT ... WHERE pk = value` seeks directly by offset.

## Concrete Failure Example
Order-support dashboard must fetch order by ID instantly, but latency spikes at dinner rush because every lookup scans the full file.

## How We Debug It
1. Compare runtime of key lookup with and without index path.
2. Add tracing to show whether scan or index path was used.
3. Inspect index file contents for missing/stale mappings.
4. Validate offset points to expected row payload.

## Our Mini DB Solution
Use direct offset lookup for PK equality queries and fallback to full scan for non-indexed filters.

## Real Production Counterpart
Production engines use B+Tree or LSM indexes with better update/read scaling and memory-aware caching.

## Exercise
Insert 1,000 rows and query one row by PK.  
Expected outcome: lookup path uses index mapping, not linear scan.
