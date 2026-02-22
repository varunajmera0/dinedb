# 05 Crash Safety and Atomicity Basics

## Outline
- What we build
- Internal focus
- Failure example
- Debugging path
- Mini DB solution
- Production counterpart
- Exercise

## What We Build
Safer metadata/index writes using atomic replace behavior.

## Internal Focus
- Write new JSON to temporary file.
- Flush temp file.
- Rename temp file over target atomically.

## Concrete Failure Example
Checkout request succeeds, process crashes during index write, and index file becomes truncated JSON. Next startup fails to load metadata cleanly.

## How We Debug It
1. Simulate interruption between write and rename.
2. Inspect file contents for truncation.
3. Verify loader behavior on corrupt JSON.
4. Add atomic write helper and rerun crash simulation.

## Our Mini DB Solution
Use temp-write + rename for schema and index files so readers always see old-good or new-good versions.

## Real Production Counterpart
Production databases rely on WAL and crash recovery to reconstruct a consistent state after partial failures.

## Exercise
Force a failure before rename in a test harness.  
Expected outcome: original metadata/index remains readable and consistent.
