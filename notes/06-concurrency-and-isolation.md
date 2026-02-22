# 06 Concurrency and Isolation

## Outline
- What we build
- Internal focus
- Failure example
- Debugging path
- Mini DB solution
- Production counterpart
- Exercise

## What We Build
A clear single-writer model for correctness before advanced concurrency.

## Internal Focus
- Serialize write operations.
- Define read visibility behavior while writes are active.
- Return explicit contention/retry signal when needed.

## Concrete Failure Example
Two transfer operations update the same account balance concurrently. One write overwrites the other, producing incorrect final balance.

## How We Debug It
1. Reproduce with parallel write threads.
2. Capture operation order and resulting stored value.
3. Confirm absence of write serialization.
4. Add lock discipline and rerun race tests.

## Our Mini DB Solution
Allow one writer at a time and document behavior instead of pretending to support unconstrained parallel writes.

## Real Production Counterpart
Production engines use lock managers or MVCC snapshots to provide stronger isolation levels with better read/write concurrency.

## Exercise
Run concurrent writes against the same key under load.  
Expected outcome: deterministic serialized outcome without lost update.
