# Medium Article Pack

This folder contains post-ready markdown articles for the database internals series.

The articles cover both:
- what real databases do in production
- which of those core features this project will actually implement

## Articles
- `00-series-overview.md`
- `01-schema-validation.md`
- `02-persistence-file-layout.md`
- `03-primary-key-indexing.md`
- `04-sql-parser-ast-executor.md`
- `05-wal-recovery-rollback.md`
- `06-locks-isolation-acid.md`
- `07-joins-query-engine.md`
- `08-page-storage-buffer-manager.md`

## Writing Style
Each article follows the same structure:
- Hook analogy
- Technical bridge
- Core challenge
- Implementation strategy
- Tradeoffs and alternatives
- Concrete example
- Bottom line

## What Real Databases Have
For this series, "real databases" means engines that usually contain all of these layers:
- SQL and query-processing layer
- durable storage layer
- indexing layer
- transaction and recovery layer
- concurrency-control layer
- operational and observability layer

The articles should explain both:
- why each layer exists
- whether this project will implement it directly or only describe it architecturally

## Core Features This Series Intends to Implement
- schema validation and constraints
- persistence and file layout
- primary-key indexing
- SQL parsing and execution
- WAL, recovery, and rollback foundations
- locks and isolation basics
- joins
- page-storage and buffer-manager concepts

## Important Distinction
Not every production database feature will be fully implemented in this project.

Some topics will be:
- **implemented directly** in `dinedb`
- **implemented partially** as a learning milestone
- **explained architecturally** without full production-grade scope

This distinction should remain explicit in the articles so readers know what is being built versus what is being studied.

## Posting Notes
- These are written as long-form technical posts.
- You can trim the examples or split larger topics into multi-part posts.
