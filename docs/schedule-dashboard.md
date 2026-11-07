# React schedule dashboard — Task 006

## Scope, architecture and contract alignment

Approved scope: [Task 006](agent-task-006.md). Branch `feature/schedule-dashboard`. The owner reports the prior backend/API work merged to main and validated with **139 passing tests/two deprecation warnings**, 842 imported games and unchanged reimport. That is prior **user-reported** evidence; it does not verify this new frontend.

No existing frontend scaffold was present. The new `frontend/` follows the approved React/TypeScript/Vite, React Router, TanStack Query, Tailwind and shadcn stack. Native accessible selection/buttons/links cover the small filter surface; locally adapted shadcn Card primitives supply reusable panels without introducing a full component runtime. Required test tools are Vitest, React Testing Library and jsdom, as anticipated by the architecture. No charts/table libraries are installed for this schedule-only slice. Source notices for shadcn's MIT component are retained.

No API/schema/ingestion conflict was found. `src/api/types.ts` manually mirrors the actual Pydantic response fields in `backend/app/schemas/schedule.py`; the UI uses only the three existing GET routes. This is compile-time typing, not automatic runtime schema validation or generated types; future API changes must keep it synchronized. HTTP errors, unexpected content types and malformed JSON reject requests into query error states. No fallback fixture data is bundled by application imports.

The interface uses a forest sidebar, neutral panels, responsive matchup cards and explicit away/home score rows. It supports 1/2/3/4 card columns across phone/tablet/desktop widths, horizontal week navigation, keyboard focus, semantic labels/status/alerts, a skip link and reduced-motion styling. Visual/browser/accessibility behavior has not been independently exercised here because frontend installation is blocked; these are implemented layouts, not a claim of browser acceptance.

## Routes and behavior

- `/` fetches available seasons and redirects to week 1 REG of the newest returned season. It does **not** guess a current NFL week from the clock.
- `/schedule/:season/REG/:week` supports weeks 1–18; `/schedule/:season/POST/:round` supports WC/DIV/CON/SB, with `all` representing the whole POST stage.
- Available seasons come from `GET /api/seasons`. Only returned seasons are selectable. POST controls/rounds use API coverage; missing POST remains disclosed and normally disabled. A direct missing-POST link shows a real empty state, never invented matchups or scores.
- Schedule requests use `/api/seasons/{season}/schedule?season_type=REG&week=…` or `season_type=POST&round=…`; `POST/all` omits week/round. There is no combined-stage query.
- `/games/:gameId` requests the existing internal UUID endpoint. Card links preserve the schedule path in `returnTo`; validated local schedule paths restore the selected week, including after refreshing a detail link. External/arbitrary return destinations are ignored. A direct detail link falls back to the game's actual season/stage/week or round.
- Invalid filter routes, malformed UUIDs, unavailable seasons, unknown pages and missing games have explicit navigation/error states. A valid empty API response has its own empty state.

The API's game order is preserved; the frontend does not reorder null kickoffs or infer source completeness. Kickoffs are formatted explicitly in America/New_York, showing EST/EDT. Unknown kickoff stays unknown; source date alone is not promoted to a timestamp. Missing scores are an em dash, labeled not reported; zero remains zero. UNKNOWN stays visible even for past games with scores. FINAL labels require stored FINAL, CONFIRMED_FINAL and a final-evidence object; the browser does not verify the evidence externally or infer status from time/scores.

Detail shows designated teams, scores, status, available UTC/Eastern kickoff, nullable venue/overtime, artifact origin/observation/retrieval metadata, source ID, attribution/license and artifact digest. It distinguishes DECLARED origin from recorded verified origin. Policy disclosures retain the original checksum uncertainty and unsupported operational status limitations. External evidence/source URLs accept HTTP(S) only and open separately with `noreferrer`. No fabricated team full names/logos are introduced; source abbreviations are returned as stored.

