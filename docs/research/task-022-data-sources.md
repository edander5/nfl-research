# Task 022 — independent data-source feasibility

Checked 2026-11-17 using public official documentation, upstream source/dictionaries and release listings. **E** denotes those observations; **R** denotes existing repository implementation; **P** denotes a recommendation. No account/key use, provider onboarding, new importer, database access or captured Buckets to Bucks dataset use occurred. A documented loader or listed file does not prove row completeness, current service health or permission from every upstream rights holder.

## Feasibility matrix

Complexity: low = existing read model; medium = new validated adapter/model/API; high = new evidence, mappings or detailed aggregation. All integration is proposed and approval-gated.

| Source / features | Coverage and historical seasons | Cadence / access | Rights and $0 feasibility | Reliability, missing evidence and complexity |
|---|---|---|---|---|
| Existing PostgreSQL accepted team stats (R) | Scoped 2024–2026, REG/POST; gross/signed sacks/NET/rush, reciprocal allowed yards; reported and evidence-backed score projections | Current accepted pointer reads via existing restricted API role; operator refresh/import | No new API spending; retain stored source attribution/origin caveats | **Best Phase 1 option; low.** Current DB counts not inspected. No completion-before-cutoff proof; no player/efficiency columns in accepted projection |
| nflverse weekly player stats (E) | Loader supports 1999 onward; current listing includes 2024–2026 weekly CSVs. Dictionary covers ten PRD stats plus targets, air yards, EPA/CPOE and shares [S1–S3] | Public release CSV/Parquet/RDS; use bounded CSV acquisition, not R installation. Publication policy [S4] | $0 public artifacts; baseline CC BY 4.0 with dataset-specific review [S5] | **Primary Phase 2 candidate; medium/high.** Actual 2026 body fetch failed; no certified counts, DNP/played-zero, correction or transfer samples. Documentation/example != verified official reconciliation |
| nflverse player IDs + season rosters (E) | Players table is one row/player with IDs; rosters documented back to 1920 [S6–S7]. Initial app remains 2024–2026 | Public CSV; roster publication policy [S4]; player update SLA not established here | $0 candidate under dataset license review [S5]; headshots/logos are not automatically cleared | **Medium.** Validate GSIS/ESPN/PFR crosswalk uniqueness, retired aliases, multi-team seasons and nulls. Season roster membership does not prove game participation |
| nflverse PFR snap counts (E) | Game-level offense/defense/ST snaps and percentages since 2012; PFR player ID plus nflverse/PFR game IDs [S8–S9] | Public release formats; cadence policy [S4], upstream-dependent | $0 access candidate; repository license plus PFR-origin rights/attribution check [S5] | **Medium/high.** Crosswalk required; special-teams-only and zero-touch appearances need real examples. Missing/zero snaps alone cannot establish DNP; never blanket zero-fill stats |
| nflverse team stats / play-by-play (E) | Team/player loader supports 1999 onward; PBP since 1999, fine-grained plays and team/game identity [S1,S10] | Public release CSV; policies [S4]; reuse existing team acquisition first | $0 baseline candidate [S5] | **Medium for reviewed team efficiency; high for PBP.** Current normalized database lacks EPA, success flags and play denominators. Raw retained rows need separate validation/grants, not accidental publication. Approve EPA/play and success definitions before calculating |
| Locally derived defense versus position (P) | Future accepted player stats + game/team/position mapping, initially 2024–2026 | Own SQL aggregation; no provider API | $0 marginal API cost; underlying source obligations apply | **Medium after player foundation.** Sum position output per defense-game, then average over covered defensive games; do not average over individual player rows. Define position as of game, no-eligible-opponent cases, unknown stats and rank direction |
| Locally derived usage (P) | Targets/carries/receptions and team denominators; snap shares when separately validated | Own SQL; published source shares are context, not automatically interchangeable with own aggregate | $0, underlying terms apply | **Medium.** Ratio of sums versus mean game share must be approved. Denominator includes relevant whole-team opportunities, including unnamed/missing players; zero denominator => unavailable. Routes/route participation are not established by snaps |
| nflverse NGS (E) | Weekly passing/rushing/receiving advanced metrics from 2016; minimum-attempt qualification [S11] | Public release formats; nightly/source-dependent policy [S4] | $0 access candidate; dataset/upstream rights review [S5] | **Medium/high.** Qualified subset cannot supply full appearance population. Field availability by season and player/week joins remain unvalidated |
| nflverse FTN charting / participation (E) | Granular context candidate; participation source changed in 2023 [S4,S5] | Public release artifacts, dataset-specific schedule | $0 access does not remove CC BY-SA obligations; FTN-specific exceptions must be inspected [S5] | **High; defer.** Post-2022 participation is released after postseason, not an in-season solution. No verified replacement for target's formations/lanes/zones/route shares |
| nflverse injuries (E) | Loader says since 2009; 2026 CSV exists in listing; statuses, practice/injury fields and date_modified documented [S12–S14] | Public CSV; nominal daily policy [S4] | $0 candidate; confirm exact source/license exceptions per release, not blanket license inference [S5] | **Medium/high.** Listing timestamp is not report freshness. Full teams, current week, practice-day history and provider continuity unverified. No inference from absence to healthy |
| nflverse depth charts (E) | Loader says back to 2001; 2026 listing exists; current dictionary has timestamp, GSIS/ESPN, formation/position/rank [S15–S17] | Public artifacts. 2025+ observations are timestamp-based rather than weekly [S4] | $0 candidate, dataset-specific rights review [S5] | **Medium/high.** Legacy/current schemas differ; validate all teams/offense/defense/ST. 2026 CSV listing is 72.6 MB, much larger than player stats: do not blindly reuse small-artifact caps or download a full append history per UI request |
| Existing nflverse schedule market fields (R/E) | Stored spread/total/moneyline/price reference fields when present, scoped seasons | Existing raw-record read and API; source files can be corrected | $0 existing-source reuse, retain license/origin limitations | **Low.** No verified book/quote time, so not live/opening/closing, and not an odds-movement series. [Existing Task 017 evidence](../game-betting-markets.md) governs signs and coverage |
| The Odds API, hyphenated domain (E) | Current NFL game markets and selected player props documented; free starter advertises all markets/most books, **500 credits/month**, no historical [S18–S19] | Key-based JSON; on-demand only proposed; refresh varies by market/approach to start, no fixed SLA claimed | $0 candidate for bounded calls. Terms permit UI/analysis and indefinite retention, forbid standalone raw-feed redistribution [S20] | **Medium/high.** No authenticated NFL sample or full-ten-market/book coverage verified. Require own canonical event/player matching, server-only key, hard cap and no paid auto-upgrade. Free does not mean unlimited |
| The Odds API historical snapshots (E) | Featured markets advertised from June 2020; extra markets/props from May 2023, only since a market/book was covered [S18–S19] | Historical endpoints paid; interval/archive metadata available | **Does not meet $0 historical backfill budget** | Defer. Future permitted retention of selected free current observations could build sparse prospective history; no retroactive archive or continuous opening/closing promise |
| Open-Meteo forecasts/history (E) | Global coordinate-based hourly temperature/wind/precipitation; forecast up to 16 days; historical reanalysis from 1940 [S21–S23] | Public JSON, no key for free non-commercial service; model-dependent updates | $0 for qualifying private/non-commercial use; CC BY 4.0 attribution. Limits: <10,000/day, 5,000/hour, 600/minute [S23] | **Medium.** Need correct stadium/neutral-site coordinates, roof context, kickoff alignment/units, source run and observation time. Reanalysis is reconstructed weather, not an archived pregame forecast or stadium observation |
| NOAA/NWS weather alternative (E) | Forecast/alerts/observations API for US coverage, not all international NFL venues [S24] | Public cache-friendly JSON, identifying User-Agent; rate cap not published numerically on reviewed page | Free service documented; review applicable NOAA reuse notices/third-party exceptions before integration | **Medium.** US fallback only; archive depth and venue observation matching not verified. Choose one source in future feasibility task, not two adapters now |

