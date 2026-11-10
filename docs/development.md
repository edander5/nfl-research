# Development foundation and schedule schema

**Task 006 update:** Owner reports prior backend/API validation complete (139 tests/two warnings, 842 imported games). The React dashboard and development frontend service are now implemented; follow [dashboard install/start/test commands](schedule-dashboard.md) for required WSL frontend validation. Foundation-specific holds and “no frontend” statements below describe earlier task boundaries.

**Scope implemented:** PostgreSQL + FastAPI development foundation, Pydantic Settings, SQLAlchemy models, initial Alembic migration and automated tests. Task 004 adds a separate development-only importer and read-only raw-data mount on its opt-in Compose service; see [schedule ingestion](schedule-ingestion.md). No frontend, schedule API, production load, scheduler, Caddy/Tailscale deployment or live status integration. The raw CSV is not mounted into FastAPI or included in its build context.

**Historical agent recovery diagnosis:** [Task 003 results](runtime-validation.md) supersede the older environment diagnosis below. Docker CLI and Compose are installed; Compose rendering passes. This agent cannot connect to the Docker socket or create an IPv4 socket (EPERM), so host engine/DNS health is unresolved. A private ignored `.env` was created; do not overwrite it with `.env.example`. No package/WSL/Docker/security setting change was made. Runtime migration/tests/HTTP checks remain blocked.

**Current status:** Owner reports successful normal-WSL foundation runtime validation (45 passed/two warnings, migration successful, health/readiness 200). Agent socket access remains denied. New ingestion verification is reported separately in [Task 004 results](schedule-ingestion.md); previous dependency/network failures below do not describe current normal WSL.

## Layout

```text
compose.yaml                    development API/db and isolated test profile
.env.example                    placeholders only; real .env is ignored
backend/
  Dockerfile                    Python 3.12 development image, non-root runtime
  requirements*.txt             bounded approved dependencies
  app/main.py                   application factory; no auto-migrations
  app/api/health.py             liveness and database/schema readiness
  app/core/config.py            Pydantic Settings and redacted password
  app/db/                       SQLAlchemy base, engine and session dependency
  app/models/schedule.py        teams, aliases, artifact provenance and games
  alembic.ini
  alembic/env.py
  alembic/versions/0001_schedule.py
  tests/                        synthetic fixtures; HTTP/settings/PostgreSQL tests
```

The existing layered architecture is retained. Only health routes and persistence models are needed here; schedule services, repositories and the separate ingestion package belong to the next approved task. Frontend work is deferred. Runtime additions are the approved FastAPI/SQLAlchemy/Alembic/Pydantic stack plus the necessary ASGI server (Uvicorn) and PostgreSQL driver (Psycopg binary). Tests use the documented pytest/HTTPX stack. No new architectural service or paid provider.

## Run a fresh development environment

Prerequisites: working Docker Engine/Desktop with Compose v2, permission to pull `postgres:17-bookworm` and build `python:3.12-slim-bookworm`, and network access to PyPI during the build. Run from the repository root:

```bash
cp .env.example .env
```

Replace the password placeholder in `.env` locally before continuing. Keep `.env` untracked. Credentials are injected by Compose; `APP_DB_*` are consumed by Pydantic Settings. No database URL/credential is embedded in Alembic or source. Do not print `docker compose config` output containing resolved secrets; `--quiet` validates without printing it.

```bash
docker compose config --quiet
docker compose build api
docker compose up -d db
docker compose run --rm api alembic upgrade head
docker compose up -d api
curl --fail http://127.0.0.1:8000/api/health
curl --fail http://127.0.0.1:8000/api/ready
```

`/api/health` returns `{"status":"ok"}` without a database query. `/api/ready` checks connectivity and migration revision `0001_schedule`; it returns 503 with a generic response if unavailable/unmigrated. API startup never creates tables or runs migrations. The first migration is additive and contains no seed records. Run it only on this approved development database; never point these commands at production or an unrelated database.

PostgreSQL has **no published host port**. The API publishes only `127.0.0.1:8000`. Database and test networks are internal. This is a local developer setup; the approved Tailscale/Caddy private deployment remains a future task. `postgres_dev` retains development data. To pause without deleting it:

```bash
docker compose stop api db
```

Do not remove database volumes as a routine reset. Initial migration downgrade deliberately raises an error; destructive schema/restore actions need a separately approved task. This task ran no migration against an existing database.

## Run tests

The full suite uses a separate `db_test` service/database on its own internal network, with tmpfs storage, no host port, and no development volume. Test records are explicitly synthetic; database tests use rolled-back transactions/savepoints and never load the CSV. The fixture refuses to run outside a database named `nfl_research_test`, and requires `RUN_DATABASE_TESTS=1` (provided by the test service).

