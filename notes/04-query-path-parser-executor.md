# 04 Query Path: Parser to Executor

## Outline
- What we build
- Internal focus
- Failure example
- Debugging path
- Mini DB solution
- Production counterpart
- Exercise

## What We Build
Deterministic SQL handling with a constrained grammar and AST dispatch.

## Why We Added It
Tokenization only splits text. Parsing is needed to build a structured AST so we can execute SQL deterministically.

## What Problem We Are Solving
- Convert tokens into structured meaning (AST).
- Detect invalid syntax early with precise errors.

## Tradeoffs
- Hand-written parser is easy to understand but supports only a small SQL subset.
- Parser generators support more SQL but hide learning details and add complexity.

## Failure Modes
- Ambiguous or partial parsing can execute the wrong statement.
- Poor error positions make debugging painful.

## Internal Focus
- Parser converts SQL text into AST (`CreateTable`, `Insert`, `Select`).
- Engine routes AST nodes to storage operations.
- Result payload format remains stable for all callers.

## Concrete Failure Example
Analytics team sends slightly malformed SQL; one environment accepts it while another rejects it, causing trust issues in reports.

## How We Debug It
1. Record exact SQL text and parser output/error.
2. Reproduce with unit tests for parser edge case.
3. Tighten grammar and error conditions.
4. Ensure executor only receives valid AST shapes.

## Our Mini DB Solution
Support a narrow, explicit SQL subset and reject everything else with clear parse errors.

## Real Production Counterpart
Real databases use full lexer/parser stacks, plan generation, and optimization rules before execution.

## Exercise
Run one valid and one invalid query that differ by a small syntax mistake.  
Expected outcome: valid query executes; invalid query returns deterministic parse error message.
