# Downloaded schedule validation report

**Validation date:** 2026-11-05. **Scope:** complete CSV readability and detailed integrity for seasons 2024–2026. Research/validation only; no application implementation.

## Recommendation

**B. CONDITIONALLY READY to begin an owner-approved Milestone 1 implementation task.** Local structural checks pass, with a documented secondary-ID collision and unresolved exact release provenance. The owner approved UNKNOWN status whenever finality is unsupported. Neither time nor score presence establishes FINAL. This recommendation does not authorize coding in this task.

Mandatory implementation checkpoints: preserve this original artifact; retain its hash and owner-declared provenance; resolve or explicitly accept the provenance discrepancy before claiming verified official-release origin; use provider `game_id` plus canonical internal IDs, and quarantine ambiguous `old_game_id` aliases; preserve unknown status and nullable reported scores; revalidate every new snapshot. No fabricated future postseason fixtures or finality.

## Artifact and provenance

- File: `data/raw/games.csv`; size **2,188,859 bytes**.
- Independently calculated SHA-256: `66f7a71b12eeb8da8a5c332cfadb245da693aa66e2064fba734983dc41e68fd5`.
- Owner declaration: downloaded from official nflverse and supplied at this path. Exact download URL, retrieval timestamp, response headers and release revision were not supplied. Filesystem time is not download provenance.
- Documented intended source: [official schedule release](https://github.com/nflverse/nflverse-data/releases/tag/schedules), [CSV](https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv). This documents the source route, not independent origin authentication of these bytes.
- [Official asset listing](https://github.com/nflverse/nflverse-data/releases/expanded_assets/schedules), accessed 2026-11-05, reports CSV SHA-256 `0284c8bfa49ee3707d5d77844d264919c29a586378bb0304734e38ca65654583`, publication 2026-11-05T17:36:37Z. **It does not match this local file.** Mutable assets, a different snapshot or transfer changes could explain it; none is established. No corruption or authenticity conclusion follows from the mismatch alone.
- Local file has 7,549 LF terminators, no CR/CRLF, no UTF-8 BOM or NUL bytes, and a trailing newline. Replacing CRLF with LF leaves its hash unchanged, so local CRLF normalization does not explain the discrepancy. No normalization or other write was applied to the original.
- Evidence level: local bytes and structural results independently verified; official-release origin remains owner-declared and unverified. Published license evidence from the contract applies to the official release; do not misrepresent source identity.

## Entire-file readability

Strict standard-library UTF-8 decoding and CSV parsing reached EOF successfully: **7,548 data records**, **46 distinct columns**, seasons 1999–2026. No malformed row widths, blank records, duplicate headers or missing contract columns. All 7,548 provider game IDs are globally unique; no exact duplicate rows. Semantic checks outside 2024–2026 were not performed. All columns remain source strings in CSV; typed/domain validation below covers scoped fields rather than every optional statistic.

## Actual scoped counts

| Season | Rows / unique game IDs | REG | WC | DIV | CON | SB | Both scores present | Both scores missing |
|---|---|---|---|---|---|---|---|---|
| 2024 | 285 / 285 | 272 | 6 | 4 | 2 | 1 | 285 | 0 |
| 2025 | 285 / 285 | 272 | 6 | 4 | 2 | 1 | 285 | 0 |
| 2026 | 272 / 272 | 272 | 0 | 0 | 0 | 0 | 121 | 151 |

Total scoped records: **842**, of which **691** have paired scores and **151** have neither score. These are score-availability counts, **not confirmed-final counts**. All 842 authoritative game statuses remain UNKNOWN with this artifact alone.

2024 and 2025 are completed-season schedule archives with all expected round counts and paired scores. No per-game finality claim or external gamebook reconciliation was performed. 2026 is in progress: scores occur only in weeks 1–8 (121 records, source dates 2026-09-09 through 2026-11-02); weeks 9–18 have no scores (151 records, source dates 2026-11-05 through 2027-01-10). No 2026 postseason records exist in this file. Future unknown matchups are unpublished coverage, not invented rows to reach 13.

## Actual week distribution

| Source week | 2024 | 2025 | 2026 |
|---|---|---|---|
| 1 | 16 | 16 | 16 |
| 2 | 16 | 16 | 16 |
| 3 | 16 | 16 | 16 |
| 4 | 16 | 16 | 16 |
| 5 | 14 | 14 | 15 |
| 6 | 14 | 15 | 14 |
| 7 | 15 | 15 | 14 |
| 8 | 16 | 13 | 14 |
| 9 | 15 | 14 | 15 |
| 10 | 14 | 14 | 14 |
| 11 | 14 | 15 | 13 |
| 12 | 13 | 14 | 16 |
| 13 | 16 | 16 | 14 |
| 14 | 13 | 14 | 15 |
| 15 | 16 | 16 | 16 |
| 16 | 16 | 16 | 16 |
| 17 | 16 | 16 | 16 |
| 18 | 16 | 16 | 16 |
| 19 | 6 | 6 | 0 |
| 20 | 4 | 4 | 0 |
| 21 | 2 | 2 | 0 |
| 22 | 1 | 1 | 0 |

REG uses weeks 1–18; WC/DIV/CON/SB use 19/20/21/22. No unexpected round codes or round/week mismatches. Each season has the expected 32 source team codes, exactly 17 REG appearances per team and one missing REG week per team. No team occurs in two records in the same source week. All rows have distinct home/away teams. The expected-team allowlist is a validation baseline, not a separately authenticated team artifact.

## Required fields, types and dates

Scoped checks found zero missing values in `game_id`, `season`, `game_type`, `week`, `gameday`, `gametime`, `home_team` and `away_team`. All game IDs follow season_week_away_home and match their row components. Valid ISO dates, HH:MM times, weekday/date agreement and season-calendar bounds passed. Every known Eastern kickoff converted to UTC and round-tripped with installed `America/New_York` rules. This validates conversion mechanics, not the correctness of source scheduled times or their final broadcast slots. No whitespace-normalization anomalies occurred.

Scope date ranges: 2024: 2024-09-05–2025-02-09; 2025: 2025-09-04–2026-02-08; 2026: 2026-09-09–2027-01-10. No missing kickoff inputs in this snapshot; future snapshots must still allow unknown/TBD.

### Actual null counts for all source columns

Blank/NA/NULL tokens counted as null. Optional-field gaps are reported, not converted to zero.

| Source field | 2024 | 2025 | 2026 |
|---|---|---|---|
| `game_id` | 0 | 0 | 0 |
| `season` | 0 | 0 | 0 |
| `game_type` | 0 | 0 | 0 |
| `week` | 0 | 0 | 0 |
| `gameday` | 0 | 0 | 0 |
| `weekday` | 0 | 0 | 0 |
| `gametime` | 0 | 0 | 0 |
| `away_team` | 0 | 0 | 0 |
| `away_score` | 0 | 0 | 151 |
| `home_team` | 0 | 0 | 0 |
| `home_score` | 0 | 0 | 151 |
| `location` | 0 | 0 | 0 |
| `result` | 0 | 0 | 151 |
| `total` | 0 | 0 | 151 |
| `overtime` | 0 | 0 | 151 |
| `old_game_id` | 0 | 0 | 0 |
| `gsis` | 0 | 0 | 151 |
| `nfl_detail_id` | 285 | 285 | 272 |
| `pfr` | 0 | 0 | 0 |
| `pff` | 285 | 13 | 167 |
| `espn` | 0 | 0 | 0 |
| `ftn` | 0 | 0 | 0 |
| `away_rest` | 0 | 0 | 0 |
| `home_rest` | 0 | 0 | 0 |
| `away_moneyline` | 0 | 0 | 123 |
| `home_moneyline` | 0 | 0 | 123 |
| `spread_line` | 0 | 0 | 123 |
| `away_spread_odds` | 0 | 0 | 123 |
| `home_spread_odds` | 0 | 0 | 123 |
| `total_line` | 0 | 0 | 123 |
| `under_odds` | 0 | 0 | 123 |
| `over_odds` | 0 | 0 | 123 |
| `div_game` | 0 | 0 | 0 |
| `roof` | 0 | 0 | 25 |
| `surface` | 2 | 1 | 56 |
| `temp` | 103 | 95 | 227 |
| `wind` | 103 | 95 | 227 |
| `away_qb_id` | 0 | 0 | 122 |
| `home_qb_id` | 0 | 0 | 122 |
| `away_qb_name` | 0 | 0 | 122 |
| `home_qb_name` | 0 | 0 | 122 |
| `away_coach` | 0 | 0 | 0 |
| `home_coach` | 0 | 0 | 0 |
| `referee` | 0 | 0 | 207 |
| `stadium_id` | 0 | 0 | 0 |
| `stadium` | 0 | 0 | 0 |

## Scores and internal consistency

All present scores are nonnegative integer tokens. No one-sided missing score pairs. Every populated `result` equals home minus away and every populated `total` equals their sum. Overtime values are 0/1 or null; location values are Home/Neutral. Internal postseason progression agrees with reported score winners: WC winners advance into DIV; DIV/CON winners match the next round. This is internal consistency, not independent results verification.

| Season | Games with a legitimate zero score | Equal-score games |
|---|---|---|
| 2024 | 2 | None |
| 2025 | 7 | `2025_04_GB_DAL` |
| 2026 | 1 | `2026_05_NYG_WAS` |

The two equal-score games are REG records; no postseason tie was found. Zero scores must survive import. Paired historical scores can be retained as **reported scores, finality unverified**, never silently promoted to confirmed finals. No actual completion or actual kickoff timestamp exists in the header.

## Secondary identity issue: eight collisions

**Eight `old_game_id` values each occur twice in 2026: 16 distinct games, eight excess aliases.** These are different matchups with distinct primary `game_id` and ESPN IDs, not duplicate schedule games. The cause is unknown. Do not merge, delete, repair or invent replacement IDs. Keep the raw value as a nonunique source attribute, or quarantine only the ambiguous alias association. It cannot back a uniqueness constraint or automatic identity reconciliation.

| Shared old_game_id | Distinct provider game IDs |
|---|---|
| `2026122700` | `2026_16_TB_ATL`, `2026_16_CLE_BAL` |
| `2026122701` | `2026_16_CIN_IND`, `2026_16_LAC_MIA` |
| `2026122702` | `2026_16_WAS_MIN`, `2026_16_ARI_NO` |
| `2026122703` | `2026_16_NE_NYJ`, `2026_16_CAR_PIT` |
| `2027010300` | `2026_17_NO_ATL`, `2026_17_WAS_JAX` |
| `2027010301` | `2026_17_SEA_CAR`, `2026_17_KC_LAC` |
| `2027010302` | `2026_17_IND_CLE`, `2026_17_DEN_NE` |
| `2027010303` | `2026_17_NYG_DAL`, `2026_17_LA_TB` |

No non-null duplicates were found within any scoped season for `gsis`, `nfl_detail_id`, `pfr`, `pff`, `espn` or `ftn`. Empty IDs were excluded from duplicate tests. Their null coverage above prevents blanket non-null requirements. Primary-ID stability through future corrections remains untested.

## Approved status contract and remaining limits

- **UNKNOWN:** reliably representable for all 842 games because no explicit state/finality field or separate final evidence is available. A schedule row establishes a planned fixture and source kickoff value, not the current operational state.
- **FINAL:** zero independently established from this artifact; do not infer from kickoff, season completion, score presence, unchanged scores or observation time.
- **IN_PROGRESS / POSTPONED:** zero established; do not synthesize either state. No actual-end timestamp or historical pregame eligibility proof is supplied.
- **Reported score availability:** 691 paired and 151 absent; this is a separate data property from status. Label accordingly if displayed.
- Counts and team/week consistency cannot rule out a wrong-but-plausible matchup, score or kickoff. No independent official full schedule comparison was performed. All future kickoff slots remain source-reported and revisable.
- The official-release digest mismatch remains a provenance warning, not a clean-origin check. Obtain the owner download URL/time/version or a corresponding publisher checksum before calling origin independently verified; an explicit owner acceptance can instead retain the provenance as declared.
- Preserve attribution and the release-specific licensing limits already documented in contract section 11; this task does not independently settle a different artifact route.

## Verification actually run

Executed temporary Python 3 standard-library validation via shell: strict complete-file parse, SHA-256, header/width checks, global primary-ID/exact-row duplicate checks, scoped field null/type/domain checks, round/week structure, team appearances/byes, timezone round-trip, score pairing/arithmetic, secondary-ID uniqueness and internal playoff progression. No packages installed, application code written, services initialized or database objects created. Optional non-schedule columns were counted for nulls but not semantically certified.

The original file is read-only throughout this work; a final byte hash comparison is recorded in the contract after documentation verification. The validation commands are research checks, not application unit/integration/e2e tests.
