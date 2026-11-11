# Architecture and Product Decision Register

**Approved through Decision 59 (2026-11-09).** Decision numbers reflect the design conversation. If a number compresses multiple earlier sub-decisions, the binding source is the consolidated specification below; the agent must not invent unrecorded approvals.

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

| 55 | Owner approved Task 004 on 2026-11-06 after reporting successful WSL foundation validation: development-only schedule ingestion on `feature/schedule-ingestion`, preserving Decision 53, UNKNOWN/reported scores, nonunique legacy IDs and declared-origin limitations. Use transactional full-snapshot reconciliation, canonical UUIDs, immutable raw artifact snapshots and correction receipts in existing artifact notes; no schema change or new dependency. Ambiguous identity changes and disappearing existing records reject the batch rather than guessing or deleting. No API/frontend, production, deployment, commit or merge authorization. See [Task 004](agent-task-004.md) and [ingestion guide](schedule-ingestion.md) for implementation and actual test limitations. |

| 56 | Owner approved Task 005 on 2026-11-07 on `feature/schedule-api`, after reporting 842 development games imported, idempotent reimport (0/0/842) and 78 passing tests. Implement read-only season coverage, stage/week/round schedule selection and canonical UUID lookup with typed JSON/OpenAPI, provenance and explicit reported-score/finality semantics. Preserve Decision 53; no schema/dependency/infrastructure changes or status inference. Use bounded single-season eager reads so schedule coverage and returned games share a statement snapshot. No frontend, editing/ingestion triggers, unrelated features, commit, merge, push or deployment. See [API guide](schedule-api.md) for actual new-test evidence and pending WSL checks. |

| 57 | Owner approved Task 006 React weekly schedule dashboard on `feature/schedule-dashboard`, reporting API/backend merged and 139 tests passed/two warnings. Use approved React/TypeScript/Vite, React Router, TanStack Query, Tailwind/shadcn primitives, current GET schemas and loopback development Compose integration. Preserve nulls, UNKNOWN/reported-score semantics, declared provenance and missing POST coverage. No schema/ingestion/API contract changes, unrelated features or deployment. Author tests and report blocked package/build/browser checks honestly; no commit/merge/push. See [dashboard guide](schedule-dashboard.md). |

| 58 | Owner approved Task 007 on `feature/schedule-auto-updates`: unscheduled, development-only guarded refresh using the approved release CSV, immutable archives and existing reconciliation. Dry-run first, then saved-candidate apply bound to operator review of source/DB diff; new scores remain UNKNOWN. Removed scores, ambiguous/disappearing identities and changed FINAL records cannot be overridden. Reuse existing schema with actual retrieval provenance and durable operational journal/commit recovery; no new dependencies, frontend, API/schema changes, scheduling, production or git publication. See [refresh guide](schedule-refresh.md) for commands, evidence and remaining runtime blocks. |

| 59 | Owner approved Task 008 frontend usability only: home defaults to the current available NFL season/week/round from actual API kickoff dates in America/New_York; explicit URL choices are preserved. Implementation uses documented dated-group spans, upcoming/latest offseason selection and disclosed undated fallback rather than opener arithmetic. These are navigation assumptions for review, not changes to statistical eligibility or UNKNOWN/finality. No backend/schema/source/dependency/refresh changes or git publication. See [dashboard policy and tests](schedule-dashboard.md#task-008--current-week-home-default). |

| 60 | Owner approved Task 009 on `feature/schedule-freshness`: expose a sanitized read-only projection of the existing runner checkpoint through GET `/api/data-status/schedule`, with the shared volume mounted read-only in API. Distinguish checks, successful applies (including unchanged reconciliation), and observed changes; timestamps do not establish source publication or game finality. Dashboard loads once with explicit manual reload, local-time timestamps and unavailable/stale/error states. Default check-age warning is 36 hours, an operational display policy rather than a data-completeness promise. No schema/dependency/refresh/scheduler changes or git publication. See [freshness guide](schedule-freshness.md). |

| 61 | Owner approved offline NFL team-statistics validation on `feature/team-stats-feasibility`: NET team passing including sacks, with gross passing and original signed sack values preserved. Derive allowed yards from reciprocal opponent records. Establish the sign using actual artifacts and reviewed reference totals before calculating net values; no sign assumption or absolute-value repair. Source capture/audit and read-only canonical identity exports only; completion eligibility stays unverified without evidence. No statistics ingestion, schema changes, ranking publication, new API/frontend, jobs or git publication. See [validator guide](team-stats-validation.md). |

| 62 | Owner approved PostgreSQL team-statistics storage/guarded ingestion on `feature/team-stats-ingestion`, after successful real audit 705 pairs/1,410 rows. Add five tables: immutable batches, pair and team revisions, accepted pair pointers and selection events, with new-table-only PostgreSQL guards. Revalidate original artifacts/receipts/references, compare canonical identities under the existing schedule transaction lock, bind every changing apply to an explicit reviewed token and retain prior pairs for logical rollback. Preserve declared origin, nullable storage, non-null accepted pairs, NET definition and UNKNOWN/completion separation. No schedule schema/logic, API/frontend, scheduler changes, real development migration/import/correction, or git publication without separate approval. See [Task 010](agent-task-010.md) and [schema/runbook](team-stats-ingestion.md). |

| 63 | Owner approved focused Task 010 security hardening after independent NO-GO: trigger-generated same-game acceptance chains, complete candidate/receipt/byte binding at apply, and native PostgreSQL owner/API/ingestion role separation within the existing container. Keep bootstrap administrator for explicit provisioning only; NOLOGIN `nfl_owner` owns schema, `nfl_api` reads schedule and revision, `nfl_ingest` has workflow-specific DML and cannot fabricate events/disable triggers/truncate history. New explicit admin Compose override and transactional existing-volume runbook; no new infrastructure. Migration 0002 remains unapplied and requires isolated restricted-login validation plus owner approval. Complete fingerprint version 2 invalidates previous review tokens. This changes security enforcement, not statistical definitions, statuses, APIs, schedule behavior or ranking eligibility. See [hardening report](team-stats-security-hardening.md). |

## Change control

New architectural or scope decisions are **proposals** until explicitly approved. Record each change, date, rationale, downstream docs/tests to update, and author/reviewer. Do not silently substitute providers, accept paid tiers, change rank definitions or increase agent autonomy.

## Known unresolved decisions, not blockers to document creation

- Exact source artifacts, provenance licenses, and per-season column coverage.
- Final database columns/indexes, detailed API schema contracts and error schema.
- Exact six-hour injury polling usefulness vs nightly source releases.
- Precise odds credit caps, account quota resets, retention permissions and market-by-market NFL availability.
- Deployment-specific HTTPS/Tailscale setup and separate backup storage medium.

These must be settled in approved task scopes, based on evidence.
