# Buckets to Bucks NFL player-prop dashboard investigation

Target: https://bucketstobucks.com/nfl/player-props  
Observed: 2026-11-17 UTC (2026-11-16 America/Phoenix).  
Method: REA CDP discovery, passive inspection of browser-loaded scripts and accessibility, controlled normal browser actions, and offline analysis of captured responses. No NFL application files were changed.

## Result and confidence

The browser connection worked. The public application uses a broad prop-table response, local filtering and presentation, and a separate player research route that fetches player-specific offers, three seasons of game logs, and matchup datasets. React 19.2.0, Recharts, Radix primitives, Vite-generated assets, and Wouter v3 markers are identifiable in browser-loaded JavaScript.

Player chart content and game logs were observable in the accessibility tree, but a normal attempt to select L5 was intercepted by a paywall overlay. No overlay was removed, no forced clicks or synthetic handler calls were used, and no authenticated endpoint was probed. Chart interactivity behind that overlay remains unverified. Publicly delivered data does not establish permission to reuse or redistribute it.

Confidence labels used below:

- **Observed:** browser request, response, URL, accessibility state, or normal action outcome.
- **Derived:** offline calculation or interpretation of shipped JavaScript observed in the browser; not proof that every code branch ran.
- **Hypothesis:** plausible explanation without enough evidence to confirm.

## Evidence and reproducibility

The full REA bundle is [bucketstobucks-evidence.json](bucketstobucks-evidence.json). [bucketstobucks-request-index.json](bucketstobucks-request-index.json) lists API requests by parent evidence ID, transaction ID, step, status, and available JSON keys. The index is an offline projection, not another network capture.

| Label | REA evidence ID / artifact | Use |
|---|---|---|
| D | `ev_21873fbfda27ea39e87b14ca7fe9b4cf275ddee1d51cabeb8426e2210d1d6bb3` | Successful target discovery |
| P | `ev_2003c65bee4176f33dddf3897d1b19ded5261d2fc3ef7608b5168f77acd32ea1` | Initial accessibility tree and loaded script sources |
| I | `ev_f5fd2ac69640818b4a622261707003ddc3ecaff62e7e8418f5577e7bf6a27732` | Initial page-load API responses |
| B | `ev_8e6179d3d022b41769745ed28e8fa207d4f4c225c41d0048a816137fce096a67` | Retained tool error containing a partial browser capture with the full table JSON |
| W | `ev_4a76ba19266dbf4343fe1f1029fc4f47dac042134d41f53dc2d11cc8ae04acd2` | Week-11 action, requests and resulting table |
| F | [bucketstobucks-interactions-partial.json](bucketstobucks-interactions-partial.json) | Complete returned tool-error payload; completed search/under/over steps before later failure |
| R | `ev_5c0f6648898901015f0d78b4ab6750dca2e13c5bd0cf70817e4b1af97fc2975d` | Successful row click, player route, requests, rendered research content |
| G | `ev_fb48c9b1a802eb646fc5428190d3aa47d53eb085d20c02a160702a33b481edfe` | Direct revisit to the observed player URL, JSON, paywall interception |

D identifies Chrome `157.0.8103.78`, CDP `1.3`, and target `B9D955AF56D94320211FDF0F2A246D6D` at the requested URL via `http://127.0.0.1:9222`. No browser installation or registration change was needed.

## 1. Loading statistics and odds

**Observed.** Initial page load made these same-origin requests (I):

| Request | Status | Role established by response/UI |
|---|---:|---|
| `GET /api/nfl/active-week?season=2026` | 200 | Published active week and publication metadata |
| `GET /api/nfl/schedule?season=2026&week=10&seasonType=2&prepared=1` | 200 | Week schedule, teams, dates, scores and available weeks |
| `GET /api/nfl/player-props?table=1` | 200 | Bulk prop rows, sportsbook offers, precomputed hit rates |
| `GET /api/search-player-catalog` | 200 | Shared search catalog; initial body exceeded capture budget |
| `GET /api/auth/user` | 401 | Normal unauthenticated account check; body `{"message":"Unauthorized"}` |
| `GET /api/subscription/plans` | 200 | Subscription product metadata |
| `GET /api/ncaab/research/teams` | 200 | Shared application bootstrap data; not evidence of NFL-stat provenance |

The active-week response was season 2026, week 10, with `publishedAt: "2026-11-10T08:00:00.238Z"`, `turnoverKey: "2026-11-10"`, and `source: "server-nightly-publication"` (I, request-86). These are server declarations, not an independently verified update schedule.

