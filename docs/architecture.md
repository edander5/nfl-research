# Technical Architecture

## System decomposition

**Current implementation:** development PostgreSQL/FastAPI foundation, schedule ingestion and [read-only API](schedule-api.md), owner-reported validated with 139 tests and 842 games. [Task 006](agent-task-006.md) adds the React schedule/matchup frontend and a loopback-only Vite Compose service, proxying `/api` through the existing default network without API/CORS changes. [Dashboard guide](schedule-dashboard.md) records pending frontend dependency/build/browser checks. Scheduler/Caddy/Tailscale deployment remains a target, not an initialized service.

**Frontend:** React + TypeScript + Vite; React Router for bookmarkable views; TanStack Query for backend state, caching and per-section failures; Tailwind CSS + shadcn/ui; Recharts for player game-log/bar/reference-line visuals; TanStack Table for rankings, game logs and book comparisons.

**Backend:** Python FastAPI, hybrid API design: small game/matchup overview endpoints and independently requested detailed team stats, injuries/depth charts, player research, and sportsbook odds. Prefer domain/service/repository layering, not business logic in HTTP handlers.

**Storage:** PostgreSQL with canonical normalized entities, SQLAlchemy and Alembic. Precompute or cache only after measuring query performance. Distinguish canonical statistics from external provider response metadata and odds quota tracking.

**Ingestion:** Separate Python data-pipeline package and **dedicated Docker scheduler container**. Initial 2024–2026 backfill; daily new data ingestion; weekly recheck of old data. Injury checks around every six hours *when source supports it*; daily depth charts, daily schedules, daily stats. Idempotent upserts, staging/validation, atomic publication, error quarantine, execution history, controlled retry/backoff and overlap prevention.

**Runtime:** Monorepo; Docker Compose; Caddy as single-origin private entrypoint with `/` for frontend and `/api/*` for FastAPI; internal Docker networking for services including PostgreSQL. Tailscale restricts access. HTTPS must be confirmed using a compatible Caddy/Tailscale scheme; never expose a public ingress by accident.

**Backup and delivery:** Daily PostgreSQL `pg_dump` backups, retained 7 daily/4 weekly as initial policy, copied to *separate physical storage*; monthly restore tests. GitHub Actions CI, **manual releases** via an approved controlled deployment procedure: verify CI, pre-deploy backup, approved Alembic migrations, update containers, smoke/health checks. Roll back app separately from database; backup restoration by explicit approval only.

## Request/data flow

1. User selects a schedule week or matchup in React Router.
2. TanStack Query calls `/api` through Caddy; cache keys include game/season/week/stage/cutoff/filter variables.
3. FastAPI queries PostgreSQL for canonical schedules/stats and computes cutoff-respecting research results.
4. Detailed sections load independently. Odds adapter consults centralized quota/cooldown/deduplication before any provider request.
5. Data ingestion updates records independently of FastAPI; source data versioning/correction metadata supports auditing and selective cache invalidation.

## Routes

- Frontend: `/schedule/:season/week/:week`, `/games/:gameId`, `/teams/:teamId`, `/players/:playerId`.
- API: `/api/seasons/:season/schedule`, `/api/games/:id/overview`, `/api/games/:id/team-rankings`, `/api/players/:id/game-logs`, `/api/players/:id/prop-research`, `/api/games/:id/injuries`, `/api/games/:id/depth-chart`, `/api/games/:id/odds`, `/api/data-status`.
- The examples above remain illustrative future contracts. Implemented Task 005 routes are `GET /api/seasons`, `GET /api/seasons/{season}/schedule` (explicit REG/POST, optional week/round) and `GET /api/games/{game_id}` (canonical UUID). See [the API guide](schedule-api.md) and generated OpenAPI for the actual contract. Task 006 frontend routes are `/schedule/:season/:stage/:selection` and `/games/:gameId`; no statistics endpoint is implemented. Broader-scope pagination is deferred; the bounded schedule reads one season.

## Security and configuration

- Tailscale access controls restrict the app to authorized private devices. No application login for personal MVP; reevaluate before public launch.
- Caddy binds only to the intended private interface/access path. Database and scheduler have no public ports. Administrative operations require trusted local access.
- Separate dev and production `.env` configuration; Pydantic Settings startup validation; safe `.env.example`; no secrets in repository, Docker image or logs.
- Treat API/provider data as untrusted; schema validation, timeouts, safe logging, request budget enforcement and fail-closed admin access.

## Performance targets

Representative controlled-network **p95** targets: schedule and matchup overview <500ms; team rankings <1s; player research <1.5s; historical comparisons <2s. Frontend render and external odds are measured separately. Start with indexes and query plans; no Redis at MVP start. Use explicit freshness policy for stale data.

## Testing and operations

- `pytest`: computations, API via HTTPX, PostgreSQL integration, ingest idempotency/retry/corrections.
- Vitest + React Testing Library: filters, charts/controls, sorting, states.
- Playwright: basic schedule → matchup → player research flow.
- Structured logs (correlation IDs, timings, status/errors), lightweight slow-query metrics, ingestion history and retention; no mandatory Prometheus/Grafana.

## Architectural invariants

