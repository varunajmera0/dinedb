# Locks, Isolation, and ACID: Why Correctness Gets Hard the Moment Two Users Arrive

## The Lame Analogy
Two cashiers editing the same invoice at the same time without coordination will lose money and blame each other.

That is a concurrency bug.

## The Technical Bridge
The core challenge we face here is not just multiple users. It is overlapping reads and writes on the same state.

Typical anomalies:
- lost update
- dirty read
- non-repeatable read
- phantom read

These are not academic terms. They are names for business bugs that appear when the system keeps running but the state becomes logically wrong.

A crash is visible. A concurrency bug is often silent.
That is why senior engineers respect isolation so much.

## ACID Breakdown
### Atomicity
All or nothing.

### Consistency
Constraints stay valid before and after the transaction.

### Isolation
Concurrent transactions behave as if they were safely separated.

### Durability
Committed work survives crashes.

The important point is that ACID is not one feature. It is a bundle of guarantees implemented by different layers.

## Milestone-by-Milestone Build

## M6.1 Transaction Boundaries

### Definition
A transaction boundary tells the engine where a logical unit of work starts and ends.

Typical SQL:

```sql
BEGIN;
UPDATE users SET name = 'Rahul' WHERE id = 1;
COMMIT;
```

### Problem We Are Solving
Without explicit transaction boundaries, the engine only sees isolated statements. It cannot distinguish:
- one logical multi-step change
- from unrelated single statements

That matters because rollback, locking, visibility, and commit protocol all need a unit of work.

### Our Mini-DB Solution
`dinedb` starts by recognizing:
- `BEGIN`
- `COMMIT`
- `ROLLBACK`

The first stage is intentionally small: the executor tracks whether a transaction is active and rejects invalid transitions like nested `BEGIN` or `COMMIT` without `BEGIN`.

### Tradeoff
- **Benefit:** establishes the state machine needed for later isolation and rollback
- **Cost:** no full transactional buffering yet, so the semantics are only the first layer

### Real Database Example
- PostgreSQL, InnoDB, and SQLite all expose explicit transaction boundaries

### Real-World Example
Bank transfer workflows need one unit of work for:
- debit
- credit
- ledger update

### Bottom Line
`M6.1` creates the unit of work that every later concurrency feature depends on.

## M6.2 Single-Writer Lock

### Definition
A single-writer model means only one write transaction can modify state at a time.

### Problem We Are Solving
Two overlapping writers can silently overwrite each other and produce logically wrong results even when the database files stay structurally valid.

### Our Mini-DB Solution
The first safe rule is:
- one writer active at a time
- later we decide what reads are allowed during that writer

In the current `dinedb` implementation, that starts as a **process-wide writer gate**:
- `BEGIN` acquires the writer slot
- `COMMIT` / `ROLLBACK` release it
- standalone write statements temporarily acquire the same slot for one statement

### Tradeoff
- **Benefit:** easiest correct concurrency model
- **Cost:** very limited write throughput

### Real Database Example
- SQLite effectively begins from a heavily constrained writer model compared with PostgreSQL/InnoDB

### Real-World Example
Inventory systems use serialization to avoid two buyers both claiming the last unit.

### Bottom Line
`M6.2` sacrifices throughput to preserve correctness.

## M6.3 Committed-Read Rule

### Definition
Readers should only see committed, stable state.

### Problem We Are Solving
If readers can observe half-finished writes, they may see:
- row changed but index stale
- one step of a multi-statement operation without the rest
- temporary values that should never be visible

### Our Mini-DB Solution
For the first version, we keep the rule conservative:
- readers see committed state only
- later versions may introduce richer read/write overlap

In the current `dinedb` implementation, that means:
- if one executor holds an active writer transaction, other executors' `SELECT` is rejected
- the transaction owner may still read

This is intentionally coarse. It blocks dirty reads without pretending we already have MVCC or transaction-local version buffers.

### Tradeoff
- **Benefit:** simpler mental model
- **Cost:** less concurrency for mixed workloads

### Real Database Example
- PostgreSQL and InnoDB solve this more elegantly with MVCC snapshots