The page initially showed no props for week 10 despite the bulk response containing upcoming offers. Selecting week 11 displayed 13 games and 100 of 1,010 matching props (W, step 2). The full table response recovered from B contained 2,626 records and was 2,161,336 bytes as exposed by Playwright. Counts and prices are snapshots, not stable API guarantees.

**Derived from shipped code, corroborated by traffic.** The table query uses a five-minute stale time and a two-second refetch interval while `building`, `refreshing`, or `metadataRefreshing` is true; otherwise five minutes. The recovered response had `building: true`. Repeated identical table requests therefore must not be attributed automatically to each click. See P, `nfl-player-props-DVkBSeEZ.js`, final page query; I includes repeat table transactions during a failed locator wait.

## 2. Requests associated with interactions

| Interaction | Direct observation | Interpretation and boundary |
|---|---|---|
| Select NFL week 11 | Schedule request changed to `week=11`; injury report, defense-rank requests and headshots appeared; table rendered (W, step 2) | Week affects schedule and visible rows. REA timed out before marking the click complete, so only its observed effects are confirmed. |
| Search `Jahmyr` | Table narrowed to two rows; URL stayed on the table route (F, steps 2–3) | No search-term API URL appeared. One identical bulk table refresh occurred during the fill; polling is a supported explanation. |
| Select Under | Gibbs anytime-TD row changed to Under, showing a different book/price and complementary hit rates (F, steps 4–5) | No new same-origin API request was recorded in these steps. This is bounded evidence of local transformation. |
| Select Over | Original over rows returned (F, step 6) | No new same-origin API request recorded in this step. |
| Click Gibbs player name | Navigated to `/nfl/player-props/jahmyr-gibbs` with event/pick context; requested player offers and logs (R, steps 3–4) | Successful normal navigation; no guessed player route was needed. |
| Select chart L5 | Normal pointer click was blocked by `data-testid="paywall-overlay"` (G, step 2) | No successful L5 transition. Subsequent planned line/side/secondary-stat actions were cancelled and are not findings. |

The row click initially produced `?g=TB-DET.mws56io0&pick=touchdowns-over-0.5&pos=RB&t=DET`; identity resolution normalized it to `?g=TB-DET.mws56io0&p=4429795&pick=touchdowns-over-0.5` (R). These query encodings are observed implementation details, not a public integration contract.

Player navigation triggered, among others (R, requests 92–114):

```text
/api/nfl/player-props?linesOnly=1&playerSlug=jahmyr-gibbs&team=DET
/api/nfl/player-game-log/jahmyr-gibbs?team=DET&position=RB&season=2026
/api/nfl/player-game-log/jahmyr-gibbs?team=DET&position=RB&season=2025
/api/nfl/player-game-log/jahmyr-gibbs?team=DET&position=RB&season=2024
```

After identifying the player, equivalent log requests used `espnId=4429795`. Related requests loaded historical closing lines, opportunity share, recent RB performance against TB, player tendencies, weather, news, injury data, team rankings, and defense-vs-position comparisons. They were initiated by the application; none were manually enumerated or replayed.

**Observed with static explanation.** The table also requested defense-vs-position data using `defenseTeam=ARI` for multiple position/stat combinations (W requests 91–111). P's code reads the returned all-team `rankings` map, which explains how one request per position/stat can support many opponents. The literal ARI parameter alone does not establish which opponent's rank was displayed.

## 3. Publicly observable JSON structures

These structures describe captured examples, not a complete formal schema. Missing/null fields are meaningful.

### Bulk props

B's captured response has top-level `data`, `building`, `refreshing`, and `metadataRefreshing`. The union of observed row keys is:

```text
playerName: string       team: string           sgoPlayerID: string
propType: string         line: number           position: string
books: array            gameInfo: object       impliedProb: number/null
hitRateL5, hitRateL10, hitRateH2H, hitRate2026, hitRate2025
_hitRatesReady           _oppAbbr
```

`gameInfo` includes `eventName` and ISO `startsAt`. Book entries include a book code, line, nullable `overOdds`/`underOdds`, and sometimes signed navigation tokens. Tokens were observed as opaque link data, not decoded or used. Full response: [bucketstobucks-props-observed.json](bucketstobucks-props-observed.json).

Player-specific `linesOnly` responses additionally expose `stale`, `refreshFailed`, and `retryAt` alongside build/refresh flags (R request-92; G request-84). A captured example was 14,761 bytes.

### Game logs

R and G returned envelopes with `data`, `player`, `identityStatus`, `availability`, and `passingDepthStatus`. Gibbs was `verified`, `available`, and passing depth was `not_applicable`.

