# SQL Is Not Magic: Tokenizer, AST, and Executor Explained

## The Lame Analogy
When you tell a waiter “one spicy paneer, no onion,” the waiter does not carry your sentence into the kitchen as raw sound. The waiter converts speech into a structured ticket.

That ticket is the database AST.

## The Technical Bridge
The core challenge we face here is ambiguity. SQL arrives as text. Text is messy:
- spacing varies
- quotes matter
- syntax can be malformed
- similar strings can mean different things
- the same statement can mean very different physical work depending on the data and available indexes

A database needs deterministic structure before execution.

That is the “why” behind tokenizers and parsers. They are not academic layers. They are the boundary between human language and machine action.

## The Flow
### 1. Tokenizer
Turns text into tokens:

```sql
SELECT * FROM users WHERE id = 1;
```

Becomes:

```text
[SELECT, STAR, FROM, IDENT(users), WHERE, IDENT(id), EQUAL, NUMBER(1)]
```

### 2. Parser
Turns tokens into AST:

```python
Select(
    table_name="users",
    columns=["*"],
    where_column="id",
    where_value=1,
)
```

### 3. Executor
Turns AST into storage calls:

```python
storage.get_by_pk("users", 1)
```

Each stage narrows ambiguity:
- tokenizer defines lexical meaning
- parser defines structural meaning
- executor defines operational meaning

## What Breaks in Production
Parser problems are not cosmetic. They cause trust failures:
- one malformed query parses differently across environments
- a parser silently accepts an invalid form and produces the wrong plan
- a shell splits statements incorrectly because of quoted semicolons
- a planner assumes a query shape that the parser did not guarantee
- error reporting is too vague for engineers to debug quickly

This is why a proper query path has to be deterministic, not just convenient.

## The Pro Definition
The parser/executor boundary is an abstraction layer between query syntax and physical execution.

The AST is the contract between “what the user asked” and “what the engine will do.”

Without that contract:
- execution logic becomes string manipulation
- validation logic gets duplicated
- edge cases leak everywhere

## Senior Insight
A hand-written parser is excellent for learning and terrible for SQL completeness. A full SQL grammar is deep, expensive, and full of edge cases. That is why production databases invest heavily in parsers and optimizers.

The senior tradeoff is visibility vs coverage:
- hand-written parser: high visibility, low coverage
- mature SQL parser: high coverage, lower learning visibility

There is no free option here. You choose the pain you want.

## Alternatives
### 1. Hand-written parser
Best for learning because every rule is explicit.

Problem:
- small SQL subset
- lots of manual grammar work

### 2. Parser generator
Better long-term grammar structure.

Problem:
- adds abstraction before the learner understands the failure modes

### 3. External SQL library
Best if the goal is product speed.

Problem:
- hides the internal structure you are trying to learn

Why choose hand-written first:
- maximum visibility into failure modes
- easier to map query text to engine behavior
- no hidden abstraction barrier while learning internals

## Why We Choose This Now and What Comes Later
For this project, a hand-written parser is the right first move because it makes every decision visible:
- how a token is recognized
- how ambiguity is resolved
- how AST shape drives execution

Later, if the SQL surface grows, we may want:
- a broader grammar
- better error locations
- planner rules
- JOIN support
- optimizer decisions over multiple access paths

So the current parser is not the final parser. It is the cleanest way to understand the contract before complexity explodes.

## How It Maps to Our Toy Database
The user types SQL.
The tokenizer breaks it into tokens.
The parser builds AST objects like `Select`, `Update`, or `Delete`.
The executor maps those AST nodes to storage calls.

That pipeline is the first real separation of concerns in the engine.

It also creates a stable place to add future features:
- `JOIN`
- planner choices
- better error reporting
- type-aware validation

## A Useful Mental Model
SQL is not execution.

SQL is a request.
The parser gives that request structure.
The executor gives that structure behavior.

That shift in mental model is essential if you want to understand how real databases work.

## Bottom Line
Without tokenizer, parser, and AST, SQL is just a string. A database becomes real when that string becomes deterministic execution.
