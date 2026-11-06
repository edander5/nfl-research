# Architecture and Product Decision Register

**Approved through Decision 54 (2026-11-05).** Decision numbers reflect the design conversation. If a number compresses multiple earlier sub-decisions, the binding source is the consolidated specification below; the agent must not invent unrecorded approvals.

| ID | Decision |
|---|---|
| 01–22 | Core product choices: personal MVP, 2024–2026 schedules, no prediction/bet-tracking/accounts, 4 yardage-based team rankings, 10 prop stat categories, player appearance/push/team/stage semantics, local PostgreSQL and free source constraints, Python/FastAPI/React/TypeScript/Vite monorepo, Docker Compose/Tailscale, canonical IDs and dynamic pregame cutoff calculations. See PRD and data model for detail. |
| 23 | Hybrid FastAPI: lightweight game overview + independent data detail endpoints. |
| 24 | TanStack Query for frontend server data and caching. |
| 25 | React Router with bookmarkable matchups/research states. |
| 26 | Tailwind CSS + shadcn/ui. |
| 27 | Recharts + TanStack Table. |
| 28 | SQLAlchemy + Alembic for PostgreSQL. |
| 29 | Initial historical backfill + incremental imports + periodic reconciliation. |
| 30 | Dedicated Docker scheduler independent of FastAPI. |
| 31 | Data-specific cadence: schedules/stats/depth daily, injuries ~6h *if supported*, reconciliation weekly, odds on demand. |
| 32 | Automatic controlled retries, ingestion history and last-good-data preservation. |
| 33 | Automated backups on separate physical storage; periodic restoration tests. Initial plan: daily + 7 daily / 4 weekly retained, monthly restore rehearsal. |
| 34 | Layered pytest/PostgreSQL/FastAPI/ingest/Vitest/Playwright tests. |
| 35 | Strict source validation, duplicate/foreign key/null handling, rejected record tracking. |
| 36 | Tailscale-only private network, no separate app login for personal MVP. |
| 37 | Caddy reverse proxy; one private frontend/API origin. |
| 38 | Separate development/production configuration via Pydantic Settings and safe `.env.example`. |
| 39 | GitHub Actions CI; manual deployments. |
| 40 | Manually triggered controlled release: backup, migrations, Docker update, health/smoke checks. |
| 41 | Optimized PostgreSQL first, selective measured backend caching; no initial Redis. |
| 42 | Balanced p95 API response objectives under controlled conditions. |
| 43 | Structured logs + lightweight metrics, no full monitoring stack. |
| 44 | External data last-known display when legally permitted, explicit stale/freshness warnings; never block historical or manual research. |
| 45 | Centralized sportsbook API quota manager: dedup, cooldown, credit monitor, configurable hard budget. |
| 46 | Build in complete vertical slices with data foundation. |
| 47 | First slice is full 2024–2026 schedule with regular/postseason and basic matchup navigation. |
| 48 | Pregame reconstruction with provider/version/import/cutoff/correction provenance. |
| 49 | Preliminary data-source audit before coding, deeper verification at each milestone. |
| 50 | Structured docs and AGENTS.md. |
| 51 | Agent autonomy limited to approved tasks; approval gates for major decisions, changes, deployments. |
| 52 | Produce a complete planning package and first agent-ready task; **no application code yet**. |
| 53 | Owner approved the limited Milestone 1 game-status contract (2026-11-05): never infer finality solely from kickoff; use explicit UNKNOWN when finality cannot reliably be established; do not invent in-progress or postponed states. Rationale: the schedule artifact lacks authoritative status/finality fields. Retain reported scores separately from confirmed-final results. Scope is schedule display only; historical cutoff rules remain unchanged. Contract, PRD, data model and roadmap synchronized; future implementation tests must cover unknown status, reported-score labeling and prohibition on time-only finality. Owner authorized dataset validation only, not application implementation. |
| 54 | Owner subsequently approved Milestone 1 development foundation and schedule schema only (Task 002). Implement PostgreSQL/FastAPI Compose development services, Pydantic Settings, SQLAlchemy, initial Alembic migration and tests. Internal UUIDs plus unique provider/source game IDs preserve links; `old_game_id` stays nonunique. Separate artifact provenance distinguishes declared origin from verified matching-hash evidence. UNKNOWN defaults and explicit final-evidence constraints preserve Decision 53. No importer/frontend/stats/odds/deployment. Runtime tests and migrations remain unexecuted due environment blockers, as recorded in development.md. No new business/statistical definition or full-milestone authorization is implied. |

## Change control

New architectural or scope decisions are **proposals** until explicitly approved. Record each change, date, rationale, downstream docs/tests to update, and author/reviewer. Do not silently substitute providers, accept paid tiers, change rank definitions or increase agent autonomy.

## Known unresolved decisions, not blockers to document creation

- Exact source artifacts, provenance licenses, and per-season column coverage.
- Final database columns/indexes, detailed API schema contracts and error schema.
- Exact six-hour injury polling usefulness vs nightly source releases.
- Precise odds credit caps, account quota resets, retention permissions and market-by-market NFL availability.
- Deployment-specific HTTPS/Tailscale setup and separate backup storage medium.

These must be settled in approved task scopes, based on evidence.