### Real-World Example
Analytics dashboards should not show half-completed payment or order transitions.

### Bottom Line
`M6.3` defines what a reader is allowed to believe.

## M6.4 Transaction-Local Write Buffer

### Definition
A transaction-local buffer keeps pending inserts, updates, and deletes private until commit.

### Problem We Are Solving
If writes immediately hit durable state before commit, rollback becomes fake. The engine has already leaked uncommitted work.

### Our Mini-DB Solution
Later in M6, we stage writes inside transaction-local state:
- staged inserts
- staged updates
- staged deletes

Then:
- `COMMIT` applies them
- `ROLLBACK` discards them

### Tradeoff
- **Benefit:** real rollback semantics begin to exist
- **Cost:** more code complexity and more memory usage

### Real Database Example
- InnoDB uses undo and transactional metadata
- PostgreSQL uses MVCC visibility and transaction status

### Real-World Example
Checkout flows should not leak partial order state if the user cancels at the end.

### Bottom Line
`M6.4` is where transactions stop being labels and start holding private work.

## M6.5 Rollback

### Definition
Rollback discards uncommitted changes safely.

### Problem We Are Solving
Without rollback, `BEGIN`/`COMMIT` are incomplete and aborted business workflows can still leak state.

### Our Mini-DB Solution
For the first version:
- rollback discards transaction-local buffered writes

Later production-style systems integrate undo more deeply with WAL, commit markers, and recovery.

### Tradeoff
- **Benefit:** failed workflows no longer poison committed data
- **Cost:** buffering and undo state make transaction handling more complex

### Real Database Example
- InnoDB uses undo records
- PostgreSQL uses transaction visibility rules and MVCC snapshots

### Real-World Example
If a payment capture fails after an order draft is created, rollback should prevent the draft from becoming committed business state.

### Bottom Line
`M6.5` is the first meaningful answer to “what if the transaction changes its mind?”

## M6.6 Isolation Tests

### Definition
Isolation tests simulate overlapping operations and prove that anomalies are blocked or serialized.

### Problem We Are Solving
Concurrency bugs often pass normal tests because happy-path tests do not force timing conflicts.

### Our Mini-DB Solution
We add focused scenarios for:
- overlapping writers
- read during active write
- rollback visibility
- lost update prevention

### Tradeoff
- **Benefit:** evidence that the isolation model is real
- **Cost:** harder, timing-sensitive test setup

### Real Database Example
- PostgreSQL and InnoDB both invest heavily in isolation-path testing

### Real-World Example
Ticketing, banking, and inventory systems depend on these tests because concurrency bugs directly become business incidents.

### Bottom Line
`M6.6` proves the correctness contract under overlap, not just under normal execution.

## Example: Lost Update
Initial balance = 100

Transaction A:
- read 100
- subtract 10

Transaction B:
- read 100
- subtract 20

If both write back blindly:
- final balance may be 90 or 80
- correct answer is 70

This is the classic proof that “my code worked in one request” does not mean “the system is correct under concurrency.”

## What Breaks in Production
Concurrency bugs are worse than crashes because they often look valid.

The database returns a value.
The application keeps running.
No exception gets raised.
But the business state is wrong.

Examples:
- account balances drift
- inventory counts go negative
- one booking overwrites another
- a reporting query sees partial state and ships the wrong numbers to finance

That is why isolation is a correctness feature, not a performance feature.

## The Pro Definition
Locking is a concurrency-control mechanism that serializes conflicting access to shared state.

Isolation level is the contract that tells users what kinds of interference are or are not allowed.

## Senior Insight
Locks are simpler to reason about than MVCC, but they reduce concurrency and can deadlock. MVCC improves read/write overlap, but increases storage and cleanup complexity.

The senior tradeoff is not “locks or performance.” The real tradeoff is:
- easier reasoning with less concurrency
- or higher concurrency with more internal complexity

The wrong move is pretending you can get both for free.

## Alternatives
### 1. Single-writer lock
Best first step for correctness.

Problem:
- low write concurrency

### 2. Coarse-grained locks
Simple mental model.

