# AGENTS.md — NFL Betting Research

This file governs any AI coding agent working in this repository. Read `README.md`, `docs/product-requirements.md`, `docs/architecture.md`, `docs/decisions.md`, and the currently approved task before action.

## Collapsible navigation — current approved frontend scope

Owner approved a shared collapsible desktop sidebar and closed-by-default mobile
navigation disclosure. See `docs/sidebar-navigation.md`. Preserve routes, API calls,
page behavior and Light/Dark/System theme. Persist desktop preference, keep icon
links/theme accessible and provide keyboard focus/expanded semantics. Frontend
changes/tests/typecheck/build only; no dependencies, backend, data, Docker or git
publication changes. Further roadmap tasks still require separate approval.

## Task 027 — prior approved frontend scope

Owner approved the interactive Game Total dashboard in existing Game Preview.
See `docs/game-total-research-ui.md`. Use Task 026 API outcomes, rates and
matchup-specific selections; preserve missing values, source finality and reference
line caveats. Team/window/manual-line/side controls synchronize native SVG history,
summary and log. No backend, schema, ingestion, dependency, Docker or publication
changes. Frontend tests, type checks and production build are authorized.
Task 028 Team Total API remains a proposal requiring separate approval.

## Task 026 — prior approved backend scope

Owner approved the read-only Game Total historical research API. See
`docs/game-total-research-api.md`. Reuse accepted reciprocal selection and exact
Decimal comparisons; support same-season/stage L3/L5/L10/L20/SEASON/H2H with
required matchup chronology, manual lines and independent unverified source total
references. Hit rates use usable scored observations including pushes, with
explicit numerator/denominator; no line means unavailable custom outcomes.
No frontend, schema/migration/permission, ingestion, dependency, external source,
accepted NFL record or Docker configuration changes. Do not infer FINAL or quote
publication/closing status. Synthetic focused backend tests are authorized;
fixtures that provision/migrate a PostgreSQL database remain excluded. Task 027
UI is subsequently approved under Task 027 above; new dependencies still require approval.

## Task 025 — prior approved planning scope

The owner approved documentation-only integration of the seven-tab REA frontend
research in `docs/research/nfl/` into the game-first development roadmap. See
`docs/research/task-025-game-research-roadmap.md`. Verify existing source, identify
reusable components/data gaps and propose small backend/frontend tasks; no code,
database/ingestion changes, installs, Docker execution, additional REA work or
git publication. This task number supersedes the earlier unapproved Task 025
manual-line implementation proposal. Proposed Task 026 and later items require
separate approval. Earlier task scopes below are historical context.

## Task 024 — prior approved frontend scope

The owner approved frontend-only Game Preview Team Performance Trends using the
existing Task 023 API. See `docs/team-performance-trends-ui.md`. Shared L3/L5/L10
selection, default L5, compares both teams' six API metrics with independent
loading/errors, actual/per-metric samples, unknown chronology and light/dark
styling. Always pass matchup season/stage/window/matchup_id; do not calculate
trends or infer finality in React. No backend, schema, data, ingestion, Docker,
dependency or publication changes. Existing Task 023 changes in this checkout
remain prior work; Task 025 and later roadmap items require separate approval.

## Task 023 — prior approved backend scope

The owner approved the read-only L3/L5/L10 Team Performance Trends API, including
six offensive/defensive yardage and reported-point averages and optional matchup
chronology. See `docs/team-performance-trends.md`. Reuse accepted reciprocal
statistics and existing definitions; never infer FINAL or completion-before-cutoff
from scores/kickoff. Exclude the selected matchup and equal/later kickoffs in
matchup mode; unknown kickoff yields unavailable trends. No frontend, schema,
migration, permission, ingestion, source, dependency, Compose, accepted NFL data
or git publication changes. Synthetic focused backend tests are in scope;
database fixtures that run migrations/provisioning are not authorized.

## Task 022 — prior audit scope

The owner approved a documentation-only repository audit, independent data-source
research and phased NFL research roadmap. See
`docs/research/task-022-expansion-audit.md`. No application code, database access
or changes, migrations, imports, dependency installation, Compose changes,
additional REA investigation or git publication is authorized by Task 022.
Roadmap tasks are proposals requiring separate approval. Earlier implementation
scope below is historical context, not authorization to resume it during this audit.

## Previously approved frontend scope

The owner subsequently approved frontend-only dark mode: a main-navigation
Light / Dark / System preference, system default, localStorage persistence,
first-paint theme application and consistent styling across existing pages.
This supersedes Task 021's frontend exclusion for this task. Preserve layout,
data, calculations and functionality; no new library, backend, database,
ingestion or publication changes. See `docs/dark-mode.md` for implementation
and validation. Earlier Schedule/Game Preview UI work remains intact.

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
