# NFL data-source feasibility audit

**Audit date: 2026-11-05. Task 001: research and documentation only.** Supersedes the preliminary reconnaissance. No approved architecture or statistical definition has changed. See [feasibility-results.md](feasibility-results.md) for recommendations.

**Schedule-only follow-up:** the owner subsequently approved Schedule Contract Closure research. [Schedule Data Contract](schedule-data-contract.md) records the newer findings and supersedes the schedule-specific evidence gaps below where explicitly updated. An official `schedules` release with CSV/Parquet/RDS assets is now metadata-verified, as is nflreadpy's release download path. Full local downloads still fail; completeness, status/finality and applicable upstream rights remain unresolved. Other dataset findings were not revisited.

## Evidence standard and limitations

**Latest local validation:** the owner supplied `data/raw/games.csv` and approved limited UNKNOWN status (Decision 53). [Contract section 12](schedule-data-contract.md#12-local-artifact-validation-and-approved-status-limitation--2026-11-05) and [validation report](schedule-validation-report.md) supersede earlier schedule blockers: 285/285/272 unique games in 2024/2025/2026; primary structural checks pass. Eight colliding secondary `old_game_id` values and a mismatch with the published release digest remain explicit limitations. Recommendation **B. CONDITIONALLY READY** for a separately approved implementation task; no implementation is authorized here. Non-schedule findings below are unchanged.

**Final schedule assessment:** [Schedule Contract section 11](schedule-data-contract.md#11-final-readiness-assessment--2026-11-05) supersedes earlier schedule licensing/readiness conclusions. Official organization documentation explicitly licenses release datasets under CC BY 4.0 with named exceptions; the schedule release route has sufficient published license evidence for the private MVP. Full downloads remain blocked by local DNS/web-tool access limitations, and explicit status/final confirmation remains unsupported. Recommendation **C. BLOCKED**, with specific artifact and owner-decision exit conditions; no further general research task is proposed. Non-schedule findings below remain historical.

**Verified** means the specific observation was inspected, not an entire dataset certified. **Partial** means documentation or metadata supports feasibility but material validation remains. **Blocked** means a required probe failed or a requirement cannot be established. **Not yet tested** means no sample probe occurred.

All evidence URLs below were accessed on 2026-11-05. The web reader exposed raw schedule samples, official loaders/dictionaries, release listings and provider pages. Local curl failed DNS resolution (exit 6). GitHub CSV body fetches failed on release-asset redirects; an injury cache-busting query also failed. These audit-environment failures do not establish that files are absent or require authentication. No authenticated requests were made.

No full-file row counts, local hashes, uniqueness/null tests, box-score reconciliation or transfer examples are claimed. Listed hashes are publisher metadata, not independently computed. Branch/tag URLs are mutable; future imports must retain exact bytes, hashes and revision/fetch metadata. Browser retrieval date is not provider publication time.

## Source matrix

| Dataset / requirement | Status | Evidence / gap | Risk / confidence |
|---|---|---|---|
| 2024 schedules | Partial | Actual REG and WC/DIV/CON/SB samples; exhaustive integrity unresolved | High / high schema, low completeness |
| 2025 schedules | Partial | Actual REG and postseason samples including SB; full counts unresolved | High / same |
| 2026 schedules | Partial | Actual opening-game scores and future week-18 REG rows; returned file ends at REG week 18 | High / current partial-season completeness unresolved |
| UTC/status/completion | Partial / Blocked | Eastern kickoff documented; no UTC, explicit status or finish-time column observed | High / high header confidence |
| Player weekly stats, 2024–2026 | Partial; body checks Blocked | Ten fields documented; three assets listed; three body fetches failed | High / medium feasibility, low completeness |
| Team weekly stats, 2024–2026 | Partial | Three assets listed; dictionary inspected; 2026 body failed, earlier bodies Not yet tested | High / medium feasibility |
| Appearance/DNP/transfers | Partial | Snap-count dictionary offers candidate evidence; bodies/crosswalk/transfer example Not yet tested | High / low denominator confidence |
| Injuries, 2024–2026 | Partial | Assets and current publication metadata listed; actual report coverage unresolved | High / low row freshness confidence |
| Depth, 2024–2026 | Partial | Assets and schema change documented; all-team/unit completeness unresolved | High / low completeness confidence |
| The Odds API, hyphenated | Partial; authenticated coverage Not yet tested | Free NFL props and storage permission documented | Medium / high posted terms, low actual coverage |
| TheOddsAPI, unhyphenated | Blocked for free props | Redirects to Betting Data API; free NFL moneylines only | High / high posted pricing confidence |

## Schedules: actual sample evidence

Official [load_schedules.R](https://raw.githubusercontent.com/nflverse/nflreadr/main/R/load_schedules.R) loads `https://github.com/nflverse/nfldata/raw/master/data/games.rds`. The inspected CSV is [nfldata games.csv](https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv), not a verified `schedules` release asset.

Observed mappings: `game_id`; `season`, `week`, `game_type`; `home_team`, `away_team`; `home_score`, `away_score`; `gameday`, `gametime`; neutral context `location`; external IDs `old_game_id`, `gsis`, `espn`, `pfr`, `pff`, `ftn`. Preserve IDs as strings and canonical mappings; the human-readable game ID contains week and teams, so correction stability requires testing.

Inspected examples: `2024_01_BAL_KC`, `2024_19_LAC_HOU`, `2024_22_KC_PHI`; `2025_01_DAL_PHI`, `2025_20_HOU_NE`, `2025_22_SEA_NE`; `2026_01_NE_SEA`, `2026_18_DAL_WAS`. Future scores are blank. These show presence, not every row's correctness. No full-season/stage counts were calculated. The returned file ends at 2026 REG week 18; postseason participants/results must remain unavailable until published. Current-week freshness is unresolved.

The [schedule dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_schedules.csv) specifies Eastern time. Proposed conversion uses `America/New_York`, daylight-saving rules and then UTC, retaining unknown/TBD values. Map REG separately from WC/DIV/CON/SB; do not infer stage solely from week. Score presence cannot certify final status during live updates. The observed header lacks authoritative status and actual completion time. Approve evidence for final/postponed/cancelled states and completed-before-cutoff eligibility before importing.

Older [nfldata dataset notes](https://raw.githubusercontent.com/nflverse/nfldata/master/DATASETS.md) contain outdated ID/week conventions relative to current rows. Do not copy those conventions into a schema.

## Concrete statistical assets

Official [load_stats.R](https://raw.githubusercontent.com/nflverse/nflreadr/main/R/load_stats.R) generates weekly CSV/RDS/Parquet paths. Exact candidate CSVs:

| Season | Player | Team |
|---|---|---|
| 2024 | [stats_player_week_2024.csv](https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2024.csv) | [stats_team_week_2024.csv](https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2024.csv) |
| 2025 | [stats_player_week_2025.csv](https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2025.csv) | [stats_team_week_2025.csv](https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2025.csv) |
| 2026 | [stats_player_week_2026.csv](https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2026.csv) | [stats_team_week_2026.csv](https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2026.csv) |

All six are listed in official [player](https://github.com/nflverse/nflverse-data/releases/expanded_assets/stats_player) and [team](https://github.com/nflverse/nflverse-data/releases/expanded_assets/stats_team) asset indexes. Listed 2026 CSV updates: 2026-11-05 10:05:41Z and 10:05:45Z respectively; 2024/2025 CSV updates dated 2026-08-13. These are file-publication observations, not newest-game or full REG/POST verification.

### Ten fields, separately assessed

Source: official [player dictionary JSON](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_player_stats.json). Each market is **Partial for each of 2024, 2025 and 2026**: documented field and listed season asset; actual values/null coverage unverified because sample body fetches failed.

| Market | nflverse field | Documented The Odds API key |
|---|---|---|
| Passing yards | `passing_yards` | `player_pass_yds` |
| Passing attempts | `attempts` | `player_pass_attempts` |
| Passing completions | `completions` | `player_pass_completions` |
| Passing TDs | `passing_tds` | `player_pass_tds` |
| Rushing yards | `rushing_yards` | `player_rush_yds` |
| Rushing attempts | `carries` | `player_rush_attempts` |
| Rushing TDs | `rushing_tds` | `player_rush_tds` |
| Receiving yards | `receiving_yards` | `player_reception_yds` |
| Receptions | `receptions` | `player_receptions` |
| Receiving TDs | `receiving_tds` | `player_reception_tds` |

Documented joins: `player_id` is GSIS; `team`, `opponent_team`, `season`, `week`, `season_type` support candidate schedule matching. Resolve REG/POST and require a unique matching game. Current dictionary uses `team`, not assumed legacy `recent_team`. Actual key uniqueness, aliases and transfer rows remain untested. Preserve the team played for in each game; never overwrite history with current roster or join by name alone.

### Team offense and allowed yards

The [team dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_team_stats.json) documents `passing_yards`, `rushing_yards`, `sack_yards_lost`, season/week/stage/team/opponent. Candidate allowed yards come from the matched opposing offense; no dedicated allowed-yard column is certified here. Require both game sides.

Gross passing and net team passing differ. Candidate net passing subtracts positive sack yards lost, subject to verifying sign and official totals. Owner must approve gross/net convention; mirror it for defense. Rushing includes kneels/scrambles per dictionary. Denominators use eligible games completed before cutoff, including official overtime totals and excluding byes. Missing imports cannot become zeros or silently shrink samples. Reconcile sack-heavy, overtime and postseason examples before ranking implementation. PBP derivation is a possible fallback, requiring separate method and rights validation.

### Appearance and transfers

Stat rows alone do not establish all played-zero appearances; active rosters, injury reports and depth ranks do not prove play. The [snap-count dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_snap_counts.csv) documents `game_id`, `pfr_player_id`, `team`, `offense_snaps`, `defense_snaps`, `st_snaps`. Positive snaps offer candidate evidence, requiring a verified PFR-to-GSIS crosswalk. Offensive snaps and any-unit appearances are different eligibility rules; do not silently narrow the approved definition.

Snap bodies, identity crosswalk and real transfer examples are Not yet tested. Missing/zero snaps do not prove DNP. Positive appearance plus missing stats does not authorize zero-filling without verified reporting completeness. Retain unknown eligibility when uncertain. FTN participation is not a current-season remedy: official availability documentation says 2023-onward participation arrives after postseason. Exact hit-rate denominators remain unproven.

## Injuries and full depth charts

| Dataset | Actual listing / formats | Publication observation | Documented fields / gaps |
|---|---|---|---|
| Injuries | [Listing](https://github.com/nflverse/nflverse-data/releases/expanded_assets/injuries): `injuries_2024.csv`, `injuries_2025.csv`, `injuries_2026.csv`; also Parquet/RDS/compressed CSV | 2026 CSV: 2026-11-05 07:01:27Z | [Dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_injuries.csv): `gsis_id`, `team`, `season`, `season_type`, `week`, `position`, `report_status`, `practice_status`, injury descriptions, `date_modified`. Practice-day history, record timezone and full-position/team coverage unresolved. |
| Depth charts | [Listing](https://github.com/nflverse/nflverse-data/releases/expanded_assets/depth_charts): `depth_charts_2024.csv`, `depth_charts_2025.csv`, `depth_charts_2026.csv`; also compressed CSV/Parquet/RDS | 2026 CSV: 2026-11-05 15:23:26Z | [Current dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_depth_charts.csv): `dt`, `team`, `gsis_id`, `espn_id`, `pos_grp`, `pos_abb`, `pos_slot`, `pos_rank`. All-team offense/defense/ST coverage unverified; legacy 2024 columns not certified. |

Body probes: injury 2024 failed; injury 2026 query failed; injury 2025 Not yet tested. Depth 2026 failed; 2024/2025 Not yet tested. Listed 2026 CSV SHA256 anchors: injury `7ac1a6b6f69974ff172cea271f28dc01fca23c49ee170bcef7c1f4ac42549072`; depth `574f2c16b842a3fd5fbd506a01e991de2dcdbf37d683880665abbf56517c158d`. Neither hash was locally checked.

Official [availability schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html) documents schedules every five minutes, stats after game days with correction rechecks, and daily injuries/depth. From 2025 depth observations are timestamped/appended instead of assigned weeks. Six-hour polling cannot promise six-hour source freshness. `dt` is load time; `date_modified` is not assured original publication time. Fresh uploads can contain old records. Compare successive imports and record times before claiming cadence. Missing injury rows cannot mean healthy; missing depth entries cannot mean roster absence. Current reports must not appear as historical pregame evidence.

Potential gap remedies: links to official team injury reports/charts for manual research, or another lawful free dataset after terms/schema review. No replacement source or restricted scraping was used or certified.

## Odds provider distinction and $0 budget

**The Odds API — [the-odds-api.com](https://the-odds-api.com/)** advertises 500 monthly free credits, all sports/markets and most bookmakers. Its [NFL page](https://the-odds-api.com/sports/nfl-odds.html) documents free current NFL props. Keys above are from the [market list](https://the-odds-api.com/sports-odds-data/betting-markets.html), not authenticated responses. DraftKings/FanDuel are advertised examples; actual free book/player/event coverage is unverified. No credentials or key tests were used.

The [V4 guide](https://the-odds-api.com/liveapi/guides/v4/) documents event odds for props, costing unique returned markets times requested regions; explicit bookmakers count in groups of ten. Track `x-requests-last`, `x-requests-used`, `x-requests-remaining`; market discovery costs one credit. Illustrative arithmetic, not measured usage: ten returned markets in one region cost ten credits per event refresh; 500 credits permits at most 50 such refreshes before other costs. Keep requests on demand with hard caps and deduplication. Provider game/player mappings require validation; names are not GSIS identifiers. Account reset/overage behavior remains untested; no paid upgrade is permitted.

[Terms updated 2026-08-31](https://the-odds-api.com/terms-and-conditions.html) expressly permit indefinite storage, UI display and analytical use; attribution is optional. Standalone raw-data redistribution is prohibited. Posted terms support last-known caching, subject to recheck before integration/public release; they do not guarantee data availability or third-party trademark rights.

**TheOddsAPI — [theoddsapi.com/pricing](https://theoddsapi.com/pricing)** now redirects to [Betting Data API pricing](https://bettingdataapi.com/pricing). The preliminary NBA/MLB-only claim is outdated: free pricing includes NFL, 25 requests/day, moneylines only. Props require the paid Business tier. Thus it remains unsuitable for free NFL props. Retention terms and authenticated responses were not tested because it fails the free-prop gate. Manual lines remain the approved fallback.

## Licenses and public release

[nflverse-data LICENSE.md](https://raw.githubusercontent.com/nflverse/nflverse-data/main/LICENSE.md) is CC BY 4.0: retain attribution/license links and mark modifications. It grants only licensor-held rights and does not clear logos/headshots or unrelated third-party rights. Dataset-specific upstream NFL/ESPN/PFR/FTN restrictions remain unresolved; public access alone is not rights clearance.

The separate [nfldata repository](https://github.com/nflverse/nfldata) did not expose an explicit license in inspected root files; `/LICENSE` returned 404. This does not prove no permission exists elsewhere. Do not transfer nflverse-data's license to nfldata automatically. Establish applicable schedule permission before import. Future public release requires renewed rights review; private use is not blanket permission.

## Remaining verification gates

1. Obtain complete schedule bytes/revision/hash and applicable rights; calculate season/stage counts, uniqueness, nulls and team consistency; verify current 2026 and postseason availability.
2. Approve final/status/completion evidence and TBD handling; validate Eastern-to-UTC conversion with real examples.
3. Inspect all six weekly stats bodies, observed values/nulls and game joins; reconcile official totals and approve passing convention.
4. Prove played-zero/DNP eligibility and identity joins using special-teams-only and transfer examples.
5. Inspect injury/depth row times, all teams/units, legacy schemas and upstream rights; compare successive publications.
6. Only with separate owner authorization, perform a bounded free-key odds test and verify markets/books/credit headers and account restrictions.

No provider substitutions, implementations or new decisions are approved by this audit.
