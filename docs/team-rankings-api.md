# Task 012 — reconstructed NFL season rankings

Approved branch: `feature/team-rankings`. Owner reports Task 011 merged and validated in WSL (374 passed, two warnings), with 705 accepted pairs / 1,410 team rows in development PostgreSQL. These are owner-reported baseline results. This task adds read-only rankings using the existing Task 011 column grants; no permissions, schema, ingestion, schedule data or frontend changes.

## Endpoint

`GET /api/team-rankings`

| Parameter | Contract |
|---|---|
| `season` | Required integer, 2024–2026; seasons are never implicitly combined |
| `season_type` | `REG` default, `POST`, or explicit `COMBINED` (REG + POST within the same season) |
| `category` | Optional `passing_offense`, `rushing_offense`, `passing_defense`, `rushing_defense`; omitted returns all four |
| `team_id` | Optional canonical UUID; applied **after league ranks are calculated** |

Example requests:

```text
GET /api/team-rankings?season=2024
GET /api/team-rankings?season=2025&season_type=POST&category=passing_defense
GET /api/team-rankings?season=2026&season_type=COMBINED
GET /api/team-rankings?season=2024&category=rushing_offense&team_id={canonical_team_uuid}
```

Response: `{data, meta}`. Each data item represents one independent category, with `category`, `direction`, `eligible_team_count` and ordered `teams`. A team row includes its canonical identity, category-specific rank/average/total/count and stored-schedule coverage. No overall rank is calculated.

Illustrative **synthetic response excerpt**, with policy strings/other metadata omitted for readability; this is not an actual development result:

```json
{
  "data": [{
    "category": "passing_offense",
    "direction": "descending",
    "eligible_team_count": 2,
    "teams": [{
      "team": {"id": "00000000-0000-0000-0000-000000000001", "code": "AAA", "name": "Synthetic A"},
      "rank": 1,
      "eligible": true,
      "average": 185.0,
      "total_yards": 370,
      "games_with_values": 2,
      "games_with_accepted_statistics": 2,
      "scheduled_games": 3,
      "missing_statistics_games": 1,
      "missing_metric_games": 0
    }]
  }],
  "meta": {
    "filters": {"season": 2026, "season_type": "REG", "category": "passing_offense", "team_id": "00000000-0000-0000-0000-000000000001"},
    "league_team_count": 2,
    "scheduled_games": 3,
    "accepted_games": 2,
    "missing_statistics_games": 1,
    "coverage_complete_for_stored_schedule": false
  }
}
```

OpenAPI supplies the complete response schemas and policy descriptions. Repeated/unknown parameters, invalid UUIDs, unsupported seasons/categories/stages and unapproved cutoff/week filters return the existing 422 error envelope. A team UUID absent from the requested season population returns `TEAM_NOT_FOUND` (404), even if present in some other season. Valid empty population queries return 200 with four empty category arrays (or one when filtered). POST/PUT/PATCH/DELETE return 405. Database failures return sanitized 503 without query details, credentials or evidence. Existing endpoint response contracts stay unchanged.

## Statistical and ranking definitions

- Passing offense uses stored **NET** passing yards, never gross: `net_pass_negative_sacks_v1`, gross plus the original nonpositive signed sack adjustment.
- Rushing offense uses stored rushing yards, preserving zero and negative values.
- Passing/rushing defense derive the opponent's NET passing/rushing from the reciprocal row of the **same accepted pair**. No independently mutable allowed-yard storage.
- Offensive categories sort descending; defensive categories ascending. Competition ranks are `1, 2, 2, 4`. Equal values sort by team code, then UUID as a deterministic final fallback. The stable sort does not break rank ties.
- The engine compares Python standard-library `Fraction(total_yards, games_with_values)` values. Totals/counts are aggregated in PostgreSQL. No rounding or float conversion occurs before sorting or tie detection. The public average is a JSON floating-point display value; rank remains based on the exact ratio.
- Each metric counts only non-null values; missing statistics and missing metric values are never zero. `missing_metric_games` is accepted-statistics games minus that metric's value count.
- A team with zero contributing values has `eligible: false`, null rank/average/total and count zero, placed after ranked teams in code order. It is not assigned a last-place rank. Different metrics can have different populations/denominators.
- All category ranks and `eligible_team_count` use the full league before optional team filtering. Category filtering selects independent metrics; it does not change any category's population.

