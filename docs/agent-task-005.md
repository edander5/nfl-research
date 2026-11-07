# Approved Task 005 — Read-Only NFL Schedule API

Owner approved this task on 2026-11-07 on `feature/schedule-api`. The owner reports the foundation/ingestion complete, 842 games imported with expected seasonal counts, unchanged reimport producing 0 inserts/0 updates/842 unchanged, and the full prior suite passing 78 tests. These are user-reported runtime results, not independently reproduced in this agent environment.

Implement read-only season coverage, REG/POST schedule filters by week/round, and canonical UUID game lookup, with matchup data, stored status, nullable reported scores/kickoff, provenance, deterministic ordering, consistent JSON/errors and OpenAPI. Add unit/API/PostgreSQL tests and WSL verification instructions. Follow existing SQLAlchemy/FastAPI architecture. No schema/migration, dependencies/infrastructure, frontend, stats, injury/odds, editing/ingestion triggers, production operations, commits, merge, push or deployment. Stop for owner review.

This approval supersedes Task 004's API hold only for this scope. Contract/design and actual verification: [Schedule API guide](schedule-api.md).