- No future-data leakage. Reconstructed historical rankings ≠ guaranteed past published snapshots.
- Missing != zero; DNP != zero result for hit-rate eligibility; pushes tracked.
- Source identifiers mapped into canonical internal team/player/game IDs; transfers retain per-game actual team membership.
- Sportsbook odds are optional, on-demand, budgeted, and never block historical research.
- New paid services/dependencies/production changes require user approval.

## Task 007 — guarded manual refresh

The [manual refresh runner](schedule-refresh.md) adds one-shot retrieval/validation/comparison and reviewed transactional apply to the existing Python ingestion package. It uses standard-library HTTPS, filesystem locks/atomic archives and a durable local run journal, plus existing SQLAlchemy. The opt-in Compose `refresh` service has outbound access on the default network and isolated development DB access on the internal database network, without ports or recurring work. The existing scheduler architecture remains planned. No source-status API/frontend or database schema changed. Source-only scores remain reported/UNKNOWN and need explicit operator review. Current approval: [Task 007](agent-task-007.md).


## Task 009 — operational freshness projection

The API reads the existing runner checkpoint through a bounded, allowlisted repository/service/schema layer. Its existing refresh volume is mounted read-only. The dashboard uses a separate TanStack Query request with explicit reload and no polling. PostgreSQL schema and schedule response contracts are unchanged. See [freshness design and limitations](schedule-freshness.md).


## Offline team-statistics audit

The [team-statistics validator](team-stats-validation.md) is a standard-library-only CLI under `backend/ingestion/team_stats/`. It captures official release bytes and produces local reports, with no application settings, SQLAlchemy session, PostgreSQL connection, API or scheduler. Optional canonical UUID exports are read-only input files. It reuses only the pure schedule validation contract; existing schedule ingestion/refresh services are unchanged.


## Task 010 — guarded statistics storage

The [statistics storage/ingestion guide](team-stats-ingestion.md) records the additive five-table schema and manually invoked transaction adapter. The offline CLI remains unchanged and offline. A separate `ingestion.team_stats.ingest` command uses the existing ingestion container, snapshot volume and development database; it holds the shared schedule advisory lock while comparing live canonical identities and publishing complete immutable pairs. Dry-run is default, every changing apply requires a baseline-bound review token, and rollback moves accepted pointers with append-only history. No new service, volume, scheduler, API, frontend or completion inference.


## Team-statistics security hardening

Native PostgreSQL roles now separate NOLOGIN schema owner, read-only schedule API and restricted ingestion. Existing bootstrap credentials are confined to an explicit admin Compose override, not routine connections. Acceptance events are trigger-generated and apply binds complete candidate evidence plus a locked baseline. See [security hardening and owner transition](team-stats-security-hardening.md); no new infrastructure or automatic provisioning at API startup.


## Task 011

Task 011 adds read-only team logs, per-game paired stats and season aggregates using explicit column projections through accepted pair pointers. Opponent joins derive allowed yards; SQL performs paging/count and per-metric aggregation. The approved nfl_api column grants omit batch evidence/raw records/history and all writes. See [API and grant procedure](team-stats-api.md). No schema, ingestion, frontend or ranking implementation.


## Task 012

Task 012 reuses accepted reciprocal team-statistic projections for a single-statement season league population, schedule coverage and metric aggregation. A small SQL-aggregated team result is competition-ranked with exact Python Fraction comparisons, then filtered by optional team/category. No per-team queries, new permissions/schema or completion inference. See [rankings contract and test gate](team-rankings-api.md).


## Task 013 — rankings frontend

The [rankings dashboard](team-rankings-dashboard.md) uses existing React Router and TanStack Query with typed Task 011/012 clients, semantic sortable tables and shared UI conventions. URL filters preserve season/stage/category/display order; sorting never recomputes API ranks. A lightweight team route shows REG/POST accepted game logs separately in explicit combined mode. No new dependencies, backend, source, infrastructure or completion eligibility.


## Task 014 — team-statistics refresh preparation

The [manual preparation runner](team-stats-refresh.md) composes existing official acquisition, pure offline validators, unchanged candidate admission and live importer comparison. It uses the existing restricted refresh container and snapshots volume, with a separate filesystem namespace and shared atomic JSON/locking primitives. Private reports retain review plans; operational metadata distinguishes source checks, valid candidates and existing database imports. No publication path, API/frontend, schema, permissions, source/status or ranking definition changes.


## Task 015 — opt-in prepare-only scheduler

The [dedicated scheduler container](scheduled-nfl-refresh.md) reuses the backend image, runtime ingestion role, existing networks/volumes and original dry-run commands. Standard-library daily ZoneInfo scheduling plus persistent claims avoids cron/queue dependencies, startup replay and duplicate work. Two independent bounded workers preserve original per-pipeline locks and database guards. No automatic acceptance or notifications; operator status reads sanitized original checkpoint observations. Default services still exclude the scheduler.


## Task 016 — Game Preview

The [game page](game-preview.md) composes existing schedule detail and one all-category league rankings request. Canonical UUIDs select the two displayed teams only after authoritative league ranking. TanStack Query isolates comparison failure/cache/filter state; React Router preserves return navigation. No per-team query, client ranking or new backend endpoint. Current accepted season comparisons explicitly do not claim completed-before-kickoff eligibility.
