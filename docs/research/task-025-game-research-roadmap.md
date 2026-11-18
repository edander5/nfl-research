# Task 025 — updated game-level development roadmap

Implementation update: owner subsequently approved Task 026 with a broader scope
than the original first-slice proposal. The [implemented API](../game-total-research-api.md)
now includes L3/L5/L10/L20/SEASON/H2H, exact manual totals and per-game unverified
reference total enrichment. Source is implemented and focused checks pass; runtime
limitations remain documented. **Task 027 UI is implemented and frontend checks pass:** see the
[dashboard guide](../game-total-research-ui.md). **Task 028 Team Total backend is
next for approval.** Native SVG required no chart dependency. The original
Task 026 proposal below is historical; its actual contract is the linked guide.
Task 034 need not reimplement Game Total reference enrichment (other markets remain
future work), and Task 035 need not reimplement these same-season filters. Their
additional scopes or cross-season changes still require separate approval.

2026-11-17. **Planning only; approve one implementation task at a time.** This is the current planning entry point for game research. Read the [seven-tab feature gaps](task-025-frontend-gap-analysis.md), [component proposal](task-025-component-architecture.md) and [data/dependency matrix](task-025-data-feasibility.md) with it.

## Status and task-number reconciliation

Task 023 implemented the six-metric L3/L5/L10 team trends API; Task 024 implemented its Game Preview UI. Source confirms both, including optional backend matchup chronology and mandatory frontend matchup context. The frontend selector is local, not URL-persisted; it is independent of ranking-stage filters. Task 027 now supplies Game Total history, manual thresholds and backend-authoritative hit rates; Team Total and Moneyline/Spread dashboards remain proposed. These facts supersede the original Task 022 plan's proposed four-metric/no-matchup API and proposed Season/L3/L5/L10 UI.

The owner has now assigned **Task 025 to this documentation task**, superseding the earlier unapproved Task 025 calculation-API proposal. The new **proposed Tasks 026–037** below replace the old unapproved numbering for game work. Old Task 022 player/research/discovery tasks are retained as later-phase descriptions, not competing active task numbers; renumber those only when they are approved. No future task is approved by its presence in either roadmap.

## Order and dependencies

| Order | Proposed tasks | Outcome / reuse |
|---|---|---|
| 1 | 026 backend → 027 frontend | Game Total history, manual threshold, chart, rate summary and matching log; shared component foundation |
| 2 | 028 backend → 029 frontend | Team Total from selected-team points, reusing the same history/threshold/chart/log contracts |
| 3 | 030 backend → 031 frontend | Moneyline descriptive results and signed-spread/margin research, reusing exact outcomes/components |
| 4 | 032 backend → 033 frontend | Expand supported matchup ranks (points first), reuse authoritative league ranks and shared comparison panel |
| 5 | 034, then 035 backend → 036 frontend | Bounded source-reference history enrichment; explicitly supported L20/H2H/season modes after sample rules are approved |
| 6 | 037 frontend | Add schedule/team/market deep links and reusable context selectors after destinations work |
| Later | Player foundation → manual-line player research → discovery/props → injury/depth/weather/advanced odds | Retain Task 022 data/eligibility/rights gates; do not move player props ahead of game research |

The first four outcomes follow the owner's priority. Later reference enrichment is optional for manually entered lines: absent reference data must never block a valid score series. First-half, advanced proprietary/unsupported ranks and verified closing prices are excluded, rather than hidden prerequisites. No new source, schema, ingestion workflow, service or dependency is needed for Task 026. Recharts approval belongs to Task 027, not backend work.

## Proposed Task 026 — full-game Game Total research API (single recommended next task)

