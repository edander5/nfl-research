# Approved Task 002 — Development Foundation and Schedule Schema

Owner authorization: 2026-11-05, after the CONDITIONALLY READY dataset assessment. This records the user-approved scope; it does not authorize the rest of Milestone 1.

Implement the minimal monorepo backend, development PostgreSQL/FastAPI Compose environment, Pydantic Settings, SQLAlchemy models, initial Alembic migration, automated schema/relationship/health tests and run/test documentation. Preserve canonical game identity, nonunique `old_game_id`, source provenance and declared origin, unknown status, nullable reported scores and the raw CSV.

No frontend, full-data/production import, player stats, rankings, injuries, odds, paid services, new technology stack, production deployment or destructive operation on an existing database. Necessary runtime ASGI server/PostgreSQL driver and the documented test stack support the approved backend technologies. Do not proceed to ingestion without approval.

Deliver files/design rationale, actual test results including blockers, limitations and a proposed next task for review. Current delivery is documented in [development.md](development.md). Runtime test/migration execution is blocked by Docker WSL integration and PyPI DNS; static checks alone are not acceptance of PostgreSQL behavior. Stop for owner review.
