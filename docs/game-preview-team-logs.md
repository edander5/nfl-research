# Task 019 — Game Preview Team Game Logs UI

## Scope and baseline clarification

Inspection found that this checkout had game logs on the standalone team-research route, but no logs section on `/games/:gameId`, no Task 018 implementation and no bundled logo assets. The owner confirmed using **existing APIs and badge fallbacks where data is available**. This task therefore adds the requested section without replacing or redesigning the existing matchup header, ranking comparison, betting markets, filters, source details or navigation. It does not claim to have restyled a previously existing Game Preview logs component.

The two cards display the away and home team names, an explicitly labeled generic abbreviation badge (not an invented NFL logo), matchup season and REG/POST stage. Existing team-research components and styles are unchanged. No external assets/source, new dependency, backend code, API contract, database model/permission, accepted statistics, ingestion or scheduler change is included.

## Presentation and data reuse

- Two separate cards in a scoped responsive grid. When approximately 1,040px of **content** width is available, both cards fit side by side; smaller widths stack. The mobile rule explicitly stacks at viewport widths of 760px or less. Each table scrolls within its own card, with min-width zero on grid/card containers to avoid page overflow.
- Seven compact headers: WK, OPP, SCORE, SPREAD, TOTAL, PASS, RUSH. Numeric columns use tabular numerals and right alignment; week is centered and opponent left-aligned. Hover/focus-within states are subtle, and the currently viewed game has a quiet row marker.
- WK is the actual source NFL week; OPP is `@ CODE` for away and `vs CODE` for home. SCORE is team points then opponent points. PASS is accepted NET passing, never gross; RUSH preserves zero and negative values. Nulls display a dash, not zero.
- Existing `/api/teams/{id}/games` requests use matchup season/stage. API pages are oldest-first, so the frontend loads every available page before sorting the small season log newest-first. Known UTC kickoff dates sort descending; unknown/invalid kickoff dates follow, then week descending and source/canonical IDs break ties deterministically. Missing kickoff dates are not invented. This is display ordering, not completion or pregame eligibility.
- Five games per team card are visible at a time, with independent older/newer controls and the complete accepted-game count. A season log is not a historical pregame snapshot and may contain the selected matchup/later accepted games. Rankings' separate `comparison_stage` control is unchanged; the logs retain the matchup's own stage, explicitly labeled in each card.
- Existing `/api/games/{id}/markets` supplies team-oriented signed spreads and all results. The frontend does not invert the source spread, add scores to lines, sum scores or calculate covers. It selects the backend's HOME/AWAY spread row. TOTAL displays the backend winning Over/Under side, or Push/undetermined. Win/cover indicators are subtle green, losses red, pushes/undetermined neutral; symbols and accessible labels supplement color. All results remain explicitly **provisional** and source references remain unverified.
- Before using market results, the response game UUID, team/opponent UUIDs and score pair must agree with the displayed statistics row. Disagreement/multiple references withholds the market cells rather than choosing a bookmaker or showing a comparison against different scores. Market values can be absent while statistics remain visible.
- Market queries run only for visible rows (at most ten across both cards), using the existing `['game-markets', id]` cache key and 60-second stale time. Shared game IDs deduplicate with each other and the existing markets panel. Paging may acquire additional local API references; there are no external provider calls, polling or new endpoints. Normal NFL REG/POST logs fit within one 20-record statistics API page per team, with existing pagination supported if more are returned.
- Each card has independent loading, empty/error/retry states. Market failures preserve stats and show a small row-specific retry action. A failed cached market refresh can retain the previous internally consistent result, still labeled provisional. No failure hides other Game Preview sections.
- Each row navigates to its canonical game preview on click. Native links in WK/OPP provide keyboard and modified-click support. The selected game links to its existing URL so filters are not discarded on a self-link. Navigating to a different matchup defaults to that game's existing context. Table regions are keyboard-focusable and source details retain statistics attribution/origin/license links. The legend discloses unknown bookmaker/quote time and links conceptually to each game's existing detailed market provenance through row navigation.
- UNKNOWN/UNVERIFIED scores remain so; recorded FINAL/confirmed-final indicators are shown only when supplied by the existing team-statistics API. A reference result never changes game status or certifies a settled wager.

Sources inspected: `frontend/src/pages/Matchup.tsx`, `TeamResearch.tsx`, `components/BettingMarkets.tsx`, `api/research.ts`, `api/markets.ts`, `styles.css`, existing frontend tests and `backend/app/api/team_stats.py`/`schemas/team_stats.py`. No new outside source was used.

