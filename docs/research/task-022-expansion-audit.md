# Task 022 — NFL research expansion audit

This is the Task 022 historical snapshot. Tasks 023/024 have since implemented
recent team trends and their Game Preview UI. For the current source-verified
inventory, seven-tab research comparison and revised game-first sequence, see
[Task 025 gap analysis](task-025-frontend-gap-analysis.md) and
[updated roadmap](task-025-game-research-roadmap.md).

Audit date: 2026-11-17. Scope: repository inspection, independent public-source research and documentation only. No feature implementation is authorized by this report. Task 022 supersedes earlier task exclusions only for this audit; all future work below requires approval. The Buckets to Bucks report is feature evidence, never a data feed, specification or permission to copy code.

## Reading map and evidence labels

- [Feature inventory and implementation evidence](#verified-feature-inventory) below.
- [Independent source feasibility](task-022-data-sources.md).
- [Phased tasks and recommended Task 023](task-022-roadmap.md).
- [Targeted REA backlog](task-022-rea-followups.md).
- Starting reference: [existing technical report](bucketstobucks-technical-report.md), sections 1–6 and its confidence definitions.

**R** = verified source code/test inspection in this working tree. **T** = tests executed during this audit (results below). **H** = historical documentation/owner report, not a newly inspected database. **E** = external documentation/listing checked on the audit date; not authenticated production coverage. **P** = proposed design awaiting approval.

Existing uncommitted dark-mode work, README/AGENTS/decision changes and the research directory were present before the audit. They are included in current-tree findings; their presence does not establish merge/deployment status. No live database was queried. Counts such as 842 games and 705 accepted pairs/1,410 team rows are **H**, not current verified counts.

Read: AGENTS, README, PRD, architecture, decisions, implementation plan, data model/source feasibility; schedule/API/refresh/freshness, team-statistics validation/storage/security/API/rankings/refresh, scheduler, Game Preview/markets/logs/presentation, updater and dark-mode guides. Inspected actual model/migration, repository/service/schema/API, ingestion, CLI, frontend and test implementations. No second REA investigation or captured-data analysis was performed.

## Verified feature inventory

Status means implementation against its **limited existing contract**, not full PRD completion. “Implemented/tested” does not certify PostgreSQL runtime, source completeness or rendered browser acceptance.

| Feature | Current status (R unless stated) | Reusable implementation / tests | Missing capability; data and dependency | Priority |
|---|---|---|---|---|
| League Schedule | Implemented/tested: imported seasons 2024–2026, explicit REG/POST/week/round, deep links, current-week default, null kickoffs, UNKNOWN/reported-score labels | `frontend/src/pages/Schedule*.tsx`, `schedule/defaultSelection.ts`; `backend/app/api/schedule.py`, schedule repository/service/schemas; `test_schedule_*`, dashboard/defaultSelection tests | No proof of current DB coverage or authoritative live/final status. New seasons exceed explicit model/API bounds; separate task, not just a selector | Preserve |
| Game Preview | Implemented/tested bounded page: summary/provenance, markets, paired offense/opponent defense, two logs | `pages/Matchup.tsx`, `components/MatchupComparison.tsx`, `matchup.test.tsx` | Enhanced recent comparisons absent. Historical pregame reconstruction blocked by eligibility evidence | Phase 1 |
| Four rankings | Implemented/tested: NET pass/rush offense descending, opponent allowed ascending; exact Fraction competition ties; null-ranked no-value teams; full population before filtering | `repositories/team_rankings.py`, `services/team_rankings.py`, `schemas/team_rankings.py`, `test_team_rankings.py`; `pages/Rankings.tsx`, `rankings/state.ts`, rankings tests | Current accepted season only; no recent-window rankings, player-position ranks, EPA/success-rate ranks or pregame cutoff. Never replace NET with player gross passing | Preserve / Phase 1 |
| Season summaries | Implemented/tested backend; standalone team UI primarily displays logs | `GET /api/teams/{uuid}/stats`; `TeamStatsService.summary`, per-metric SQL count/sum/avg; `test_team_stats_api.py` | No recent L3/L5/L10 service/UI. Nulls and accepted coverage need window-specific denominators | Phase 1 |
| Team game logs | Implemented/tested in team research and preview | `GET /api/teams/{uuid}/games`, `GET /api/games/{uuid}/team-stats`; `TeamResearch.tsx`, `PreviewTeamLogs.tsx`, `gameLogs/presentation.ts`, previewLogs tests | Team route pages 20 rows; preview loads all season pages then sorts, displays five/card. No advanced filters/window summaries/charts | Phase 1 |
| Historical spread/total comparisons | Partial: backend provisional WIN/LOSS/PUSH/UNDETERMINED against stored reported score; preview logs display them | `services/markets.py`, market schemas/API, `BettingMarkets.tsx`, market tests; `referenceFor` rejects mismatched IDs/scores | No aggregate ATS/O/U histories, manual controls or verified settlement; unknown book/time means these cannot become certified closing-line results | Phase 1 |
| Game markets | Partial: source-reference spread, moneyline, total and prices from hash/identity-checked schedule raw record | `GET /api/games/{uuid}/markets`; Decimal arithmetic, provenance/hash fields | No live offers, bookmaker comparison, normalized offer tables or observation series. Artifact retrieval != quote time | Phase 1 manual; optional later offers |
| NFL Data Updater CLI | Implemented/tested orchestration: Bash readiness launcher, Python sequential independent schedule/stats reviews, default-no y/yes, guarded original applies, private internal tokens/stdin, read-only verification, indeterminate stops | `scripts/update-nfl-data.sh`, `ingestion/update_cli.py`, `tests/test_update_cli.py` | Only schedule/team stats; no player pipeline. Synthetic tests don't prove real Docker/update runtime; no real invocation in audit | Preserve; Phase 2 extension only after review |
| Refresh/scheduler | Implemented/tested prepare-only source acquisition/validation/diff/archive; opt-in daily scheduler, existing locks and state | `ingestion/refresh*.py`, `team_stats/refresh.py`, `scheduler.py`, refresh/scheduler tests | No evidence scheduler currently enabled; no auto import permitted. Website freshness projection is schedule only | Preserve |
| Physical storage / provenance | Implemented model + migrations 0001/0002: teams, aliases, games, source artifacts; batches, pair revisions, two team revisions/pair, accepted pointers, selection events | `models/schedule.py`, `models/team_stats.py`, `alembic/versions/`, role allowlists and security tests | Player/roster/offer/injury/weather tables in conceptual docs are absent. Team accepted columns store gross/signed sacks/NET/rush only; retained raw JSON is not an approved EPA API | Phase 2 |
| Player identities, season rosters, player statistics/API | Planned in PRD/data model; no physical model, migration, pipeline, endpoint, client or page | Team/game UUID and alias patterns, artifact evidence and accepted revision conventions | Stable mappings, participation eligibility, stats validation, correction storage and restricted grants all needed | Phase 2 |
| Player profiles/logs/window stats/thresholds/charts | Planned, entirely unimplemented | Query/Router/shared UI and backend layer patterns | Needs player foundation, approved denominators/market mappings, bounded APIs, chart dependency approval | Phase 3 |
| Prop discovery/search/advanced filters | Planned player-first/market-first UX; no player discovery implementation | Existing URL filters, native sortable team table and Query keys | Needs Phase 3 summaries, search/pagination, market/position filters; sportsbook not prerequisite | Phase 4 |
| Defense versus position / usage | Missing implementation; broad opponent-context ambition only | Existing defense rank engine supplies team yardage context only | Requires player-game totals, historical position, complete opponent-game samples, shares denominator policy; snaps separate | Phase 4 |
| Injuries/full depth charts | Planned, no code/schema/API/UI | Independent section requests and provenance patterns | Source/current coverage, all units, IDs, timestamp/schema versions, snapshot semantics | Phase 5 |
| Weather | Missing implementation | Schedule kickoff/teams, optional raw references may inform feasibility but no validated weather contract | Venue/coordinates/roof, actual game location and independently sourced forecast/archive; no fabricated roof status | Phase 5 |
| Sportsbook comparison / movement | Planned odds context; movement is a new expansion proposal | Reference-market UI can supply visual conventions only | Authorized provider, quota manager, exact line/book/side matching, immutable observations; no free historical backfill verified | Phase 4 optional / Phase 5 |
| Dark mode/shared UI | Implemented/tested in current tree: Light/Dark/System, localStorage, head script, OS/cross-tab updates, CSS tokens | `theme/ThemeToggle.tsx`, `public/theme.js`, `index.html`, `styles.css`, theme tests; shared loading/error/provenance/Card components | Browser first-paint/mobile/visual acceptance still pending. New tables/charts must use theme tokens and accessible labels | Preserve throughout |
| Recharts / TanStack Table | Planned stack choices, **not installed or imported** | `frontend/package.json` has React/Router/Query; current tables are native semantic HTML; Card is local shadcn-style primitive | Approve/install only in a task that needs them; no wholesale frontend rewrite, no R runtime/SDK required for CSV | Phase 3 / Phase 4 if justified |

### Actual read-only API surface

`backend/app/main.py` registers health/readiness, schedule, freshness, team stats, rankings and markets routers. Research endpoints are:

- `GET /api/seasons`, `/api/seasons/{season}/schedule`, `/api/games/{game_id}`.
- `GET /api/data-status/schedule` (sanitized operational checkpoint, not source publication).
- `GET /api/teams/{team_id}/games`, `/api/teams/{team_id}/stats`, `/api/games/{game_id}/team-stats`.
- `GET /api/team-rankings`, `/api/games/{game_id}/markets`.

There is no player, injury, depth-chart, weather or sportsbook-provider router. Architecture route examples are future illustrations. Frontend routes are `/`, `/schedule/:season/:stage/:selection`, `/games/:gameId`, `/rankings`, `/teams/:teamId/research`. There is no `/players` route.

### Reuse and limits that affect design

Accepted-stat queries join reciprocal opponents within the same pair revision; allowed yards must keep that identity. Per-metric non-null counts, signed sack definition and exact ranking ties already solve difficult semantics. New recent aggregates should reuse those projections and avoid private raw-record access/grant expansion.

Existing log pagination counts and page share a SQL statement snapshot, but multiple frontend page requests do not share a database snapshot. Preview detects changed counts/duplicate IDs but not every same-count correction between pages. A bounded backend recent-summary query reduces that risk. Visible preview rows currently issue at most ten market requests, sharing Query cache; do not extend this per-row fanout to discovery tables.

Historical pregame eligibility is **not implemented**: earlier kickoff alone does not prove earlier completion; accepted statistics, reported scores, revision time and download time do not establish it. A current-season upcoming-game view can show explicitly labeled current accepted data without claiming an as-of pregame snapshot. True historical pregame results require an approved evidence contract and future task.

## REA feature crosswalk

Observed/derived below mean **reported by the supplied REA report**, not independently rerun during Task 022. Its evidence bundle links are not present in this checkout; only the report was supplied. This limits re-verification and does not block original product design.

| Feature | Directly observed in report | Derived / inferred | Unverified | Our equivalent and independent requirement |
|---|---|---|---|---|
| Schedule / matchup navigation | Week 11 selection changed schedule and visible prop rows; player row navigation succeeded (§§1–2) | Week/event context scopes research | Dedicated game-research page behavior and full schedule coverage | Schedule/preview already exist; extend their own contracts, no target endpoints |
| Team trends/rankings | Ranking/support requests and average/rank/sample fields (§3) | Shared all-team rank map explains bounded opponent lookups | Exact ranking populations, recent windows, completion rules | Four own season rankings exist; add independently specified recent summaries |
| Prop discovery | Table with player/market/line/books/time/defense/window rates; 100 rows plus load-more (§4) | Local filtering/sorting and column/preset storage identified in shipped script | Load-more action, all markets, preset sync, end-to-end sort correctness | Absent; typed own paginated table over accepted stats and optional permitted offers |
| Search/filter/side | Jahmyr search narrowed rows; Under then Over changed displayed values (§2) | Search/market/odds/rate filters and sorting appear local (§4) | All combinations, reset semantics and integer-push complement handling | Only team sorting/URL controls reusable; own null-safe filters and explicit pushes |
| Player logs / identity | Three season requests, identity/availability envelopes, nullable stats (§3) | Provider IDs imply identity resolution, not contract proof | Full transfer/DNP/zero/duplicate handling | Absent; canonical IDs, validated mappings and actual team per game |
| L5/L10/season/H2H | Controls and table rates visible; sampled ten-row log/average (§§4–5) | Offline L10 spans 2026/2025; sampled 9/10 over 0.5 and mean match | L5 click was blocked; universality/eligibility of all windows and H2H | Absent; PRD defaults within selected season/stage. Cross-season only explicit separately approved option |
| Adjustable lines/charts | Chart, line/side controls and secondary selector exposed in accessibility tree (§5) | Shipped chart code accepts custom line, uses Recharts, initializes L10 | Successful line/tooltip/secondary-series/click/reset interactions behind paywall | Absent; own accessible chart + matching table/manual finite Decimal line contract |
| DvP / opponent rank | Comparison/rankings/history/completeness responses; requests across stat/position (§§2–3) | All-team map could avoid per-row calls | Denominator, position history, ties and display mapping | Team defense exists, DvP absent; aggregate own opponent player outputs per defense-game-position |
| Usage / opportunity | Opportunity rows/shares; target/rush-share and formations/lanes/zones in accessible content (§§3,5) | Useful supplemental matchup views | Route participation, share denominators, zone geometry/coverage and control behavior | Absent; counts/shares first; routes/zones only with independently validated granular data |
| Injuries / depth | Injury requests appeared (§2) | Supporting player availability context likely | Full depth-chart functionality and report freshness/coverage not established | Both absent; source audit then independently designed current-state sections |
| Weather / news | Supporting weather/news requests (§2) | Context sections likely | Display, forecast origin/time, completeness and historical accuracy | Absent; weather adapter/venue mapping; licensed news not core expansion dependency |
| Book comparisons / probability | Multiple book prices; sampled displayed probability and under price changed (§4) | Numeric example consistent with odds-implied probability; selection rule hypothesis only | Best-price rule, coherent probability model, settlement rules | Source references only; compare identical lines/sides/books, label implied probability separately from hit rate |
| Historical lines / movement | Response rows with line/method/observedAt/startsAt (§3); lines in logs (§5) | Could support historical reference context | Opening/closing provenance and a genuine time-series movement UI not established | No odds series; timestamped independent observations needed; artifact versions cannot substitute |

Do not replicate five-minute polling, bulk multi-megabyte payloads, complementary under rates or cross-season L10 merely because target code suggests them. Independent acceptance criteria and our PRD control behavior. No signed links, target assets, code or captured response datasets enter production.

## Verification record

Frontend `npm --prefix frontend test`: **142 passed, eight files**; `npm --prefix frontend run typecheck`: **passed**. Tests use synthetic responses. Theme tests execute the actual startup script and check head order/contrast tokens; they do not measure a browser's rendered first paint.

Backend verification outcomes are recorded in the final audit validation entry below. Database tests are explicitly disabled: their fixtures provision roles/run Alembic and therefore must not run in this planning task. No containers, application services, imports or database commands were invoked. No dependencies were installed. A broad non-database attempt was interrupted after stalling; it is not a passing suite. Transport/runtime acceptance must remain separate from pure calculation tests.

| Audit command (backend commands run from `backend/`) | Actual result |
|---|---|
| `RUN_DATABASE_TESTS=0 ../.venv/bin/pytest -q -m 'not database'` | Stalled after progress output; interrupted, exit 130. No passing-suite claim; exact blocked test/root cause not established |
| `RUN_DATABASE_TESTS=0 timeout 60 ../.venv/bin/pytest -q -m 'not api and not database'` | Timed out, exit 124. Marker exclusion did not make the whole suite complete |
| `RUN_DATABASE_TESTS=0 timeout 45 ../.venv/bin/pytest -q tests/test_team_rankings.py tests/test_markets.py tests/test_update_cli.py -m 'not api and not database'` | **139 passed, 7 deselected**, 3.38s, one existing Starlette/httpx deprecation warning. Includes pure calculations, async HTTP error validation and synthetic guarded CLI tests; excludes marked TestClient success and PostgreSQL cases |
| `npm --prefix frontend test` | **142 passed / 8 files**, 3.54s |
| `npm --prefix frontend run typecheck` | Passed |

Shell startup emitted read-only envman configuration warnings on the first backend run; subsequent commands used a non-login shell. No permission/system configuration changes were made. No broad reruns or dependency changes were attempted after the focused checks passed. Existing source tests were used; this documentation-only task adds no tests.

Final documentation checks: `git diff --check` passed; all relative inline file links in the four new Task 022 documents resolved. External sources were reviewed through the public web tool, with failed body/dictionary requests recorded in the source matrix. Application changes shown by git status predate this audit; this task changed documentation only.

## Documentation drift and remaining blockers

README, architecture, data-model and the original implementation plan retain chronological “current Task 010/no statistics endpoint” statements that later appendices supersede. This audit supplies a dated verified inventory and navigation pointers without rewriting historical acceptance reports. Task 018 has no verified implementation artifact; numbering does not imply completion. Existing planned Caddy/Tailscale, backups, production scheduling and deployment cannot be inferred from architecture prose.

Main gates: completion-before-cutoff evidence; appearance versus DNP (including special teams); mapping transfers and snap IDs; player dataset actual bytes/coverage; source-specific permissions; injury/depth currentness; optional sportsbook key/market coverage and quotas; browser visual checks; isolated PostgreSQL runtime acceptance. None prevents the proposed bounded current-accepted team-trend task. Proposed statistical/window definitions require owner approval with that task.