Do not infer ESPN/private endpoints or provider contracts from target request names. No direct ESPN, PFR scraping or licensed FTN/Rotowire integration is approved. The unhyphenated `theoddsapi.com` is a different product; it is not the source of [S18–S20] claims and is not selected. Prior comparisons remain historical in `docs/data-sources.md`.

## Artifact and schema evidence

The [stats_player listing][S3] exposed `stats_player_week_2026.csv`, approximately 4.4 MB, updated `2026-11-16T19:34:38Z`, publisher digest `6e7ccdf7c215867e43a65b720c88a79a1aaa571d159b8afb957e5b03a7e253a5`. This is **listing metadata**, not a locally verified body/hash or latest-game completeness assertion. Weekly 2024/2025 assets are also listed. The loader constructs `stats_player/stats_player_week_{season}.csv` and supports years >=1999 [S1]. A browser fetch of the 2026 CSV failed at a release redirect; no player data body was accepted. The HTML dictionary rendered no fields, and two legacy/guessed CSV dictionary paths returned 404; the actual JSON dictionary [S2] was then located through the repository tree.

Schema evidence in [S2]: `player_id` is GSIS; `season_type`, `week`, `team`, `opponent_team` supply context. PRD mapping candidates: passing yards/attempts/completions/TDs => `passing_yards`/`attempts`/`completions`/`passing_tds`; rushing yards/attempts/TDs => `rushing_yards`/`carries`/`rushing_tds`; receiving yards/receptions/TDs => `receiving_yards`/`receptions`/`receiving_tds`. `targets`, `passing_epa`, `passing_cpoe`, `rushing_epa`, `receiving_epa`, `target_share`, `air_yards_share` are documented too. These field names establish feasibility, **not** actual non-null coverage or eligible appearance denominators. Do not subtract team sacks from a player's prop passing yards.

