# AGENTS.md — NFL Betting Research

This file governs any AI coding agent working in this repository. Read `README.md`, `docs/product-requirements.md`, `docs/architecture.md`, `docs/decisions.md`, and the currently approved task before action.

## Current owner-approved frontend task

The owner subsequently approved Schedule and Game Preview UI adjustments: move refresh
history below the schedule, compare offense against opposing defense with rank colors,
and embed compact reference markets below the game-summary scores with secondary grading
details. This frontend-only authorization supersedes Task 021's frontend exclusion for
this task. Preserve game logs, APIs, statistical/betting calculations and data safety.
See `docs/schedule-preview-ui.md` for scope and validation. No git publication or deployment.

## Hard rules

1. Work **only** within a user-approved, narrowly scoped task. Do not start the next task without approval.
2. Task 001 (`docs/agent-task-001.md`) was research-only. Foundation/schema scope is recorded in `docs/agent-task-002.md`; recovery/runtime-validation is recorded in `docs/agent-task-003.md`. Development-only schedule ingestion is recorded in `docs/agent-task-004.md`. Read-only schedule API scope is recorded in `docs/agent-task-005.md`. React dashboard scope is recorded in `docs/agent-task-006.md`. Guarded manual refresh scope is recorded in `docs/agent-task-007.md`. Current-week navigation scope is recorded in `docs/agent-task-008.md`. Freshness scope is recorded in `docs/agent-task-009.md`. Offline validation and references are recorded in `docs/team-stats-validation.md`. Current owner-approved work is Task 021, documented in `docs/interactive-nfl-update.md`: presentation and guided-flow improvements to the Task 020 interactive updater, including plain-text summaries, sequential independent reviews and default-no y/yes confirmations. Preserve original guarded importers, internal token handling/stdin transport, source/admission/provenance/concurrency and UNKNOWN/finality contracts, read-only verification and indeterminate-operation stops. No frontend, schema, PostgreSQL permission, ingestion contract, scheduler behavior, dependency/service/source, automatic import, commit/merge/push/deployment changes are authorized. System package, WSL networking, Docker Desktop and privileged changes require prior owner approval during recovery.
3. Honor the existing stack: React/TypeScript/Vite, React Router, TanStack Query, Tailwind/shadcn/ui, Recharts, TanStack Table; Python/FastAPI, SQLAlchemy/Alembic, PostgreSQL; Docker Compose, Caddy, Tailscale.
4. $0/month sports data API budget is non-negotiable. Never sign up for a paid tier, enable overages, or expose credentials. Verify licenses and terms before using a dataset.
5. Never change business/statistical definitions without approval. Pregame cutoffs and regular/postseason separation are mandatory. Missing != zero; DNP != an eligible zero-performance game; pushes are distinct outcomes.
6. No speculative data or invented odds, timestamps, rankings, availability, or injury statuses. Label uncertain coverage explicitly.
7. Never write secrets to code, logs, git history, images, or documentation. Use safe `.env.example` placeholders when implementation is approved.
8. Do not expose database or internal administration ports publicly; Tailscale-only MVP access. No automated production deployment.
9. Ask permission before: large/new dependencies, technology changes, paid services, destructive database changes, migration or backup restoration, production deployment, scope expansion, security changes, or accessing unrelated files.
10. Create or update appropriate unit/integration/API/frontend/e2e tests as the approved implementation task warrants. Never claim tests passed unless actually run.
11. On completion report: files changed, rationale, source references, tests run and their results, limitations, unresolved risks, and the next proposed task **for approval**.
12. Keep these documents synchronized when an approved decision changes; record rationale in `docs/decisions.md`.

## Working style

- Prefer incremental, reviewable diffs over sweeping scaffolds.
- Explain architectural choices and tradeoffs in plain language; do not silently replace decisions.
- Validate external source claims against current official source documentation and sample artifacts. Record URLs, retrieval dates, schema evidence, license/terms, source freshness and gaps.
- Treat source metadata, timestamps, provider IDs and correction history as first-class records.
- Use real data for accepted features; clearly label synthetic test fixtures.
- Error states should preserve valid historical research and distinguish stale/external failures.

## Approval-gated workflow

1. Confirm task scope and acceptance criteria.
2. Inspect only the relevant repository components and references.
3. Explain planned approach and key risks.
4. Implement only what was approved (research-only tasks produce documents, not code).
5. Run permitted verification; report outcomes and stop for owner review.
