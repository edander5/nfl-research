# Read-only schedule API — Task 005

## Scope and contract checks

Approved scope: [Task 005](agent-task-005.md). Branch: `feature/schedule-api`. No database/model/migration, dependency manifest, Docker service, raw CSV or ingestion changes. Queries use imported PostgreSQL data only; requests do not download data, trigger ingestion, edit schedules, commit or finalize games.

Before implementation, inspection identified stale documentation claiming ingestion/runtime checks were still pending. The owner now reports 842 development games, expected seasonal coverage, idempotent reimport (0 inserted/0 updated/842 unchanged), and 78 passing tests. These are **owner-reported prior-task results**, not verification of this new API. No conflict with the physical schema or approved source/status contract requires a schema change.

Existing team names contain source abbreviations. They are returned as stored, without invented full names. The original CSV's checksum discrepancy remains unresolved. Artifact origin is exposed as stored; successful database import does not authenticate origin. Coverage means imported database coverage, not an official completeness/freshness assertion. Original source licensing conclusions remain those in the [Schedule Data Contract](schedule-data-contract.md); this task performs no new download or licensing verification.

## Endpoints

All routes are under `/api`; only GET is implemented. Existing `/api/health` and `/api/ready` responses remain unchanged. These replace the architecture's provisional schedule/overview examples for this approved scope.

| Endpoint | Parameters | Successful response |
|---|---|---|
| `GET /api/seasons` | None | Actual available imported seasons, ascending, with REG and POST coverage; supported/missing seasons in metadata |
| `GET /api/seasons/{season}/schedule` | Path season: 2024–2026; required `season_type=REG` or `POST`; optional `week` and `round` | Matching games, echoed filters, returned count and coverage for both stages of that season |
| `GET /api/games/{game_id}` | Internal canonical UUID, no query parameters | One matchup with provenance and score/finality information |

Filter rules:

- REG weeks are 1–18; postseason round is forbidden.
- POST weeks are 19–22; `round=WC/DIV/CON/SB` maps to 19/20/21/22.
- Both POST week and round may be supplied when they agree.
- Omit week/round for the entire requested stage. REG/POST are never implicitly combined.
- Uppercase enum tokens are required. Unknown query keys, repeated keys, missing season type, invalid season/UUID/type/range or conflicting filters return 422.
- A valid empty selection returns 200 and `data: []`, including absent 2026 POST, a week with no imported matches, or a supported season not yet imported. Coverage counts are zero/empty for missing stages. No synthetic game records are added.
- Unknown valid UUID returns 404. Source game IDs/legacy IDs are not accepted as UUID aliases. The API is scoped to provider `nflverse`; unrelated provider records do not appear and do not satisfy UUID lookups.

Order: **week ascending → scheduled UTC kickoff ascending, nulls last within week → source game ID lexically → internal UUID**. This remains deterministic for tied or unknown kickoff times. It preserves calendar-week navigation for whole-stage responses.

No pagination is needed for this bounded 2024–2026 schedule contract (a complete season has 272 REG and 13 POST games). The schedule repository reads one season with eager team/artifact joins, then the service filters that ordered result and computes both-stage coverage from the same SQL statement snapshot. This avoids games/coverage straddling an atomic import. UUID lookup is one eager query; season availability uses one grouped SQL query. New requests may observe legitimate committed corrections. Performance targets have not been benchmarked; broader scopes/pagination remain separate decisions.

## Response schemas

Successful schedule responses use `{ "data": [...], "meta": {...} }`; single-game `data` is an object. See full types/nullability in `/openapi.json` or interactive `/docs`.

`GameView` contains:

