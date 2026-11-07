# Vertical-Slice Implementation Roadmap

**Status:** Owner reports foundation, ingestion and read-only API validated/committed/merged with 842 games and 139 passing backend tests/two warnings. Task 006 React schedule dashboard is implemented; frontend install/build/tests and real browser/API validation remain pending due agent environment restrictions. Milestone 1 is not yet end-to-end accepted. Each task remains approval-gated.

## Preflight — Research gate (first agent task)

- Follow `docs/agent-task-001.md`; verify prospective free sources, actual data schemas, licensing and 2024–2026 coverage.
- Output documented findings and risks; **no application code**, installs, account creation, secret usage or deployment.
- Owner approval is required before any implementation work.

## Milestone 1 — Complete weekly NFL schedule (first functional vertical slice)

Current approved subset: [Task 006 React schedule dashboard](agent-task-006.md). [Implementation, validation evidence and exact WSL commands](schedule-dashboard.md) distinguish completed code/client smoke checks from unexecuted frontend build/RTL/browser acceptance. No subsequent milestone, statistics feature or deployment is authorized.

**Outcome:** The user runs the local environment, opens the app, selects 2024/2025/2026 and season stage/week, sees real game information and opens a basic matchup overview.

Suggested approved tasks (one at a time):

1. Approve source data contract and dev environment plan; inspect sample assets.
2. Establish minimal monorepo dev scaffolding, Docker Compose, config management, CI seed, development PostgreSQL, and migration workflow.
3. Model team/game/season/provider-ID relationships in SQLAlchemy, with Alembic migration and integrity tests.
4. Implement schedule import with validation, last-good-data preservation, idempotency, provenance and tests.
5. Implement FastAPI season/week schedule and lightweight matchup overview responses with API tests.
6. Implement React Router schedule page and basic matchup link with TanStack Query, loading and error states, frontend tests.
7. Run Playwright smoke test; document data counts, source caveats, latency, and all acceptance evidence.

**Acceptance:** All three seasons; regular and postseason selection; correct kickoff timestamps/timezones, home/away names, status and scores when completed; navigable stable game IDs; deep links; no mock production records; schema and import integrity; test results reported. If source has a real data gap, display it and document it, don't fabricate.

Decision 53 permits explicit UNKNOWN status and clearly labeled reported scores when finality is unverified; no invented in-progress/postponed state or kickoff-only finality. The [local validation report](schedule-validation-report.md) supports conditional readiness, subject to retaining declared provenance/digest warnings, handling nonunique `old_game_id` aliases, and rerunning validation on each imported snapshot. The 2026 postseason selector must disclose absent source matchups without synthetic game rows. This evidence does not itself authorize any implementation task.

## Milestone 2 — Team statistics, rankings, matchup context

- Verify source semantics for passing/rushing yards and *yards allowed* at the game level.
- Add team game stats, canonical relationships and pregame-cutoff calculation endpoints.
- Four ranking definitions; denominators; reverse sorting; team logs and comparisons; matchup research tabs.
- Unit/integration tests for rankings, incomplete/zero games, cutoff correctness, before/after schedule changes.

**Acceptance:** For any 2024–2026 game, all eligible pregame team metrics use games completed before kickoff. Correct top/bottom ranks and sample sizes.

## Milestone 3 — Player research and all feasible player-stat markets

- Validate each of ten required fields and participation eligibility from actual source rows.
- Add player IDs/provider mappings, player/team timelines, player game logs, stat calculations.
- Implement unified player-first/market-first research view, line controls, Recharts charts, TanStack tables, last-5/last-10/season filters.
- Unit tests: DNP exclusion, played-zero inclusion, bye exclusion, integer-line pushes, trades, stage separation, pregame cutoff.

**Acceptance:** Correct sample denominators and push reporting; cached filters safe across players; no silent missing-to-zero conversions. Unsupported markets documented and not invented.

## Milestone 4 — Injury reports and full depth charts where available

- Validate provider update cadence, actual positions, practice participation and designation availability.
- Implement current-state ingesters, mapping, source timestamps and per-section UI with freshness/failure states.
- Mark historical limitations distinctly, avoiding present-day reports falsely represented as historical pregame.

**Acceptance:** Team-wide source-covered injury/depth records, clear coverage gaps, accurate last-updated labels, graceful outages.

## Milestone 5 — Optional free sportsbook integration and manual prop lines

- Reverify provider, quota, free markets, terms and cache/retention permission with explicit owner approval before credentials or paid-risk actions.
- Centralized FastAPI odds adapter with keyed dedup, cooldown, credits/budget cap, rate-limit handling, provider timestamps.
- On-demand only; no background odds refresh. Clear stale/unavailable labels, multiple books when free market coverage exists.
- Manual prop-line entry always operational, with correct hit-rate recalculation independent of odds.

**Acceptance:** Zero paid spend, no unsupported market claims, provider failures cannot break player stat features, quota controls verified against fixtures.

## Milestone 6 — Operational hardening and private deployment

- Daily/wk schedules, reconciliation, retry history, rejected-record review, health endpoints and structured logs.
- Backup retention 7 daily/4 weekly, independent storage and restore rehearsal.
- GitHub Actions CI; manually triggered controlled release with backup, approved migrations, smoke verification.
- Caddy + Tailscale private single origin; secret handling, closed admin/database ports, verified HTTPS, mobile usability.
- Performance benchmarks under controlled load: schedule/matchup p95 <500ms; ranking <1s; player <1.5s; historical comparison <2s.

**Acceptance:** Owner can install, verify, back up, restore, and update private app safely; documentation matches deployed architecture.

## General definition of done for each task

- Task scope and user acceptance criteria are approved.
- Required provider coverage and licensing checks documented.
- Data behavior and error handling match product/statistical invariants.
- Applicable automated tests executed with results reported; no fabricated passing claims.
- Docs and decisions updated, with known risks and user review checkpoint.
