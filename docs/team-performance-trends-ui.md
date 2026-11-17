# Task 024 — Game Preview Team Performance Trends

Owner-approved frontend-only integration of the [Task 023 API](team-performance-trends.md). No backend, statistics, database, ingestion, Docker, dependency or publication changes were made. Task 023 backend changes already present in the working tree were preserved.

## Interface and data integrity

The new section appears after current accepted season rankings and before Team Game Logs. One labeled native select controls both teams: L3 / Last 3 Games, L5 / Last 5 Games (default), L10 / Last 10 Games. The selection is local to this preview and resets to L5 on navigation to a different game. It does not modify URL return navigation or the separate rankings stage selector.

Six comparison rows pair each team's NET passing, rushing and source-reported points offense with the opponent's corresponding defense. Together they show all six API metrics for both teams, using backend averages directly and existing one-decimal formatting. No averages, rankings, differences, eligible-game selection or score grading are calculated in React. Neutral theme colors are intentional: these averages do not imply a league rank, prediction or betting recommendation.

Each team's status card shows `Last 5 Games (4 available)` or the actual selected window/sample. Every metric displays its own `games_with_values` against that team's eligible-game count, including a partial-metric label when smaller. Null averages display a dash with an accessible unavailable label; legitimate zero and negative values remain visible. Empty history is explicitly unavailable, never a zero-filled table. Partial-window/metric coverage and unknown-kickoff/missing-accepted-stat counts remain visible.

Both requests call the existing `GET /api/teams/{id}/trends`, always passing the game's own `season`, `season_type`, selected `window` and canonical `matchup_id`. This uses the backend's before-matchup behavior for historical **and** upcoming games without classifying finality in the frontend. Unknown matchup chronology is shown as unavailable; there is no fallback to unanchored latest data. The section explains that statistics are current accepted reconstructions, not independently verified pregame snapshots, and points are source-reported rather than independently verified final results. A secondary eligibility disclosure shows API cutoff/status information.

`research.trends()` adds typed response contracts and bounded runtime checks for requested identity, season/stage/window/matchup, anchored selection mode, cutoff/unavailable state and metric averages/counts. Mismatched, malformed and HTML responses become that team's error state. These checks validate the response for display; they do not reconstruct the backend's sample or statistical definitions.

## Fetching, errors and presentation

Each team has its own TanStack Query request/key, including team, season, stage, window and matchup ID. Requests forward cancellation signals, use the existing 60-second stale-time convention and disable automatic retries/window-focus refresh. Changing the shared window switches both query keys. No placeholder from the previous window is shown; late responses cannot replace the selected window. Returning to an already cached window can display its own cached data.

One team's loading/error/empty state never blocks the other's available cells. Retry targets only the affected team; failed refreshes retain explicitly labeled cached results for the same window. Existing markets, season rankings, scores, navigation and logs continue independently.

Existing comparison-table/loading/error/select styles are reused. Added status cards and numeric text use shared CSS variables in both themes. Status cards stack on mobile; comparison cells wrap within a focusable overflow region, with compact padding at <=760px. No rank color or dark-mode calculation changes were made.

## Files changed for Task 024

- `frontend/src/components/TeamPerformanceTrends.tsx`: shared selector, independent team states, six offense/defense comparison rows and coverage disclosure.
- `frontend/src/api/research.ts`: trend response types, existing-endpoint client and response-context checks.
- `frontend/src/pages/Matchup.tsx`: section insertion with game-specific React key.
- `frontend/src/styles.css`: scoped responsive layout and theme-token styling.
- `frontend/src/test/trends.test.tsx`: synthetic requests, states, comparisons, integrity, theme and preview integration tests.
- `frontend/src/test/fixtures.ts`, `matchup.test.tsx`, `markets.test.tsx`, `dashboard.test.tsx`: contract-shaped empty trend responses keep existing preview tests isolated from the new section.
- This guide, `AGENTS.md`, `README.md`, `docs/decisions.md`, `docs/team-performance-trends.md`: scope, behavior, validation and approval references.

The test fixtures are synthetic only and are not bundled as production fallback data. Existing uncommitted Task 023 files remain separate prior work; the backend diff hash was unchanged throughout Task 024.

## Validation results

- Focused trends/preview/markets/logs/theme Vitest run: **81 passed in five files**.
- Full existing frontend suite plus new trends tests: **166 passed in nine files** (3.58s), no failures.
- `npm --prefix frontend run typecheck`: passed.
- `npm --prefix frontend run build`: TypeScript and Vite production build passed (105 modules, no build warning).
- `git diff --check`: passed.

Coverage includes default and all window choices; both team IDs and full query parameters; all six metrics per team; per-metric/partial/empty samples; missing/zero/negative values; independent loading/failure/retry; same-window stale retention; cancellation/late-response safety; historical/upcoming/POST contexts; unknown chronology; malformed response rejection; theme switching and a focusable comparison region; existing preview sections/navigation and independent ranking filters.

No live PostgreSQL/API requests, imports or backend tests were needed for this frontend task. Automated theme checks are DOM/token behavior, not proof of rendered contrast, native-select appearance or mobile layout in a real browser. Live-data browser acceptance remains an owner check; the API's documented completion/publication-time limitations still apply. No new data source, dependency, commit, merge, push or deployment was performed.

## Verify in WSL

From the existing repository with frontend dependencies already installed:

```bash
cd /home/edander5/nfl-research-planning
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

For the existing development Compose environment, rebuild only the frontend (commands for the owner; not run by the agent). The existing API must already expose Task 023:

```bash
docker compose up -d --build --no-deps frontend
```

Open `http://127.0.0.1:5173`, choose a real schedule game and check:

1. The section appears between rankings and logs; L5 is selected and both teams have their own sample/state. Switch L3 and L10 without a full-page reload.
2. Inspect network requests: both team endpoints include the selected window, matchup season/stage and `matchup_id`; rankings `comparison_stage` changes do not change trend stage. Existing schedule return link works.
3. Compare displayed API averages/counts with the response. Inspect any actual missing/zero/negative/small-sample cases without creating records to demonstrate them. An early-season game may honestly have no prior eligible history.
4. Open historical and upcoming games, and postseason where available. Unknown kickoff must show chronology unavailable, with no unanchored fallback.
5. Toggle Light and Dark. At desktop, 390px and 320px, inspect selector/cards, wrapped cells, keyboard focus, loading/errors, partial labels and expanded coverage. Scroll/focus the comparison region if needed; unrelated sections should retain their layout.
6. Use browser request blocking for one team’s **trends** request, then retry it. The other team and rankings/markets/logs must remain available. Change windows rapidly and confirm old data cannot overwrite the current selection.

## Next task for approval

After reviewing this UI, the next [expansion roadmap](research/task-022-roadmap.md) implementation task is **Task 025 — bounded hypothetical game-line calculation API**: user-entered spread/total scenarios over accepted history using existing exact Decimal and provisional-score semantics. That backend task is not authorized by Task 024. Player foundation and new providers remain later phases.

References: [existing Game Preview](game-preview.md), [team logs](game-preview-team-logs.md), [theme behavior](dark-mode.md), [API eligibility contract](team-performance-trends.md) and [expansion roadmap](research/task-022-roadmap.md). No new external research was required.