## Validation

Synthetic frontend tests cover both card headers/badges/seven columns, newest ordering, team/opponent score orientation, home/away display, NET/zero/negative/null metrics, backend-result preservation with a deliberately contradictory synthetic result, outcome styles and provisional labels, row/native-link navigation, pagination, multi-page API loading, isolated team and market failures/retry, empty data and withholding mismatched market identities/scores. Sorting is tested without mutating source arrays. Table scroll-region accessibility is covered; jsdom does not verify actual desktop/mobile geometry.

The initial full run found test-only issues: existing header queries also matched the new card headings, an asynchronous empty-state assertion ran before both cards completed, and a synthetic response shared an object with its input. Selectors, wait behavior and fixture mutation were corrected. No API/settlement assertion was weakened.

Final executed checks:

- `npm --prefix frontend test -- --reporter=dot`: **119 passed across seven files**, including **12 new log tests** and existing schedule/Game Preview/markets/rankings regressions.
- `npm --prefix frontend run build`: **passed**, including TypeScript (`tsc --noEmit`) and Vite production bundle (103 modules). Generated `dist/` is ignored.
- `git diff --check`: **passed**.

 Backend tests are not rerun for this frontend-only change; their previous results are not re-certified here. No container/runtime/API or real browser acceptance is claimed. No lint script exists, and no dependencies were installed.

## Exact normal-WSL checks

From repository root using the already configured development environment:

```bash
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build

# Equivalent checks using the existing frontend Docker image.
docker compose build frontend
docker compose run --rm --no-deps frontend npm test
docker compose run --rm --no-deps frontend npm run build

# Existing services only; no migrations, imports, grants or scheduler enablement.
docker compose up -d --build --wait db api frontend
curl --fail-with-body -sS http://127.0.0.1:8000/api/health
curl --fail-with-body -sS http://127.0.0.1:8000/api/ready
```

Open `http://127.0.0.1:5173`, select a season/week and click a game. In Team Game Logs verify:

1. Correct away/home team cards and the matchup's season/stage labels; generic code badges are the approved logo fallback.
2. Seven aligned columns, newest dated games first, NET passing and team-first reported scores; a dash for missing fields and visible UNKNOWN/unverified labels.
3. Spread signs/results match each row's existing `/markets` response, including a cover/loss/push example when available. Totals display the backend's Over/Under/Push result. Unknown outcomes stay unknown.
4. At 1600px viewport the cards normally fit side by side; at 768px and 375px they stack. Drag-scroll each narrow table without page-wide overflow. Check keyboard focus on scroll regions, game links and paging buttons.
5. Click a row's score/PASS cell, or activate its WK/OPP link with the keyboard, and confirm the correct UUID route opens. Use browser Back to return. Page older/newer records independently.
6. Expand Sources & coverage; verify attribution, declared origin and source/license links. Existing header, ranking and full markets sections must still render.
7. Use browser request blocking to test one log/market request failing; the other card and existing page remain available. Restore the request and retry. No database interruption is needed.

Network note: two season-log requests plus market reads for visible rows is expected; no odds-provider or logo-host requests should occur. Additional source/API data remains governed by existing contracts. Actual live performance and responsive screenshots remain owner acceptance work, not inferred from synthetic tests.

## Complete changed-file inventory

- New `frontend/src/components/PreviewTeamLogs.tsx`: compact independent cards, data reuse, pagination, reference display and navigation.
- New `frontend/src/gameLogs/presentation.ts`: pure newest-ordering and identity/score consistency selection (no settlement logic).
- `frontend/src/pages/Matchup.tsx`: additive logs section only.
- `frontend/src/styles.css`: scoped card/table/result/scrolling/responsive styles.
- New `frontend/src/test/previewLogs.test.tsx`: dedicated synthetic presentation/integration tests.
- `frontend/src/test/fixtures.ts`, `dashboard.test.tsx`, `matchup.test.tsx`, `markets.test.tsx`: explicit empty-log responses for existing tests and precise header selectors.
- `AGENTS.md`: current scope and approved baseline/logo clarification.
- `docs/development.md`: acceptance link.
- New `docs/game-preview-team-logs.md`: behavior, source/finality guarantees, tests, inventory and WSL/browser checks.

No backend/API, ingestion, scheduler, database, ranking or settlement-calculation changes. No commits, merges, pushes or deployment. Next proposed task is owner live-browser acceptance of this layout and existing API data at desktop/mobile sizes; no new feature work is implied.
