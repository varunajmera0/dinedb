# 01 Schema and Row Validation

## Outline
- What we build
- Internal focus
- Failure example
- Debugging path
- Mini DB solution
- Production counterpart
- Exercise

## What We Build
We define table schema metadata and validate every row before write.

## Internal Focus
- `Column`: name, type, primary-key flag.
- `TableSchema`: ordered columns and validation rules.
- Insert path validates row shape and types before persistence.

## Concrete Failure Example
E-commerce ingestion accepts supplier rows where `price` is `"N/A"` instead of numeric. Search ranking and discount calculations crash later.

## How We Debug It
1. Capture failing row payload.
2. Compare payload keys/types against schema contract.
3. Confirm validation is missing or incomplete in insert path.
4. Add validation and assert failure occurs before file write.

## Our Mini DB Solution
Reject writes that have:
- missing columns,
- unknown columns,
- type mismatch,
- duplicate primary keys (when PK exists).

## Real Production Counterpart
Production databases use catalogs and typed storage formats. Invalid writes fail at statement execution, not during later reads/analytics.

## Exercise
Try inserting `{id: "one", name: "Asha"}` into `id INT, name TEXT`.  
Expected outcome: deterministic type error before any disk change.