TanStack Query caches are keyed by available-seasons, complete season/stage/selection, or game UUID. Production UI configuration uses a 60-second stale window, no automatic retry loop, request cancellation on navigation and normal Query focus/reconnect refresh. This is cache behavior, not source-freshness certification. Manual retry/refresh is provided. On refresh failure, previously loaded matching-query data stays visible with a clear warning; initial failures do not masquerade as empty schedules. Different filter keys never share previous games as placeholder data.

## Development network and containers

Vite calls `/api` on its own origin and proxies requests to FastAPI. In Compose, `API_PROXY_TARGET=http://api:8000`; local Vite defaults to `http://127.0.0.1:8000`. This server-side configuration has no database credentials and is not a browser database connection. No backend CORS/API changes are needed.

Compose adds only `frontend`, on the existing default network, with host **127.0.0.1:5173**. It waits for API health and runs as the image's non-root `node` user. The database remains internal with no host port. The existing API remains at 127.0.0.1:8000. Local `npm run dev` binds loopback; only the container command binds 0.0.0.0 internally. No public ingress, Caddy/Tailscale deployment, authentication or security-setting changes were made. This Vite service is development tooling, not a production hosting solution.

The image copies frontend source and installs dependencies; no source bind mount or shared node_modules volume is added. Rebuild after changes. It uses `npm ci` when a lockfile is supplied, otherwise initial `npm install`. A lockfile could not be generated here because registry DNS fails. The first successful normal-WSL installation must generate/review `frontend/package-lock.json`, run the checks below, then rebuild so the image uses that lock. Do not fabricate a lockfile or treat current package ranges/image tags as fully reproducible. No dependency is downloaded from an unverified mirror.

## Exact normal WSL checks

From repository root, with the existing `.env` intact, use Node **22.12+** and npm. Do not overwrite `.env`, print credentials, run ingestion, reset volumes or execute development migrations for this task.

```bash
git branch --show-current
node --version
npm --version
cd frontend
npm install
npm run typecheck
npm test
npm run build
npm run test:client
cd ..
docker compose config --quiet
docker compose --profile test run --build --rm tests
docker compose --profile test stop db_test
docker compose up -d --build --wait db api frontend
```

Expected branch `feature/schedule-dashboard`. `npm install` creates node_modules and the missing lockfile from the trusted npm registry. If it fails, stop and capture sanitized error output; diagnose DNS/network or version conflicts without repeatedly retrying or adding packages to hide the error. `typecheck` must exit zero; Vitest currently has **23 authored cases**; the production build should create `frontend/dist/index.html` and bundled assets. The dependency-free client smoke checks must also pass. None of these expected outputs are claimed as executed success here except the client smoke checks.

Backend suite should still pass its existing 139 cases (not skip database tests); it uses isolated `nfl_research_test` via the established fixture, not development data. Frontend request integration must use the already populated development DB. On Compose errors, inspect `docker compose logs frontend api` without pasting secrets. A proxy 503/network failure should show the retry UI, not trigger reingestion. If a rebuilt image has stale code, confirm the build succeeded before editing unrelated settings.

Verify frontend HTML, deep links and proxy access:

```bash
curl --fail-with-body -sS http://127.0.0.1:5173/ > /tmp/nfl-dashboard.html
curl --fail-with-body -sS http://127.0.0.1:5173/schedule/2026/REG/9 > /tmp/nfl-dashboard-deep-link.html
curl --fail-with-body -sS http://127.0.0.1:5173/api/seasons
curl --fail-with-body -sS 'http://127.0.0.1:5173/api/seasons/2026/schedule?season_type=REG&week=9'
curl --fail-with-body -sS 'http://127.0.0.1:5173/api/seasons/2026/schedule?season_type=POST'
```