## Population and coverage

The league universe consists of canonical teams appearing on either side of an nflverse schedule game in the requested season, **across either REG or POST**. This preserves all 32 teams when the stored season schedule supports them, including zero-stat teams and regular-season teams that did not qualify for postseason. Unknown/unmapped teams are not invented. Canonical IDs/code/name come from existing team records; aliases are not substituted for UUIDs.

Selected-stage scheduled games and accepted statistics are left-joined to this universe. The accepted join and reciprocal opponent query are reused from Task 011, with the same definition/provider checks. Historical unaccepted revisions never enter aggregates. A known schedule game without accepted stats increases missing coverage, not the performance denominator. A bye is not a schedule game and does not increase any denominator. REG and POST remain separate unless COMBINED is explicitly requested.

Metadata includes league team count, selected-stage scheduled/accepted/missing games, accepted games with UNKNOWN stored status, per-category missing metric team-games, and unverified-origin team-games. League metadata remains unfiltered by optional team/category selectors so the comparison population stays clear. Whole-game counts divide the two reciprocal team observations by two; this relies on the existing accepted-pair integrity guards. Counts are not completion evidence. A positive stored schedule with no missing statistics/metrics has `coverage_complete_for_stored_schedule: true`; an empty stage/season does not claim completeness.

This completeness flag means coverage of the **stored schedule only**, not full upstream coverage, authoritative finality, source authentication or freshness. For an incomplete 2026 snapshot, available accepted samples are ranked and missing schedule coverage remains visible. Future scheduled games can legitimately contribute to missing coverage. Unequal sample sizes are disclosed; no minimum-game threshold beyond one non-null observation is silently imposed. The original source/checksum uncertainty and partial-season limitations remain.

These are **reconstructed season rankings using current accepted revisions**. They may include a selected matchup or games that occurred later than a historical matchup. They must not be displayed as historical pregame rankings. No kickoff cutoff is accepted because independently supported completion-before-cutoff eligibility is still unavailable. Imported stats, scores, timestamps and UNKNOWN statuses are never treated as proof of completion, and no status/score is changed.

## Query architecture and security

One SELECT statement loads the requested season's team universe, stored-schedule coverage and all accepted metric totals/counts. CTEs keep that result on one statement snapshot, including concurrent accepted-pointer transitions. Defensive joins require reciprocal opponents and the same pair/game. The small per-team result set is ranked in Python; there is no per-team query/N+1 retrieval or raw game-history transfer. `category` does not change SQL reads; all four inexpensive metric aggregates supply completeness metadata.

The repository uses only the existing `nfl_api` permissions. It never reads approval tokens, batch evidence, raw source JSON, private paths or selection history and issues no DML. No permissions/provisioning, migration, infrastructure, dependencies or API runtime credentials change. No administrator override is used for live requests. The database test with actual nfl_api credentials runs all three stage modes and verifies forbidden reads/writes/TRUNCATE/trigger alteration still fail. A separate populated synthetic fixture uses SET LOCAL ROLE nfl_api so it can see uncommitted fixture data; it supplements actual-login tests.

## Exact normal-WSL verification

From repository root, using the existing private `.env` and already configured roles. No grants, migrations against development, reimports or corrections are required.

```bash
# Available local unit, SQL compilation, validation and error-handler checks.
.venv/bin/python -m pytest backend/tests/test_team_rankings.py -m 'not api and not database' -q

# Isolated PostgreSQL plus HTTP/ranking/security/regression checks.
docker compose --profile test run --build --rm tests python -m pytest \
  tests/test_team_rankings.py tests/test_team_stats_api.py \
  tests/test_team_stats_security.py tests/test_schedule_api.py -q -ra

# Full isolated backend acceptance suite.
docker compose --profile test run --build --rm tests
docker compose --profile test stop db_test
```

