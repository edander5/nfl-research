# Schedule and Game Preview UI adjustments

Owner-approved scope: frontend presentation only. No API, database, ingestion,
ranking or betting calculations, dependencies, game-log behavior or deployment
changes. The owner’s request supersedes the earlier Task 021 frontend exclusion
for this narrow task. Existing working-tree CLI work is preserved.

## Behavior

- Schedule refresh history follows the weekly schedule, game listings and policy
  notice. Its query, reload button, timestamps and error handling are unchanged.
- Four comparison rows show away passing offense/home passing defense, away
  rushing offense/home rushing defense, home passing offense/away passing defense,
  and home rushing offense/away rushing defense. Each metric retains its API rank,
  average, contributing games and partial-coverage indicators. Offense #1 means
  highest average; defense #1 means lowest average allowed. Green applies to ranks
  1–5, neutral gray to 6–27 and red to 28–32. Missing ranks are unranked without a
  strength/weakness color. Current accepted-season and historical-pregame warnings
  remain unchanged; this display does not create a pregame snapshot.
- Market references sit inside the game summary directly below scores. Two team
  rows show spread, moneyline and game total (Over/Under), including source prices.
  Over and Under apply to the combined score; their row placement does not assign
  the total to a team. Missing sides, prices and lines remain unavailable. The
  layout uses fixed compact columns with wrapping and a keyboard-focusable scroll
  region. Full hypothetical grading, score context, source timestamps, attribution,
  source/license links, hashes and calculation policy remain accessible through
  “Hypothetical grading & source details”. No grade is recomputed in React.
- nflverse references remain explicitly unverified, with unknown bookmaker and
  quote freshness. They are never labeled live odds or settled results. Independent
  loading, cached-data failure and retry handling are retained.
- Team Game Logs implementation and its styles are unchanged.

## Files and rationale

Presentation: `frontend/src/pages/Schedule.tsx`, `frontend/src/pages/Matchup.tsx`,
`frontend/src/components/MatchupComparison.tsx`,
`frontend/src/components/BettingMarkets.tsx`, `frontend/src/styles.css`.
Tests: `frontend/src/test/dashboard.test.tsx`, `frontend/src/test/matchup.test.tsx`,
`frontend/src/test/markets.test.tsx`. The schedule test now waits for its asynchronous
week request rather than assuming rendering the heading means it has started.
Documentation: this guide, `AGENTS.md`, `docs/decisions.md`, `docs/game-preview.md`,
`docs/game-betting-markets.md`.

Local contract references: [Game Preview](game-preview.md),
[market reference definitions and provenance](game-betting-markets.md),
[rank definitions](team-rankings-api.md), [schedule history](schedule-freshness.md).
No external source claims, new source access or source-license changes are involved.

## Validation

- `npm --prefix frontend test`: **129 passed across seven files**, using synthetic
  fixtures. Tests cover row ordering, exact category/team/rank/average/sample
  mappings, rank boundaries 1/5/6/27/28/32 and missing ranks, history placement,
  market placement, exact and missing market values, grading disclosures,
  disclaimers, errors/retries and existing game-log pagination/navigation.
- `npm --prefix frontend run build`: TypeScript and Vite production build passed.
- `npm --prefix frontend run test:client`: **failed** with `ERR_MODULE_NOT_FOUND`
  for the existing extensionless `./freshness` import from `src/api/client.ts`
  under Node v26.13.0. Neither client module nor smoke script was changed.
- `git diff --check`: passed.

No browser automation/browser executable is available in this environment.
Desktop/mobile visual layout, real API responses and local service integration
remain owner-run checks; jsdom tests do not establish actual visual usability.
No real data was imported or modified. No commit, merge, push or deployment occurred.

## Local verification in WSL

With existing frontend dependencies and the existing development API running:

```bash
cd /home/edander5/nfl-research-planning
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run dev
```

Visit `http://127.0.0.1:5173`. If the frontend already occupies that port, use the
existing local workflow rather than starting a competing server. The dev server
proxies `/api` to `http://127.0.0.1:8000` by default.

Check desktop and mobile widths (for example 1280, 390 and 320 pixels):

1. Open a schedule week. Confirm history follows games; reload history independently.
2. Open a game and inspect all four opposing-category rows against API values.
   Check missing/zero-game teams show no fabricated rank or average.
3. Confirm markets follow scores inside the summary. Inspect available, partially
   missing and wholly unavailable references; verify prices and signs against the
   API response. Confirm Over/Under refer to the game, not team totals.
4. Expand grading/source details using keyboard and pointer. Confirm provisional
   results, unknown finality/freshness, attribution, policy and source links remain.
5. Check wrapping, readable cells, focus and horizontal scrolling where needed.
   Verify Team Game Logs pagination and matchup navigation remain unchanged.

Next proposed task, for owner approval: local browser acceptance against existing
real API data. A fix to the standalone client smoke tooling is separately scoped.