Injury listing [S14]: `injuries_2026.csv`, approximately 354 KB, updated `2026-11-16T17:00:35Z`; depth listing [S17]: `depth_charts_2026.csv`, approximately 72.6 MB, updated `2026-11-16T16:59:03Z`. Neither body was downloaded or reconciled. Dictionaries show report/practice status and `date_modified`, versus depth `dt`/`pos_grp`/`pos_slot`/`pos_rank`. Injury dictionary even types some identifier/stage fields unexpectedly: validate actual strings rather than blindly generating types. Recheck metadata, bytes, coverage and exceptions at implementation time.

## Cadence and rights interpretation

[S4] documents schedules every five minutes in season; team/player stats nightly after game days plus selected game-day runs; correction rechecks Wednesday night/Thursday; rosters daily 07:00 UTC; snaps four times daily subject to PFR; injuries/depth nominally daily 07:00 UTC. These are upstream policies, not app guarantees or observed SLAs. New-season injuries and depth need actual record-date audits. Current-season participation from FTN is unavailable until postseason finishes.

[S5] identifies a broad CC BY 4.0 baseline and FTN CC BY-SA exception. Preserve attribution, license, modification notices and artifact provenance. Dataset-specific markings and upstream rights must be checked before adoption; this research does not supply legal clearance or copy the maintainer's interpretation as a definitive licensing conclusion. Keep license evidence per dataset/version. Public availability does not clear player photos, team logos or target assets.

The reviewed [The Odds API terms][S20], updated 2026-08-31, explicitly allow retaining observations indefinitely and displaying/deriving analytical values, while prohibiting competing raw-data redistribution. This resolves the older generic retention question at a documentation level; authenticated account conditions and any later term changes still require verification before onboarding. Their initial `/terms-of-use.html` path was unavailable; the actual `/terms-and-conditions.html` was successfully reviewed.

Quota example (**P calculation**, not a proposed polling job): ten prop markets × one region × sixteen games × one check = up to 160 credits at the event endpoint. Three such full-slate checks consume up to 480 of 500 monthly credits before game-market checks or other requests. This is inadequate for frequent comprehensive discovery refreshes. The event endpoint charges unique returned markets × regions; actual cost headers remain authoritative [S19]. Selective on-demand comparison can remain optional; manual thresholds must always work.

## Verification gates before any source integration

