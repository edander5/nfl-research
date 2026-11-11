# Task 013 — NFL team rankings dashboard

Approved branch: `feature/team-rankings-dashboard`. Owner reports Task 012 rankings API merged and verified, with 705 accepted pairs / 1,410 statistics rows in development. Task 013 adds only frontend views and documentation. It does not repeat backend setup, change contracts or touch database data/permissions.

## Routes and interaction

- `/rankings` is available through **Team rankings** in workspace navigation. The existing home/current-week schedule and matchup routes remain intact.
- `/rankings?season=2025&season_type=POST&category=passing_defense` deep-links a ranking selection.
- `/teams/{canonical_uuid}/research` provides the lightweight team game-log view, since the application had no existing team detail route. Links preserve season, stage, category and display sorting; **Back to team rankings** restores the prior selection. Workspace ranking navigation also preserves the active research selection.

Supported URL parameters: `season=2024|2025|2026`, `season_type=REG|POST|COMBINED`, one of the API's four category names, `sort=api|rank|team|average|total|games`, and `dir=asc|desc`. Defaults are latest supported season **2026**, **REG**, **passing_offense**, and **API order**. This is a supported-season default, not a calculation of live season eligibility. Filter changes write the explicit selection to the URL; defaults are also valid on the bare `/rankings` route. Browser back/forward and bookmarks preserve explicit selections. Unsupported values and duplicate parameters show a reset state without issuing an API request. Sorting parameters are local presentation state and never sent to the backend.

Season/stage controls preserve the selected category. Category switches preserve season/stage and display sorting. All ranking rows supplied for that category are displayed, including explicitly unranked zero-value-count teams. There is no overall rank or client-side minimum-game threshold.

## Data and correctness

The typed research client matches the actual [Task 012 rankings schema](team-rankings-api.md) and [Task 011 game-log schema](team-stats-api.md):

- Rankings: `GET /api/team-rankings?season=...&season_type=...&category=...`.
- Team research: `GET /api/teams/{uuid}/games?season=...&season_type=REG|POST&limit=20&offset=...`.

The rankings table starts in the exact API row order. Team/rank/average/total/contributing-game sorting operates on a copied list and never recalculates ranks, rewrites competition ties or treats null as zero. Null numeric values remain last in either numeric sort direction. API order can be restored explicitly. Average display rounds to one decimal only; official ranks remain those calculated from unrounded backend ratios. A dash means unavailable. Zero and negative values remain visible.

Category cards explain highest-first offense versus lowest-allowed-first defense. Passing labels explicitly say NET, and game logs preserve gross passing and original signed sacks separately. Coverage uses the real API metadata and per-row missing-statistics/missing-metric counts. **Stored schedule covered** is distinct from finality, external completeness and source freshness. Partial/current-season coverage and zero-game populations remain visible; teams without a metric sample remain unranked rather than disappearing or receiving arbitrary last-place numbers.

The compact team view shows accepted team/opponent games, kickoff information, NET/gross/sacks/rushing/allowed yards and nullable reported scores. COMBINED triggers two independent REG and POST requests, displayed in separate labeled sections, because the existing game-log API does not support a combined stage. It does not calculate another season summary or rank. Each stage handles its own loading/error/empty state and supports a 20-record page with previous/next controls when needed. Changing season/stage/team resets the relevant page. Source references are projected from the existing public provenance fields; paths/private ingestion evidence are not displayed.

A FINAL label requires both the API's stored FINAL status and CONFIRMED_FINAL score finality. UNKNOWN and scores are not used as completion evidence. No actual completion timestamp or historical pregame eligibility is inferred. Persistent context labels these as reconstructed season statistics and includes nflverse/nflfastR attribution and the approved CC BY 4.0 link. Declared-origin and original schedule checksum limitations remain disclosed.

## Cache, freshness and failure behavior

TanStack Query keys include every request filter: rankings season/stage/category, and game-log canonical team/season/stage/offset. Requests receive abort signals. Cache stale time is one minute; explicit refresh is available, no polling or new background job is introduced. Window-focus refetch is disabled for these views. Switching to a new uncached filter shows its loading state rather than displaying old-filter ranks. A failed refresh retains the cached records with a visible error and retry action.

Rankings metadata may show the browser's last load time; it is explicitly **not source publication/update time**. No schedule-refresh timestamp is reused as a claim about statistics freshness. If a statistics dataset timestamp becomes available through a future approved API contract it can be added later; none is invented here.

Network/HTTP failures use bounded messages and do not display backend bodies. Invalid bookmarks, unavailable teams, empty league populations, all-unranked populations and missing game logs have usable states. Source links pass through the existing safe URL helper.

## Layout and accessibility

The interface follows the existing forest-green/off-white palette, typography, cards, spacing and shared state conventions. Four category links provide the main research navigation; a compact coverage strip precedes a semantic statistical table. Desktop shows the full table. Narrow layouts wrap filters/category cards and horizontally scroll the table inside a labeled keyboard-focusable region, preserving access to every column. Mobile navigation keeps visible text labels. Column sort buttons expose `aria-sort`; team names link to research; captions explain sorting/null semantics. No chart, logo asset, frontend package, backend endpoint or infrastructure was added. Native HTML tables suit the bounded league population without introducing a new table dependency.

## Validation commands

Use the existing installed approved dependencies from repository root:

