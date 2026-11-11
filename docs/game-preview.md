# Task 016 — NFL Game Preview / Matchup Dashboard

## Implemented scope and eligibility decision

The existing React route `/games/:gameId` is now titled **Game preview**. Existing weekly schedule cards already link to it with a validated `returnTo` schedule path; no second game route or backend endpoint is introduced. The header retains canonical away/home names and codes, the matchup season/week or postseason round, Eastern kickoff, nullable reported scores, stored status/finality labels and source provenance. The comparison appears immediately below the matchup header/score card.

**Historical pregame rankings are unavailable.** Inspection of the schedule contract, Task 011/012 contracts and actual query/model implementation confirmed:

- Schedule kickoff is a scheduled timestamp, not completion evidence. UNKNOWN and reported scores do not prove completion.
- Accepted statistics and revision/import timestamps do not prove that another game completed before this game's kickoff.
- `team_stats_accepted` selects current revisions, not a publication-time statistical snapshot.
- `GET /api/team-rankings` has no approved cutoff parameter. Its SQL filters season/stage only, and may include this matchup and later games.

Accordingly the page uses the owner-authorized fallback: **Current accepted season comparison** within the matchup's NFL season. A prominent warning above the data states that this is not a pregame snapshot or prediction and may include the matchup and later games. No cutoff, exclusion guarantee, completion state or historical accuracy is invented. Even a selected game with recorded FINAL evidence cannot establish completion-before-cutoff for all contributing games. No new historical pregame calculation is implemented.

Sources for this decision: `docs/data-model.md`, `docs/schedule-data-contract.md`, `docs/team-stats-api.md`, `docs/team-rankings-api.md`; `backend/app/models/team_stats.py`, `backend/app/repositories/team_stats.py`, `backend/app/repositories/team_rankings.py`, `backend/app/schemas/team_rankings.py`. These are inspected repository contracts/code, not independent live-data verification. No new external source was used.

## API reuse and UI behavior

1. Existing `GET /api/games/{canonical_uuid}` supplies game identity/header. Invalid or missing games retain existing not-found handling and never launch a comparison.
2. One `GET /api/team-rankings?season={game.season}&season_type={stage}` retrieves all four categories for the league. No category/team filter is sent. The component selects away/home rows by canonical UUID after the backend has ranked the whole league.
3. The existing API supplies NET passing offense, rushing offense, opponent NET passing defense and opponent rushing defense, authoritative ranks/ties, averages, metric game counts and coverage. No client-side ranking, opponent derivation or per-team database/API loop is added.
4. Offense labels say highest average ranks #1; defense labels say lowest average allowed ranks #1. No overall rank is shown. Averages display one decimal; rank numbers remain exactly those returned by the API. Each metric uses its own non-null game count.
5. The season is fixed to the matchup season. The default stage is its REG/POST stage. Optional `comparison_stage=REG|POST|COMBINED` is explicit URL state; COMBINED never happens implicitly. Repeated/unsupported comparison-stage values show a reset state without a rankings request. Existing return navigation is preserved when changing stage.
6. Team headings link to existing lightweight team research routes with season and selected stage preserved. A comparison failure does not hide the schedule header, reported scores or provenance.
7. TanStack Query keys include season, stage and an `all` category marker. Comparisons use a 60-second stale time, no automatic retry and no focus-triggered refresh. A user can retry or explicitly refresh. There is no polling loop. A failed refresh retains cached comparison rows with a warning; stage changes do not show the previous stage's rows as the new selection.
8. Missing teams/categories produce unavailable/unranked cells. Zero-game teams stay visible and unranked. Empty populations show a specific empty state. Zero/negative values remain values; nulls never become zero. Partial coverage, contributing-game counts and missing-stat/metric counts remain visible. Coverage refers to the stored schedule and can include future games; it is not finality, source freshness or upstream completeness.
9. The semantic three-column table wraps names/metrics and narrows spacing at mobile widths, with an accessible focusable region. Shared attribution/NET/source limitations appear below it. Existing schedule source/provenance details remain available.

No new API, backend calculation, migration, grant, dependency, source, ingestion, statistics edit, scheduler behavior, odds, player feature or prediction is included. Existing `nfl_api` permissions and accepted-pair reciprocal joins are unchanged.

## Validation evidence

Agent execution used existing dependencies; no packages were installed. Synthetic fixtures are test-only and never application fallback data.

- `npm --prefix frontend test -- --reporter=dot`: **99 passed across five files**, including **15 new matchup tests**, schedule/current-week/freshness/rankings regressions.
- `npm --prefix frontend run build`: **passed**, including `tsc --noEmit` and Vite production build (99 modules). Generated `dist/` is ignored.
- `.venv/bin/python -m pytest backend/tests/test_team_rankings.py backend/tests/test_team_stats_api.py backend/tests/test_schedule_service.py -m 'not database and not api' -q`: **84 passed, 7 deselected**, one existing Starlette TestClient deprecation warning. This includes service/schema/query compilation and available async validation/error contracts, not PostgreSQL integration.
- `git diff --check`: passed during implementation; final check recorded in the delivery report.
- No lint command is configured in `frontend/package.json`; no lint pass is claimed.
- `docker version --format '{{.Server.Version}}'`: socket permission denied. No container build, PostgreSQL test, real API/browser request, import or migration was performed. No sandbox workaround was attempted.

