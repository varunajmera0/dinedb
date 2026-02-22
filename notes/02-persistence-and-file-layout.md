# 02 Persistence and File Layout

## Outline
- What we build
- Internal focus
- Failure example
- Debugging path
- Mini DB solution
- Production counterpart
- Exercise

## What We Build
A simple durable layout:
- `data/schema.json` for metadata
- `data/<table>.tbl` for append-only rows

## Internal Focus
- Startup loads schema from disk.
- Inserts append serialized rows to table file.
- Reads scan table file when index is not applicable.

## Concrete Failure Example
A restaurant admin updates menu items, service restarts, and all changes vanish because writes never hit durable files.

## How We Debug It
1. Insert rows and query successfully.
2. Restart process.
3. Query again and compare result.
4. Inspect disk for schema and row files.
5. Confirm write path persisted both metadata and rows.

## Our Mini DB Solution
Persist schema and rows to disk immediately in the write path so restarts can reconstruct state.

## Real Production Counterpart
Real systems use page files and durability protocols (write ordering, fsync policies, checkpoints) to survive crashes and restarts.

## Exercise
Insert two rows, restart the program, run the same select.  
Expected outcome: exact same rows appear after restart.
