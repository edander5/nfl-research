# Approved Task 004 — NFL Schedule Ingestion

Owner approval: 2026-11-06, after reporting the committed foundation and successful normal-WSL validation (45 tests passed, two warnings; Compose, PostgreSQL, initial migration and health/readiness successful). Those foundation results are user-reported, not independently reproduced by this task.

Implement only development schedule ingestion on `feature/schedule-ingestion`: validate the unchanged owner-supplied CSV for 2024–2026 REG/available POST, preserve nulls/UNKNOWN/declared provenance, reconcile idempotently with correction evidence, transact atomically, and test success, duplicates, invalid input, corrections and rollback. Document import/reimport commands and actual verification limitations. No original CSV changes, new dependencies, production access, frontend, schedule API, unrelated features, deployment, commit or merge. Stop for review.

The owner explicitly authorized this scope; it supersedes Task 003's ingestion hold, without authorizing the rest of Milestone 1. See [ingestion guide and verification report](schedule-ingestion.md).
