# Game Total

## Observed layout

Week matchup strip → team/matchup header → Full Game / 1st Half, Save and Track → line stepper, MOVE, Over/Under, book filter and offer chips → upcoming matchups → Filters with premium opponent section → chart and Game Log → pass/run distribution, usage and schematic field views → injury/QB context, Matchup Rankings, Splits and Matchup Insights. Advanced cards expose subscription prompts. Refer to [desktop](screenshots/game-total-desktop.png) and the [evidence ledger](evidence/README.md).

Full Game baseline was HOU vs IND at 44.5. The chart uses date and opponent on the x-axis, combined points on the y-axis, a research threshold at 44.5 and per-game values. Controls show L5, L10, L20, H2H, 2025, 2026 and Team Cont. %. In the baseline, chart dates run oldest to newest while the matching log runs newest to oldest. The log columns are WK, DATE, OPPONENT, SCORE, TOTAL, HIST LINE, O/U. A prior-season playoff game is included in the ten sampled rows. The display showed Over 60% (6–4), Avg Total 49.6.

**Derived from rendered rows.** HOU–CLE 24–27 yields 51, above 44.5. HOU–NE 16–28 yields 44, below 44.5 even though its HIST LINE was 40.5. The ten totals sum to 496 and six exceed 44.5. This identifies the threshold behind the summary and demonstrates why the historical line needs a separate column. The visual comparison below verifies the sampled O/U cell basis. Historical line source and timing remain open.

## Workflow

- Full Game → 1st Half kept the route and team, changed the title and score sample to the half-market view, showed Avg 1H Total 26.2, and replaced HIST LINE with 1H LINE.
- Over → Under changed the odds and the schematic matchup labels. The historical chart summary continued to display Over in this trial.
- See the [ledger](evidence/README.md) for the window/stepper and matchup trials, associated requests and screenshot references.

## Implementation

Essential components are event/team navigation, period and side selectors, threshold stepper, shared window and summary, historical bar chart, and matching game log. Data includes per-period scores with availability flags, stable event IDs, team/opponent, date/week/phase, current offer snapshots, historical snapshots with provenance, and independently sourced matchup metrics. Bind chart and log to the same eligible IDs. Keep period changes scoped to the market and prevent unavailable first-half scores from entering averages. On mobile, preserve the line and count controls above a legible chart and provide horizontal access to log columns. Acceptance: recompute hit counts on line changes, preserve historical snapshot values, use consistent sample counts in chart and log, and give pushes and missing values distinct labels. Team-contribution overlay, rich tooltips, chooseable ranking panels and line movement are optional. Cross-market push rules, hover content, historical line provenance and premium filter semantics remain open.

## Verified threshold, window and historical outcomes

The [chart and game log image](screenshots/game-total-chart-log.png) shows green bars above the dashed 44.5 research line and red below it for the sampled Over view. The y-axis in that view starts at 20. The Jan 18 row provides a direct historical comparison: its 44-point bar is red against 44.5, while its log total is green with a check against HIST LINE 40.5. Confirm source and market conventions before generalizing the historical label.

On the same L10 sample, stepping down from 44.5 to 44.0 yielded 67% (6–3–1), then 43.5 yielded 70% (7–3); 49.6 remained the mean. The observed display is consistent with excluding the push from the percentage denominator (6/9). L5 at 44.5 selects the five newest games, with totals 51, 66, 48, 65 and 29 in newest-first order, producing 80% (4–1) and 51.8. Checking Team Cont. % exposed a chart overlay and an average label of 49.9%. Its precise aggregation remains open. [L5](screenshots/game-total-l5.png), [43.5](screenshots/game-total-line-43-5.png), [Team contribution](screenshots/game-total-team-contribution.png), [mobile](screenshots/game-total-mobile.png).

The public Matchup Rankings card shows past/current season toggles and HOU OFF vs IND DEF / HOU DEF vs IND OFF. It places the metric labels between two team ranks. Rows cover points/game, rushing/passing yards, red-zone rate, yards/play, third-down rate, possession time, sacks and turnovers. The card labels #1 as best for each team and colors ranks from the selected-team perspective. Its published rank computation, minimum sample and refresh rules remain open. [Matchup Rankings](screenshots/game-total-matchup-rankings.png).

Switching the rankings card to HOU DEF vs IND OFF updated the paired ranks without changing the route. Points/game moved from HOU #9 and IND #29 to HOU #18 and IND #23. The market, threshold and history are separate from this comparison control.