1. Capture official 2024–2026 sample bytes/metadata/hash/license into a research-only evidence directory under a separately approved task; reconcile known box scores, zero-touch and special-teams appearances, DNPs, transfers and postseason rows.
2. Measure uniqueness/nulls and map provider player/team/game identities; quarantine ambiguity, never match by name alone. Audit coverage against canonical schedule and appearance population.
3. Validate corrections and complete-snapshot semantics; missing rows must not silently delete accepted history. Record publisher/retrieval/import times separately.
4. Prove metric and denominator definitions with examples. Sparse player statistics alone cannot establish every played zero. Full eligibility is a foundation blocker; do not silently narrow the PRD to “players with touches.”
5. For odds only after approval: verify a free-only account/key, available NFL books/markets, credit resets/headers, budget controls and retention restrictions. No registration or credential inspection happened here.
6. Weather: validate venue/roof/neutral-site coverage and historical forecast versus reconstructed weather labels. Injury/depth: compare record dates and units, not just file upload times.

## Official source register (all retrieved 2026-11-17)

| ID | Official reference |
|---|---|
| S1 | [Player/team loader source][S1] |
| S2 | [Current player-stat JSON dictionary][S2] |
| S3 | [Player-stat release asset listing][S3] |
| S4 | [nflverse update/availability policy][S4] |
| S5 | [nflverse licensing statement][S5] |
| S6 | [Player identity loader][S6] |
| S7 | [Season roster loader][S7] |
| S8 | [PFR snap loader][S8] |
| S9 | [Snap-count dictionary][S9] |
| S10 | [Play-by-play loader][S10] |
| S11 | [NGS loader and qualification limitations][S11] |
| S12 | [Injury loader][S12] |
| S13 | [Injury dictionary][S13] |
| S14 | [Injury asset listing][S14] |
| S15 | [Depth-chart loader][S15] |
| S16 | [Depth-chart dictionary][S16] |
| S17 | [Depth-chart asset listing][S17] |
| S18 | [The Odds API free plan and archive overview][S18] |
| S19 | [The Odds API endpoints, quotas and historical limitations][S19] |
| S20 | [The Odds API current usage/retention terms][S20] |
| S21 | [Open-Meteo forecast documentation][S21] |
| S22 | [Open-Meteo historical reanalysis documentation][S22] |
| S23 | [Open-Meteo free-service terms][S23] |
| S24 | [NWS API documentation][S24] |

[S1]: https://raw.githubusercontent.com/nflverse/nflreadr/main/R/load_stats.R
[S2]: https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_player_stats.json
[S3]: https://github.com/nflverse/nflverse-data/releases/expanded_assets/stats_player
[S4]: https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html
[S5]: https://github.com/nflverse
[S6]: https://nflreadr.nflverse.com/reference/load_players.html
[S7]: https://nflreadr.nflverse.com/reference/load_rosters.html
[S8]: https://nflreadr.nflverse.com/reference/load_snap_counts.html
[S9]: https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_snap_counts.csv
[S10]: https://nflreadr.nflverse.com/reference/load_pbp.html
[S11]: https://nflreadr.nflverse.com/reference/load_nextgen_stats.html
[S12]: https://nflreadr.nflverse.com/reference/load_injuries.html
[S13]: https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_injuries.csv
[S14]: https://github.com/nflverse/nflverse-data/releases/expanded_assets/injuries
[S15]: https://nflreadr.nflverse.com/reference/load_depth_charts.html
[S16]: https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_depth_charts.csv
[S17]: https://github.com/nflverse/nflverse-data/releases/expanded_assets/depth_charts
[S18]: https://the-odds-api.com/
[S19]: https://the-odds-api.com/liveapi/guides/v4/
[S20]: https://the-odds-api.com/terms-and-conditions.html
[S21]: https://open-meteo.com/en/docs
[S22]: https://open-meteo.com/en/docs/historical-weather-api
[S23]: https://open-meteo.com/en/terms
[S24]: https://www.weather.gov/documentation/services-web-api

References above link the specific claims in the matrix. Additional baseline license: [nflverse-data CC BY 4.0](https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md). No captured target data is an independent-source candidate.
