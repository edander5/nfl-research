# Approved Task 007 — Guarded NFL Schedule Refresh Runner

Owner approved implementation on `feature/schedule-auto-updates` after the [feasibility investigation](schedule-auto-update-feasibility.md). Scope: a manual, development-only workflow that retrieves the approved release CSV, archives source bytes, measures provenance, validates the entire snapshot, compares existing PostgreSQL data, and applies only explicitly reviewed changes through existing reconciliation safeguards.

Dry-run is default; new reported scores and historical/corrected data require snapshot/baseline-specific operator review. Score removals, ambiguous/disappearing games and changed FINAL records stay blocked. Keep UNKNOWN; no clock/score finality inference. Preserve original `data/raw/games.csv`. Add automated tests, transaction/commit recovery and clear WSL review/apply instructions.

No scheduler/recurrence, frontend, source/status API changes, schema/migration, paid service, unrelated research feature, production operation, commit, merge, push or deployment. Stop for review. Implementation/evidence: [refresh guide](schedule-refresh.md).
