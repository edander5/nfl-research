# Task 009 — NFL Schedule Data Freshness Indicator

Owner-approved scope: `feature/schedule-freshness`.

Implement an additive read-only FastAPI endpoint and responsive React schedule indicator using existing persisted refresh metadata. Show available attempt, successful check, successful apply, observed-change times and outcome. Distinguish checks/no-change applies from record changes; retain UNKNOWN and reported-score semantics. Timestamps are neither game completion nor source publication evidence.

Use the existing Docker refresh volume read-only in API. Do not expose paths, locks, tokens, credentials, source receipts or raw journals. Handle missing/incomplete/invalid/unreadable/stale metadata and request failures. Display local timezone dates, manual operation and explicit reload; no polling or jobs.

No schema/migration, ingestion/runner behavior, existing response contract, dependency, unrelated feature or deployment changes. No commit, merge or push. Add backend/frontend tests and document actual results and blocked normal-WSL checks. Stop for owner review.

Implementation contract, inventory and evidence: [freshness guide](schedule-freshness.md).