Problem:
- unnecessary blocking

### 3. Fine-grained locks
Higher concurrency.

Problem:
- harder deadlock reasoning

### 4. MVCC
Excellent read/write overlap.

Problem:
- version management
- vacuum/cleanup burden
- more complex visibility rules

Why choose single-writer first:
- easiest correctness model
- clear mental model
- fewer hidden anomalies

## Why We Choose This Now and What Comes Later
For this project, single-writer discipline is the right starting point because it makes concurrency bugs visible instead of hiding them behind incomplete abstractions.

Later, a more advanced engine could evolve toward:
- finer-grained locks
- read/write lock separation
- deadlock detection
- MVCC snapshot reads
- explicit isolation-level support

That ordering is deliberate. First learn what anomaly you are preventing. Then learn how to prevent it with less blocking.

## What PostgreSQL, InnoDB, and Other Production Databases Do Later
Once a database moves past the learning-first stage, concurrency control becomes much more sophisticated.

### 1. Lock manager
Production engines do not rely on one global writer flag forever. They add a lock manager that can reason about:
- row locks
- page locks
- table locks
- intent locks

**Tradeoff**
- better concurrency
- much harder lock-state bookkeeping

**Real database example**
- InnoDB has row-level locking and intention locks
- SQL Server and Oracle have rich lock hierarchies

**Real-world example**
- inventory and ticket-booking systems need more than one writer at a time, but still need to prevent overselling

### 2. Deadlock detection and resolution
Once multiple locks exist, transactions can wait on each other in a cycle.

That is a deadlock.

Production systems detect this cycle and abort one transaction so the system can keep moving.

**Tradeoff**
- higher concurrency
- need wait-for graph logic or equivalent detection

**Real database example**
- PostgreSQL and InnoDB both detect deadlocks and abort a victim transaction

**Real-world example**
- order-processing workflows touching inventory, payment, and fulfillment rows can deadlock under load if lock ordering is inconsistent

### 3. MVCC snapshots
Instead of blocking readers behind writers, many engines let readers see a stable snapshot.

That is Multi-Version Concurrency Control.

**Tradeoff**
- strong read/write overlap
- more storage pressure, version cleanup, visibility rules

**Real database example**
- PostgreSQL is built around MVCC snapshots
- InnoDB also uses MVCC for consistent reads

**Real-world example**
- analytics dashboards and admin panels should keep reading stable data while live writes continue

### 4. Isolation levels
Production databases let users choose how strong isolation should be:
- Read Committed
- Repeatable Read
- Serializable

These are not just labels. They define which anomalies are allowed.

**Tradeoff**
- stronger correctness usually means lower concurrency or more internal complexity

**Real database example**
- PostgreSQL and InnoDB expose multiple isolation levels

**Real-world example**
- finance often needs stronger guarantees than a low-risk internal reporting job

### 5. Undo, cleanup, and garbage collection
Once versions and rollback become real, the engine must clean up old state safely.

**Tradeoff**
- better transactional behavior
- background cleanup complexity

**Real database example**
- InnoDB uses undo segments and purge
- PostgreSQL uses vacuum to reclaim dead row versions

**Real-world example**
- long-running systems cannot keep every historical row version forever without performance collapse

### Bottom Line
Our `M6` starts with a single-writer model because that is the smallest correctness-preserving foundation.

Production databases go further by adding:
- finer-grained locking
- deadlock handling
- MVCC snapshots
- configurable isolation levels
- background cleanup

That progression is the honest path from a teaching engine to a serious transactional system.

## How It Maps to Our Toy Database
The first safe concurrency model for our engine is:
- one writer at a time
- readers allowed only under clearly documented rules

That is intentionally conservative. The point is to make anomalies visible before optimizing them away.

Later, if we add richer concurrency, we will know exactly which guarantee we are changing and why.

## A Useful Mental Model
Concurrency control is not a speed feature.

It is a social contract for shared state.

It answers:
"What does one user have the right to see and change while another user is working?"

## Bottom Line
The database becomes socially correct only when it becomes concurrent-correct.
