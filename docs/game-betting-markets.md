# Task 017 — Game Betting Markets: feasibility and supported reference slice

## Finding and implementation boundary

The existing source supports a read-only **unverified source-reference** display and exact hypothetical score comparisons. It does **not** establish current sportsbook offers or independently timestamped historical pregame snapshots. This is a deliberately limited Task 017 implementation, not completion of the unsupported current-offer/verified-history features. The eligibility findings were reported to the owner before application changes.

No provider was added, credentials requested, database migration designed for execution, or ingestion contract changed. No accepted schedule/statistics data was edited. Current accepted-season rankings remain intentional and unchanged. A separate provider/storage contract requires explicit approval before work, as requested in Task 017.

## Verification record

Actual review clock observation: **2026-11-11 22:04:28 UTC**. Web references below were consulted in this investigation; this timestamp records the review session, not publication, quote time or a source retrieval claim for the CSV. The original local artifact was read with Python's standard library and not downloaded or modified.

### Official definitions — verified through documentation

The official [nflreadr schedule dictionary CSV](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_schedules.csv), rows 24–31 (zero-based web line locations), defines both moneylines, spread prices, total and over/under prices. A positive `spread_line` favors home; a negative value favors away. Thus the signed handicap used in score arithmetic is **home = -spread_line; away = spread_line**. Zero means an equal handicap.

The dictionary does not identify a sportsbook, per-market quote timestamp, opening/closing phase or capture-before-kickoff evidence. Its field type is numeric, but stored CSV cells are strings. No payout conversion or price-format promise is implemented. In particular, a revised schedule record does not establish a historical closing price. The public rendered dictionary table may require client-side loading; its raw official CSV supplied the reviewed definitions.

### Local data — verified by reading actual original bytes

File: `data/raw/games.csv`. SHA-256 measured in this investigation:

`66f7a71b12eeb8da8a5c332cfadb245da693aa66e2064fba734983dc41e68fd5`

The entire CSV parsed: **7,548 rows**, including seasons outside the application scope. Selected seasons:

| Season | Rows | Nonmissing values in each of all eight market fields | Rows with both reported scores | Unscored rows with spread |
| --- | ---: | ---: | ---: | ---: |
| 2024 | 285 | 285 | 285 | 0 |
| 2025 | 285 | 285 | 285 | 0 |
| 2026 | 272 | 149 | 121 | 28 |

The eight fields are `away_moneyline`, `home_moneyline`, `spread_line`, `away_spread_odds`, `home_spread_odds`, `total_line`, `over_odds`, `under_odds`. Each has the same observed nonmissing count within these selected seasons. No bookmaker, odds update or odds observation timestamp column was present. No selected-season zero-spread example was found; pick'em behavior is tested synthetically. Missing fields are never replaced with zeros.

Actual sample rows, **source values only**, not independently verified sportsbook records:

| Source game | Away/home reported score | Source spread | Derived away/home handicap | Total | Away/home moneyline |
| --- | --- | --- | --- | --- | --- |
| 2024_01_BAL_KC | 20 / 27 | 3 | +3 / -3 | 46 | 124 / -148 |
| 2024_01_HOU_IND | 29 / 27 | -3 | -3 / +3 | 49 | -155 / 130 |
| 2025_01_DAL_PHI | 20 / 24 | 8.5 | +8.5 / -8.5 | 47.5 | 330 / -425 |
| 2026_01_NE_SEA | 10 / 13 | 3 | +3 / -3 | 44.5 | 140 / -166 |

These numbers describe the original file, not the current PostgreSQL snapshot after owner-applied refreshes. Canonical database identity and actual current source pointers were not verified here because Docker access was denied. The artifact's previously unresolved published checksum/origin discrepancy remains; measuring its hash does not independently authenticate its origin.

### Existing storage — verified by repository inspection