- `id`, `season`, `season_type`, `week`, `game_type`.
- `home_team` and `away_team`: canonical UUID, code and stored name, preserving designated sides at neutral sites.
- Nullable `scheduled_kickoff_utc` (ISO 8601 UTC), source date/time and explicit `source_timezone: America/New_York`.
- Nullable `reported_home_score`, `reported_away_score`; legitimate zero stays zero.
- Stored `status` (UNKNOWN or FINAL); `score_finality` is NOT_REPORTED for absent scores, UNVERIFIED for scores with UNKNOWN, or CONFIRMED_FINAL only for stored FINAL.
- Nullable `final_evidence` with stored URL/verification timestamp, emitted for FINAL only. This is a stored evidence indicator, not a new external verification by the API.
- Nullable `neutral_site`, `overtime`, and database `updated_at` (not completion time).
- `provenance`: artifact UUID, provider/source game ID, artifact and canonical-record SHA-256, source line; stored DECLARED/VERIFIED origin; nullable documented/declared URLs, source revision, publisher checksum, verification time/method, publication/retrieval times; artifact database observation time; license URL/attribution.

Neither kickoff nor score presence changes status. Historical season context never creates FINAL. Missing scores/time stay null; no scheduled/in-progress/postponed state is invented. Source publication/retrieval/observation/update times have separate meanings and cannot establish completion or current freshness.

Public responses exclude local artifact paths, raw source rows, private ingestion notes and correction receipts, credentials and other provider ID aliases. The original artifacts/correction trail remain in the database/volume under the existing ingestion contract.

`StageCoverage`, always supplied in REG then POST order, contains `season_type`, `game_count`, sorted available `weeks`, ordered available POST `rounds`, `reported_score_pairs`, `missing_score_pairs`, `unknown_status_games`, `final_status_games`, `unknown_kickoff_games`, `unverified_origin_games`. The last count includes games linked to artifacts without stored VERIFIED origin. Null source values remain visible rather than fabricated to meet expected counts.

`GET /api/seasons` returns only years with actual imported records. A completely empty database returns `data: []` and all three years in `meta.missing_seasons`; supported years remain visible in metadata. Every returned season includes both coverage entries, even when POST count is zero. No field claims that an expected count proves official correctness or completeness.

Common metadata discloses provider, reported-score semantics, database-only coverage, unsupported operational statuses, declared-origin/checksum limitations and missing-value handling. List metadata also includes filters/season, returned count and season coverage; availability metadata includes supported and missing years. No freshness timestamp is invented or cutoff-based research statistic computed.

Errors use:

```json
{"error":{"code":"GAME_NOT_FOUND","message":"Game not found","details":[]}}
```

| HTTP | Code | Meaning |
|---|---|---|
| 200 | — | Successful object/list, including valid empty results |
| 404 | GAME_NOT_FOUND | Canonical UUID has no accessible nflverse game |
| 404 | RESOURCE_NOT_FOUND | Route not found |
| 405 | METHOD_NOT_ALLOWED | Read-only route; `Allow` header retained |
| 422 | VALIDATION_ERROR | Invalid parameter; details contain location/type/message, without raw input/context |
| 503 | DATABASE_UNAVAILABLE | SQLAlchemy connection/query failure; no partial response or sensitive SQL/connection details |

Database failure is never returned as an empty successful schedule. SQLAlchemy errors during eager loading are covered by the same handler. Existing explicit health/readiness responses keep their previous shapes. Unhandled internal defects remain server errors rather than being mislabeled as missing data. OpenAPI declares typed 200/422/405/503 responses, plus 404 on UUID lookup.

## Normal WSL verification

From the repository root, using the already validated `.env` and Docker setup. These commands do not ingest or reset development data. The existing test fixture upgrades the **isolated test database only**, as in the approved test workflow; no development migration is needed for this task.

```bash
git branch --show-current
docker compose config --quiet
docker compose --profile test run --build --rm tests
docker compose --profile test stop db_test
```

Expected branch: `feature/schedule-api`. Full test collection currently contains 139 cases. The full suite must pass in WSL, including PostgreSQL and HTTP tests, before accepting the API; skipped database tests are not a substitute. Dependency versions may emit warnings; do not add dependencies based on a warning without approval. If failing, retain sanitized pytest output and stop before proceeding.

Start/rebuild the existing API and development database:

```bash
docker compose up -d --build --wait db api
curl --fail-with-body -sS http://127.0.0.1:8000/api/health
curl --fail-with-body -sS http://127.0.0.1:8000/api/ready
curl --fail-with-body -sS http://127.0.0.1:8000/api/seasons
curl --fail-with-body -sS 'http://127.0.0.1:8000/api/seasons/2024/schedule?season_type=REG&week=1'
curl --fail-with-body -sS 'http://127.0.0.1:8000/api/seasons/2025/schedule?season_type=POST&round=WC'
curl --fail-with-body -sS 'http://127.0.0.1:8000/api/seasons/2026/schedule?season_type=REG&week=9'
curl --fail-with-body -sS 'http://127.0.0.1:8000/api/seasons/2026/schedule?season_type=POST'
curl --fail-with-body -sS http://127.0.0.1:8000/openapi.json
```

Use an actual returned `data[].id` for UUID lookup. This standard-library check selects a real imported game, makes the lookup, and asserts the expected current dataset counts/null/status contract without needing shell placeholders:

```bash
python3 - <<'PY'
import json
from urllib.request import urlopen
base = 'http://127.0.0.1:8000'
def get(path):
    with urlopen(base + path, timeout=10) as response:
        assert response.status == 200
        return json.load(response)
seasons = get('/api/seasons')['data']
assert [s['season'] for s in seasons] == [2024, 2025, 2026]
counts = {s['season']: {c['season_type']: c['game_count'] for c in s['coverage']} for s in seasons}
assert counts == {2024: {'REG':272,'POST':13}, 2025: {'REG':272,'POST':13}, 2026: {'REG':272,'POST':0}}
week = get('/api/seasons/2024/schedule?season_type=REG&week=1')['data']
assert week
matchup = get('/api/games/' + week[0]['id'])['data']
assert matchup['id'] == week[0]['id']
assert matchup['status'] == 'UNKNOWN' and matchup['score_finality'] == 'UNVERIFIED'
assert matchup['provenance']['origin_status'] == 'DECLARED'
current = get('/api/seasons/2026/schedule?season_type=REG')['data']
assert len(current) == 272
assert sum(g['reported_home_score'] is None and g['reported_away_score'] is None for g in current) == 151
assert all(g['status'] == 'UNKNOWN' for g in current)
assert get('/api/seasons/2026/schedule?season_type=POST')['data'] == []
print('Read-only API checks passed for the original imported snapshot')
PY
```

These expected counts reflect the originally validated CSV; a legitimate later import may change scores/POST coverage. Review updated provenance rather than altering correct records to satisfy an old check. No live data was verified by this task.

Error checks (use `-i` to see status, without `--fail` for expected failures):

```bash
curl -sS -i 'http://127.0.0.1:8000/api/seasons/2026/schedule?season_type=REG&week=19'
curl -sS -i http://127.0.0.1:8000/api/games/not-a-uuid
curl -sS -i http://127.0.0.1:8000/api/games/00000000-0000-0000-0000-000000000000
curl -sS -i -X POST http://127.0.0.1:8000/api/seasons
```

Expected: 422, 422, 404 for absent UUID, 405. Database failures are tested using dependency overrides rather than intentionally disrupting your running database. A 503 requires checking PostgreSQL/API logs and readiness; do not reimport, reset volumes, or expose database ports to fix an API connection problem.

## Actual agent verification — 2026-11-07

Executed checks:

| Check | Actual result |
|---|---|
| `.venv/bin/python -m pytest backend/tests/test_schedule_service.py backend/tests/test_settings.py backend/tests/test_ingestion.py backend/tests/test_schedule_database.py -q -ra` | **55 passed, 48 skipped**. Includes 28 new service/schema/query/OpenAPI unit tests. PostgreSQL cases skip because the isolated server is inaccessible and `RUN_DATABASE_TESTS` is not enabled. |
| `.venv/bin/python -m pytest backend/tests/test_schedule_api.py -k 'invalid_request or read_only or async_error_handler_transport' -q -ra` | **23 passed, 10 deselected**, one Starlette TestClient/httpx deprecation warning. Covers real ASGI validation, read-only methods and 404/503 handler wiring with synthetic dependency failures; no actual DB failure is induced. |
| Full collection: `.venv/bin/python -m pytest backend/tests --collect-only -q` | **139 cases collected**. Collection is not execution. |
| `timeout 15 .venv/bin/python -m pytest backend/tests/test_schedule_api.py::test_seasons_json -vv -o faulthandler_timeout=8` | **Exit 124**, waiting in TestClient/AnyIO portal before any assertion. No successful HTTP response or assertion failure established. |
| `docker version` | Client available; daemon socket permission denied. No PostgreSQL/container-backed checks executed. |
| `docker compose config --quiet`; Python `compileall` for backend/app and backend/tests; `git diff --check` | **Passed**. These do not verify runtime PostgreSQL or successful synchronous HTTP requests. |
| Original raw CSV SHA-256 | Unchanged: `66f7a71b12eeb8da8a5c332cfadb245da693aa66e2064fba734983dc41e68fd5`. |

