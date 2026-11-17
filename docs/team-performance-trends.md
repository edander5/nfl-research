# Task 023 — NFL team performance trends API

Task 024 now adds the separately approved [Game Preview trends UI](team-performance-trends-ui.md).
The backend contract and historical Task 023 validation below are unchanged.

Owner-approved backend-only implementation, 2026-11-17. Extends the existing team-statistics router/repository/service/schema layers. No frontend, schema, migration, permissions, ingestion, external source, dependency, accepted NFL data, Compose or deployment changes.

Task 023 explicitly extends the Task 022 proposal: six metrics (including reported points) and optional matchup-bound chronology are now included. This does **not** establish independently verified completion before kickoff or publication-time historical snapshots. Existing rankings, logs, source-reference market calculations and update safeguards retain their contracts.

## Endpoint

`GET /api/teams/{team_id}/trends`

| Input | Contract |
|---|---|
| `team_id` | Canonical team UUID |
| `season` | Required integer, 2024–2026 |
| `season_type` | Required `REG` or `POST`; no implicit combined stage |
| `window` | `L3`, `L5` (default) or `L10` |
| `matchup_id` | Optional canonical game UUID involving this team and matching requested season/stage |

Returns the existing typed `{data, meta}` envelope. Team not found => 404 `TEAM_NOT_FOUND`; missing/non-nflverse matchup => 404 `GAME_NOT_FOUND`; team/season/stage mismatch => 422 `VALIDATION_ERROR`. Invalid/unknown/duplicate query parameters and malformed UUIDs => 422; mutation methods => 405; SQLAlchemy database errors => sanitized 503. No arbitrary cutoff timestamp, pagination or provider-ID aliases are accepted.

Without matchup context, select latest accepted **dated** games in that season/stage. With context, select only games with known kickoff **strictly earlier** than the matchup kickoff, excluding the selected game explicitly. This same rule handles upcoming and historical matchups without deciding game completion from the clock or scores. Upcoming games normally have all existing accepted history before them. Historical contexts exclude the selected game, equal-time games and later games. Unknown matchup kickoff returns 200 with empty sample/null averages and `unavailable_reason: matchup_kickoff_unknown`; it never falls back to an unfiltered latest sample.

## Calculation and eligibility

1. Reuse `accepted_query()` and existing `net_pass_negative_sacks_v1`. A row contributes only through the current accepted pair pointer, source/provider/definition constraints and a reciprocal opponent row from the **same pair and game**. Never-accepted, superseded or incomplete reciprocal pairs cannot enter the sample.
2. Require known kickoff so chronology is supportable. Sort kickoff descending, then source game ID and canonical UUID descending for deterministic ties. Take at most N rows **before** averaging; return the selected games newest first, their source hashes/IDs, accepted pair and generation. No cross-season carryover, REG/POST merge or additional FINAL restriction is introduced.
3. Offensive metrics: `net_passing_yards`, `rushing_yards`, `reported_points_scored`. Defensive metrics: reciprocal `net_passing_yards_allowed`, `rushing_yards_allowed`, and `reported_points_allowed`. Each uses existing `{total, average, games_with_values}`; AVG/SUM/count ignore nulls per metric. Zero and negative yardage remain values. Missing metrics do not cause older games to be backfilled. An empty metric has null total/average and count zero.
4. Points come from existing source-reported schedule score projections, oriented to actual HOME/AWAY. They do not become certified final scores. Each returned game retains status/score-finality labels; selected UNKNOWN/unverified-score counts are separate. A verified FINAL row still does not prove its completion time was before a historical anchor.
5. The whole trend statement sees a single database snapshot for matchup context, accepted rows, selected sample, all six aggregates and coverage. A separate team identity lookup makes **two bounded SQL statements per request**, independent of N/metric count. At most ten game rows are returned; no per-statistic/per-game requests, new raw-column reads, cache service or new index.

### Response completeness

