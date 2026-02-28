# Building a Database From Scratch: What Actually Matters

Most people start with the wrong mental model of a database.

They think a database is:
- a file with rows
- plus some SQL
- plus maybe an index if performance gets bad

That is not how a senior engineer thinks about it.

A database is a machine that takes hostile reality:
- volatile memory
- slow persistent storage
- partial failures
- concurrent writers
- ambiguous query text

and turns it into something applications can trust.

That trust is the real product.

## The Lame Analogy
Think about a restaurant during dinner rush.

At first glance, it looks simple:
- customers place orders
- cooks make food
- servers deliver plates

But once the place gets busy, chaos appears immediately.

What if:
- the waiter keeps orders in memory and forgets them
- two cooks modify the same order ticket
- the kitchen has no numbering system
- the cashier records payments after handing over food
- a power cut happens halfway through service

Now the restaurant cannot answer basic questions:
- what was ordered
- what was served
- what is still pending
- which table paid
- which state is trustworthy after the failure

A database solves the same class of problem.

It is not just storage.
It is operational discipline under load and failure.

## The Technical Bridge
The core challenge we face here is that computers hide the pain until the system becomes real.

### Memory lies to beginners
RAM feels instant. You put values in a dictionary or list and everything looks fine.

But RAM is volatile. Restart the process and the state is gone.

That means an in-memory data structure is not yet a system of record.

### Files lie to beginners
A file feels like a nice, simple abstraction. You open it, write bytes, close it, done.

But the hardware reality is harsher:
- disks are block-oriented, not “row-oriented”
- writes can be interrupted
- the process can crash between related steps
- acknowledging success before durable flush is a correctness bug

That means “I wrote to a file” is not the same as “the database is consistent.”

### SQL lies to beginners
SQL looks declarative:

```sql
SELECT * FROM users WHERE id = 1;
```

It feels like the query just “happens.”

But under the hood, the engine still has to:
- tokenize text
- parse syntax
- build a structured representation
- choose an access path
- touch actual storage

That means SQL is not execution. SQL is a request for execution.

### Concurrency lies to beginners
A single user path usually looks correct.

Then two writes arrive at the same time and suddenly the same code produces:
- lost updates
- stale reads
- inconsistent balances
- duplicated or missing records

That means correctness is not just about code. It is about ordering and isolation.

## What a Database Actually Has to Do
A real database has to answer five hard questions:

### 1. How do we stop bad data from entering?
That is schema validation and constraints.

### 2. How do we make data survive restart and crash?
That is persistence, write ordering, WAL, and recovery.

### 3. How do we find data quickly as tables grow?
That is indexing, access paths, and eventually query planning.

### 4. How do we interpret SQL consistently?
That is tokenizer, parser, AST, executor, and later optimizer work.

### 5. How do we protect correctness when many users operate at once?
That is transactions, locks or MVCC, isolation, and deadlock handling.

If one of these is weak, the database still exists, but the trust boundary is broken.

## Which Real Core Features This Project Will Actually Build
This series is not just theory. The project intends to implement a meaningful subset of real database core features:
- schema validation and constraints
- durable persistence
- primary-key indexing
- SQL parsing and execution
- WAL and recovery foundations
- rollback foundation
- locking/isolation basics
- joins
- page-storage evolution

That is enough to teach the core shape of a real database engine.

There are also features we will likely explain more deeply than we implement:
- cost-based optimization
- full MVCC
- replication and failover
- PITR and backup systems
- distributed coordination

That distinction matters because “understand deeply” and “build fully” are not always the same scope.

## What Real Databases Usually Have
A mature database engine usually contains all of these:

### 1. A logical query layer
- SQL parser
- semantic validation
- planner and optimizer
- relational operators like join, sort, aggregate

### 2. A storage layer
- durable files
- page layout
- free-space management
- checksums and physical metadata

### 3. An access-path layer
- primary indexes
- secondary indexes
- ordered scans
- maintenance rules for keeping indexes consistent with data

### 4. A transaction and recovery layer
- WAL or equivalent logging
- checkpoints
- recovery replay
- rollback semantics

### 5. A concurrency-control layer
- locks or MVCC
- isolation levels
- deadlock handling

### 6. An operational layer
- backup and restore
- point-in-time recovery
- replication and failover
- metrics and explain plans

The reason to list these explicitly is simple: a real database is not one algorithm. It is a stack of guarantees.

## The Real Stack, In Order
The easiest mistake is to think all features are equal. They are not.

Some features are expressive.
Some features are protective.
Some features are performance multipliers.

Here is the actual dependency chain.

### Layer 1: Schema and validation
Before the engine can be fast, it has to reject nonsense.

If this layer is weak:
- indexes store invalid values
- query semantics become unreliable
- downstream systems inherit silent corruption

This layer answers:
"Does this row even belong in the database?"

