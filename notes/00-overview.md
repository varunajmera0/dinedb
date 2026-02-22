# 00 Overview: Why Build a Database This Way

## Outline
- Goal of this track
- Mini DB scope
- Failure example
- Debugging path
- Production counterpart
- Exercise

## Goal of This Learning Track
You are not just writing code that works. You are learning why database internals exist and what failures forced those designs in production.

## Mini DB Scope
- Python implementation for clarity.
- Minimal SQL path first: `CREATE TABLE`, `INSERT`, `SELECT`, `WHERE =`, `LIMIT`.
- File-backed storage with primary-key index.
- Slow, milestone-based progression.

## Concrete Failure Example
An app stores orders in memory only. During deployment restart, all unflushed orders disappear. Support cannot reconcile user complaints with system state.

## How We Debug It
1. Reproduce with a controlled restart.
2. Check whether state lives only in process memory.
3. Verify there is no persistent metadata/data file.
4. Add persistence and rerun restart test.

## Real Production Counterpart
At scale, systems use durable storage layers plus recovery workflows. Databases persist data in structured on-disk formats and recover using logs/checkpoints instead of trusting process memory.

## Exercise
Write down one user-facing incident caused by non-durable state in any app you know.  
Expected outcome: clear mapping from user symptom to missing durability guarantee.
