# Task 026 — Game Total historical research API

Backend-only implementation using existing accepted team/game statistics and schedule references. No frontend, database schema/migration/permission, ingestion, external source, dependency, Docker configuration or accepted NFL data changes. This owner-approved scope extends Task 025's first-slice proposal to L20, SEASON, H2H and historical **reference total** enrichment now; those portions must not be reimplemented as later roadmap tasks.

## Endpoint and inputs

`GET /api/teams/{team_id}/game-research`

| Input | Contract |
|---|---|
| `team_id` | Canonical team UUID |
| `season` | Required 2024, 2025 or 2026 |
| `season_type` | Required `REG` or `POST`; no combined-stage mode |
| `matchup_id` | Required canonical nflverse game UUID, involving this team in the requested season/stage |
| `window` | `L3`, `L5` (default), `L10`, `L20`, `SEASON`, `H2H` |
| `line` | Optional manual Decimal, 0 through 1,000,000, at most six nonzero fractional decimal places and 13 significant digits; non-finite values rejected |
| `side` | `OVER` (default) or `UNDER`; chooses the hit-rate numerator, not the underlying observations or raw counts |
| `market` / `period` | Only `GAME_TOTAL` / `FULL_GAME`, both defaults. Unsupported team/half markets reject rather than using full-game scores |

Uses the existing typed `{data, meta}` response and error envelope. Unknown team/game returns 404 `TEAM_NOT_FOUND` / `GAME_NOT_FOUND`; a matchup involving another team or season/stage returns 422 `VALIDATION_ERROR`. Invalid/unknown/duplicate parameters, unsupported filters, bad UUIDs and invalid lines return 422. Mutation methods return 405. SQLAlchemy failures return sanitized 503 with no raw data/query details. No provider/source ID aliases, arbitrary timestamp cutoff, season ranges or client-selected opponent are accepted.

## Selection rules

`history_selection()` is shared by the existing trends query and this endpoint. It selects only currently accepted pair pointers with reciprocal team/opponent rows in the same game/pair, existing provider/definition checks, and the requested season/stage. Never-accepted, superseded or incomplete reciprocal pairs do not contribute. No FINAL-only filter is added: accepted statistics are not independently verified game completion.

Known kickoff is required. Historical and upcoming matchups use the same strict bound: exclude the selected game and every game whose kickoff is equal to or after its kickoff. No wall-clock/score-based classification promotes FINAL. Unknown anchor kickoff yields `availability=UNAVAILABLE`, `unavailable_reason=matchup_kickoff_unknown`, no observations and null averages/rates, not unanchored latest data.

Observations are newest-first by kickoff, source game ID and canonical UUID, all descending. A future chart may reverse a copy to plot oldest-first; its log and summary must retain the identical IDs/sample. Select rows **before** checking score availability; missing-score rows are not replaced with older games.

- L3/L5/L10/L20 select at most N accepted dated rows. Actual selected count is separate from requested N; short samples are normal. L20 does not borrow a previous season to fill a regular season with fewer games.
- SEASON selects all eligible rows in the **explicitly requested season and stage**, before the anchor. For current-season research, request that NFL season explicitly; the API does not guess a season from the calendar year. `requested_game_count=null` because no N is requested.
- H2H selects all eligible rows in that same season/stage against the anchor's canonical opposing team. It is not cross-season history or H2H plus a hidden latest-N filter. `opponent_id` discloses the opponent and `requested_game_count=null`. No meetings returns `availability=EMPTY`, `unavailable_reason=no_h2h_games`; missing opponent identity returns UNAVAILABLE (real game constraints normally ensure identity).

All supported filters preserve season/stage separation. Current accepted corrections may alter reconstructed historical values; this is not an as-originally-published or verified completed-before-cutoff snapshot. `completion_before_cutoff_verified=false` remains explicit.

## Observations, exact outcomes and rates

Each observation includes the existing `TeamGameStats` fields: canonical/source game ID, season/stage/week/kickoff, team/opponent, HOME/AWAY, source-reported points for/allowed, UNKNOWN/FINAL and score-finality fields, accepted pair/generation/revision and statistics artifact/record provenance. Existing yardage fields remain available for contextual reuse. Added fields:

- `combined_points`: team reported points + opponent reported points only when both are known; otherwise null.
- `scores_available`: both scores usable; legitimate 0–0 gives total zero.
- `outcome`: OVER, UNDER, PUSH, or UNDETERMINED. With manual line T and total X, compare **Decimal(X) − T** using the existing exact comparison primitive: positive => OVER, negative => UNDER, equality => PUSH.
- `outcome_unavailable_reason`: `scores_unavailable`, or `threshold_required` when scores exist but no manual line was supplied.
- `reference_total`: independent original-source line, comparison, provenance and availability, described below.

The single summary returns requested window via the surrounding data context, selected `eligible_game_count`, `games_with_usable_scores`, missing-score count, and average combined points over the usable-score games. No scores means null mean; missing scores never become zero or Under.

With a custom line, `over_count + under_count + push_count = games_with_usable_scores`. Hit rate is a **fraction from 0 to 1**, not a percentage or prediction:

```text
hit_rate_numerator   = over_count for side=OVER, under_count for side=UNDER
hit_rate_denominator = games_with_usable_scores  (pushes included)
hit_rate             = numerator / denominator, or null if denominator=0
```

The denominator policy is returned as `usable_scores_including_pushes`. Thus one Over, one Under and one Push yields an Over rate of 1/3, not 1/2. An all-push nonempty sample has hit rate 0 and positive denominator. No alternative non-push percentage is silently substituted. Counts remain authoritative; float means/rates follow existing display-stat conventions while line comparisons remain exact.

Without a manual line: history/mean/reference fields still work, `line=null`, `threshold_origin=null`, custom outcome counts/numerator/denominator/rate are null and `outcomes_unavailable_reason=threshold_required`. With a line but no scored games, counts/numerator/denominator are zero, rate null and reason `no_usable_scores`. No line is fabricated from a source reference; `threshold_origin=MANUAL` only when a user line is supplied. Nothing is persisted.

## Historical reference totals and provenance

Each selected game's existing schedule raw record is joined in the **same SQL snapshot**, with its source artifact. The shared `source_record_error()` helper validates canonical source identity and stored record SHA-256, then the existing bounded Decimal parser reads `total_line`. Public responses do not expose raw records, private paths, batch evidence or tokens.

`reference_total.line` is a nullable Decimal serialized as a JSON string. Its own `outcome` compares the game's reported total to **that event's reference line**, entirely independently of the custom research threshold. Example: 44 points is UNDER a custom 44.5 but OVER a reference 40.5. Changing line/side changes neither original source reference nor persisted records. Missing scores can coexist with an available reference line and UNDETERMINED reference outcome.

Unavailable references carry reasons such as `source_record_unavailable`, `source_record_identity_or_hash_mismatch`, `total_line_unavailable` or `invalid_total_line`. Missing/malformed reference lines never remove a valid score observation or prevent manual research. Validated record provenance includes schedule artifact ID/hash, row hash, artifact retrieval/recording times, origin status, source URL, attribution and license; statistics provenance remains separate.

Every reference is `UNVERIFIED_SOURCE_REFERENCE`, provider nflverse, bookmaker null, quote timestamp null and freshness UNKNOWN. Artifact times do not establish quote time, opening/closing designation or historical pregame availability. `reference_lines_verified_pregame=false`. These are not live offers or certified wager settlement, even for a score row with final evidence.

## Availability and completeness

`data.availability` is UNAVAILABLE for unknown cutoff/opponent identity; EMPTY for no eligible history; PARTIAL for a short requested window, missing scores or missing optional references; otherwise AVAILABLE. Threshold availability is independent: a complete score history with no user line can be AVAILABLE while its custom outcomes require a threshold.

`meta` exposes accepted rows in the season/stage (and H2H opponent scope where applicable), total eligible rows before the N limit, unknown-kickoff exclusions, at/after-matchup exclusions, known-date stored schedule coverage and missing accepted rows, selected UNKNOWN/unverified-score counts, available/missing reference totals, `window_complete`, `scores_complete` and `references_complete`. SEASON/H2H window completeness means a nonempty full eligible scope was returned; it does not certify upstream/finality completeness. Missing accepted schedule rows may include future games; no completion is inferred. Unknown cutoff has zero cutoff-scope counts with explicit unavailability, not a claim that the season is empty.