```bash
cd frontend
npm run typecheck
npm test
npm run test:client
npm run build
```

There is **no configured lint script or lint dependency** in this project. No lint pass is claimed and none was installed. TypeScript, Vitest, the existing dependency-free client smoke checks and the Vite production build are the available checks. If local dependencies are missing in WSL, use the existing committed lockfile with `npm ci` first; this task did not install or change dependencies/lockfiles.

For owner-run live integration with the existing development services:

```bash
# From repository root, normal WSL. No admin override, imports or grants.
docker compose up -d --build --wait api frontend
curl --fail 'http://127.0.0.1:8000/api/team-rankings?season=2026&season_type=REG&category=passing_offense'
curl --fail 'http://127.0.0.1:5173/api/team-rankings?season=2025&season_type=POST&category=passing_defense'
```

Open `http://127.0.0.1:5173/rankings` and validate:

1. Switch 2024/2025/2026 and REG/POST/COMBINED; compare requests and rows with the existing API. Confirm no unavailable team/game values were fabricated.
2. Switch all four categories; inspect offensive versus defensive labels and competition ties. Sort each numeric column both ways; ranks must not change, nulls must remain distinct from zero, and **Restore API order** must restore backend order.
3. Open a team and return. The URL's season/stage/category/sort must survive. COMBINED must show separately labeled REG/POST game logs and no unsupported combined API request.
4. Inspect partial coverage, zero-game/unranked rows, source references, UNKNOWN status and reported zero/missing scores. A complete stored-schedule flag must not be interpreted as FINAL or source freshness.
5. Test a 375px viewport and keyboard-only navigation: readable mobile navigation, focusable table scroll regions, all columns reachable, visible focus and accessible sort controls. Test desktop spacing and category/filter layout. Use browser back/forward and reload deep links.
6. Simulate offline/503 behavior, retry and failed manual refresh. Existing schedule, current-week default, freshness indicator and matchup navigation must continue working.

No browser executable was found in the agent environment. JSDOM checks validate markup and interactions, including narrow-viewport accessible controls, but do **not** prove browser geometry, contrast measurements, screenshots or live proxy/database integration. These remain owner-run checks; no live-data rendering was claimed here.

## Complete changed-file inventory

- `frontend/src/App.tsx`: rankings/team routes, workspace navigation/current section and general source footer.
- `frontend/src/styles.css`: responsive category controls, coverage/table/team-log layouts, keyboard scroll regions and mobile navigation labels.
- New `frontend/src/api/research.ts`: typed actual rankings/game-log response schemas, read-only client and bounded errors.
- New `frontend/src/rankings/state.ts`: validated URL state, paths, immutable presentation sorting and formatting.
- New `frontend/src/components/ResearchShared.tsx`: season/stage controls, errors and source/statistical context.
- New `frontend/src/pages/Rankings.tsx`: API-backed rankings dashboard and display sorting.
- New `frontend/src/pages/TeamResearch.tsx`: lightweight accepted game logs, stage separation, pagination and source references.
- New `frontend/src/test/rankings.test.tsx`: synthetic API integration, filters, history/navigation, order/ties/sorting, coverage/nulls, loading/retry/stale/error/empty states and accessibility tests.
- New `docs/team-rankings-dashboard.md`: behavior, correctness, commands, inventory and validation evidence.
- `AGENTS.md`, `README.md`, `docs/architecture.md`, `docs/implementation-plan.md`, `docs/decisions.md`: approved scope/current frontend behavior and implementation rationale.

No backend files, API contracts, database/schema/migrations/permissions, sources, statistics/schedule data, package manifests/lockfiles or deployment configuration changed. No commit, merge, push or deployment occurred.

## Executed results and review gate

Final command results are recorded below. The owner-reported Task 012 acceptance is the backend baseline, not an independent agent live-data verification. Proposed next task, for separate approval: review normal-WSL browser/live integration results and any necessary visual corrections. No historical pregame-ranking, full matchup research, player/odds or ingestion work is implied.

Executed agent validation:

| Check | Result |
|---|---|
| `npm run typecheck` | Passed |
| `npm test` | **84 passed across 4 files**, including 18 new rankings/research tests and the existing schedule/current-week/freshness regressions |
| `npm run build` | Passed; TypeScript and Vite production output generated successfully |
| `npm run test:client` | **Failed in the existing optional smoke script**: Node v26.13.0 cannot resolve the extensionless `./freshness` import in the unchanged `src/api/client.ts` (`ERR_MODULE_NOT_FOUND`). The same import is present in HEAD. No pass is claimed; this standalone Node module-resolution issue was left outside the rankings changes. Vite/Vitest resolve it and their checks passed |
| Lint | Not run: no configured lint script/dependency exists |
| `git diff --check` | Passed |
| Docker server probe | Permission denied on the Docker socket; no live container/database requests executed |
| Real browser/mobile geometry | Not executed; no browser executable available. Narrow-viewport DOM/accessibility checks passed in JSDOM only |

No dependencies were installed. The table above distinguishes successful checks from the known failed or unavailable checks.

**Review recommendation:** frontend implementation is ready for owner review. Complete the live WSL/proxy/browser smoke checks before merge. The optional pre-existing Node smoke-script failure remains documented for a separately scoped correction; it was not silently fixed or counted as a pass. Stop at this review gate; no commit or merge is authorized.