| Field | Meaning |
|---|---|
| `data.requested_game_count` / `eligible_game_count` | Requested N versus selected accepted dated rows, at most N; fewer games are a valid sample |
| `meta.available_eligible_games` | All accepted dated games satisfying requested season/stage/cutoff, before window limit |
| `accepted_games_in_season_stage` | All rows supported by accepted reciprocal projection in that season/stage, before date/cutoff exclusions |
| `excluded_unknown_kickoff_games` | Accepted rows that cannot be ordered by known kickoff |
| `excluded_at_or_after_matchup_games` | Accepted dated games at/after known anchor; includes anchor if accepted; zero without known anchor |
| `scheduled_games_in_scope` | Known-date stored schedule involving team in season/stage, and strictly before anchor when supplied |
| `scheduled_games_without_accepted_statistics` | That schedule count minus eligible accepted count; can include future schedule slots in unanchored mode, not a claim that all are missing completed games |
| `selected_unknown_status_games` / `selected_unverified_score_games` | Sample rows retaining UNKNOWN / lacking confirmed-final score evidence |
| `missing_metric_games` | Selected count minus non-null metric count, separately for each metric |
| `window_complete` | Exactly N selected games; does not certify schedule/source/finality completeness |
| `selected_metrics_complete` | Nonempty selected sample with all six metrics present; independent of requested window size |
| `cutoff_utc`, `selection_mode`, `unavailable_reason` | Transparent context and absence reason; no inferred cutoff from week arithmetic |
| `completion_before_cutoff_verified` | Always false: this API is a current-revision chronological reconstruction |

For an unknown anchor kickoff, no dated cutoff scope can be formed: eligible/scheduled scope counts are zero with the explicit unavailable reason; season/stage accepted and unknown-date counts remain visible. No source freshness or originally-published guarantee is implied by row revision times.

## Example

```text
GET /api/teams/{team_uuid}/trends?season=2026&season_type=REG&window=L3&matchup_id={game_uuid}
```

**Abridged synthetic response illustration**, not live NFL data. `games`, additional coverage counts and policy strings are omitted here; OpenAPI contains the full `TeamTrendsResponse` contract.

```json
{
  "data": {
    "team": {"id": "00000000-0000-0000-0000-000000000001", "code": "AAA", "name": "Synthetic A"},
    "season": 2026,
    "season_type": "REG",
    "window": "L3",
    "requested_game_count": 3,
    "eligible_game_count": 2,
    "offense": {
      "net_passing_yards": {"total": 300, "average": 150.0, "games_with_values": 2},
      "rushing_yards": {"total": 30, "average": 15.0, "games_with_values": 2},
      "reported_points_scored": {"total": 0, "average": 0.0, "games_with_values": 1}
    },
    "defense": {
      "net_passing_yards_allowed": {"total": 300, "average": 150.0, "games_with_values": 2},
      "rushing_yards_allowed": {"total": 30, "average": 15.0, "games_with_values": 2},
      "reported_points_allowed": {"total": 7, "average": 7.0, "games_with_values": 1}
    }
  },
  "meta": {
    "selection_mode": "before_matchup",
    "window_complete": false,
    "selected_metrics_complete": false,
    "completion_before_cutoff_verified": false
  }
}
```

## Verification

Tests use labeled synthetic data only. `test_team_trends.py` executes the real CTE/aggregate query against an in-memory SQLite projection of the existing columns (not production DDL), covering windows, six averages, home/away scores, ordering/ties, small/empty samples, zero/negative/null values, all supported seasons and stages, accepted/superseded/corrected/rolled-back pointers, reciprocal-pair isolation, missing dates, historical/upcoming/unknown anchors, context rejection, two-query bound, allowed projections, typed route serialization, invalid filters and HTTP error/read-only behavior. A separately marked PostgreSQL test checks actual nfl_api execution under existing column grants.

Final focused run from `backend/`:

```bash
RUN_DATABASE_TESTS=0 timeout 45 ../.venv/bin/pytest -q \
  tests/test_team_trends.py tests/test_team_stats_api.py \
  tests/test_team_rankings.py tests/test_markets.py -m 'not api and not database'
```

**141 passed, 12 deselected, 3.49s**, with one existing Starlette/httpx deprecation warning. No failures in this run. `git diff --check` passed. This includes real synthetic SQL execution, PostgreSQL query compilation, direct typed-route serialization, async HTTP validation/error handling and regressions for existing summaries/rankings/markets.