## Example

```text
GET /api/teams/{team_uuid}/game-research?season=2026&season_type=REG&matchup_id={game_uuid}&window=L3&line=44.5&side=OVER
```

**Abridged synthetic response illustration**, not real NFL results. Identity/game-stat fields and full metadata are omitted; OpenAPI supplies the complete `GameResearchResponse` schema.

```json
{
  "data": {
    "market": "GAME_TOTAL",
    "period": "FULL_GAME",
    "window": "L3",
    "requested_game_count": 3,
    "line": "44.5",
    "threshold_origin": "MANUAL",
    "side": "OVER",
    "availability": "PARTIAL",
    "observations": [{
      "reported_points_scored": 20,
      "reported_points_allowed": 24,
      "combined_points": 44,
      "scores_available": true,
      "status": "UNKNOWN",
      "score_finality": "UNVERIFIED",
      "outcome": "UNDER",
      "outcome_unavailable_reason": null,
      "reference_total": {
        "line": "40.5", "outcome": "OVER",
        "classification": "UNVERIFIED_SOURCE_REFERENCE",
        "bookmaker": null, "quote_updated_at": null, "freshness": "UNKNOWN"
      }
    }],
    "summary": {
      "eligible_game_count": 1,
      "games_with_usable_scores": 1,
      "games_without_usable_scores": 0,
      "average_combined_points": 44.0,
      "over_count": 0, "under_count": 1, "push_count": 0,
      "hit_rate": 0.0,
      "hit_rate_numerator": 0,
      "hit_rate_denominator": 1,
      "hit_rate_denominator_policy": "usable_scores_including_pushes",
      "hit_rate_unit": "fraction",
      "outcomes_unavailable_reason": null
    }
  },
  "meta": {
    "selection_mode": "before_matchup",
    "window_complete": false,
    "scores_complete": true,
    "references_complete": true,
    "cross_season": false,
    "completion_before_cutoff_verified": false,
    "reference_lines_verified_pregame": false
  }
}
```

## Architecture and files

Two read statements per request: existing team identity lookup, then one CTE-based query for shared accepted selection, matchup/opponent, coverage and selected game/source-reference joins. There is no per-game HTTP/SQL fetch and no provider call. L windows cap rows; SEASON/H2H are limited to one stored NFL season/stage/team. Python aggregates that bounded observation list once; future chart/log consumers must use it without selecting another sample. Existing `/trends`, `/games`, `/stats`, ranking and market contracts remain unchanged.

New files: `backend/app/{repositories,schemas,services}/game_research.py`, `backend/tests/test_game_research.py`, this guide. Updated app files: `api/team_stats.py` (route/dependency), `repositories/team_stats.py` (shared selection), `services/team_stats.py` (shared context validation), `services/markets.py` (shared record check). Extended the existing synthetic SQLite fixture in `tests/test_team_trends.py` for source-reference columns and opponent identity; no application physical model or migration changed. Scope/status links are updated in AGENTS/README, architecture/decisions/team-statistics guide and the Task 025 roadmap.

References: [accepted trends contract](team-performance-trends.md), [existing market semantics](game-betting-markets.md), [Task 025 roadmap](research/task-025-game-research-roadmap.md), [component proposal](research/task-025-component-architecture.md), [data feasibility](research/task-025-data-feasibility.md), [Game Total behavioral reference](research/nfl/game-total.md). No target code, captured datasets or endpoints are used as implementation inputs.

## Validation

Focused command from `backend/`:

```bash
RUN_DATABASE_TESTS=0 timeout 45 ../.venv/bin/pytest -q \
  tests/test_game_research.py tests/test_team_trends.py tests/test_team_stats_api.py \
  tests/test_team_rankings.py tests/test_markets.py -m 'not api and not database'
```

