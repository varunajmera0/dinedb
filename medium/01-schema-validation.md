# Why Schema Validation Is the First Real Database Feature

## The Lame Analogy
A nightclub bouncer checks IDs at the door. The goal is not to make the line slower. The goal is to stop problems from getting inside.

Schema validation is the bouncer of a database.

## The Technical Bridge
The core challenge we face here is data correctness at the boundary. Once invalid data lands on disk, every downstream system pays the cost:
- indexes carry bad values
- queries return nonsense
- analytics pipelines fail later and farther away from the root cause
- business logic starts compensating for data that should never have existed

Validating early is cheaper than debugging late.

That is the first systems lesson. Databases are not just storage engines. They are correctness boundaries.

## What We Actually Build
A table schema usually defines:
- column names
- data types
- primary key rules
- missing and unknown column handling

In a mini database, this can be as simple as:

```python
TableSchema(
    name="users",
    columns=[
        Column(name="id", data_type="INT", is_primary_key=True),
        Column(name="name", data_type="TEXT"),
    ],
)
```

The important point is not the class definition. The important point is that this schema becomes part of the write path.

## Concrete Example
Suppose someone tries to insert:

```python
{"id": "one", "name": "Asha"}
```

If `id` is `INT`, this must fail immediately.

If it does not fail, you do not have a clean type system anymore. You have a future incident.

Now scale that mistake up:
- IDs are mixed strings and integers
- primary key checks become unreliable
- index lookups behave inconsistently
- joins later compare values that should never have been comparable

That is how one missing validation step poisons the whole engine.

## What Breaks in the Real World
The worst schema bugs are rarely immediate syntax errors. They are delayed correctness failures.

Examples:
- a price column stores strings for a few hours, and analytics pipelines silently coerce or drop rows
- an ID column accepts mixed types, and indexes become unreliable
- a required field is missing, but downstream jobs invent defaults and hide the bug
- a data science team “fixes” dirty rows in notebooks while production writes continue generating more

These failures are expensive because they move the blast radius away from the original write path.

## The Pro Definition
Schema validation is write-time integrity enforcement.

It is the layer that asserts:
- this row belongs to this table
- this value belongs to this column type
- this constraint is valid before the row is accepted

That is not a cosmetic layer. It is foundational.

## Senior Insight
Strict schemas improve correctness but reduce ingestion flexibility. This is why some systems choose schema-on-read for analytics and schema-on-write for OLTP.

That tradeoff matters:
- schema-on-write favors correctness and transactional systems
- schema-on-read favors flexibility and exploration
- weak typing improves ingestion speed, but transfers complexity to consumers

The senior mistake is pretending this tradeoff does not exist. Every system chooses where pain will land:
- at write time
- or later, during reads and debugging

## Alternative Approaches
### 1. Strict schema at write time
Best for transactional systems where correctness matters immediately.

### 2. Schema-on-read
Useful in data lake or exploratory systems, where ingest flexibility matters more than immediate enforcement.

### 3. Weak typing with coercion
Convenient at first, but dangerous because the database starts guessing.

We choose strict validation in a learning database because correctness has to become muscle memory first.

## Why We Choose This Now and What Comes Later
For this project, strict write-time validation is the right first move because it keeps every later layer honest:
- persistence writes known-good rows
- indexes map well-typed keys
- query results stay predictable

Later, in a more production-like version, we may add:
- richer constraints
- nullability rules
- default values
- schema migration paths
- better error taxonomies

But the core principle does not change: the database should reject invalid state before it becomes durable.

## How It Maps to Our Toy Database
In our implementation:
- `Column` defines the contract
- `TableSchema` owns table-level rules
- `validate_row()` checks types and shape before any write hits storage

That means validation is not a helper. It is part of the write path.

This matters because once the row is written:
- persistence depends on it
- indexes depend on it
- query correctness depends on it

## Bottom Line
Schema validation is not “just validation.” It is the first line of defense against systemic corruption.
