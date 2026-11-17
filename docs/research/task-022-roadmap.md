# Task 022 — phased integration roadmap

2026-11-17. **Proposals for approval, not implementation authorization.** Preserve FastAPI/repository/service/schema boundaries, PostgreSQL/SQLAlchemy/Alembic, React/TypeScript/Vite, Query/Router, Tailwind and Docker Compose. No restart, new platform, queue/cache service or bulk rewrite is needed. Task numbers after 022 below are proposed; approve one narrow task at a time.

Related: [verified inventory](task-022-expansion-audit.md), [data gates](task-022-data-sources.md), [REA backlog](task-022-rea-followups.md). No target code, private endpoints, assets, signed links or response datasets are permitted dependencies.

## Architecture and statistical contracts

Reuse `accepted_query()` and reciprocal pair joins for team research; never read unapproved raw statistics fields just because artifacts retain them. Recent summaries should execute one bounded statement over accepted projections, expose source/pair generations, and reuse per-metric non-null denominators. Keep existing ranking endpoints/definitions unchanged. Do not add an index, cache or materialized view before measuring a real query need.

Proposed Phase 1 recent-window contract: latest **N accepted team-game rows** with known kickoff in one selected season and REG or POST, N in 3/5/10; deterministic kickoff/source-ID/UUID descending. Select rows first, then count non-null values per metric; do not silently backfill older games to satisfy each metric. Report requested N, selected count, metric counts, unknown-date exclusions, identities and coverage. UNKNOWN remains UNKNOWN. This is a **current accepted reconstruction**, never evidence that games completed before a selected matchup. Proposed ordering/window rules require approval in Task 023; they are not a revision of the existing season rankings.

True pregame calculations need independently supported completed-before-kickoff evidence, not just an earlier start or accepted statistics. Keep historical pregame controls unavailable until that contract exists. Upcoming-matchup summaries use the matchup's current season/stage with clear current-data labels; never carry a prior season rank forward as current. Missing current-season samples show unavailable. A historical page can continue showing the explicitly labeled season reconstruction.

Player foundation: canonical internal UUID, provider-scoped stable-ID mapping (GSIS primary candidate), season/team membership separate from actual game team, versioned accepted player-game facts and participation evidence. Reuse artifact/review/lock/correction conventions, **not** the exact two-team-pair shape for individual players. Do not build a universal entity abstraction or new event-sourcing service. Appearance eligibility must be known independently of missing stat rows; preserve unknown. Default player windows remain within selected season/stage per PRD/data model; explicit cross-season mode would require separate approval despite the target's observed L10 behavior.

Player calculations: pure tested market mappings; Decimal thresholds; over/under/push separate, unknown/DNP excluded with reasons. Proposed display: O/N, U/N, P/N where N is eligible appearances with known metric; O+U+P=N. A non-push rate, if desired, must be separately labeled O/(O+U), never inferred by 100%-over when pushes exist. Show requested/actual sample, missing stats and eligibility gaps. These denominator details require owner approval before implementing Task 030.

APIs return typed `{data, meta}` with coverage/definition/cutoff semantics; server computes canonical statistics, ranks and threshold outcomes. Query keys include identity/season/stage/window/team/market/line and cutoff mode where supported. UI uses URL state for shareable filters and local state for temporary presentation; abort superseded requests and isolate odds/injury/weather errors. Runtime validation at external boundaries should use existing Python/Pydantic and small typed frontend checks before proposing another library.

Use current semantic tables and shared loading/error/provenance/Card/theme components. Recharts and TanStack Table are approved architectural intentions, not installed dependencies: request task-specific installation approval when needed. Use Recharts for original accessible performance charts with a table alternative; consider TanStack Table when discovery filtering/pagination complexity warrants it. Never swap out current team tables merely for consistency.

