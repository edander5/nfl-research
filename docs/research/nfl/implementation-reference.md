# Independent implementation reference

The individual [page briefs](README.md) define scope, requirements and acceptance criteria. These shared contracts are proposed for the React, TypeScript, FastAPI and PostgreSQL application.

## Types and identity

- Event holds canonical event ID, phase, season/week, team IDs, scheduled kickoff, status, scores by period and updated timestamp.
- Observation identifies event, subject (game, team or player), metric, unit, availability and value. Matchup context includes venue and opponent. A stat of zero and a missing stat are distinct.
- Market snapshot identifies event, market, period, book, side, line, price, observed timestamp and provenance. Keep a separately labeled research threshold in UI state. Display a closing designation only when your source supports it.
- Rank observation includes population, period, source, direction, metric and sample count. For fantasy ranks include scoring rules. For schematic data show the actual denominator.
- Lineup slot includes player, position group, role/order, availability, projected/confirmed status and freshness.

## State and API boundaries

Use URL-backed identity for event, team/player and market context. A shareable line and window can also be URL parameters if desired. Keep temporary disclosure state local. Serialize optional preferences separately from bookmarked research state. Transition event selection → resolve selection → show loading/partial → show ready or recoverable error. Cancel stale requests, and reject late responses tied to a previous selection. Cache immutable history separately from prices and injury updates. Use pagination for discovery and load optional matchup panels on demand.

Compute team margin as selected-team score minus opponent score, full game total as a sum, team total as selected team points, and first-half totals from available first-half scores. For totals, compare eligible values with the selected threshold; assign equality to push. Decide and document denominator treatment explicitly, alongside sample and push counts. H2H uses a declared opponent and phase rule; recent windows have explicit cross-season and postseason eligibility. Apply the same eligible IDs to summary, chart and game log. Keep historical results against event-specific historical lines independent of hypothetical results.

## Cross-page acceptance

- Navigation reaches all seven proposed research areas, with meaningful Back behavior.
- Shared controls are keyboard operable, named and announce selected state. Tabular data remains available at mobile widths and charts have accessible equivalents.
- A market line change updates hypothetical records and threshold visuals while history keeps its event line values.
- Tests exercise ties and pushes, all missing / partly missing inputs, season boundaries, absent historical prices, short windows, and stale fetch responses.
- Independently implemented visual design, licensed data and original application endpoints support the observed functional patterns.