Each game includes IDs, date, week, season, preseason/postseason flags, `seasonType`, team/opponent, home/away, result, and nullable statistics. Examples include `rush_attempts`, `rush_yards`, `rush_tds`, `receptions`, `targets`, `rec_yards`, `rec_tds`, `long_rec`, snaps, snap percentage, and depth metrics. Passing and kicking fields were null for the sampled RB game; they must not be interpreted as zero.

The 2026 sample's most recent game had 22 carries, 153 rushing yards, 2 rushing TDs, 7 receptions on 8 targets, and 99 receiving yards. These are website-reported values, not independently verified league statistics. Separate captured files contain [2026](bucketstobucks-gamelog-2026.json), [2025](bucketstobucks-gamelog-2025.json), and [2024](bucketstobucks-gamelog-2024.json) logs.

### Supporting datasets

| Response | Observed fields |
|---|---|
| Schedule | `data`, `week`, `season`, `availableWeeks`; game objects include nested teams, status, scores, odds and weather |
| Defense vs position | `defenseTeam`, `comparison`, `rankings`, `history`, `position`, `stat`, `season`, `completeness`, `completedGames`, `teamsRanked`, `rankMeaning` |
| Rank comparison entry | Overall/position objects containing `average`, `rank`, `sampleSize` |
| Opportunity share | `rows`, `team`, `season`, `completeness`, `completedGames`; player rows include counts and a `shares` object |
| Historical closing lines | `data[]` with `eventId`, `gameDate`, home/away teams, `line`, `method`, `observedAt`, `startsAt` |

Evidence: I request-87; G requests 91, 95–96. Exact transaction mappings and body digests are in the request index.

## 4. Frontend transformations and display

**Observed.** The table presents proposition, line, several sportsbook prices, game time, probability, defense rank, L5/L10/H2H, and two season hit rates. Missing values appear as dashes. The table initially renders 100 results and exposes a load-more control. Load-more itself was not exercised.

For Gibbs over 0.5 TD, the table showed L5 80%, L10 90%, H2H 50%, 2026 89%, and 2025 59%. Under changed these to 20%, 10%, 50%, 11%, and 41% (F). This demonstrates complementary display for this sampled half-line; it does not establish correct push handling for every market.

The displayed probability changed from 78% over to 37% under. These are not complementary probabilities from one calibrated model. Their values are consistent with rounding the American-odds implied probabilities of a displayed -280 over offer and +167 under offer. **Hypothesis:** the UI derives probability from a selected sportsbook offer; the exact selection rule is not established by this numeric example alone. The bulk Gibbs record separately contained `impliedProb: 72`, so that snapshot field alone does not explain every displayed value.

**Derived from observed scripts.** The table uses local array filtering/sorting for search, prop types, side, hit-rate bounds and odds. Non-default hit-rate filters round values before range comparison and exclude unavailable rates. Sort fields include player, market, line, game time, probability, defense rank, and hit-rate windows. Column preferences and saved presets have localStorage persistence; authenticated preset synchronization code exists but was not exercised. See P, `nfl-player-props-DVkBSeEZ.js`, table component `Ci` and constants near `b2b_nfl_props_visible_columns_v1`.

## 5. Charts, statistics and access boundary

**Observed in the player accessibility tree (R/G):** a game-series chart, L5/L10/H2H/season controls, secondary-stat selector, line controls, over/under controls, game-log table with averages and historical lines, target/rush-share visualization and table, formation splits, three rushing lanes, and eighteen schematic target-depth zones. The markup includes subscription upgrade overlays. Accessibility exposure does not mean the controls are freely interactive.

**Derived and independently reproduced from captured JSON:** combine the three season logs, exclude preseason, sort descending by date, and take ten games. Rush TD plus receiving TD gives `[2,1,1,0,2,1,3,1,2,1]`. Nine values exceed 0.5 and the average is 1.4, matching `O90% (9-1) Avg: 1.4` and the ten-row game log. Nine games are from 2026 and one from the end of 2025. Thus L10 in this example spans seasons. This validates the sampled calculation, not every market or exclusion rule.

**Derived from shipped chart code:** `Ki` combines season logs and sorts chronologically; it accepts a custom line and side, initializes L10, and declares filters and secondary-stat state. Recharts code implements SVG charts. These branches are a static explanation, not proof that gated interaction succeeds. Tooltip behavior, line changes, secondary-series changes, chart clicks and reset semantics were not verified. No further chart actions were attempted after the paywall interception.

## 6. Frontend technology identification

Evidence comes from browser-loaded source captured in P; files are retained under [bucketstobucks-assets](bucketstobucks-assets).