```bash
docker compose --profile test run --build --rm tests
docker compose --profile test stop db_test
```

The full test command starts the isolated database, applies the initial migration there, and checks ORM/migration agreement, relationships, non-null/foreign-key/unique/check constraints, restricted team deletion, status/finality/provenance safeguards, missing-versus-zero scores, and accepted duplicate `old_game_id` values. Health/configuration tests run in the same suite. A database connection or migration failure is a failure, not an automatic skip. Database tests skip only when deliberately not enabled.

For a local Python-only health/settings run (Python 3.10+), if pip is available:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
cd backend
../.venv/bin/python -m pytest tests/test_health.py tests/test_settings.py -q -ra
```

This workspace's virtual environment was created with existing `uv` and has no pip seed. The equivalent installation command for that environment is:

```bash
UV_CACHE_DIR=/tmp/nfl-foundation-uv-cache uv pip install --python .venv/bin/python -r backend/requirements-dev.txt
```

To inspect DDL without applying it, once Alembic is installed:

```bash
cd backend
../.venv/bin/python -m alembic upgrade head --sql
```

Optional local database execution requires deliberately provisioned isolated PostgreSQL named `nfl_research_test` plus `APP_DB_HOST`, `APP_DB_PORT`, `APP_DB_NAME`, `APP_DB_USER`, `APP_DB_PASSWORD`, and `RUN_DATABASE_TESTS=1`. Prefer the Compose test profile; no database is created/reset by the fixture itself. Never reuse the development DB for tests.

## Physical schema and safeguards

- `teams`: internal UUID primary key; unique canonical code and required nonblank name. Codes are independent of names and stadiums.
- `team_aliases`: provider/code composite primary key pointing to a team, preserving provider identity without changing canonical UUIDs. Temporal alias changes are not inferred; the 2024–2026 importer must review conflicts.
- `source_artifacts`: UUID, provider/path, measured SHA-256/size, separate documented and declared URLs, optional publisher hash/revision/publication/download timestamps, attribution/license, notes and explicit origin status. `recorded_at` means database observation time. No fabricated retrieval time. Default origin is DECLARED; VERIFIED requires matching publisher hash, declared URL, verification method/time. Matching structure is not proof of source authenticity.
- `games`: internal UUID plus unique `(provider, source_game_id)`, required canonical sides, source team labels, season/stage/round/week, nullable source Eastern date/time and UTC scheduled kickoff, nullable reported scores, optional venue flags, source artifact/record hash/line/raw record and observation/update timestamps. Provider must match the linked artifact. Scope is 2024–2026; round/week and distinct-side checks prevent inconsistent records.

`old_game_id` is nullable and **nonunique**, not a foreign/identity key. Other optional provider IDs can be retained in JSONB `external_ids`; ambiguous mappings are not turned into unique aliases. `raw_source_record` remains nullable until a real importer can retain the original record; `source_record_sha256` is required for each game. The importer must define that record hash consistently and preserve raw artifacts. No importer or correction/rejected-record history machinery is implemented here; these are required in the next ingestion task before publishing imported data.

Statuses are limited to UNKNOWN and FINAL. UNKNOWN is the Python and database default. FINAL requires paired scores, nonblank explicit evidence URL and verification time. No time-based or score-based transition exists, and IN_PROGRESS/POSTPONED are rejected. The database verifies evidence-field presence, not authenticity of a document. All supplied CSV games therefore remain UNKNOWN unless separately verified. Reported scores are not labeled final; NULL stays NULL and legitimate zero stays zero. Only paired nonnegative scores or two NULLs are accepted.

The local CSV's hash mismatch remains unresolved: expected declared state with mismatching publisher hash must not become VERIFIED. No real artifact/provenance rows were seeded in this migration. Internal game IDs survive later source corrections; explicit source-ID alias/revision history and import validation must be designed in the next approved task. `updated_at` updates through SQLAlchemy, not a PostgreSQL trigger; direct SQL changes need explicit timestamp handling. Future schedule changes must not be inferred as postponements or create synthetic postseason games.

## Foundation-task verification (historical)

| Check | Actual result |
|---|---|
| Docker/Compose availability | Blocked: Windows Docker wrapper reports Docker unavailable in this WSL distro; WSL integration must be enabled |
| Python dependency installation | Blocked: one uv installation attempt failed DNS resolution for `pypi.org`; dependencies were not installed |
| pytest suite | Could not start: `.venv/bin/python -m pytest backend/tests -q -ra` reports `No module named pytest`; no tests collected/passed |
| Alembic offline SQL | Could not start: `No module named alembic`; DDL not rendered or applied |
| PostgreSQL migration/constraint suite | Not run: no usable Docker/PostgreSQL or installed driver |
| Static verification | All 17 Python files compile/parse; all four model/migration column sets and 24 frozen check expressions/names match; local Markdown file-link targets resolve. These checks passed but do not verify SQLAlchemy mapping or PostgreSQL behavior |
| Raw CSV | SHA-256 unchanged: `66f7a71b12eeb8da8a5c332cfadb245da693aa66e2064fba734983dc41e68fd5` |

The foundation task previously suggested checking Docker Desktop WSL integration. Task 003 has since established that CLI/Compose exist and this agent receives socket EPERM denials. **Do not change WSL/Docker/network settings based on the historical table.** First compare normal-terminal `docker version` and `getent hosts pypi.org`; see the current report for exact results and pending commands. System/privileged changes require owner approval. No such configuration was changed.

The dependency ranges and container tags are bounded but not immutable locks/digests. A network-enabled resolution and successful integration run are mandatory before relying on this environment, and exact reproducible dependency/image pinning remains a delivery risk. There is no CI or deployment automation in this scoped foundation. All PostgreSQL-specific behavior, Compose configuration and ORM/migration compatibility remain unverified at runtime here.

## References and next review gate

Project requirements: [architecture](architecture.md), [schedule contract](schedule-data-contract.md), [actual CSV validation](schedule-validation-report.md), [data model](data-model.md). Implementation references checked 2026-11-05: [SQLAlchemy declarative mapping](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html), [Alembic environments](https://alembic.sqlalchemy.org/en/latest/tutorial.html), [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/), [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/), [Psycopg installation](https://www.psycopg.org/psycopg3/docs/basic/install.html), [Docker WSL integration](https://docs.docker.com/desktop/features/wsl/).

Next proposed implementation task, for approval: first run the provided isolated PostgreSQL suite after environment recovery, resolve any failures, then implement a development-only schedule ingester with idempotency, staged validation/quarantine, correction provenance and last-good preservation. It must retain the known ID and origin limitations and keep every unsupported status UNKNOWN. No ingestion/frontend/production work is authorized by this foundation task.

## Task 004 — development schedule ingestion

The owner subsequently approved [Task 004](agent-task-004.md) after reporting successful normal-WSL foundation validation: 45 tests passed/two warnings, Compose and PostgreSQL healthy, initial migration successful, health/readiness HTTP 200. Those are user-reported results. Earlier environment failures and ingestion holds above are historical.

The development-only importer is now implemented; see [schedule ingestion commands, provenance safeguards and actual verification](schedule-ingestion.md). The existing schema/migration is unchanged. Immutable artifact captures and versioned import/correction receipts now supply provenance for imports; no dedicated audit tables were added. Full runtime verification of these additions still requires the separate test database through normal WSL. No frontend or schedule API is authorized by this task.

## Task 005 — read-only schedule API

Owner now reports Task 004 validated in normal WSL: 842 development games with expected seasonal counts, reimport 0 inserts/0 updates/842 unchanged and 78 passing tests. These are prior-task user-reported results, not independent evidence for the new API. [Task 005](agent-task-005.md) authorizes only read-only schedule/coverage/UUID endpoints, now implemented without schema, dependencies, infrastructure or ingestion changes. See [API guide](schedule-api.md) for exact WSL test/start/curl commands, response contracts and actual agent results. Earlier “no schedule API” statements describe the foundation/ingestion task boundaries. Frontend and later features still require approval.

## Task 006 — React weekly schedule dashboard

See [scope](agent-task-006.md) and [complete frontend guide/inventory](schedule-dashboard.md). The only Compose addition is non-root frontend Vite on 127.0.0.1:5173, proxying relative `/api` requests to the existing API. No CORS, schema, ingestion, database-port or backend contract changes. Install approved dependencies locally in `frontend/`, then run `npm run typecheck`, `npm test`, `npm run build`; generate/review the missing lockfile before claiming reproducibility. Dependency installation failed registry DNS in the agent, so these checks must run in normal WSL. Existing backend test and migration procedures remain unchanged; this task needs no development migration or reimport.

## Task 007 — guarded manual refresh

The owner approved an unscheduled development refresh workflow after [feasibility research](schedule-auto-update-feasibility.md). Follow the [refresh guide](schedule-refresh.md) for `docker compose --profile refresh run --build --rm refresh` dry-run, reviewing the full saved report, token-bound saved-candidate apply, commit recovery and exact WSL tests. The profile uses separate durable state plus existing archives, no ports or timers, and never replaces the original CSV. No development migration, frontend change or source API contract change. New-source and PostgreSQL integration remain unverified here; unit evidence is distinguished in the guide.


## Task 009 — schedule freshness

See [freshness guide](schedule-freshness.md) for exact local/container verification commands, result evidence, environment limitations and complete changed-file inventory. The existing refresh volume is read-only in API; no migration, import or refresh execution is needed to view its existing checkpoint.