A first new-suite run including synchronous success transport stalled and was terminated by the 45-second timeout (exit 124); it is not a passing test run. The existing synchronous success-test convention is retained under `api` and is available for normal WSL acceptance. No database tests were executed: the existing `pg_engine` fixture provisions roles and invokes Alembic, which are outside this task's no-migration/no-permission-change constraints. SQLite execution and PostgreSQL SQL compilation do not establish live PostgreSQL permissions/runtime behavior. No installations, real imports, PostgreSQL connections or container startup occurred.

Changed files: `backend/app/repositories/team_stats.py` (bounded query/shared aggregate expressions), `services/team_stats.py` (typed trends/shared serialization), `schemas/team_stats.py` (filters/response/policy), `api/team_stats.py` (route), `api/errors.py` and `app/main.py` (sanitized matchup mismatch), `backend/tests/test_team_trends.py` (synthetic regression coverage). Documentation: this guide, `AGENTS.md`, `README.md`, `docs/architecture.md`, `docs/decisions.md`, `docs/implementation-plan.md`, `docs/team-stats-api.md` (current scope, contract and approval boundaries). No frontend or other application files changed.

## Verify in normal WSL

Using existing dependencies (no install) from the repository:

```bash
cd /home/edander5/nfl-research-planning/backend
RUN_DATABASE_TESTS=0 ../.venv/bin/pytest -q \
  tests/test_team_trends.py tests/test_team_stats_api.py \
  tests/test_team_rankings.py tests/test_markets.py -m 'not database'
```

This includes the synchronous API success tests omitted locally. To reproduce the agent's permitted focused checks, use `-m 'not api and not database'`. Do not enable `RUN_DATABASE_TESTS=1` under this task; its fixture runs migrations/provisioning. Any future isolated PostgreSQL acceptance must be separately approved or adapted to a pre-provisioned test database without those actions.

Against an existing development database/API with migrations/grants already in place, rebuild only the development API when ready for owner review (not run by the agent):

```bash
cd /home/edander5/nfl-research-planning
docker compose up -d --build api
curl --fail 'http://127.0.0.1:8000/api/seasons/2026/schedule?season_type=REG&week=1'
```

Copy canonical team and game UUIDs from that response; use a game involving the team in the chosen season/stage:

```bash
trend_team_id='REPLACE_WITH_TEAM_UUID'
trend_matchup_id='REPLACE_WITH_GAME_UUID'
curl --fail "http://127.0.0.1:8000/api/teams/${trend_team_id}/trends?season=2026&season_type=REG&window=L5"
curl --fail "http://127.0.0.1:8000/api/teams/${trend_team_id}/trends?season=2026&season_type=REG&window=L3&matchup_id=${trend_matchup_id}"
curl --fail 'http://127.0.0.1:8000/openapi.json'
```

Check L3/L5/L10; REG and POST separately; an early historical matchup (empty/small sample), a later historical matchup (all selected kickoffs strictly earlier), an upcoming matchup, missing stats and unknown kickoff where actual records exist. Never insert records or run imports to fill a demo. Unknown/incomplete source data must remain visible. Current accepted corrections can change reconstructed historical averages, with selected pair/generation provenance.

## Next task for approval

Task 024: frontend-only Team Performance Trends on Game Preview, using this typed endpoint for both teams, explicit L3/L5/L10 controls, sample/metric counts, reported-score and chronological-reconstruction labels, independent request/error states and existing dark-mode tokens. Preserve season ranking calculations and existing preview/logs/markets. Pass `matchup_id` for matchup context; never silently request latest unanchored data when historical cutoff is unavailable. No Recharts or other dependency is needed for an initial comparison table.

Source references: existing [team-stat API](team-stats-api.md), [ranking definitions](team-rankings-api.md), [Game Preview eligibility limitation](game-preview.md), [Task 022 audit](research/task-022-expansion-audit.md) and [roadmap](research/task-022-roadmap.md). No external source claim or provider change was needed.