| Technology | Confidence | Concrete marker |
|---|---|---|
| React / React DOM 19.2.0 | Confirmed shipped dependency | React production license header and explicit version assignments in `vendor-react-BzrpNAyj.js` |
| Recharts | Confirmed shipped chart implementation | Numerous `recharts-surface` / `recharts-layer` markers and SVG components in `vendor-charts-CXGReANn.js` |
| Radix UI primitives | Confirmed shipped implementation | `radix.slottable`, `__radixId` and Radix attributes in `vendor-ui-B-WcWTF6.js` |
| Vite-generated build | Strongly supported | `__vite__mapDeps` and dependency/preload mapping in `index-A9E75iQq.js` |
| Wouter v3 | Strongly supported | `Symbol.for("wouter_v3")` and browser-history routing implementation |
| TanStack/React Query family | Strongly supported identification | QueryClient/QueryClientProvider implementation plus query-key, stale-time, invalidation and refetch APIs in `vendor-query-DiHQmPLe.js`; exact package version unverified |
| Tailwind-style utility CSS | Likely | Utility class names throughout rendered and shipped components; package/build configuration not inspected |
| Original TypeScript source | Unknown | Public JavaScript alone does not establish the original source language |

Backend framework, database, licensed feed contracts, deployment topology and server aggregation code are unverified. Names such as `ftn-stats`, `rotowire-news`, `sgoPlayerID` and ESPN-style IDs are observable integration clues, not proof of provider contracts or data ownership.

## Limitations and request discipline

The investigation used normal page loads and UI actions, not guessed API probes, credential changes, token replay, rate-limit evasion or access-control bypass. The site's own bootstrap, polling, analytics and related-data fanout generated requests automatically.

Several captures failed: responsive-layout locators differed, one week click changed state but exceeded its action deadline, and several later actions produced REA execution errors with useful partial observations. These were not treated as fully successful scenarios. Initial body limits omitted large responses; the full bulk body was eventually retained inside B's exported error payload. F is saved separately because it was returned as a partial error rather than a normal retained capture. Some request bodies/headers were deliberately not captured, and some responses were unavailable or unfinished. REA does not provide request initiator stacks in controlled scenarios. Step timing establishes association, not complete causality.

REA warns that Playwright response-body retrieval can fall back to another load when CDP cannot supply bytes; these captures are browser API observations, not packet-level wire evidence. No claims of a complete API inventory or wire-exact payload identity are made. The initial passive capture excluded third-party origins; controlled scenarios separately observed third-party analytics. The external Chromium browser was left open; REA reported disconnection rather than browser termination.

## Independent design for React, TypeScript and FastAPI

This proposal is original architecture informed by observable behavior, not copied implementation code or a dependency on the investigated endpoints.

1. **Own the data pipeline.** Ingest permitted/licensed statistics and odds into PostgreSQL through scheduled jobs. Store provider IDs, provenance, observation timestamps and corrections. Separate players, events, game statistics, prop offers and historical offer snapshots. Keep provider secrets on the server.
2. **Provide two API layers.** Offer a paginated research table with typed filters, and a player-detail endpoint returning authorized game logs and current offers. Add cached matchup summaries only when needed. Return freshness, completeness and explicit pending/error states; avoid making every visible row initiate separate ranking calls.
3. **Control payload and polling costs.** Start with server pagination and compact table summaries rather than a multi-megabyte universal payload. Cache by normalized filter keys. Use conditional requests and bounded polling/backoff for genuinely pending jobs; refresh current offers separately from historical statistics.
4. **Use shared pure calculations.** Define eligible games, cross-season L10, market-to-stat mappings, pushes, DNPs and missing values explicitly. Return sample sizes with rates. Keep historical threshold frequencies distinct from bookmaker implied probability and any forecasting model. Test half-lines, integer pushes, season boundaries and stat corrections.
5. **Build typed React state.** Use TypeScript types and runtime response validation. Store shareable player/event/market/line context in the URL. Keep temporary controls local, persist optional preferences locally, cancel superseded requests, and prevent stale responses from replacing a newer selection.
6. **Render accessible charts and tables.** Use an independently implemented SVG chart or an appropriately licensed chart library. Plot per-game values and a labeled threshold, distinguish pushes/missing values, show a matching table and sample counts, and provide keyboard-accessible filters. Opportunity-share and schematic zone views should state denominators and data coverage.
7. **Enforce any product permissions on FastAPI.** If your app has paid or restricted data, authorize before returning it. A visual overlay is insufficient protection. Do not import this site's bundles, signed links, assets or response datasets into your production application without permission.

Suggested original routes: `GET /api/nfl/research`, `GET /api/nfl/players/{id}/games`, `GET /api/nfl/events/{id}/offers`, and `GET /api/nfl/teams/{id}/matchup-summary`. These are proposed interfaces for your application, not claims about the target's contract.