Result: **202 passed, 14 deselected, 7.23s**, one existing Starlette/httpx deprecation warning. Tests execute actual CTE SQL on synthetic in-memory SQLite projections and compile PostgreSQL SQL, covering all windows/H2H/stages/seasons, exact Decimal thresholds, counts/mean/nulls/zero, references/hash/identity, chronology/context/unavailability, current accepted pointers/corrections, finality preservation, read-only statements/no row changes, bounded query count, typed route serialization, HTTP validation/error/method contracts and existing endpoint regressions.

The separate synchronous HTTP success test was attempted with `timeout 15` and timed out (exit 124), consistent with earlier TestClient limitations here; it did **not** pass. Direct route/model serialization and async HTTP validation/error checks passed. The success test remains marked `api` for normal WSL verification. PostgreSQL-specific execution tests were authored but not run: existing `pg_engine` provisions roles and invokes Alembic, excluded by this task's constraints. No Docker startup, real database connection/import/migration, dependency install or frontend test was needed. Live PostgreSQL execution and actual populated coverage remain WSL acceptance checks, not claimed results.

Final `git diff --check` and guide relative-link checks passed. Scope inspection
showed no changes under frontend, physical models, Alembic, ingestion or Compose.
Prior Task 025 documentation changes present at task start were preserved.

## WSL verification

Using existing dependencies:

```bash
cd /home/edander5/nfl-research-planning/backend
RUN_DATABASE_TESTS=0 ../.venv/bin/pytest -q \
  tests/test_game_research.py tests/test_team_trends.py tests/test_team_stats_api.py \
  tests/test_team_rankings.py tests/test_markets.py -m 'not database'
```

This includes synchronous success checks omitted from the passing local run. For the exact permitted local selection, use `-m 'not api and not database'`. Do not enable the migration/provisioning database fixture as a shortcut; separately approve a pre-provisioned isolated PostgreSQL runtime procedure if needed.

For the existing development database/API only, owner verification commands (not run by the agent):

```bash
cd /home/edander5/nfl-research-planning
docker compose up -d --build --no-deps api
curl --fail 'http://127.0.0.1:8000/api/seasons/2026/schedule?season_type=REG&week=11'
```

Choose actual team/matchup UUIDs from that schedule; keep season/stage consistent:

```bash
research_team_id='REPLACE_WITH_TEAM_UUID'
research_matchup_id='REPLACE_WITH_GAME_UUID'
research_url="http://127.0.0.1:8000/api/teams/${research_team_id}/game-research"
curl --fail "${research_url}?season=2026&season_type=REG&matchup_id=${research_matchup_id}&window=L5&line=44.5&side=OVER"
curl --fail "${research_url}?season=2026&season_type=REG&matchup_id=${research_matchup_id}&window=L20"
curl --fail "${research_url}?season=2026&season_type=REG&matchup_id=${research_matchup_id}&window=SEASON&line=44&side=UNDER"
curl --fail "${research_url}?season=2026&season_type=REG&matchup_id=${research_matchup_id}&window=H2H&line=44.5"
curl --fail 'http://127.0.0.1:8000/openapi.json'
```

The lines above are manually entered hypothetical test thresholds, not actual sportsbook lines. Repeat with real historical/early-season/POST games where available; no import or data creation is needed for a demo. Inspect source/finality labels, selected IDs/dates strictly before anchor, reference independence and actual sample counts. No commitment, deployment or production data modification is authorized by these commands.

## Recommended Task 027 scope for approval

Frontend-only additive Game Total research on Game Preview: typed request/identity validation, shared L3/L5/L10/L20/SEASON/H2H selector using this exact contract, manual line/side controls, `HitRateSummary`, chronological `HistoricalGameTrendsChart` and newest-first `HistoricalGameLog` over the **same** response observations. Default L5, manual line initially unset, unknown/short samples and push denominator explicit; preserve reference columns/finality and independent team errors/cancellation/theme/mobile/accessibility. No frontend calculations, new endpoint or duplicated history pipeline. Recharts installation is not approved by Task 026; request a narrow dependency approval with UI scope or use an agreed React/SVG fallback. Keep Team Total/Spread/first-half markets for their separately approved tasks.
