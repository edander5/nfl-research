# Reusable components

| Component | Standings | Schedule | Lineups | ML / Spread | Game Total | Team Total | Player Props |
|---|---|---|---|---|---|---|---|
| Shared menu, global search | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Week / event context | — | Week buttons | Upcoming slate | Matchup strip | Matchup strip | Matchup strip | Week & matchups |
| Main discovery surface | Grouped table | Matchup cards | Roster cards | Team market | Team market | Team market | Sortable prop list |
| Threshold control | — | Market links | — | Spread stepper / slider | Total stepper | Total stepper | Detail, gated trial |
| Windowed history | — | Expanded recent games | — | Team margin/results | Combined points | Team points | Player stat |
| Historical odds/line in log | — | — | — | ML / ATSh | HIST LINE / 1H LINE | HIST LINE | Detail |
| Matchup context | — | Expanded comparison | Injuries/weather | Offense/defense | Rankings and insights | Rankings and insights | DvP and detail |
| Data coverage signals | Disabled views | Status / partial | Updated, projected | Gated panels | Dashes / gated | Dashes / gated | Dashes / gated |

A dash marks a feature outside the observed main workflow.

## Matchup and market state

Pair away and home team buttons under the week label with a strong selected-team indicator. Input is a slate keyed by event ID and selected team. Output is a new event/team selection; Game Total confirmed URL navigation with explicit week, phase and game ID. Keep subsequent opponents in a separate control. Team and player links are reusable across discovery cards. Team-picker menus and cross-page persistence are open.

Market selection sets stat, period, side and odds context. Render clear selected-state buttons. Game Total explicitly switches Full Game / 1st Half, and Moneyline / Spread has a pressed market group. A line stepper needs a nullable initial line, step, allowed range and onChange. Spread additionally displayed a slider. Book chips require book ID, line, side, offer price and availability. Alternate odds and historical odds have distinct scopes.

## Historical chart, window, summary and game log

Use one window selector and derive one eligible sample. Input is event-indexed observations, ordered time, phase, metric, selected threshold and optional historical market snapshots. Output is the filtered log, plot values, outcome counts and average. Chart direction can be oldest-first while log direction is newest-first. Provide a horizontal threshold marker, signed margin axis for spread, textual outcomes and accessible outcome labels. Keep each historical line tied to its event. Display unavailable values explicitly. Recent windows, H2H and season filters appear on the totals pages; L20 was absent from the sampled Moneyline / Spread controls. The props detail window was access-restricted in the prior trial. See the [ledger](evidence/README.md) for window and stepper outcomes.

## Matchup comparisons and availability

An offense/defense switch changes the comparison subject, and a season switch changes the comparison dataset. Display rows with metric, value, unit, rank, rank direction and sample coverage. Schedule expansion labels #1 best and #32 worst for its specific comparison. Schematic lane/field legends on the team market pages separately define ranges by production allowed and distinguish frequency fill from favorable/unfavorable underlines. Treat those as panel-specific semantics. Use named availability states for missing ranks, projected starters, suspended views, partial seasons, gated cards and unavailable offers. Returning paid content is a server-side product authorization decision.

## Discovery and detail disclosure

Standings uses segmented grouping, Schedule reveals event comparisons, Lineups discloses ordered depth, and Props uses a searchable list with sort, filters and pagination. Reuse accessible search, clear controls, disclosure and empty-state primitives with page-specific state. Inputs include stable entity IDs and independent display labels. On expansion preserve existing list context; expose expanded state to assistive technology and handle asynchronous data per item.