### Layer 2: Persistence
Before the engine can be useful, it has to survive restart.

If this layer is weak:
- deployments erase data
- process crashes become business incidents
- "success" responses are meaningless

This layer answers:
"Will this state still exist tomorrow?"

### Layer 3: Indexing
Before the engine can scale reads, it needs shortcuts.

If this layer is weak:
- point lookups become table scans
- latency grows with table size
- every success becomes slower as the business succeeds

This layer answers:
"Can I find one record without paying the full scan cost?"

### Layer 4: SQL path
Before the engine can serve humans and applications cleanly, it needs deterministic interpretation.

If this layer is weak:
- the same text may behave differently
- malformed queries may partially work
- debugging becomes guesswork

This layer answers:
"What exactly did the user ask the engine to do?"

### Layer 5: WAL and recovery
Before the engine can be trustworthy, it must survive interrupted writes.

If this layer is weak:
- table files and index files drift apart
- crash recovery is guesswork
- acknowledged writes may not actually be safe

This layer answers:
"What is the durable truth after a failure?"

### Layer 6: Locks or MVCC
Before the engine can support real concurrent use, it must control overlapping reads and writes.

If this layer is weak:
- balances become wrong
- counters drift
- business logic appears valid while state is corrupt

This layer answers:
"How do multiple users safely share one mutable system?"

### Layer 7: Page model and buffer manager
Before the engine can perform like a database instead of a file utility, it must align with hardware reality.

If this layer is weak:
- locality is poor
- repeated reads hammer storage
- tiny logical operations trigger large physical costs

This layer answers:
"How do we make block storage behave efficiently for database workloads?"

### Layer 8: Advanced query engine
After the base is trustworthy, we deepen expressiveness:
- joins
- aggregations
- multiple access paths
- cost-aware planning

This layer answers:
"How do we answer richer questions without collapsing performance?"

## Why the Order Matters
This is where many learning projects fail.

They build:
- parser
- SQL shell
- joins
- fancy syntax

before they build:
- crash safety
- recovery
- isolation

That creates an engine that looks impressive and behaves unreliably.

The senior rule is simple:

**Do not deepen query power on top of an untrustworthy core.**

That is why milestone order matters so much.

## The Tradeoffs That Matter
Every database feature is a trade, not a free upgrade.

### Strict validation vs flexible ingest
- strict validation catches errors early
- flexible ingest reduces friction
- but pushes cleanup downstream

### Append simplicity vs update efficiency
- append-only files are easy to reason about
- but expensive to update and scan later

### Read speed vs write amplification
- indexes improve point lookups
- but every insert/update becomes more expensive

### Reliability vs fast path throughput
- WAL and fsync improve safety
- but add I/O and latency

### Simpler concurrency vs higher throughput
- single-writer rules are easy to reason about
- MVCC is more scalable
- but much harder to implement correctly

### Learning clarity vs production realism
- JSON files are easy to inspect
- page files are closer to real engines
- but much harder to teach from day one

The important thing is not to eliminate tradeoffs. It is to make them explicit.

## What Breaks If You Ignore the Internals
If you skip schema validation, bad data enters and poisons later logic.

If you skip persistence, your database is just a cache with better marketing.

If you skip indexing, success becomes a latency tax.

If you skip WAL, crash boundaries become corruption boundaries.

If you skip isolation, concurrency bugs quietly become business bugs.

If you skip page-aware design, the storage layer eventually dominates performance.

If you skip optimizer and join strategy, richer SQL turns into unbounded compute cost.

## How This Maps to Our Toy Database
In our project, the toy database is intentionally being built in this order:
- schema rules first
- then persistence
- then indexing
- then SQL execution
- then crash safety
- then concurrency
- then deeper storage design
- then advanced query features like joins

That is not accidental.

It reflects a professional systems view:
- correctness first
- durability second
- performance third
- expressiveness after the core is trustworthy

## Common Beginner Misconceptions
### “A database is basically a file plus SQL.”
Wrong. A database is a consistency and recovery system that happens to expose SQL.

### “If it works on restart once, persistence is solved.”
Wrong. Durability is about correct behavior under interruption, not just happy-path restart.

### “Indexes make databases fast.”
Incomplete. Indexes make some reads fast by making writes and maintenance more expensive.

### “ACID is one feature.”
Wrong. It is a bundle of guarantees spread across validation, WAL, recovery, and concurrency control.

### “JOIN is just syntax.”
Wrong. JOIN is where the query engine starts paying real execution cost.

## The Bottom Line
If you want to understand databases deeply, do not start with SQL syntax and do not stop at file storage.

Start with the actual engineering questions:
- what can fail
- what must remain true
- what physical cost we are paying
- what tradeoff each internal is making

That is the difference between learning how to use a database and learning how a database earns trust.