Expected original-snapshot availability: 2024 272 REG/13 POST; 2025 272 REG/13 POST; 2026 272 REG/0 POST. The latter POST request returns 200/empty `data`, without invented games. Later approved imports may legitimately change scores or coverage; inspect provenance rather than changing valid records to satisfy an old expectation.

Open **http://127.0.0.1:5173** in a browser. Check season changes, all week links, historical POST rounds, missing 2026 POST explanation, card/detail/back navigation, direct detail refresh, visible UNKNOWN/reported-score labels and provenance disclosure. Check 375px phone, tablet and desktop layouts, keyboard focus and overflow. Refresh requests in browser Network should target `/api`, with correct stage/week/round and canonical UUID. No PostgreSQL URL or credentials should be present. The UI should show readable errors when requests fail and label retained records on refresh failure. Browser checks remain mandatory; curl HTML/proxy checks alone do not validate React rendering.

For a locally running frontend against Compose API instead of the frontend container:

```bash
docker compose up -d --wait db api
cd frontend
npm run dev
```

Visit the same loopback 5173 address; stop the container frontend first if it already occupies that port. Vite uses strictPort and will report the conflict instead of silently selecting another port. No package or service installation outside the approved project dependencies is required by these instructions.

## Actual agent validation

- Single `npm install --prefix frontend --cache /tmp/nfl-dashboard-npm-cache --fetch-retries=0 --fetch-timeout=10000 --no-audit --no-fund` attempt failed **EAI_AGAIN** resolving registry.npmjs.org. `getent hosts registry.npmjs.org` also produced no resolution. No repeated download or mirror substitution. No node_modules/lockfile exists.
- `npm --prefix frontend run typecheck`, `run build`, and `test` were attempted and **could not run**: shell reports `tsc`/`vitest` permission denied; required local executables are unavailable after installation failed. This is not a successful compilation, build, test collection or assertion run.
- `node --experimental-strip-types frontend/scripts/client-smoke.mjs`: **passed** with existing Node 26.13.0. These dependency-free checks exercise actual client URL/round encoding, AbortSignal propagation, HTTP/content-type errors, Eastern DST formatting, null kickoff, unsafe URL rejection and selection validation. They do not compile/render TSX or validate React dependencies.
- Compose configuration and diff whitespace checks passed. Docker daemon socket access remains denied; no container startup, browser inspection or real frontend-to-development-API request was executed.
- Backend regression subsets: `.venv/bin/python -m pytest backend/tests/test_schedule_service.py backend/tests/test_settings.py backend/tests/test_ingestion.py backend/tests/test_schedule_database.py -q -ra` → **55 passed, 48 skipped** (isolated PostgreSQL unavailable). `.venv/bin/python -m pytest backend/tests/test_schedule_api.py -k 'invalid_request or read_only or async_error_handler_transport' -q -ra` → **23 passed, 10 deselected, one deprecation warning**. These are disjoint selected checks, not a full 139-test run; remaining synchronous HTTP/database cases were not run here. Prior owner-reported 139-pass/two-warning result is separate evidence and predates the frontend.

No TypeScript/production-build/Vitest/browser success is claimed. No production data, schema, ingestion, API contracts, deployment or git commits/merges/pushes were changed.

## Sources and unresolved checks

