# 08 Production-ish Roadmap

## Outline
- What we build
- Internal focus
- Failure example
- Debugging path
- Mini DB solution
- Production counterpart
- Exercise

## What We Build
A staged path from learning DB to more production-like behavior.

## Internal Focus
- Add `UPDATE` and `DELETE`.
- Add secondary indexes.
- Introduce transaction log ideas (`BEGIN`/`COMMIT`/`ROLLBACK`).
- Add stronger concurrency and recovery guarantees iteratively.

## Concrete Failure Example
A growth-stage app adds features quickly without safety gates. Data anomalies accumulate, incident response time increases, and audits fail.

## How We Debug It
1. Map each incident to missing guarantee (durability, isolation, constraints).
2. Prioritize guarantees by business risk.
3. Add acceptance tests before feature rollout.
4. Roll out milestone by milestone with rollback paths.

## Our Mini DB Solution
Use milestone gates: do not add new features until acceptance checks for current guarantees pass.

## Real Production Counterpart
Teams harden engines through staged releases, backward compatibility policies, observability, chaos testing, and incident-driven roadmap updates.

## Exercise
Pick one future feature (`UPDATE`, secondary index, or transactions) and define:
1. user-visible benefit,
2. failure mode if implemented poorly,
3. acceptance test needed before release.  
Expected outcome: a risk-aware feature spec, not just implementation tasks.