- `Game.raw_source_record` preserves optional CSV fields, with canonical per-row SHA-256 and source artifact ID. These are not normalized market columns.
- `ingestion/service.py` replaces the current source-record pointer only through approved guarded reconciliation; previous artifact bytes and correction receipts are retained. This is source artifact history, **not** a bookmaker quote-history model or proof that capture preceded kickoff.
- The new API reads only the current source pointer. It does not search old files, select an old artifact as a closing quote, backfill missing values from earlier artifacts, or modify source history. Snapshot ID combines current artifact UUID and row hash so changes remain distinguishable.
- Existing `nfl_api` table SELECT privileges on schedule tables already permit the required reads. No new grant is needed. Public output allowlists scalar market values and existing sanitized game/provenance fields; raw source JSON, paths, notes, review tokens and private ingestion history stay private.

### Current odds candidates — documentation verified; authenticated coverage unverified

The **hyphenated [The Odds API](https://the-odds-api.com/)** advertises a free plan with 500 credits/month, all sports/markets and most bookmakers. Its [official V4 guide](https://the-odds-api.com/liveapi/guides/v4/) documents `americanfootball_nfl`, `h2h`, `spreads`, `totals`, bookmaker key/title and last-update metadata. Three requested markets in one region normally cost three credits per nonempty odds request; actual cost must be read from quota response headers. Provider event IDs require canonical mapping. This is a plausible candidate, not an activated source or measured free-account result.

[Historical odds](https://the-odds-api.com/historical-odds-data/) are paid-only. The free plan cannot backfill the 2024–2026 historical quote gap. Prospective authorized snapshots could be retained without calling that paid endpoint; they would remain timestamped observations, not automatically opening/closing prices.

The [official terms, dated 31 August 2026](https://the-odds-api.com/terms-and-conditions.html) permit retention, analytical use and UI display, while prohibiting standalone raw-data resale/redistribution. No account/key, live response, real bookmaker coverage, account reset behavior or quota-exhaustion behavior was verified. No signup, payment or request using a key occurred.

The similarly named unhyphenated [theoddsapi.com pricing](https://theoddsapi.com/pricing) currently lists free NBA/MLB moneylines rather than the required free NFL markets. Prior project documentation about redirects/NFL eligibility is historical and should not be treated as current provider validation. It is not selected. No sportsbook scraping or unapproved mirror was used.

The [nflverse-data license](https://raw.githubusercontent.com/nflverse/nflverse-data/main/LICENSE.md) is CC BY 4.0; retain attribution/license and indicate derived modifications. It covers licensor-held rights only. Unresolved upstream schedule/third-party permission questions documented in `docs/data-sources.md` remain unresolved. No public redistribution or new rights claim is made by this task.

## Supported API and exact calculations

`GET /api/games/{canonical_uuid}/markets` is read-only, with no query parameters. It reuses one provider-scoped schedule repository query and existing canonical game identities. It returns:

- `data.game`: existing `GameView`, providing the scores/status actually used by this response.
- `data.references`: zero or one current nflverse source-reference snapshots; a collection permits eventual independent bookmaker snapshots without flattening them into a single consensus.
- Reference identity/provenance: artifact UUID/hash, source-record hash, source URL, license, attribution, declared/verified origin and separately named artifact retrieval/recording timestamps. These do not establish quote freshness.
- Reference classification `UNVERIFIED_SOURCE_REFERENCE`, `bookmaker: null`, `quote_updated_at: null`, `freshness: UNKNOWN`.
- Six sides: away/home moneyline, away/home signed spread, over/under total. Decimal line/price values serialize as exact **JSON strings**, or null. Moneyline has no point line.
- Per-side result `WIN`, `LOSS`, `PUSH` or `UNDETERMINED`, with an explanatory reason. Every available calculation is hypothetical/provisional; `meta.settlement_verified`, `current_offers_available` and `verified_pregame_snapshot_available` remain false, including when selected-game FINAL evidence exists.

Examples:

```text
GET /api/games/{canonical_uuid}/markets
```

Synthetic side excerpt, not a real sportsbook quote:

```json
{"market":"SPREAD","side":"HOME","line":"-3.5","price":"-110","result":"WIN","reason":"provisional_source_reference_comparison"}
```

Calculations use bounded Python `Decimal` values, never binary floating-point comparisons. No calculations are duplicated in React:

- Moneyline: compare reported team/opponent scores when that side has a source price. A tie stays `UNDETERMINED`, because no two-way/three-way or bookmaker tie rule is documented. No assumed refund/push.
- Spread: compare `own_score + signed_handicap - opponent_score` to zero. Positive wins, negative loses, exact zero pushes. A missing price does not prevent a hypothetical line comparison, but the price stays unavailable.
- Total: compare score sum to source total, reversing direction for UNDER; exact equality pushes.
- Require both nonnegative integer scores. Missing scores yield undetermined calculations. Missing/invalid line or moneyline price makes the corresponding market unavailable. Source line zero, score zero and negative spreads remain meaningful.
- Reject nonstring source cells, nonfinite/scientific/malformed values, overlong values, precision beyond six decimals, magnitudes over one million, negative totals and zero prices. These conservative read-time bounds are not new ingestion acceptance rules: invalid market values are withheld, never repaired or written back.
- Validate raw game/source-team/season identity and its canonical JSON hash before deriving any reference. Mismatch returns no references and an explicit unavailable reason. This detects inconsistency; it does not authenticate source origin.

Unknown game UUID: existing 404 envelope. Invalid UUID/unknown or repeated query: 422. Mutation methods: 405. Database failures: existing sanitized 503. A known game without usable source/market fields returns 200 with unavailable information; source failure is not fabricated as live odds.

## Game Preview behavior

The independent Game Betting Markets section follows the existing rankings comparison. It never reorders or replaces rankings. It shows reported prices, derived signed spreads, totals, hypothetical/provisional results and score leader/tie context. A reported score leader is not asserted to be the final winner. UNKNOWN/UNVERIFIED remain unchanged.

Upcoming/unscored games may display retained source-reference values, but no current-offer claim is made. Missing quote times always remain unavailable, even if the artifact was downloaded recently. The UI does not classify a game as completed from kickoff time. Table headings, source attribution, source hashes and artifact-observation timestamps make the limitations inspectable. Small screens use a horizontally scrollable focusable market table. It has independent loading, unavailable, error/retry and failed-reload-with-cached-data states. No polling or provider requests from the browser.

## Approval-gated next contract (proposal only)

To meet the unsupported upcoming/historical features, explicit owner approval is required for a new provider integration and any storage migration/ingestion contract:

1. Candidate: The Odds API **free tier only**, no paid upgrade/overages. A bounded owner-authorized validation should verify NFL h2h/spread/total responses, actual quota headers and account limitations. Keys remain backend-only and outside logs/history.
2. Proposed immutable market snapshot storage: canonical game UUID, provider event ID and reviewed identity mapping; bookmaker key/name; market key and scope; captured-at plus provider/bookmaker/market update times where supplied; observation-phase provenance; exact decimal lines/prices; source artifact hash/receipt. Keep raw provider data private. Do not overwrite historical quotes with new prices. Separate snapshot/outcome rows could support multiple books without changing schedule tables. This is a conceptual proposal, not an implemented migration.
3. Proposed on-demand cache/quota contract: no scheduler changes; shared deduplication and persistent credit accounting, with a hard free-tier reserve before provider calls. For illustration, 150 one-region/three-market calls consume 450 credits, leaving 50 of an advertised 500; actual charged credits and account cycle must control enforcement, not that arithmetic alone. Out-of-quota must retain stale labeled data, never upgrade.
4. Historical display must require an actually captured pre-kickoff quote with validated game/book/market identity. No archive backfill on paid endpoints. Even those quotes produce provisional results until game finality and applicable market rules are established.

None of these actions was implemented or executed. The current reference slice does not require them; full completion remains approval-gated.

## Validation and exact WSL commands

Executed local checks (synthetic fixtures, no PostgreSQL writes or source downloads):

- Final focused backend run (`pytest backend/tests/test_markets.py -m 'not api' -q`): **36 passed, 2 skipped, 1 deselected**. The two PostgreSQL tests skipped; the synchronous HTTP success/error test was deselected and remains owner-run.
- Broad backend non-API subset, excluding existing health transport file: **377 passed, 81 skipped, 36 deselected**, one existing TestClient deprecation warning, 32.97 seconds. This run preceded the final additional populated-PostgreSQL test and two timestamp cases. The latter passed in the final focused run; the populated PostgreSQL test remains unexecuted.
- Frontend full suite: **107 passed across six files**, including eight new market tests and existing Game Preview/schedule/rankings regressions. Final rerun had no duplicate-key warnings after fixing sibling component keys.
- TypeScript and Vite production build: **passed**, 101 modules. No new dependencies installed. No lint script is configured; no lint pass claimed.
- Docker server probe: permission denied at `/var/run/docker.sock`; no workaround, container startup or real API/database check occurred.
- Python compile checks and `git diff --check` passed. No full Docker suite pass is claimed. Counts across subsets overlap.

From repository root in normal WSL, using existing `.env`, roles and development services. No administrator override, migration, grant or data refresh is required:

```bash
.venv/bin/python -m pytest backend/tests/test_markets.py -m 'not database and not api' -q
npm --prefix frontend test
npm --prefix frontend run build

# Isolated PostgreSQL + HTTP/security checks (synthetic test DB only).
docker compose --profile test run --build --rm tests \
  python -m pytest tests/test_markets.py tests/test_schedule_api.py tests/test_team_stats_api.py -q -ra
# Full isolated backend regression, if desired for acceptance.
docker compose --profile test run --rm tests python -m pytest -q -ra --durations=10
docker compose --profile test stop db_test

# Frontend image verification and existing development services only.
docker compose build frontend
docker compose run --rm --no-deps frontend npm test
docker compose run --rm --no-deps frontend npm run build
docker compose up -d --build --wait db api frontend
curl --fail-with-body -sS http://127.0.0.1:8000/api/health
curl --fail-with-body -sS http://127.0.0.1:8000/api/ready
```

Read-only smoke test chooses an existing canonical game; it does not assume a particular current score or artifact version:

```bash
python3 - <<'PY'
import json
from urllib.request import urlopen
base = 'http://127.0.0.1:8000'
def get(path):
    with urlopen(base + path, timeout=30) as response:
        return json.load(response)
games = get('/api/seasons/2024/schedule?season_type=REG&week=1')['data']
assert games, 'No stored games in selected week'
game = games[0]
markets = get('/api/games/' + game['id'] + '/markets')
assert markets['data']['game']['id'] == game['id']
assert markets['meta']['settlement_verified'] is False
for reference in markets['data']['references']:
    assert reference['freshness'] == 'UNKNOWN' and reference['quote_updated_at'] is None
    assert reference['bookmaker'] is None
print('Read-only reference check passed for', game['id'])
PY
```

Browser acceptance at `http://127.0.0.1:5173`: click a scored and an unscored schedule game; confirm rankings still render and market requests use the same canonical UUID. Inspect positive and negative source-spread examples against home/away signs. Confirm scores, provisional labels, unknown quote freshness, attribution and unavailable values, and that no line is called a current offer or verified historical pregame/closing price. Check mobile scrolling/keyboard access and independent failed-request/retry behavior without disrupting PostgreSQL. Actual live data coverage/latency and browser layout were not verified by this agent.

## Complete changed-file inventory

- New `backend/app/api/markets.py`, `backend/app/schemas/markets.py`, `backend/app/services/markets.py`: read-only route, safe typed projection and exact comparisons.
- `backend/app/main.py`: additive router registration only.
- New `backend/tests/test_markets.py`: unit/validation/privacy/identity/finality/exact arithmetic and owner-run HTTP/restricted PostgreSQL tests.
- New `frontend/src/api/markets.ts`, `frontend/src/components/BettingMarkets.tsx`, `frontend/src/test/markets.test.tsx`: typed reference client, independent UI and synthetic tests.
- `frontend/src/pages/Matchup.tsx`, `frontend/src/styles.css`: section integration and scoped responsive styles.
- `frontend/src/test/fixtures.ts`, `frontend/src/test/dashboard.test.tsx`, `frontend/src/test/matchup.test.tsx`: explicit market-unavailable fixtures preserve existing regression tests.
- New `docs/game-betting-markets.md`: findings, implemented boundary, remaining approval gate, tests and commands.
- `AGENTS.md`, `README.md`, `docs/architecture.md`, `docs/decisions.md`, `docs/implementation-plan.md`, `docs/development.md`, `docs/data-sources.md`: current scope, contract links and updated source limitations.

No database model/migration/role, ingestion/refresh/scheduler, accepted source file, statistics or ranking calculation changes. No commit, merge, push or deployment.