Official implementation references checked 2026-11-07: [Vite guide](https://vite.dev/guide/), [Tailwind Vite integration](https://tailwindcss.com/docs/installation/using-vite), [React Router declarative setup](https://reactrouter.com/start/declarative/installation), [Vitest 3 guide](https://v3.vitest.dev/guide/), [Vitest 3.2.4 manifest with Vite 7 compatibility](https://github.com/vitest-dev/vitest/blob/v3.2.4/packages/vitest/package.json), [shadcn Card source](https://github.com/shadcn-ui/ui/blob/main/apps/v4/registry/new-york-v4/ui/card.tsx), [MIT license](https://github.com/shadcn-ui/ui/blob/main/LICENSE.md). Package resolution/build compatibility remains unverified until npm succeeds. These setup references do not verify NFL data; the existing [schedule API](schedule-api.md) and [data contract](schedule-data-contract.md) govern that.

Remaining risks: unresolved dependency resolution/lockfile, unexecuted TypeScript/build/RTL and browser checks, no production serving/deployment configuration, API source checksum/finality limitations, and manually maintained API types. Do not mark Milestone 1 end-to-end accepted based on code presence alone.

Next proposed task **for owner approval**, after these WSL checks and review: a focused Milestone 1 browser smoke/accessibility/acceptance pass, including deep links, phone/desktop layouts and real imported data. Do not begin rankings/statistics or deployment automatically. Stop for review.

## Complete changed-file inventory

The inventory below includes every authored/modified task file. No generated lockfile, production bundle or node_modules is included.

| File | Change |
|---|---|
| `frontend/.dockerignore` | Exclude dependencies, bundles, coverage and environment files from the image |
| `frontend/Dockerfile` | Non-root Node development image; conditional lockfile-based installation |
| `frontend/THIRD_PARTY_NOTICES.md` | Retained shadcn Card source attribution and MIT license |
| `frontend/components.json` | shadcn source-component configuration and aliases |
| `frontend/index.html` | Vite HTML entry and viewport metadata |
| `frontend/package.json` | Approved stack/test dependencies and npm commands; no fabricated lockfile |
| `frontend/scripts/client-smoke.mjs` | Executable dependency-free API/formatting smoke assertions |
| `frontend/src/App.tsx` | Responsive application shell and React Router route definitions |
| `frontend/src/api/client.ts` | Relative GET client, cancellation, filters, timezone and safe links |
| `frontend/src/api/types.ts` | Types matching existing FastAPI schemas |
| `frontend/src/components/shared.tsx` | Reusable game/finality/source and loading/error/empty components |
| `frontend/src/components/ui/card.tsx` | Locally adapted shadcn Card primitives |
| `frontend/src/lib/utils.ts` | Minimal string class-name utility for local primitives |
| `frontend/src/main.tsx` | React bootstrap, QueryClient and BrowserRouter |
| `frontend/src/pages/Matchup.tsx` | Canonical-UUID detail, nullable values, provenance and return navigation |
| `frontend/src/pages/Schedule.tsx` | Available seasons, stage/week/round routes, queries and coverage states |
| `frontend/src/styles.css` | Tailwind import/theme plus responsive sports dashboard styling |
| `frontend/src/test/dashboard.test.tsx` | 23 authored RTL/Vitest cases; not executed here |
| `frontend/src/test/fixtures.ts` | Synthetic API fixtures excluded from application entry imports |
| `frontend/src/test/setup.ts` | DOM matchers, cleanup and mock reset |
| `frontend/tsconfig.json` | Strict TypeScript/JSX, aliases and tooling types |
| `frontend/vite.config.ts` | React/Tailwind plugins, loopback dev host, API proxy and Vitest setup |
| `.gitignore` | Ignore frontend dependencies/build/coverage |
| `compose.yaml` | Add loopback-only frontend development service and healthcheck |
| `AGENTS.md` | Record current approved Task 006 scope |
| `README.md` | Current status and dashboard startup pointer |
| `docs/agent-task-006.md` | Owner-approved scope and acceptance boundary |
| `docs/schedule-dashboard.md` | Implementation, evidence, WSL commands, limits and complete inventory |
| `docs/architecture.md` | Current frontend/proxy boundaries and actual routes |
| `docs/decisions.md` | Record Decision 57 |
| `docs/development.md` | Frontend startup/checks and historical-scope clarification |
| `docs/implementation-plan.md` | Current slice status and remaining acceptance gate |
| `docs/schedule-api.md` | Record owner-reported API validation; unchanged API contract |
| `docs/schedule-data-contract.md` | Document frontend projection retaining existing safeguards |
