# Product Requirements Document (PRD)

## Purpose and audience

A private, primarily single-user NFL betting research dashboard that brings together historical team tendencies, player game logs, opponent context, injuries, depth charts and—only where freely and lawfully available—sportsbook player props. It supports human research, **not** placing bets or promising profitable bets. Potential public release is a separate future project.

## MVP scope

### Schedule and matchup entry

- Home page: week-by-week schedules for **2024, 2025, 2026**, regular and postseason, upcoming and completed games.
- Season / week / stage selectors, kickoff time with explicit timezone, game status, completed scores, working deep links to basic matchup views.
- Approved Milestone 1 status limitation (Decision 53): use explicit UNKNOWN when finality is unsupported; never infer finality solely from kickoff or invent in-progress/postponed states. Keep source-reported scores separate and clearly labeled when finality is unverified.
- Completed matchups retain final results while ranking/trend views use a cutoff before that game's kickoff.

### Team research

- Four rankings, *not power rankings*: passing offense (pass yards/game descending), rushing offense (rush yards/game descending), passing defense (pass yards allowed/game ascending), rushing defense (rush yards allowed/game ascending).
- Team pages: season averages, game logs, side-by-side comparisons, rank reversals for finding weak defenses; clear sample counts and contextual filters.
- Ranking methodologies must be fully specified and regression-tested before launch, including team games played and overtime conventions where applicable.

### Player prop research

- Ten player statistic markets: passing yards, passing attempts, passing completions, passing TDs, rushing yards, rushing attempts, rushing TDs, receiving yards, receptions, receiving TDs.
- Player-first and market-first navigation converge on one player research dashboard.
- Game-by-game Recharts visuals, user-adjustable prop lines, hit rates for last 5, last 10 and season, opponents' defensive context, current/historical seasons.
- Eligibility: exclude DNP and bye weeks from attempts; include actual appearances with zero performance; classify integer-line pushes separately. Show numerator, denominator, and push count.
- Multiple-team seasons: default to all eligible appearances, with optional team filter.
- Regular and postseason separate by default, optional combined scope.

### Dynamic context

- Team-wide injury status and practice designations with source timestamps when accessible; complete offense, defense and special-teams depth charts to the extent the validated source supports them.
- Data gaps are visible. Historical injury snapshots are deferred unless verified preexisting archival data can support them without new platform complexity.
- Sportsbook prices: multiple books and markets **where covered under a genuinely free tier**. No promise of all 10 markets/books; manual prop-line entry is always usable.
- On-demand odds fetching, explicit stale warnings, permitted last-known-data reuse, no historical sportsbook odds required. Never imply stale numbers are live offers.

### Product qualities

- Responsive desktop/mobile UI; bookmarkable game, player and filter views.
- Empty/error/loading states by section; independently failing odds/injury endpoints cannot block core game logs.
- Historical statistical cutoff and source provenance visible or inspectable.
- Private Tailscale access, no personal-user login for MVP; no public access.

## Explicitly out of scope

- Bet placement, wager tracking, saved bets/watchlists, live in-game analysis, betting recommendations or predictive ML.
- Public signup, billing, multi-tenant access, subscriptions and automatic deployment.
- Guaranteed historical injury snapshots or historical sportsbook odds.
- Guaranteed current multiple-book NFL player props if free provider terms/capacity cannot support them.

## Success criteria

- Schedule works across all scoped seasons/stages and navigates to matchups.
- Metrics are reproducible from canonical game records and no future data leaks into pregame computations.
- Game-log sample selection, pushes, team moves and period filters conform to rules above.
- User can research a player using a manually entered line even if all external odds integrations fail.
- End-to-end ingestion is idempotent, validated, and explainable; failures preserve last-good data.