- **Objective/scope:** one read-only backend market-research projection for `GAME_TOTAL`, including selected game observations, combined reported points, known-value mean and exact manual-threshold outcomes. No frontend, schema, permissions, sources, imports, scheduler, odds-provider or dependency changes.
- **Likely files:** `backend/app/repositories/team_stats.py` (reuse/factor selection helper without changing existing routes), `services/team_stats.py` or a focused game-research service, `schemas/team_stats.py` or focused schemas, `api/team_stats.py`; new `backend/tests/test_game_research.py`, API guide/decisions.
- **Reuse/data:** Task 023 `accepted_query`/trend selection, canonical team/game/season/stage and reported score projections, accepted pair/generation/source provenance; existing Decimal comparison primitive from `services/markets.py`. Do not call `/trends` internally over HTTP or implement another importer.
- **Proposed contract for approval:** adjacent `GET /api/teams/{team_id}/game-research` with required season, REG/POST, matchup UUID; `window=L3|L5|L10` (L5 default), `market=GAME_TOTAL`, optional bounded manual Decimal line and explicit Over/Under side. Exact naming is reviewable, not an existing endpoint. Existing `/trends` and `/markets` remain backward compatible.
- **Acceptance:** same accepted reciprocal dated rows and strict before-matchup bound as Task 023; unknown anchor => unavailable, never latest fallback; at most N rows selected before missing-score checks. Combined points require both scores; missing scores remain unknown rows. Return selected/known/unknown counts, mean, per-game outcomes and explicit raw over/under/push counts and denominator policy. Proposed hits/known-values rate includes pushes; optional non-push rate is separately named/null on all-push. Approve this policy before coding. No line => `threshold_required`, no fabricated default/outcomes. Chart/log/summary get the same canonical IDs and sample generation metadata. All score comparisons labeled provisional/current-revision, not final settlement or pregame publication snapshots.
- **Tests:** synthetic exact full-game totals, zero scores, integer push/half-line, Over/Under symmetry/count conservation, all-push/all-null/empty/fewer-than-N, missing scores not backfilled, chronological ties, REG/POST/season separation, historical/upcoming/unknown matchup cutoff, bad team/game context, accepted/superseded/reciprocal-pair revisions, 404/422/405/503, bounded query count and existing endpoint regressions. PostgreSQL tests only against separately approved/pre-provisioned isolated runtime; existing fixtures run migrations/provisioning and must not be casually enabled.
- **Dependencies/risks:** owner approval of sample/rate/route contract; actual existing DB coverage/runtime unverified by Task 025. Need backend calculation despite raw inputs already being returned; no client recomputation shortcut. Keep known kickoff versus verified completion distinction explicit.
- **Behavior reference:** [Game Total](nfl/game-total.md), [threshold outcomes](nfl/evidence/threshold-step-outcomes.txt), [independent contracts](nfl/implementation-reference.md). Implement independently, not from target payloads.

## Proposed Task 027 — Game Total chart and shared research UI

- **Objective/scope:** additive Game Total research section on Game Preview using Task 026; establish `HistoricalGameTrendsChart`, `RecentGamesSelector`, `BettingLineControl`, `HitRateSummary` and `HistoricalGameLog` with one consumer first. No redesign of existing preview sections.
- **Likely files:** new `frontend/src/components/gameResearch/` components, typed `api/research.ts` extension or adjacent client, `pages/Matchup.tsx`, scoped `styles.css`, new research tests. Manifest/lock/notices only with explicit Recharts installation approval.
- **Reuse/data:** Task 024 Query/context-validation/cancellation patterns, existing semantic tables/shared states/theme/Card and safe game links; Task 026 response. User enters the total; optional reference seed is not required for initial slice.
- **Acceptance (updated to the actual Task 026 contract):** L3/L5/L10/L20/SEASON/H2H, default L5, shared committed manual threshold/side controls, chronological chart/newest-first log with identical sample, visible known/unknown/push counts/denominator. One team can fail while the other loads. No stale line/outcome mixing, frontend hit-rate math, source-reference replacement or invented sportsbook chips. Native keyboard/table alternative, light/dark, 320/390px and desktop legibility; preserve scores/rankings/trends/logs/return links. No line => history/mean and an entry prompt.
- **Tests:** request/context keys, threshold/side/window changes, partial/zero/null/push displays, cancellation/late responses, independent failure and same-context stale data, chart/table correspondence and stable IDs, original preview regressions; TypeScript/build and actual browser resize/tooltip/focus checks. Use independent synthetic fixtures.
- **Dependencies/risks:** 026 accepted; approve stable Recharts/peer/license/bundle check **or** explicitly choose limited React/SVG fallback. No new table/state library. Renderer changes cannot dictate statistics or eligibility.
- **Behavior reference:** [chart/log image](nfl/screenshots/game-total-chart-log.png), [Game Total](nfl/game-total.md), [mobile constraints](nfl/navigation.md), [component catalog](nfl/reusable-components.md).

