# Standings

**Observed.** Header and shared search → NFL Standings → 2026 Regular Season → view selector → standings tables. League is default and shows AFC and NFC separately. Division renders division tables under each conference. All Teams renders a single league-wide table. Playoff Picture and Playoff Bracket were visibly disabled. Each table renders ordinal, team, W, L, T, PCT and GB. The leading team's GB is a dash in the sampled conference table. Team names link to team Moneyline / Spread research.

League → Division and League → All Teams both succeeded, replacing table grouping on the same URL. See network associations and captures in the [ledger](evidence/README.md). [Default screenshot](screenshots/standings-desktop.png).

**Derived.** The Giants' 5–3–1 and .611 are consistent with a half-win per tie. Exact ordering of tied records, GB calculation across groups and official postseason tiebreak rules remain open.

**Implementation.** Essential components are the season title, segmented view control, semantic table and team detail links. Supply season, phase, team IDs, division/conference membership, record and standings order. Use source-provided order or declare the exact method. Preserve the selected grouping when a background refresh updates records. On narrow screens, keep team identity visible and allow table scrolling when needed. Acceptance: grouping changes without losing the season, aggregation covers every team once, and tied and missing records render distinctly. Season selection, column sorting, streaks, advanced stats, playable playoff views and failures were unverified. Treat them as optional application features.

Clicking Buffalo Bills in League view opened /nfl/moneyline/BUF and rendered the Buffalo Bills research header. Related NFL data requests followed navigation.