The two completed test subsets are disjoint: 55 unit/config/parser cases and 23 async HTTP cases passed. This is **not a full-suite pass**. The 48 existing database cases skipped; the ten remaining new API cases (including one PostgreSQL end-to-end case) and three existing health cases remain unverified here. The new PostgreSQL fixture covers historical years, REG/POST/round/week filters, null scores, tied/unknown kickoff order, empty selections, provider isolation, canonical lookup and unchanged row count. Full normal-WSL execution is mandatory before acceptance.

No API call against the real development database, container startup, import or migration was executed by the agent. Docker client works but daemon access is denied at `/var/run/docker.sock`. A bounded synthetic HTTP TestClient attempt times out entering the AnyIO thread portal, before assertions; a direct async HTTPX request to a synchronous handler also timed out. The precise environment cause remains unresolved; no Docker/WSL/security configuration change was attempted.

Validation-only requests and unsupported methods can execute using HTTPX async ASGI transport without invoking synchronous work; those tests exercise actual routing/validation/error serialization, without a database or lifecycle startup. Passing service/schema/query-compilation tests and these HTTP cases do not prove successful PostgreSQL-backed endpoints work. The owner's prior 78-test result predates this task.

## Changed files and remaining review gate

| Files | Purpose |
|---|---|
| `backend/app/api/schedule.py`, `errors.py`, `main.py` | Read-only routes, consistent sanitized error handlers and router registration |
| `backend/app/schemas/` | Typed public contracts and stage/week/round validation |
| `backend/app/repositories/`, `backend/app/services/` | Provider-scoped eager SQL queries, same-statement schedule coverage, response mapping without status inference |
| `backend/tests/test_schedule_service.py`, `test_schedule_api.py`, `conftest.py`, `backend/pyproject.toml` | Synthetic service/OpenAPI/HTTP/PostgreSQL tests, shared fixtures and HTTP test marker |
| `AGENTS.md`, `docs/agent-task-005.md`, `docs/decisions.md` | Current approved scope and decision record |
| `README.md`, `docs/architecture.md`, `docs/implementation-plan.md`, `docs/development.md`, `docs/schedule-ingestion.md`, `docs/schedule-data-contract.md`, this guide | Current implementation/evidence, endpoints, WSL commands and historical-result distinctions |

Remaining risks: source origin/checksum uncertainty, no explicit operational status source, source abbreviations as display names, unbenchmarked query performance, and pending successful-request/PostgreSQL runtime validation in normal WSL. The API provides no current-data freshness guarantee or independently verified final results. Existing dependency ranges are not immutable locks; no packages were installed or changed here.

Next proposed task **for owner approval**, after reviewing this API and completing WSL validation: the React weekly schedule and basic matchup view, consuming these contracts and visibly labeling UNKNOWN/reported scores, provenance and missing POST coverage. No frontend work, commit, merge, push or deployment is authorized or performed in Task 005. Stop for review.

## Subsequent owner validation and dashboard scope

Before Task 006, the owner reported this API/backend validated with 139 passing tests/two deprecation warnings, committed and merged to main; 842 games remain imported. Those user-reported results supersede the earlier normal-WSL pending gate without retroactively becoming agent-executed checks. [Task 006 dashboard](schedule-dashboard.md) consumes the existing schema unchanged. New frontend test/build/browser evidence is reported separately.
