# Task 011 — read-only accepted NFL team statistics

Owner approved Task 011 on `feature/team-stats-api`, including narrowly scoped API column grants. Owner reports migration 0002, restricted roles, 705 accepted game pairs / 1,410 team rows and 343 passing WSL tests before this task. These are owner-reported baseline results, not new agent verification. No development permissions, schema, data or imports were changed by the agent.

## Endpoints and response semantics

All endpoints return `{data, meta}` with typed OpenAPI schemas. Canonical UUIDs are required; source IDs and team abbreviations are not path aliases.

| GET route | Query | Data |
|---|---|---|
| `/api/teams/{team_id}/games` | Required `season=2024..2026`, required `season_type=REG|POST`; optional `week` (REG 1–18 / POST 19–22), `limit` (1–100, default 50), `offset` (0–1,000,000, default 0) | Paginated accepted team-game rows; total/returned counts in meta |
| `/api/games/{game_id}/team-stats` | No query parameters | Home then away accepted team rows. An existing game without accepted stats returns `data: []`, `statistics_available: false` |
| `/api/teams/{team_id}/stats` | Required `season`, required `season_type` | Accepted game count and totals/averages/known-value denominators for offensive NET pass/rush, opponent NET pass/rush allowed, reported points and independently stored verified-final points |

Examples (replace UUID placeholders with existing canonical IDs):

```text
GET /api/teams/{team_id}/games?season=2024&season_type=REG&week=2&limit=10&offset=0
GET /api/games/{game_id}/team-stats
GET /api/teams/{team_id}/stats?season=2026&season_type=REG
```

Unknown teams/games return 404 using the existing error envelope (`TEAM_NOT_FOUND` / `GAME_NOT_FOUND`). Valid empty team filters return 200, an empty log or a zero accepted-game count; aggregate totals/averages remain null when no values exist. Invalid UUIDs, missing/unsupported seasons, unknown/duplicate query keys, out-of-range pagination and incompatible week/stage filters return 422. Mutating methods return 405. Database failures return sanitized 503, without SQL, credentials or evidence. Existing schedule response contracts stay unchanged.

A game row includes game/source IDs, season/stage/week, nullable UTC kickoff and source date, team/opponent UUID/code/name, HOME/AWAY, gross passing, original signed sacks, NET passing, rushing and opponent-derived allowed yards; reported points, stored status/score finality, accepted pair UUID, selection generation and revision observation time. Public provenance includes source artifact UUID/hash, provider, declared/verified origin, documented URL/license/attribution, row hash/line and the separate schedule artifact reference. No raw JSON, filesystem paths, batch IDs/evidence, review tokens or selection history are returned. Revision observation time is not source publication or game completion time.

NET passing uses the stored verified definition `net_pass_negative_sacks_v1`: gross plus original signed nonpositive sack adjustment. No gross substitution, absolute-value repair or API-side correction. Opponent metrics come from the reciprocal team row of the **same accepted pair**, never another revision. Statistics and reported scores do not imply FINAL or completed-before-cutoff eligibility. Verified-final point aggregates require stored FINAL status and final evidence URL/time. With current UNKNOWN schedules these verified-final aggregates normally have no values.

Each aggregate is `{total, average, games_with_values}`. SQL SUM/AVG ignore nulls; the count of non-null values is the denominator for that exact metric. Zero and negative yardage remain values. No values gives null total/average and denominator zero. All aggregates cover only accepted-statistics games, not the complete schedule. They are reconstructed historical aggregates, **not pregame rankings**. REG and POST are required explicit separate selections; combined mode is deferred.

Logs sort by known kickoff ascending, unknown kickoff last, then week/source game ID/canonical UUID. This is a date ordering policy, not completion eligibility. The repository uses explicit projections and reciprocal joins; no lazy-load/N+1 behavior. A CTE returns page and total count in one statement snapshot, including offsets beyond the last row. Summaries aggregate in SQL. Team/game existence adds one bounded lookup. Concurrent reads see a consistent accepted pair per data statement; the preceding identity lookup is not a historical snapshot guarantee.

## Security grant review

No table-wide SELECT grant is added. `API_STATS_COLUMNS` in `backend/app/db/roles.py` is the single allowlist used by provisioning and the explicit grant CLI:

- `team_stats_accepted`: game_id, pair_id, generation.
- `team_stats_pairs`: id, game_id, source_artifact_id, definition_version, recorded_at.
- `team_game_stat_revisions`: pair_id, game_id, team_id, opponent_team_id, side, gross_passing_yards, original_sack_yards, net_passing_yards, rushing_yards, source_record_sha256, source_line.

Batches and selection events remain inaccessible. Batch IDs, pair history links/content hash and raw source records remain inaccessible. All API writes, TRUNCATE, owner membership, schema/trigger alterations remain forbidden. Ingestion grants are unchanged. A SQL credential holder can read permitted columns from past revisions; selecting **only currently accepted revisions** is enforced in the API's pointer joins. Database-level row isolation would require a separately approved view/RLS design; no such schema change is made here.

## Existing development database: owner-executed grants only

The following commands are prepared for the owner, **not executed by the agent**. Use the existing private `.env` and database volume; do not repeat migrations, imports, password provisioning or backups/restore. This new CLI only grants the approved SELECT columns and never changes credentials, roles, ownership, ingestion ACLs or data. It requires development settings, actual development DB name and revision 0002, then SET LOCAL ROLE to the existing NOLOGIN schema owner. Errors are sanitized. Repeated apply is idempotent.

From repository root:

