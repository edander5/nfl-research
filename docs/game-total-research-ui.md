# Task 027 — Interactive Game Total research

Game Preview now includes Game Total Research after Team Performance Trends.
This is an independent frontend implementation of the behavioral references in
[Game Total](research/nfl/game-total.md) and
[reusable components](research/nfl/reusable-components.md), using only the
[Task 026 API](game-total-research-api.md). No captured research data is used.

## Controls and contract

Away-team history and L5 are the defaults. Select either matchup team, any of
L3/L5/L10/L20/SEASON/H2H, and Over or Under. A manual threshold starts unset;
enter a value and choose Apply line, or use the half-point steps. Clear line
restores unavailable custom outcomes/rates. Draft edits are explicitly separated
from the applied value. Inputs retain up to six decimal places within API bounds.
Controls reset when navigating to another matchup and are not URL-persisted.

The typed client passes season, season_type, matchup_id, window, side,
market=GAME_TOTAL, period=FULL_GAME and optional line. It validates response
context and documented policy markers before displaying data. TanStack Query
keys include every control; AbortSignal cancels superseded requests. A changed
selection never displays the prior selection's data. Same-control refresh errors
retain available cached results with an explicit warning and retry.

## Components and integrity

- `GameTotalResearch` owns selection, requests, independent errors and provenance.
- `RecentGamesSelector` and `BettingLineControl` encapsulate controls.
- `HitRateSummary` displays server averages, counts and fractional hit rate.
- `HistoricalGameTrendsChart` uses native responsive SVG and theme tokens, with
  keyboard-focusable bars, textual details and horizontal scrolling for long series.
- `HistoricalGameLog` displays the same observation IDs, scores, reference totals,
  custom outcomes and status/finality. It preserves existing game links.

The chart reverses API newest-first observations to oldest-first; the table keeps
newest-first order. Geometry and selected-side Hit/Miss labels are presentation
only. No combined scores, thresholds versus scores, rates or eligibility are
recalculated in the client. Hit-rate denominator includes usable scored games,
including pushes. Missing scores and missing reference lines remain unavailable;
zero is a valid value. Missing bars use dashed markers distinct from zero markers.

SEASON and H2H retain the selected season and REG/POST stage. Unknown matchup
chronology, unavailable opponent history, empty samples and partial coverage are
explicit. Accepted source-reported scores retain UNKNOWN/UNVERIFIED labels;
chronological reconstruction is not an independently verified pregame snapshot.
Reference totals are separate from manual lines and are not verified sportsbook
closing quotes. Historical hit rates are not predictions.

No frontend dependency was added. The native chart is sufficient for this bounded
bar-series scope. Team Total may reuse these patterns after its backend contract
is separately approved; market-specific labels will need parameterization then.

## Verification and limitations

Task 027 validation: all 196 frontend tests in 10 files passed, including 30 new
Game Total tests; TypeScript and production build passed. Coverage includes team
and six-window switching, manual line and steps, both sides, push/zero/missing
values, backend-authoritative summaries, chronology/context validation, synchronized
IDs, cancellation, independent errors/retry, existing preview and both themes.
Fixtures are synthetic. No live PostgreSQL requests, Docker rebuild or browser
visual acceptance was performed. Existing backend runtime limitations remain in
the API guide. Automated theme checks do not replace visual review on devices.

From the project root in WSL:

```bash
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
docker compose up -d --build --no-deps frontend
```

The Docker command is supplied for owner verification and was not executed.
Open an existing Game Preview; check both teams and all windows, apply a line,
switch Over/Under, and compare chart bars with table rows in both themes and on
mobile. Empty/partial results depend on the installed accepted data.

Next proposed task for approval: Task 028, read-only Team Total research API,
reusing accepted history and exact manual-threshold semantics for team points.