Sportsbook offers remain a separate optional domain: provider event/player mappings, market/side/line/book, source quote timestamp, fetched timestamp, stale status and permitted observations. Manual thresholds have no bookmaker provenance. Compare prices only for the same event/player/market/side/**exact threshold** and disclose settlement-rule differences. Empirical hit rate, odds-implied probability and prediction are different quantities; no prediction model is proposed. No raw third-party feed is exposed as a product.

## Phase 1 — game-level research

### Proposed Task 023 — read-only recent team trends API (recommended next)

- **Objective/scope:** add L3/L5/L10 current-accepted passing/rushing offense and defense summaries. Backend only, no schema/grants/ingestion/finality/ranking changes or new dependency.
- **Dependencies/data:** existing accepted pairs, canonical team/game IDs, kickoff/stage/season; approval of the recent-window contract above. No external source needed. Missing/unknown-date records remain visible in coverage.
- **Likely files:** `backend/app/repositories/team_stats.py`, `services/team_stats.py`, `schemas/team_stats.py`, `api/team_stats.py`, `tests/test_team_stats_api.py` or a focused trends test; API guide.
- **Acceptance:** proposed `GET /api/teams/{uuid}/trends?season=2026&season_type=REG&window=5` (contract to approve) validates keys/window/stage; full response in one aggregate statement plus bounded identity check; four metrics, totals/averages/counts, selected IDs/pair generations and exclusions; fewer than N games honest; zero/negative retained. No pregame or league-rank claim, no selected-game cutoff parameter.
- **Testing:** pure window/aggregate cases; HTTP 404/422/405/503; SQL allowed-column/query-count inspection; separately authorized isolated PostgreSQL pair-correction/stage/snapshot tests. Include equal dates, undated rows, null metric, empty season and 2026 upcoming sample. No real imports required.
- **Risks/blockers:** owner may prefer only certified completed games, in which case eligibility work is required first. Unknown-date exclusions and current reconstruction labels must be accepted; existing privileges must suffice or stop before expansion.

### Proposed Task 024 — recent Game Preview comparison

- **Objective/scope:** add Season/L3/L5/L10 comparison controls and four recent offense-versus-opposing-defense averages alongside existing authoritative season ranks. Frontend only.
- **Dependencies/data:** Task 023 accepted API; existing game-season/stage and season rankings. No rank recomputation or recent league rank unless separately scoped.
- **Likely files:** `MatchupComparison.tsx`, `api/research.ts`, `ResearchShared.tsx`, `styles.css`, matchup tests.
- **Acceptance:** bookmarkable window, same sample definition on both teams, explicit counts/coverage/current-data warning; existing season behavior and logs preserved; independent loading/error/retry; readable both themes and mobile.
- **Testing:** RTL controls/cache transitions/partial and no sample/API errors; typecheck/build; owner browser desktop/mobile/dark/keyboard checks.
- **Risks:** recent average must not appear to be paired with a recent rank when the rank is season-wide. Data may include a historical selected game/later games.

### Proposed Task 025 — bounded hypothetical game-line calculation API

- **Objective/scope:** separate read-only endpoint for user-entered team spread and game total comparisons over bounded selected historical games. Keep stored-reference endpoint unchanged.
- **Dependencies/data:** Task 023 selection conventions; existing schedule reported scores and market Decimal comparison functions. Define home-handicap input once; no sportsbook required.
- **Likely files:** markets API/schema/service, team-stat projection helper if needed, `test_markets.py` and API guide.
- **Acceptance:** proposed typed manual-line query contract, finite bounded decimals; return per-game provisional cover/over/under/push/undetermined, totals/counts and explicit reported-score/finality coverage. Manual scenario and source-reference line never overwrite one another; no certified ATS or closing-line claim.
- **Testing:** signed home/away spreads, pick'em, integer pushes, null scores, tied moneyline excluded from spread/total math, hostile precision/input limits, stage/window and read-only errors; isolated DB only separately approved.
- **Risks:** score availability is not completion; no arbitrary dates/large unbounded cross-season scan. No wager-settlement or profit/ROI calculation.

### Proposed Task 026 — manual game lines and provisional reference history UI

- **Objective/scope:** accessible spread/total inputs and selected-history table with separate manual-scenario and existing-reference results; enhanced matchup context from recent offense/defense.
- **Dependencies/data:** Tasks 024–025, existing market reference API. Reference histories reuse only stored game references, not fabricated past offers.
- **Likely files:** `BettingMarkets.tsx`, `PreviewTeamLogs.tsx`, `api/markets.ts`, focused new component/tests/styles.
- **Acceptance:** manual threshold changes recompute through backend, cancellable/debounced bounded requests; show wins/losses/pushes/unknowns and denominator; reset/reference distinctions, keyboard input, both themes. Avoid new requests for every offscreen game by using bounded summaries/batched own API if measured necessary and separately scoped.
- **Testing:** RTL thresholds/reset/pushes/stale-response rejection/independent failures and provenance; browser responsive smoke.
- **Risks:** never label source-reference aggregates verified historical ATS/O/U; current raw source revisions have no guaranteed pregame quote timestamps.

### Proposed Task 027 — historical eligibility feasibility gate

- **Objective/scope:** research-only contract for true completed-before-kickoff team/player reconstruction; do not weaken UNKNOWN or change importers.
- **Dependencies/data:** current evidence fields and independent official completion evidence candidates. Phase 1 current summaries can ship before this research; historical mode cannot.
- **Likely files:** new eligibility evidence/contract document; decisions only after approval.
- **Acceptance:** examples of postponed/overlapping/undated games, evidence timestamps versus known completion time, corrected-current versus as-published distinction; explicit go/no-go and small separately approved implementation task if feasible.
- **Testing:** documented hand-worked counterexamples and source artifact checks, no application/database changes.
- **Risks:** no $0 lawful evidence may establish completion time/as-published values. Date-only cutoff is insufficient. A NO-GO leaves labeled season reconstruction intact.

## Phase 2 — player data foundation

### Proposed Task 028 — player source and eligibility validation

- **Objective/scope:** offline research/validator only for weekly player stats, IDs, rosters and optional snaps; validate all ten PRD markets and appearance population before schema design.
- **Dependencies/data:** source-matrix rights gates; official 2024–2026 sample bytes and canonical schedule read-only export only if separately approved. No DB writes/imports.
- **Likely files:** `docs/player-stats-feasibility.md`, narrowly scoped `backend/ingestion/player_stats/` pure validator and synthetic tests if code is explicitly approved for this future task.
- **Acceptance:** retrieval/hash/license evidence, field/null/count/uniqueness audit, game joins, GSIS/PFR mappings, regular/postseason, trade and special-teams-only/played-zero/DNP cases; official reference reconciliation; stop unsupported fields/eligibility.
- **Testing:** malformed IDs, duplicate/missing rows, source-schema drift, negative/zero stats, transfers and reconciliation fixtures.
- **Risks:** listed artifacts don't prove coverage; sparse stats may fail appearance eligibility. No changing PRD to touches-only as a shortcut.

### Proposed Task 029A — player identities, membership and revision schema

- **Objective/scope:** reviewed minimal additive models/migration and schema tests for canonical players/provider mappings, season roster membership, participation evidence and accepted player-game revisions.
- **Dependencies/data:** Task 028 GO and approved row identity/correction/eligibility contract; reuse canonical games/teams/source artifacts. No real migration execution/import in coding scope.
- **Likely files:** `app/models/`, new Alembic revision, narrowly scoped role allowlists/admin runbook, schema/security tests, data model docs.
- **Acceptance:** provider uniqueness and ambiguous-match quarantine, actual team per appearance, immutable corrections/selection history, nulls/unknown eligibility, consistent source/version keys. Minimal restricted API/ingest grants reviewed explicitly.
- **Testing:** isolated PostgreSQL foreign keys/uniqueness, forbidden writes/history mutation, revision selection; separate approved test DB migration only.
- **Risks:** schema/permission work requires explicit approval; don't edit applied 0001/0002. No universal provider mapping schema unless justified by validated joins.

### Proposed Task 029B — guarded player preparation/import workflow

- **Objective/scope:** one independent player pipeline using bounded acquisition, immutable evidence, dry-run/review/baseline-bound apply and correction handling. No automatic importer or expansion of original pipelines.
- **Dependencies/data:** 028, 029A; separately approved development schema availability. Reuse atomic state/locks/review conventions and approved provider artifacts.
- **Likely files:** `ingestion/player_stats/`, tests and runbook; narrowly scoped updater adapter later only after core workflow passes review.
- **Acceptance:** idempotency, ambiguity/missing-data quarantine, reviewed correction diffs, no silent deletions, stop uncertain commit; separate review/approval for player pipeline if CLI adapter included. API role cannot import; no new scheduler activation.
- **Testing:** offline preparation/revalidation/receipt binding; isolated transaction rollback/correction/concurrency; fake CLI approval/skip/stale-baseline/indeterminate tests. Actual development import is a separately approved owner step.
- **Risks:** source missing row versus DNP distinction; failed/corrected imports must preserve prior accepted data. Do not copy team-pair importer assumptions onto players.

### Proposed Task 029C — read-only player catalog and game-log APIs

- **Objective/scope:** typed canonical player lookup/search, paginated season/stage/team logs with participation and per-stat missingness/provenance. No frontend yet.
- **Dependencies/data:** accepted player foundation and narrowly approved SELECT projections; runtime coverage established by owner.
- **Likely files:** player repository/service/schema/API/tests and endpoint docs.
- **Acceptance:** stable IDs, no name-only identity joins, explicit season/REG/POST, optional historical team filter, actual team/opponent/game IDs, bounded deterministic pagination and correction generation; missing players/data distinct; no live provider calls.
- **Testing:** filters, identity collisions, transfers, empty/missing/zero data, HTTP failures/forbidden writes, query count and isolated restricted-role projections.
- **Risks:** season roster is not historical availability; no private raw source or approval tokens in public API.

## Phase 3 — player research

### Proposed Task 030 — player threshold/window calculation API

- **Objective/scope:** pure ten-market mapping, L5/L10/season averages and O/U/push calculations with manually entered Decimal threshold. No sportsbook dependency.
- **Dependencies/data:** 029C, validated appearances and known metrics; owner approves denominator/window definitions above. Historical pregame mode also depends on 027 and subsequent approved implementation.
- **Likely files:** new player-research service/schema/API, pure tests and API tests.
- **Acceptance:** select eligible appearances within season/stage/team before latest-N, disclose missing/unknown/DNP exclusions and actual counts, zero retained, pushes separate, fewer-than-N explicit. No implied-probability/prediction conflation or default cross-season carryover.
- **Testing:** each market, integer/half-line/negative yards, all pushes, no samples, DNP/bye/played-zero, correction, trade, stage/season boundary, exact decimal comparisons.
- **Risks:** participation incompleteness can block hit rates even when a log can be shown; show unavailable rather than a biased denominator.

### Proposed Task 031 — player profile and manual-line research UI

- **Objective/scope:** player-first navigation/profile, game table, market selector, L5/L10/season and manual threshold/side controls backed by Task 030.
- **Dependencies/data:** 029C/030; existing Router/Query/theme/shared states, no odds source.
- **Likely files:** `App.tsx`, new player page/API types/components/tests, styles.
- **Acceptance:** bookmarkable player/season/stage/market/line/team context; actual historical teams, sample/coverage/source details, persistent historical logs during optional-section failures; manual use works offline from sportsbook services.
- **Testing:** RTL deep link/filter/navigation/reset/errors/cache isolation/missing data and keyboard; typecheck/build and owner browser mobile/dark checks.
- **Risks:** expanding default market scope to anytime TD/combined yards is separate definition approval, not implied by target examples.

### Proposed Task 032 — interactive player performance chart

- **Objective/scope:** original Recharts series/reference threshold/tooltip with matching accessible table. Keep data calculation on shared API.
- **Dependencies/data:** 031 and explicit approval to install Recharts; bounded per-game values/threshold outcomes from 030.
- **Likely files:** player chart component/tests, package manifest/lock only under approved dependency scope, theme tokens.
- **Acceptance:** controls/chart/table/rates agree; distinguish zero/missing/push, show dates/opponents/team and sample; accessible keyboard/table fallback; line changes and series selection cannot show stale prior player responses.
- **Testing:** chart/table data alignment, null gaps, theme contrast, threshold updates; browser tooltip/resizing/focus tests. Avoid asserting only SVG internals.
- **Risks:** test environment lacks real browser proof; secondary usage series only after validated data, no copied schematic zones.

## Phase 4 — player prop discovery

### Proposed Task 033 — stat-driven discovery API/table

- **Objective/scope:** searchable player/market catalog, position/team/window filters and stable sorting/pagination, linking to manual-line research. No odds required.
- **Dependencies/data:** 030–031; roster/catalog plus covered stat-market population. Thresholds are explicitly user-entered scenarios, not invented sportsbook props.
- **Likely files:** discovery repository/service/API/schema and React page/table/API tests; consider TanStack Table only with explicit dependency approval.
- **Acceptance:** compact bounded summaries, server allowlisted filters/sort/null ordering and deterministic tie keys; full sample counts, clear threshold origin, preserved URL state; no multi-megabyte universal payload or per-row remote calls.
- **Testing:** search/diacritics, empty filters, ties, null rate sorting, page transitions, invalid query, query count, deep-link player context and partial coverage.
- **Risks:** no rate sort without defined threshold; do not market a catalog of unsupported sportsbook offers. Saved presets/local preferences optional later usability task.

### Proposed Task 034A — defense-versus-position summaries

- **Objective/scope:** own aggregate opponent player output by defense, game, historical position and supported market, with league ranks and coverage.
- **Dependencies/data:** 029C/030 and an approved position/defensive-game denominator policy. Existing four team ranks remain separate context.
- **Likely files:** team/opponent repository/service/API/schema/tests; focused discovery/player context component.
- **Acceptance:** position totals per defensive game before averaging; complete opponent population or explicit unavailable; rank direction/ties/sample units visible. Use current season for upcoming games; historical mode requires eligibility gate. No averaging per player and calling it per team game.
- **Testing:** multiple RB/WR per opponent, position changes, byes, no position output, missing player subset, ties and regular/postseason. Test reciprocal team/game identity.
- **Risks:** unknown position and incomplete player facts bias rankings; do not label team rushing defense as RB DvP.

### Proposed Task 034B — basic usage and opportunity summaries

- **Objective/scope:** target/carry counts and own team opportunity shares; snaps only if Task 028 validated them. API plus small research table/series.
- **Dependencies/data:** accepted player facts, complete team denominators; optional snap mapping. Approve ratio-of-sums/averaged-share semantics.
- **Likely files:** player research service/schema/components/tests; no PBP ingestion solely for basic targets/carries.
- **Acceptance:** counts and denominators visible, traded games use actual team, zero denominator/missing totals unavailable, no routes/route-run inference from snaps.
- **Testing:** missing teammate rows, null/zero totals, transfer, negative-yard game with positive opportunity, snap crosswalk failure, correction and stage/window filters.
- **Risks:** source-provided shares may use different definitions. Do not average percentages without documenting weighting.

### Proposed Task 035 — optional bounded sportsbook comparisons

- **Objective/scope:** first a documentation/key-access feasibility gate; only a separately approved subtask adds one provider's on-demand backend adapter and same-line UI comparison.
- **Dependencies/data:** 029 mappings, 031, verified free account/markets/terms/quota. Game-market comparison can reuse this adapter; it need not wait for advanced player features.
- **Likely files:** new provider/odds service/schema and usage/observation model only if approved, configuration placeholders, optional offers UI/tests/runbook.
- **Acceptance:** $0 hard cap, no paid upgrade/overages, server key, dedup/cooldown/credit headers, book/market/line/time provenance, stale/unsupported states, manual thresholds unaffected. Storage/migration/grants require explicit separate approval.
- **Testing:** provider fixtures, quota exhaustion, 429/timeouts/stale data, concurrent request dedup, mismatched player/event/line, changed start times, absent under price and retention policy.
- **Risks:** 500 credits cannot support frequent whole-league ten-market polling; no key or exact NFL coverage was tested in 022. A NO-GO leaves complete manual research intact.

## Phase 5 — advanced research

### Proposed Task 036 — current injury reports

- **Objective/scope:** first validate actual records/rights/cadence, then separately approved guarded snapshot adapter/read-only independent UI section.
- **Dependencies/data:** player/team mapping, source-matrix injury gate; explicit status/time vocabulary and last-known policy.
- **Likely files:** injury feasibility doc, future ingestion/models/API/UI/tests under separate subtask approvals.
- **Acceptance:** report/practice statuses as supplied, source-modified/fetched times separated, stale/error/coverage per team, absence != healthy; no historical pregame claims without archive evidence.
- **Testing:** stale dates in newly uploaded files, unknown IDs/statuses, correction, missing team and independent failure; isolated storage tests only if separately authorized.
- **Risks:** loader existence/current asset does not prove current-week reports or practice-day history. Source gate can stop implementation.

### Proposed Task 037 — full depth-chart context

- **Objective/scope:** validate legacy versus timestamped schemas and all units, then separately scoped guarded snapshots/API/UI.
- **Dependencies/data:** player mappings and source-matrix depth gate; preserve timestamped observations rather than invent weeks.
- **Likely files:** depth feasibility doc; later ingestion/models/schema/API/section and tests.
- **Acceptance:** offense/defense/ST explicitly covered or unavailable, formation/slot/rank not collapsed into one player position, record load time labeled, traded/unknown players handled; bounded artifact/history retention strategy.
- **Testing:** 2024/2025+ schema fixtures, repeated snapshots, ties/duplicate slots, missing units, same player in multiple formations, stale data and payload limits.
- **Risks:** 72.6 MB current CSV; current membership not guaranteed starter/injury replacement. No full-depth promise until coverage proven.

### Proposed Task 038 — venue-aware weather context

- **Objective/scope:** verify one free permitted source and venue mapping, then optional forecast UI/API; historical reconstructed weather separately labeled.
- **Dependencies/data:** canonical game location/kickoff, verified coordinates/roof/neutral-site handling; approved provider/cache behavior.
- **Likely files:** weather feasibility doc, future venue reference data and optional adapter/API/UI/tests; no new service.
- **Acceptance:** forecast-valid time, source/model/fetched time, units, stale/unavailable, international fixtures and roof uncertainty; never show current forecast as historical pregame conditions.
- **Testing:** UTC/DST alignment, reschedule/venue changes, outside horizon, indoors/unknown roof, unit conversion, API failures and independent sections.
- **Risks:** schedule home team is not venue; source forecast grid != stadium observation. No inferred roof position.

### Proposed Task 039 — sparse historical odds observations

- **Objective/scope:** only if 035 succeeded, store permitted on-demand observations and plot exact event/market/book/side/line observations. No paid backfill or scheduler expansion.
- **Dependencies/data:** verified retention terms, approved immutable schema/migration/permissions and timestamps, prospective observations. Any unattended collection needs a new task.
- **Likely files:** odds model/repository/API, chart/table/tests and provenance runbook.
- **Acceptance:** visible gaps, first/last observed labels, distinct price versus threshold movement, no interpolation as actual quotes or “closing” label without verification; reference source artifacts excluded.
- **Testing:** out-of-order/duplicate/corrected snapshots, missing quote time, two books/lines, DST/UTC, rescheduled event and sparse-series UI.
- **Risks:** no history until collected; on-demand gaps are unavoidable; $0 prevents comprehensive historic archive from reviewed provider.

### Proposed Task 040 — efficiency and granular matchup intelligence gate

- **Objective/scope:** research and one metric at a time for EPA/play, success rate, red-zone usage, routes, formation/target depth or rushing lanes. No broad granular-feed build.
- **Dependencies/data:** demonstrated user need after 034; independently licensed fields, complete denominators and historical mappings; dataset-specific FTN/NGS gates.
- **Likely files:** metric feasibility/definition doc, then individually approved validator/ingestion/API/chart tasks.
- **Acceptance:** exact numerator/denominator/qualification/garbage-time/kneel/spike definitions as relevant, actual sample coverage, source/license and missingness; no target zone geometry copied or inferred coordinates invented.
- **Testing:** hand-reconciled game examples, incomplete plays, qualification thresholds, corrections and cutoff/season/stage cases before implementation.
- **Risks:** detailed participation can lag until postseason; licensing and scarce coordinates may produce NO-GO. Basic counts/manual research remain useful.

## Approval and verification strategy

Each item is intentionally bounded, but schema, guarded importer, real migration/import and new-source onboarding are different review gates. If a task contains a research gate followed by implementation, research delivers GO/NO-GO first and implementation requires its own concrete scope approval. Development data changes never follow automatically from passing synthetic tests. Existing updater default-no confirmations, original tokens/stdin, lock/baseline/admission/concurrency controls and unknown-commit stops remain mandatory.

Use current unit/HTTP/RTL suites; isolated PostgreSQL tests explicitly approved for schema/grants/SQL behavior; owner browser smoke for actual rendering/charts/first paint. Add regression cases at each changed business rule; do not multiply tests that only mirror presentation internals. Measure SQL query count and representative response latency before adding caches; keep optional source failures isolated. No commit, merge, push or deployment is included in any proposed task unless later explicitly approved.

## Single recommended next implementation task

Approve **Task 023, read-only recent team trends API**, with its explicit current-accepted window contract. It uses data/provenance already stored, provides the four recent offense/defense averages needed by the existing preview, centralizes consistent selection and avoids frontend multi-page calculations. It needs no new provider, dependency, schema, migration, permission or import. Historical pregame eligibility stays unavailable. Task 024 is a separate frontend approval after that API is reviewed and tested.