```bash
# Validate without printing credentials.
docker compose -f compose.yaml -f compose.admin.yaml config --quiet

# Inspection only: shows booleans for the approved column reads.
docker compose -f compose.yaml -f compose.admin.yaml --profile ingestion run --build --rm \
  ingestion python -m admin.team_stats_api

# Owner explicitly applies the reviewed grants (no migration or import).
docker compose -f compose.yaml -f compose.admin.yaml --profile ingestion run --rm \
  ingestion python -m admin.team_stats_api --apply

# Confirm all approved columns report true and all restriction checks report true.
docker compose -f compose.yaml -f compose.admin.yaml --profile ingestion run --rm \
  ingestion python -m admin.team_stats_api

# Runtime API uses base Compose with nfl_api, never the administrator override.
docker compose up -d --build api
curl --fail http://127.0.0.1:8000/api/health
curl --fail http://127.0.0.1:8000/api/ready
```

Fresh environments must also run the dedicated grant command after migration 0002. Full role provisioning now applies the same allowlist when statistics tables already exist; no new migration or startup DDL is introduced. Do not modify applied migration 0002. A grant error requires diagnosis; never switch API credentials to an administrator. Do not use the full role provisioning command merely to add these grants, as that also changes passwords/ownership.

## Tests and exact WSL commands

```bash
# File-only/unit/validation tests in the existing isolated Python environment.
.venv/bin/python -m pytest backend/tests/test_team_stats_api.py -m 'not api and not database' -q

# Existing isolated test DB profile: bootstrap test setup only, then actual restricted-login tests.
docker compose --profile test run --build --rm tests python -m pytest \
  tests/test_team_stats_api.py tests/test_team_stats_security.py tests/test_schedule_api.py -q -ra

# Full regression suite, including database and HTTP transport tests.
docker compose --profile test run --build --rm tests
docker compose --profile test stop db_test
```

Never point tests at `nfl_research_dev`. The fixture provisions only `nfl_research_test`. Synthetic ingestion/correction/rollback cases exercise accepted-pointer selection inside rolled-back test transactions; they do not operate on owner statistics. One test authenticates as actual `nfl_api` and runs the public projection plus denied-column/write/owner/trigger tests. A separate populated synthetic fixture uses SET LOCAL ROLE nfl_api inside the same uncommitted transaction so it can inspect its fixture data; this supplements, not substitutes for, real-login tests. PostgreSQL tests must pass without skips in WSL. A failure is not a pass.

Agent results: selected non-API backend suite **251 passed, 76 skipped, 34 deselected** before supplemental validation/error tests were added. Existing async schedule validation/read-only/error regression subset: **23 passed, 10 deselected**. New synchronous HTTP success/error test timed out at 25 seconds in the known local TestClient thread portal, and is unverified here. Docker probe returned socket permission denied. No PostgreSQL tests or grants ran here. Python compilation and diff whitespace checks passed. Supplemental and final suite results are appended below. These suites overlap; do not sum their counts. Existing TestClient thread-portal limitations may block synchronous transport tests locally; WSL remains the final runtime gate. Source authentication/checksum, missing current-season coverage, UNKNOWN/finality and completion eligibility limitations are unchanged.

## Changed files

- New `backend/app/api/team_stats.py`: read-only routes/dependencies/OpenAPI.
- New `backend/app/schemas/team_stats.py`: strict filters, public data/meta and aggregate contracts.
- New `backend/app/repositories/team_stats.py`: column-only accepted/reciprocal joins, SQL paging/count and aggregation.
- New `backend/app/services/team_stats.py`: views, missing-resource and score/statistics semantics.
- `backend/app/main.py`: register router.
- `backend/app/api/errors.py`: team-not-found handling and statistics-specific sanitized DB failure message; existing schedule messages unchanged.
- `backend/app/db/roles.py`: shared column-grant allowlist and fresh provisioning hook, unchanged ingestion ACLs.
- New `backend/admin/team_stats_api.py`: explicit inspection/apply CLI, owner-only grant procedure.
- New `backend/tests/test_team_stats_api.py`: service/query/API/filter/security/accepted-selection tests.
- `AGENTS.md`, `README.md`, `docs/architecture.md`, `docs/data-model.md`, `docs/decisions.md`, `docs/implementation-plan.md`, the two existing team-statistics ingestion/security guides, and this document: scope/security/API decisions and owner-reported current status.

No migration, schema, schedule/ingestion logic, raw data, frontend or dependency change.

## Final agent verification and recommendation

- Final broad non-API suite: **260 passed, 76 skipped, 34 deselected**, one existing TestClient deprecation warning. Command: `.venv/bin/python -m pytest backend/tests -m 'not api' --ignore=backend/tests/test_health.py -q`.
- Final Task 011 subset: **28 passed, 2 skipped, 1 deselected**, same existing warning. PostgreSQL cases were skipped because RUN_DATABASE_TESTS was not enabled without accessible PostgreSQL. Later additions to those unexecuted PostgreSQL assertions compiled successfully but remain runtime-unverified.
- Existing async schedule API regression subset: **23 passed, 10 deselected**. Existing additive readiness compatibility test: **1 passed, 3 deselected**. These overlap broader evidence; counts are not additive.
- New synchronous TestClient case: **timed out after 25 seconds**, not passed. Remaining synchronous HTTP/health cases require WSL execution. No repeated retry of the hanging method.
- Docker server probe: socket permission denied. All actual PostgreSQL projections, permission denials, correction/rollback selection and populated aggregate/order tests require the owner-run isolated Docker suite. No development grants or data operations occurred.
- Compileall and git diff whitespace validation passed. No dependency install or frontend build was needed or performed.

**GO for owner review and isolated WSL testing; NO-GO for relying on the new endpoints in development until that suite passes, the owner applies and verifies the column grants, and live read-only endpoint checks succeed.** Next proposed task for approval: review WSL results and read-only smoke checks of the three endpoints against the existing 705 accepted pairs. Rankings, frontend, new imports or correction publication remain outside this authorization.