The existing test fixture targets only `nfl_research_test`, never development. Its synthetic import/never-accepted revision fixtures are rolled back and do not operate on owner data. PostgreSQL tests must execute without skips in WSL. Any failure is a failure; do not alter roles/guards to obtain a passing result.

After tests pass, optional owner-run live **read-only** smoke checks use the base Compose API:

```bash
docker compose up -d --build api
curl --fail 'http://127.0.0.1:8000/api/team-rankings?season=2024'
curl --fail 'http://127.0.0.1:8000/api/team-rankings?season=2025&season_type=POST'
curl --fail 'http://127.0.0.1:8000/api/team-rankings?season=2026&category=passing_defense'
curl --fail 'http://127.0.0.1:8000/api/team-rankings?season=2024&season_type=COMBINED'
curl --fail 'http://127.0.0.1:8000/api/health'
curl --fail 'http://127.0.0.1:8000/api/ready'
```

Review all-32 population where supported, category directions, competition ties, category-specific sample sizes, partial coverage and unchanged existing endpoints. No specific real ranks are asserted without querying the database.

## Changed-file inventory

- New `backend/app/repositories/team_rankings.py`: single-statement league coverage and accepted aggregates.
- New `backend/app/services/team_rankings.py`: exact-ratio competition ranking and post-ranking filters.
- New `backend/app/schemas/team_rankings.py`: filter/data/meta contracts and explicit eligibility/coverage policies.
- New `backend/app/api/team_rankings.py`: read-only endpoint/OpenAPI/dependency wiring.
- `backend/app/main.py`: router registration.
- `backend/app/api/errors.py`: statistics-specific sanitized failure message for the new route; existing endpoint messages preserved.
- New `backend/tests/test_team_rankings.py`: unit, SQL, validation/error/HTTP, opponent/accepted/unaccepted/coverage and restricted-login tests.
- New `docs/team-rankings-api.md`: contract, methodology, examples, commands and evidence.
- `AGENTS.md`, `README.md`, `docs/architecture.md`, `docs/data-model.md`, `docs/decisions.md`, `docs/implementation-plan.md`: current scope, approved methodology and owner-reported baseline synchronization.

No schedule/statistics data, ingestion, migrations/schema, database role configuration, frontend or dependencies changed. Agent executed no development migrations/imports/corrections/rollbacks/grants/commits/merges/pushes/deployments.

## Validation and merge gate

Agent results are recorded below at completion. PostgreSQL and synchronous HTTP acceptance require WSL when sandbox socket/TestClient restrictions persist. The owner-reported 374-test Task 011 result predates this implementation and does not certify new rankings code.

Executed agent checks:

- Broad available backend suite: **287 passed, 79 skipped, 35 deselected**, one existing TestClient deprecation warning. Command: `.venv/bin/python -m pytest backend/tests -m 'not api' --ignore=backend/tests/test_health.py -q`. This preceded the final extra per-metric-denominator unit test and display-conversion cleanup.
- Final rankings subset after those changes: **28 passed, 3 skipped, 1 deselected**, same existing warning. Command: `.venv/bin/python -m pytest backend/tests/test_team_rankings.py -m 'not api' -q`. The three skips are PostgreSQL cases; the deselected case is synchronous HTTP success serialization.
- Existing async schedule validation/read-only/error regression subset: **23 passed, 10 deselected**. Additive readiness compatibility: **1 passed, 3 deselected**. Counts overlap and are not additive.
- The new synchronous HTTP serialization test **timed out after 20 seconds** in the known local TestClient portal; it did not pass and was not repeatedly retried. Other synchronous API/health transports were left for WSL.
- Docker server probe: **permission denied** on the socket. No PostgreSQL execution, actual restricted-role checks or live ranking endpoint results were claimed here.
- Python compilation and `git diff --check` passed. No dependency installation was necessary.

**Merge recommendation: NO-GO pending the owner-run full WSL suite and read-only live smoke checks.** Implementation is ready for review, but SQL/runtime and synchronous HTTP acceptance must pass with the real restricted role before merge. No permission/migration/import step is needed. Next proposed task for approval: review those results and accept the reconstructed ranking API; a rankings frontend is a separate later task, and historical pregame rankings remain blocked on independent completion eligibility.