## Proposed Task 028 — Team Total research backend adapter

- **Objective/scope:** add `TEAM_TOTAL` to the shared research contract using selected-team reported points, with no new pipeline/physical schema. Keep Game Total adapter stable.
- **Likely files:** new/shared game-research service/schema, existing team API allowlist, backend research tests/docs.
- **Reuse/data:** 026 selection/outcome/coverage engine; team UUID and HOME/AWAY own-point orientation. No reference odds needed.
- **Acceptance:** subject flip selects the actual other team's point series; same mean/outcome/unknown rules and explicit counts; missing historical team-total references remain unavailable. Never compute an offered line from game total/spread. Reject first-half/unsupported markets rather than returning full-game values.
- **Tests:** home/away team flips, actual opponent identity, same anchor/different team, null/zero scores, pushes and small windows, unknown cutoff and existing Game Total regressions; bounded query/typed validation.
- **Dependencies/risks:** 026; approved team-total metric/threshold domain. Game Total's combined-point series must never leak into Team Total. No additional backend dependency required.
- **Behavior reference:** [Team Total](nfl/team-total.md), [L5 evidence](nfl/screenshots/team-total-l5.png).

## Proposed Task 029 — Team Total frontend adapter and team/market control

- **Objective/scope:** add Team Total alongside Game Total, reusing 027 primitives and one clear selected-team control. No duplicated chart/log or backend math.
- **Likely files:** `components/gameResearch/` market configuration/context selector, typed client, preview integration and focused tests/styles.
- **Reuse/data:** 027 renderer/controls/summary/log and 028 response; matchup canonical participants and existing Router navigation.
- **Acceptance:** all point values/means/counts are supplied by the correct adapter; switching subject/market cannot retain an unlabeled prior threshold as an offered line. Manual line origin stays explicit; historical line column unavailable if unsupported; failure of one subject doesn't remove other sections. No first-half switch without data support.
- **Tests:** team/market/line transitions, no old Game Total values under Team Total labels, query keys and request IDs, same-sample chart/table and dark/mobile/input/accessibility regressions; typecheck/build.
- **Dependencies/risks:** 027/028. Decide manual-threshold reset versus explicitly retained user scenario in approval, not implicit behavior hidden in a generic component.
- **Behavior reference:** [Team Total](nfl/team-total.md), [reusable state](nfl/reusable-components.md#matchup-and-market-state).

## Proposed Task 030 — Moneyline results and signed-spread backend adapter

- **Objective/scope:** add margin series, descriptive reported-score W/L/T and manual selected-team spread outcomes to the shared projection. Preserve old source-reference moneyline rules.
- **Likely files:** shared research service/schema/API/tests, reusable exact comparison helper if needed; no schema/ingestion changes.
- **Reuse/data:** selected own/opponent scores and existing accepted history; existing market Decimal comparison/sign conventions. No prices needed for descriptive W/L/T or a manual spread scenario.
- **Acceptance:** margin = own − opponent; cover/push/fail by margin + selected-team signed handicap. Clearly document input as **selected-team signed handicap**, distinct from raw nflverse home-favorite convention. A raw-score tie is TIE, not certified moneyline push; existing `/markets` still returns UNDETERMINED for unknown tie rules. No ROI/payout or implied-probability model. Returned sample/unknown/denominator/provenance matches other adapters.
- **Tests:** away/home orientation, positive/negative handicap, pick'em, margin zero, exact push, zero scores and missing score pair, side validation, correction/cutoff/stage, reference sign regression; preserve existing market arithmetic/API contracts.
- **Dependencies/risks:** 026 shared engine, initial totals slices reviewed; approve score-record language so UNKNOWN is never labeled a verified final record.
- **Behavior reference:** [Moneyline / Spread](nfl/moneyline-spread.md).

## Proposed Task 031 — Moneyline/Spread history frontend

- **Objective/scope:** add market switch and signed spread/margin view using the existing chart/filter/log/summary components; include descriptive W/L/T independently of current prices.
- **Likely files:** research market configuration/controls, shared chart signed-axis mode, log columns, client/tests/styles.
- **Reuse/data:** 027–030; existing team/context selection, null/provenance/status components. Spread line control reuses decimal input/stepper; slider only if separately useful/approved.
- **Acceptance:** market switch retains valid team/anchor identity; signed y-axis displays negative and zero margins correctly. Cover/push/fail and score W/L/T labels stay distinct. Current/manual/reference handicap and odds never share an ambiguous column. No fabricated line or live offers; preserve totals behavior and original preview.
- **Tests:** signed-axis range, controls/window/context transitions, rate/count agreement, tie/null/error states, historical-source versus manual labels, keyboard/table/tooltip equivalents; TypeScript/build/mobile/browser checks.
- **Dependencies/risks:** 030 plus reused UI. Target hover/click/slider semantics were not verified; use independently approved controls.
- **Behavior reference:** [Moneyline / Spread](nfl/moneyline-spread.md), [component catalog](nfl/reusable-components.md).

## Proposed Task 032 — supported scoring matchup rankings API

- **Objective/scope:** add separately specified points-for/points-allowed ranks using existing accepted reported-score data; preserve all four yardage rank definitions and contracts.
- **Likely files:** ranking repository/service/schema/API and tests; API guide and decision definitions. Use additive optional response/route contract only after reviewing compatibility.
- **Reuse/data:** full-league population before team filtering, exact unrounded ratios and competition ties; existing per-metric score denominators and accepted pointers. No two-team local ranking.
- **Acceptance:** approve population/REG/POST/combined policy, offense descending/defense ascending and missing-value denominators; source-reported ranking labels. Unit-neutral points fields, **not** points stuffed into `total_yards`. No expanded red-zone/third-down/possession/sack-count/turnover/DVOA rows without validated data; current season for upcoming comparisons and explicit no historical-pregame certification.
- **Tests:** all-team population, exact ties, missing/zero points, denominators differing by metric, stage/season/corrections, team filter after ranking, old yardage responses/ranks unchanged; API/SQL permission projections.
- **Dependencies/risks:** approval of new scoring rank definitions. No source/schema expected, but stop if implementation would require permission expansion; do not grant it as a shortcut.
- **Behavior reference:** [Game Total rankings](nfl/game-total.md), [rankings image](nfl/screenshots/game-total-matchup-rankings.png), [ranking interaction ledger](nfl/evidence/README.md).

## Proposed Task 033 — shared matchup rankings comparison frontend

- **Objective/scope:** extract existing comparison presentation into a reusable panel and add only the supported points metrics. Offer offense/defense direction and explicit comparison season independently of market controls.
- **Likely files:** `MatchupComparison.tsx`, proposed `MatchupRankingsComparison.tsx`, research client/types/tests; original ranking table integration remains intact.
- **Reuse/data:** existing season/stage selectors, four category API ranks, samples/nulls/direction and 032 new scoring contract. Query cache shared across Preview/research panels.
- **Acceptance:** clear metric/unit/rank direction/sample, no overall rank; opponent low defense rank means strong defense, not automatically favorable offense. Keep original current-revision season warnings. Historical comparison-season override is visibly separate from game-history sample. No target-specific color semantics copied without approval.
- **Tests:** OFF vs DEF reversal, explicit comparison season/stage without modifying history, authoritative ranks/ties/nulls, current-season no-data, source finality labels and original ranks/navigation; both themes/responsive panel.
- **Dependencies/risks:** 032 and prior core market slices. Do not expand season bounds past 2024–2026 or silently reuse past-season ranks as current.
- **Behavior reference:** [rank direction switch](nfl/game-total.md), [comparison patterns](nfl/reusable-components.md#matchup-comparisons-and-availability).

## Proposed Task 034 — bounded historical source-reference enrichment

- **Objective/scope:** add optional original source spread/full-game total reference fields and their provisional outcomes to shared history, separately from manual-threshold outcomes. No verified closing-label or odds-history storage.
- **Likely files:** shared market validation helpers/service, bounded schedule repository projection, research schema and historical-log columns/tests; reuse existing `/markets` detail unchanged.
- **Reuse/data:** `MarketsService` identity/hash checks, Decimal parser, source artifact/row hashes and exact team orientation; selected canonical game IDs already bounded by history.
- **Acceptance:** at most one bounded enrichment query, no per-row HTTP/provider call; missing/invalid source reference does not remove known scores or manual outcomes. Expose unknown bookmaker/quote timing, original retrieval/recording distinction and explicit “unverified source reference” headings. Team-total historical reference remains null. If future multiple references appear, never silently pick a book.
- **Tests:** source-record hash/identity mismatch, score-pair disagreement, missing/ref-only rows, signed handicap, custom line changed while historical reference unchanged, unknown time/finality and reference-free/manual functionality.
- **Dependencies/risks:** core shared history/log, original schedule-column privileges. Corrected raw schedule references are current source revisions, not a time series or quote archive. No scope to add a provider or migration.
- **Behavior reference:** [separate historical/custom comparisons](nfl/game-total.md), [missing team-total line](nfl/team-total.md), [ATS labels](nfl/moneyline-spread.md).

## Proposed Task 035 — explicit L20/H2H/season sample selection backend

- **Objective/scope:** extend the shared market-research selector only after specifying window semantics; existing Task 023 `/trends` L3/L5/L10 contract remains unchanged unless separately requested.
- **Likely files:** factored selection helper, research filter/schema/service, focused selection/API tests/docs.
- **Reuse/data:** canonical opponent/date/season/stage and required matchup cutoff; existing stable sorting and accepted reciprocal game projection.
- **Acceptance:** approve same-season L20 and bounded SEASON; define H2H as filter on anchor's actual opponent before latest-N (or an explicitly selected H2H scope), disclose short samples. No default cross-season or REG/POST mixing despite target examples; unknown date excludes and missing scores remain explicit. Reject unsupported/conflicting filters; counts/IDs shared across every representation.
- **Tests:** <20 available, 17-game REG, opponent rematches, no H2H, equal/unknown kickoff, early historical anchor, season boundaries and approved composition semantics, bounded season sample/query count; old API regressions.
- **Dependencies/risks:** owner definition approval. Cross-season history requires a new explicit scope and provenance rules, not appending another season's log in React.
- **Behavior reference:** [Game Total windows](nfl/game-total.md), [Team Total](nfl/team-total.md), [unverified ML window differences](nfl/moneyline-spread.md).

## Proposed Task 036 — shared expanded research filters frontend

- **Objective/scope:** expose only backend-supported L20/H2H/SEASON controls and shared URL-backed research state; preserve Task 024's existing selector unless its extension is separately approved.
- **Likely files:** `RecentGamesSelector`, research context/state/client, shared log/chart consumers and tests; no backend calculation.
- **Reuse/data:** 035 plus previous controlled window component, Router/Query identities and current stage scope.
- **Acceptance:** actual sample/opponent/season/stage visible for every mode; no stale counts/rates when controls change. Valid Back/deep-link/reset behavior preserves `returnTo` and rank controls. No unavailable advanced filters/premium simulation.
- **Tests:** URLs/invalid inputs/reset/back, H2H opponent scope and short samples, cancellation and cached contexts, chart/table/summary ID parity, keyboard/mobile/dark and original L3/L5/L10 functionality.
- **Dependencies/risks:** 035. “H2H” must not erase the postseason boundary or imply more data exists than the selected season allows.
- **Behavior reference:** [filter/window catalog](nfl/reusable-components.md), [navigation/state distinctions](nfl/navigation.md).

## Proposed Task 037 — incremental team/event/market navigation

- **Objective/scope:** add targeted schedule/team-log links into implemented market research and reuse a compact canonical team/event selector. No seven-tab app-shell redesign.
- **Likely files:** schedule/shared game links, Game Preview and team research route/state, research context selector, Router/client tests/styles. A standalone team-market route is optional and must be explicitly included at approval.
- **Reuse/data:** actual schedule participants/IDs, existing `returnTo` validation, supported markets and known-date states. No global player search, broadcast/venue feed or logos required.
- **Acceptance:** event/team/market context survives navigation and Back; default and current research profile distinguished from browsing another week. Mobile selector does not clip control labels or obscure content. No link to unsupported first-half/player/lineup/standings features.
- **Tests:** schedule → market → game log → preview → Back, team flip/event validation, wrong-team/unknown-ID links, week-only navigation versus selected anchor, no loss of original schedule/ranking controls; responsive and keyboard checks.
- **Dependencies/risks:** functioning market destinations and approved state rules. Do not infer past-player/projection data from team selection.
- **Behavior reference:** [Schedule](nfl/schedule.md), [navigation](nfl/navigation.md), [standings team link pattern](nfl/standings.md), [shared matchups](nfl/reusable-components.md).

## Later phases and unavailable parity

Retain the original Task 022 dependency order: offline player source/identity/participation validation → minimal schema/guarded ingestion (separate approvals) → player logs/API → manually entered prop research/chart → discovery/DvP/usage → injury/depth/weather and optional lawful $0 odds. Reuse the game chart/table/control **presentation**, never team-game eligibility rules for player appearances. Standings is a separate later product/data-definition task; lineup projections require actual players/depth/injury evidence. Save/Track/My Picks and bet tracking remain outside scope.

Research-only gates before unsupported features: period score/source audit for first-half; published/completed-before-cutoff evidence for true pregame snapshots; metric-by-metric numerator/denominator/coverage audit for advanced ranks; quote/license/retention/cost audit for real offers or movement. The supplied documents suffice for current independent design; no new REA action is needed or authorized. Open hover/H2H/persistence/tie questions are not blockers to our own explicit contracts.

## Task 025 validation and completion

Reviewed the thirteen REA Markdown references and selected retained artifacts listed in the [gap analysis](task-025-frontend-gap-analysis.md), current models/API/frontend/tests and original roadmap. Checked only official Recharts repository/license/manifest for the dependency proposal. No app code, schema, imports, services, dependency installation or REA/browser actions. No application tests/builds were run because changes are documentation-only. Historical 023/024 tests remain recorded in their original guides, not claimed as new runs.

Documentation validation: relative-link checks for the four new documents and updated navigation pointers, `git diff --check`, and final changed-file scope inspection. Results are recorded after those checks below. No Docker command, commit, merge, push or deployment followed this planning task.

Actual results: all **103 relative file links** in the four new documents resolved;
the broader **120 planning/navigation links**, including specified heading anchors,
passed. `git diff --check` passed. Scope inspection confirmed **12 Markdown files
only**, with no application, test, manifest, Docker or data changes.

Files created: `task-025-frontend-gap-analysis.md`,
`task-025-component-architecture.md`, `task-025-data-feasibility.md` and this
`task-025-game-research-roadmap.md` under `docs/research/`. Existing files updated:
`AGENTS.md`, `README.md`, `docs/architecture.md`, `docs/decisions.md`,
`docs/implementation-plan.md`, `docs/team-performance-trends-ui.md`,
`docs/research/task-022-expansion-audit.md` and
`docs/research/task-022-roadmap.md`. Updates reconcile completed 023/024 work,
planning Task 025 and proposed implementation numbering without altering original
REA artifacts or authorizing the next task.

**Recommended next approval after implemented Task 026:** Task 027, Game Total chart and shared research UI, using the [actual API contract](../game-total-research-api.md). No new backend calculation is needed for supported filters/reference totals. Chart dependency and frontend work require separate review; no new market or cross-season scope is implied.