New tests cover one all-category request, canonical identity/orientation, API rank preservation and offense/defense directions; game season/default postseason/explicit combined stage and URL return state; invalid/repeated stage reset; rounded display, ties, zero/negative/null and Week 1 unranked samples; absent teams/categories/populations; independent loading/error/retry and stale cached data; schedule-to-game/back navigation; honest historical fallback labels even for a selected FINAL game. The pregame-exclusion requirement is conditional on supported eligibility: no supported eligibility exists, so the tests verify the unavailable/fallback policy instead of asserting fabricated pregame exclusion.

The prior owner-reported **424 passed, two warnings** backend suite predates this frontend slice and remains user-reported. The previously investigated slow rankings SQL is reused, not optimized here. This task adds one league query per comparison cache miss instead of four category queries or two per-team ranking queries; actual development query latency is still unbenchmarked.

## Exact normal-WSL verification

From repository root with the existing private `.env`. No administrator override, grants, migration, import or scheduler profile is needed. The sandbox checkout was on `main`; creating `feature/game-preview` was denied because `.git` is read-only. Before staging/committing later, the owner can move the uncommitted work onto the desired branch. No commits were created.

```bash
# Inspect branch/worktree first. Choose the owner-approved feature branch before future commits.
git branch --show-current
git status --short

# Host checks when the existing Node/dependency setup is available.
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build

# Equivalent frontend checks in the existing Docker image.
docker compose build frontend
docker compose run --rm --no-deps frontend npm test
docker compose run --rm --no-deps frontend npm run build

# Full isolated backend regressions, if desired for final acceptance.
# This uses nfl_research_test and synthetic transactional fixtures, never development imports.
docker compose --profile test run --build --rm tests \
  python -m pytest -q -ra --durations=10
docker compose --profile test stop db_test

# Existing development services only; this does not enable the scheduler.
docker compose up -d --build --wait db api frontend
curl --fail-with-body -sS http://127.0.0.1:8000/api/health
curl --fail-with-body -sS http://127.0.0.1:8000/api/ready
curl --fail-with-body -sS 'http://127.0.0.1:8000/api/team-rankings?season=2026&season_type=REG'
```

In a browser at `http://127.0.0.1:5173`, select a week and click a real game. Confirm the Game preview heading, correct away/home sides, reported-score/UNKNOWN labels, four comparison rows, authoritative rank/averages and the pregame-unavailable warning. Inspect the network panel: one league-wide rankings request should retrieve all categories. Check a 2024 game, a postseason matchup and an early-season selection. Explicitly switch comparison stage and reload the URL; verify back-to-schedule returns to the original week. Follow a team research link and verify season/stage. At 375px and desktop widths, verify readable wrapping, keyboard focus and no page-wide horizontal overflow. Test unavailable service/retry in a local browser without disrupting PostgreSQL. Record actual latency for the rankings request; retain the earlier query-performance issue if it recurs rather than changing rank definitions or security.

## Complete changed-file inventory

| File | Change |
| --- | --- |
| `frontend/src/components/MatchupComparison.tsx` (new) | Comparison query, stage URL state, four-category table, independent states and disclosure |
| `frontend/src/api/research.ts` | Typed all-category rankings request using existing endpoint |
| `frontend/src/pages/Matchup.tsx` | Game preview title and comparison integration |
| `frontend/src/styles.css` | Scoped comparison styles and mobile wrapping |
| `frontend/src/test/matchup.test.tsx` (new) | Fifteen synthetic matchup tests |
| `frontend/src/test/dashboard.test.tsx` | Updated title assertions and explicit empty rankings response in schedule regression mocks |
| `frontend/src/test/fixtures.ts` | Contract-shaped synthetic empty rankings response |
| `docs/game-preview.md` (new) | Eligibility findings, behavior, evidence, exact WSL acceptance and inventory |
| `AGENTS.md` | Current approved Task 016 scope |
| `README.md` | Visible feature entry and fallback limitation |
| `docs/architecture.md` | Existing two-endpoint composition and query isolation |
| `docs/decisions.md` | Decision 69: approved honest season-comparison fallback |
| `docs/implementation-plan.md` | Task 016 vertical slice and review gate |
| `docs/development.md` | Acceptance guide link |

## Remaining review gate

GO for owner review of this frontend implementation, subject to WSL/live-browser acceptance. Historical pregame rankings remain unavailable. No runtime source freshness is inferred from browser fetching. Unresolved source authentication/checksum and query-performance limitations remain inherited contracts. Next proposed task is focused live Game Preview acceptance (responsive layout, real identity/API comparison and measured rankings-request latency), not additional data ingestion or historical pregame eligibility implementation. Stop for review before further work, commits, merges, pushes or deployment.
