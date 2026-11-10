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
