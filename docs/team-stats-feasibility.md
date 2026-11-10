# NFL Team Statistics and Rankings — Feasibility

Research date: **2026-11-09**. Branch: `feature/team-stats-feasibility`. **Research only; proposals below require owner approval.** Only this document is created. No application/schema changes, dependency installation, database access/imports, migrations, new endpoints, frontend work or git publication.

## 1. Assessment and evidence boundaries

**Recommended primary candidate:** nflverse weekly team statistics, joined to existing canonical games; use schedule-reported scores for points, subject to independent completed-game eligibility. Use nflverse play-by-play (PBP) as a bounded reconciliation/exception fallback, not a silent substitute. Neither candidate has passed full artifact validation in this environment.

**Readiness:** conditionally suitable for a separate offline validation implementation; **not ready to publish completed-game pregame rankings**. Exact current-season completeness, artifact schema/signs and finality/completed-before-cutoff evidence remain open. The limited schedule UNKNOWN contract deliberately did not solve historical statistical eligibility. Do not relax it to make rankings appear populated.

Evidence labels used throughout:

- **LOCAL:** independently read existing repository/artifact; no claim about current PostgreSQL contents.
- **DOC:** inspected official documentation, source code, release metadata or one official gamebook through the web reader. Listings and rendered examples are not downloaded season datasets.
- **UNVERIFIED:** artifact-dependent claim not tested because bytes were inaccessible.
- **PROPOSED:** implementation/methodology recommendation, not an approved statistical decision.

The owner reports schedule ingestion/API/dashboard/guarded refresh/current-week/freshness implemented and validated. These prior runtime results are user-reported. Some repository overview documents still describe older task boundaries and pending tests; they are historical, not evidence these features are absent. This report does not rewrite prior evidence or change binding definitions.

Inspected local sources: [AGENTS](../AGENTS.md), [README](../README.md), [PRD](product-requirements.md), [architecture](architecture.md), [data model](data-model.md), [decisions](decisions.md), [roadmap](implementation-plan.md), [source audit](data-sources.md), [schedule contract](schedule-data-contract.md), [validation report](schedule-validation-report.md), [ingestion](schedule-ingestion.md), [refresh](schedule-refresh.md), [freshness](schedule-freshness.md); [actual ORM models](../backend/app/models/schedule.py), [initial migration](../backend/alembic/versions/0001_schedule.py), [schedule validator](../backend/ingestion/validation.py), [reconciler](../backend/ingestion/service.py), [source retrieval](../backend/ingestion/source.py), [Compose](../compose.yaml).

## 2. Candidate sources and access results

### Primary: weekly team statistics

**DOC:** the official [team loader](https://raw.githubusercontent.com/nflverse/nflreadr/main/R/load_stats.R) supports week, REG, POST and combined summaries, using release assets since 1999 through the loader's current season. Choose **weekly**, not season-summary files, for game cutoffs. [Release notes](https://github.com/nflverse/nflverse-data/releases/tag/stats_team) identify `nflfastR::calculate_stats()` as the producer. Supported-season code is not proof every season/stage has complete records.

Exact CSV URLs, all listed in the official [team asset index](https://github.com/nflverse/nflverse-data/releases/expanded_assets/stats_team):

| Season | URL | Listed CSV size / update UTC |
|---|---|---|
| 2024 | https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2024.csv | 224 KB / 2026-08-13 16:49:13Z |
| 2025 | https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2025.csv | 224 KB / 2026-08-13 16:51:24Z |
| 2026 | https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2026.csv | 107 KB / 2026-11-09 14:15:12Z |

Advertised SHA-256 values, **not locally calculated or matched**:

```text
2024 b207a1430c2715d03bbf1844c4eae98695f364851ff6025f422febc2c13f5255
2025 91058a59d894855377b2f39f40c4e7bdbeef96d12144289dc68215209a1c93cb
2026 e08569e6a53934828417a8b1061424d7c0e9981b8fbafb4ffe0db5e8e6b7d9f6
```

CSV.gz, Parquet and RDS are also listed. CSV is sufficient for a future standard-library validator; no Python/R loader installation is needed. The three advertised CSVs total roughly 555 KB; mutable listing sizes/digests are observations, not promises about later retrieval.

**DOC:** nflverse's [availability policy](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html) describes stats/PBP builds after game days, with additional game-day builds, and recommends a Wednesday-night/Thursday recheck for corrections. This is neither a completeness SLA nor proof every row represents a finished game. Recheck after game days, reconcile weekly, and inspect actual coverage before publication. Do not attach schedule freshness timestamps to this separate dataset.

### Fallback/reconciliation: play-by-play

**DOC:** [PBP loader](https://raw.githubusercontent.com/nflverse/nflreadr/main/R/load_pbp.R) and [release](https://github.com/nflverse/nflverse-data/releases/tag/pbp) use:

```text
https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2024.csv
https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2025.csv
https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.csv
```

The [PBP asset index](https://github.com/nflverse/nflverse-data/releases/expanded_assets/pbp) lists CSV sizes 94.9 / 93.4 / 45.2 MB and corresponding `.csv.gz` sizes 18.5 / 18.2 / 8.85 MB. Rough totals: 233.5 MB CSV, 45.55 MB compressed. Observed CSV updates: 2024/2025 on August 13, 2026; 2026 on November 9, 2026. This is much larger than team summaries, shares upstream failure/correction risks, and is not an independent source of truth.

**DOC:** [PBP dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv) supplies team/game identifiers, stage/week, play identifiers, play classifications and score fields. It describes `start_time` as Eastern kickoff and `time_of_day` as a UTC clock string, not a complete completion timestamp. Its `game_id` description still says ten-digit ID; actual modern format needs artifact validation. `old_game_id` is legacy, never our unique key. Game-clock zero, final row, score fields or a file upload alone cannot establish completed-game eligibility.

**PROPOSED:** avoid naive sums of `yards_gained` for every pass/run. Sacks, no-play penalties, laterals, aborted plays and special teams need explicit rules. The [upstream calculator](https://raw.githubusercontent.com/nflverse/nflfastR/master/R/calculate_stats.R) uses supplemental play-stat records, not just one generic yardage sum. Reproducing it correctly can require those additional official releases and separate validation. Do not promise PBP alone is an immediately equivalent fallback. Manual official box-score comparison is an exception diagnostic; direct NFL document ingestion is not cleared by nflverse licensing.

### Actual retrieval log and limitations

Bounded attempts; no mirrors, access-control bypass or signed-URL replay:

| Method | Actual result | Interpretation |
|---|---|---|
| Local `curl -I --connect-timeout 10 --max-time 20` to 2024 team CSV | Exit 6, could not resolve `github.com` | Agent environment DNS failed; no response body downloaded |
| Web reader, direct release CSV for each of 2024/2025/2026 | All three failed with redirect/safe-open errors | No CSV header/rows obtained; errors contained expired-looking cached September signed redirects, not a verified current source outage |
| Official GitHub releases API, tag `stats_team` | Web reader reported inaccessible | JSON metadata/body alternative unavailable here |
| Web reader, official 2024 PBP `.csv.gz` | Same redirect/safe-open failure | No PBP bytes or decompression validation |
| Official loaders/dictionaries/release listings | Read successfully | Documentation/metadata evidence only |

The local DNS failure is environmental. The web failures are retrieval-tool/cache limitations with source availability unresolved; they do not establish missing assets, authentication requirements or a source prohibition. Downloads were not repeatedly retried. No team-stat/PBP season file was archived or hashed locally. REG/POST row counts, duplicates, null rates, team pairs, full score joins and representative nflverse yardage totals remain **UNVERIFIED for all three seasons**.

A search hit presented an unrelated NFL spectrum-analysis PDF as a statistics guide. Opening it exposed the mismatch; it was discarded. Statistical rules below reference the actual NFL GSIS guide, not that search snippet.

### Licensing and attribution

**DOC:** nflverse's [organization licensing statement](https://github.com/nflverse#licensing) explicitly covers release data under CC BY 4.0 except marked exceptions, including FTN. Neither inspected team/PBP release page advertises a different license. The [data repository license](https://raw.githubusercontent.com/nflverse/nflverse-data/main/LICENSE.md) is CC BY 4.0: preserve attribution/notices/license links, identify changes and avoid additional downstream restrictions. Commercial/noncommercial reuse and redistribution are supported within the grant. Code licenses are separate. This supports the private release-data MVP; it does not clear third-party marks or rights the licensor cannot grant. The [package terms](https://nflverse.nflverse.com/#terms-of-use) also defer underlying data rights to their owners.

Proposed attribution: “Team statistics: nflverse/nflfastR, sourced from NFL data via nflverse-data; CC BY 4.0; [exact asset URL], retrieved [actual UTC], measured SHA-256 [hash]. Changes: canonical identity mapping, net-passing calculation and opponent-derived allowed totals.” Retain any supplied additional credit. No FTN, logos or headshots are needed. Pin the applicable notices with each artifact; review rights again before public redistribution.

The official [2024 gamebook](https://static.www.nfl.com/gamecenter/7d3e8f84-1312-11ef-afd1-646009f18b2e.pdf) carries media-purpose/permission restrictions; the [NFL GSIS guide](https://www.nflgsis.com/gsis/documentation/stadiumguides/guide_for_statisticians.pdf) also restricts reproduction. They were consulted as references, not copied into a dataset or approved as an automated ingestion fallback. nflverse's grant must not be transferred to direct NFL PDFs. Further direct collection/redistribution permissions remain unresolved.

## 3. Statistics contract and definition choices

**DOC:** the [team dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_team_stats.json) documents `season`, `week` as numeric; `season_type`, `team`, `opponent_team` as character; `passing_yards`, `sack_yards_lost`, `rushing_yards` as numeric. It includes kneels/scrambles in rushing and distinguishes rushing versus passing laterals. Numeric documentation does not certify CSV token types, integer ranges, nullability or completeness. No direct total-team-points/points-allowed or passing/rushing-allowed field was established from this dictionary.

| Required metric | Proposed exact definition | Validation gate |
|---|---|---|
| Offensive passing yards | **Net team passing** = gross `passing_yards` + signed negative sack-yard adjustment | Owner must approve net versus gross; verify actual source sign first |
| Offensive rushing yards | Source `rushing_yards`, including recorded kneels/scrambles and overtime | Check gamebook examples; preserve negative/zero values |
| Defensive passing yards allowed | Matched opponent's **same net definition** | Both sides uniquely mapped and valid |
| Defensive rushing yards allowed | Matched opponent's `rushing_yards` | Both sides uniquely mapped and valid |
| Points scored | Canonical game's reported score for that side, with separate eligible-completion evidence | All team scoring, including defense/ST; do not reconstruct from offensive TDs |
| Points allowed | Same game's opposite-side score | Includes opponent defense/ST scores, not only points surrendered by defensive unit |

Net team passing is a **proposal**, not a silent change to existing “passing yards” requirements. Preserve gross passing and original signed sack field so a gross view remains possible without redownloading. Gross passing defense would mean opponent gross passing; never mix conventions in offense/defense comparisons.

**Important verified correction to older feasibility assumptions:** [nflfastR's rendered calculator example](https://nflfastr.com/reference/calculate_stats.html) explicitly shows negative `sack_yards_lost` (e.g. -10 and -57), in a **2023 player season example**, not a 2024–2026 team-file sample. Its producer sums sack stat yardage. Thus `gross - sack_yards_lost` is unsafe without sign validation. Proposed negative-sign adapter adds it; a proven positive-loss source version would instead subtract, with a different recorded adapter version. Never guess the sign from the column name or apply `abs()` to hide inconsistency. Actual target artifacts must settle this before computing net values.

**DOC:** the [2025 NFL GSIS guide](https://www.nflgsis.com/gsis/documentation/stadiumguides/guide_for_statisticians.pdf), pp. 8–15, distinguishes team net passing from passer gross yards, deducting sack losses from the former. Penalty enforcement can erase an attempt or preserve the play's statistics depending on enforcement spot and exceptions. Therefore penalty presence alone is not a valid exclusion filter, and penalty yardage is not offensive passing/rushing yardage. Official scoring governs fumbles/laterals/sack-versus-rush decisions; do not reclassify from descriptions. Conversion attempts have separate statistical treatment. Use source official-stat totals, including overtime, not custom regulation-only or kneel-adjusted approximations. A 2025 guide is definition evidence, not proof no rule changes occurred across all three seasons.

**PROPOSED validation types:** identities required nonempty strings; season/week finite integral values with stage-specific ranges; yardage finite signed integers (negative net passing/rushing allowed); scores nullable nonnegative integers; no NaN/infinity, rounding or missing-to-zero coercion. Required identity nulls reject. Missing metric fields block that metric; a reported zero is valid. Preserve original tokens/raw rows, not only converted values. If actual fields differ, fail for review rather than changing definitions.

**Future usefulness, DOC only:** team dictionary includes attempts/completions, TDs, turnovers, sacks, first downs, penalties, kicking/returns, EPA and CPOE. These could support later contextual research; EPA/CPOE are modeled and not interchangeable with official yardage. No validation, storage expansion, player research or implementation of those future metrics is authorized here.

## 4. Actual local validation and completeness findings

**LOCAL:** read original `data/raw/games.csv` fully using Python standard-library CSV; 7,548 data rows, 2,188,859 bytes, SHA-256:

```text
66f7a71b12eeb8da8a5c332cfadb245da693aa66e2064fba734983dc41e68fd5
```

This matches the previously recorded local artifact, **not independent authentication**; its old published-checksum discrepancy remains unresolved. It is not the latest refresh volume or a query of development PostgreSQL.

| Season | Local schedule games / unique IDs | REG | WC/DIV/CON/SB | Paired reported scores | Expected team-stat rows if fully covered |
|---|---:|---:|---|---:|---:|
| 2024 | 285 / 285 | 272 | 6/4/2/1 | 285 | 570 = 544 REG + 26 POST |
| 2025 | 285 / 285 | 272 | 6/4/2/1 | 285 | 570 = 544 REG + 26 POST |
| 2026 | 272 / 272 | 272 | absent | 121 | Not 544 completed rows now; up to 544 REG eventually |

Expected statistics counts are arithmetic, **not observed source counts or certified completions**. Each local season contains 32 team codes. The probe found no missing game/team/season/stage/week identities and no duplicate team/stage/week appearances. 2026 scored schedule dates span September 9–November 2; all 2026 schedule dates span September 9, 2026–January 10, 2027. These describe this old artifact, not current results. 2024/2025 are past seasons; 2026 is in progress and postseason is future/unavailable. Never require future games to have statistics or fabricate POST participants.

**DOC/LOCAL spot-check:** official 2024 Week 1 BAL at KC gamebook, p. 4, reports:

| Side | Gross pass | Sack losses (magnitude) | Net pass | Rush | Points |
|---|---:|---:|---:|---:|---:|
| BAL | 273 | 6 | 267 | 185 | 20 |
| KC | 291 | 10 | 281 | 72 | 27 |

The local row `2024_01_BAL_KC` has away/home scores 20/27: **one-game score match**. Arithmetic checks: 273−6=267; 291−10=281; 267+185=452, 281+72=353, matching the book's net offense. Opponent-derived BAL net passing/rushing allowed would be 281/72 and KC 267/185. These are gamebook facts/calculations, **not values verified in nflverse season files**. No 2025/2026 statistical sample or full cross-source comparison succeeded. The local scheduled 20:20 Eastern differs from the book's actual 19:44 CDT start (20:44 Eastern): scheduled kickoff is not guaranteed actual start. No schedule record was changed.

**Required future integrity checks, PROPOSED:**

1. Read full bytes/EOF and strict width/header; reject HTML, truncated transfer, duplicate headers/records, missing identity fields, invalid tokens and unexpected schema changes. Compare measured size/digest to contemporaneous metadata; check for publication races. Matching a publisher digest is integrity evidence, not independent NFL authentication.
2. Unique source game/team when present; additionally unique season/stage/week/team and reciprocal team/opponent pairs. Exactly two distinct sides per accepted game, matching canonical home/away membership; no self-opponents, orphans, unexplained alias changes or duplicated schedule matches.
3. Historical expected 570 team rows per season is a reconciliation target; verify actual REG/POST games and rounds, not just matching counts. Current coverage is a set of source-evidenced completed games; no denominator from remaining scheduled games. A one-sided game is incomplete and cannot produce allowed metrics.
4. Compare available scoring evidence against canonical reported scores; classify missing versus conflicting scores. If the team file has no points, record that schedule supplies them rather than claiming independent agreement. PBP score agreement, if tested later, shares the upstream and is corroboration, not independent finality.
5. Reconcile sack-heavy, negative/zero-yard, kneel-ending, overtime, penalty/no-play, lateral/fumble, neutral-site, REG and POST examples; include at least one real 2024, 2025 and 2026 game. Confirm signed sacks, passing convention and exact null behavior.
6. Compare newly retrieved full-season sets with accepted versions. Removed games/metrics, score changes, changed team pairs/identity and historical corrections require review; partial snapshots cannot replace accepted history. Do not label untested checks as passed.

## 5. Identity mapping and architecture compatibility

**LOCAL:** `Team.id` and `Game.id` are internal UUIDs. `TeamAlias` keys `(provider, source_team_code)`; games uniquely key `(provider, source_game_id)`. Schedule provider is `nflverse`. Current accepted codes are:

```text
ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LA LAC LV
MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS
```

The reconciler checks alias drift and retains UUIDs for narrowly evidenced source-ID corrections. Its scope/database/validation assumptions are schedule-specific; do **not** pass stats into this importer or widen its allowed source configuration. Existing raw game records/source artifact receipts and immutable archives provide patterns to reuse, not a ready stats importer. No stats model/table exists. No database rows or current aliases were inspected through SQL in this task.

**PROPOSED mapping:**

- Resolve exact provider aliases to current team UUIDs; reject unknowns. `LA` is the current schedule Rams code. Variants such as `LAR`, `JAC` or old franchise names are candidates for reviewed explicit mappings only, not observations of target-file values. Never join by display name or overwrite aliases automatically.
- Prefer source `game_id` plus team and cross-check season, stage, week, opponent, and both sides. The dictionary does not list game ID, but current producer source explicitly emits it for weekly output: a **schema-documentation discrepancy**, not proof the release CSV contains it.
- If genuinely absent, uniquely match `(season, season_type, week, team, opponent_team)` against canonical games. Require exactly one match and reciprocal other side. Do not construct an assumed home/away order from team names. Missing/ambiguous matches quarantine the pair; no synthetic games.
- POST maps explicitly to canonical `season_type=POST` and WC19/DIV20/CON21/SB22. Verify actual source week encoding; do not use calendar year for January postseason.
- Never use `old_game_id` uniquely. A stale stats source ID after schedule correction needs explicit crosswalk evidence/review; do not rerun heuristics or mutate schedule identity. Retain raw IDs and canonical UUID link per revision.

## 6. Proposed PostgreSQL model — no migration authorized

Keep FastAPI/service/repository layering, SQLAlchemy/Alembic, PostgreSQL and separate ingestion package; no new infrastructure or dependencies. Extend the existing conceptual `team_game_stats` only after an artifact-backed contract and owner schema approval.

| Proposed record | Fields / safeguards |
|---|---|
| Stats import batch | UUID; dataset/season; `SourceArtifact` FK; actual retrieval/recorded timestamps; observed publisher revision/digest; parser/definition version; counts/coverage/validation result; accepted/superseded status. No source publication time invented |
| Immutable team-game revision | UUID; canonical game/team/opponent FKs; batch/artifact FK; raw source game/team IDs; raw row JSONB and row hash/line; nullable signed integer gross passing/sack adjustment/rushing; numeric-definition version; recorded timestamp; predecessor/supersession reference |
| Accepted pair selection | Canonical game plus dataset/definition version points to one validated batch/pair revision; publish both sides atomically; unique game/team within that selection; no silent overwrite of revision history |
| Completion/cutoff evidence | Canonical game FK; explicit evidence kind/reference/artifact/hash; finality verification observation; actual completion UTC or defensible completion upper bound when supported; uncertainty/disposition and verifier/method. Separate from schedule's UNKNOWN status unless separately authorized |

Enforce team/opponent differ and belong to canonical game's two sides through transactional validation (cross-row SQL checks need deliberate design, not a misleading simple CHECK). Row uniqueness alone does not guarantee a complete pair. Index game/team and accepted team/season/stage access, using canonical game joins for cutoff. Missing != zero; signed yards are permitted. Revision/batch foreign keys restrict deletion; no cascade replacing schedule history.

Prefer deriving allowed yards from the accepted opponent revision, not separately mutable duplicated defense totals. Points can be read from canonical scores with schedule artifact/version provenance. For reproducible historical outputs, record the exact schedule score/kickoff evidence hash/version used alongside stats revisions; current schedule updates must not silently rewrite a saved ranking result. Do not duplicate schedule scores as independently certified facts. A future approved cutoff service should combine independent stats quality/eligibility with schedule identity while leaving schedule status behavior unchanged.

At most 1,710 team-game rows for three fully covered 285-game seasons before revisions; the existing 842-game schedule represents 1,684 possible sides, not current completed-stat coverage. Normalized selected metrics should be small (planning allowance under 20 MB including indexes/basic revisions, **not measured**); raw JSON/history/index choices can change that. Keep full raw archives, store selected fields, and avoid loading full PBP into PostgreSQL initially. Streaming gzip/CSV is possible with the standard library; actual peak memory/row counts remain unmeasured. Daily full team snapshots are cheap individually but retention/revisions still need policy; do not auto-prune evidence.

## 7. Pregame ranking methodology — proposal for approval

### Eligibility is a separate gate

A stats row, both scores, a prior scheduled kickoff, a nightly upload, or a “past season” label is **insufficient** completion evidence. The current model only has scheduled kickoff, optional final evidence URL/verification observation, and UNKNOWN/FINAL; it has no actual end instant. `final_verified_at` is when verification occurred, not actual completion. Even FINAL alone cannot prove completion before a historical target.

For target game's cutoff `C`, eligibility requires all of:

1. Same season and selected stage (REG/POST separate), different canonical game; no inclusion of target itself.
2. Verified game completion with evidence establishing **completion strictly before C**. A trusted actual end instant or documented upper bound `< C` works; a final observation made before C can bound completion. A final document fetched today cannot be backdated to establish every historical cutoff.
3. Valid accepted two-team stat pair, correct identities and the relevant metrics, with no unresolved integrity dispute. Preserve both statistical-quality and completion-evidence exclusions.
4. Known target kickoff. Use canonical scheduled UTC as the current product target with a disclosed scheduled-time basis; actual-start/postponement differences need evidence/review. Unknown or disputed target kickoff means unavailable historical ranking, not “use now.”

A proposed operator evidence manifest could supply supported game-specific completion-before bounds without changing schedule status. Merely approving a score or selecting an old date is not evidence. PBP terminal descriptions plus UTC play-clock strings may help future verification but lack a certified full completion timestamp/coverage here; fourth-quarter clock zero can precede untimed downs/overtime. Do not infer end from kickoff plus a fixed duration, midnight, `max(time_of_day)`, or a prior week number. Ended/abandoned/suspended games need explicit adjudication; no invented statuses.

Without this evidence, show “completed-game eligibility unverified,” null rank/average and missing-coverage reasons. This can leave all current UNKNOWN games ineligible for rankings; that is preferable to violating the approved historical cutoff rule. An alternative “reported box-score” exploratory view would be a **separate explicitly approved limitation**, not completed-game/pregame research.

### Aggregation, denominators and ties

For each team and each metric, use the eligible set `E(team, season, stage, C)`:

```text
average = sum(accepted metric for game in E) / count(E)
```

Count games, not weeks or raw stat rows; no season totals ranking. Use both sides' matching definitions, retain official overtime totals and report games counted, expected/evidenced games, omitted games and reasons. Four yardage ranks plus points-for/game and points-against/game:

- Passing/rushing offense and points scored: higher average ranks first.
- Passing/rushing allowed and points allowed: lower average ranks first (#1 = fewest allowed).
- **Proposed ties:** competition ranks (1, 2, 2, 4). Equal exact averages share rank; alphabetical canonical code then UUID stabilizes presentation only. Compare integer sum/count rationally (cross-multiplication or exact numeric), not rounded UI values or floating tolerances. Rank after cutoff/stage filtering; never rank by code to break a statistical tie.
- Zero eligible games: null average/rank, never 0 or tied-first. Week 1 may have no sample; a team's first game later in Week 1 may legitimately face a league with some earlier completed games. No preseason or prior-season carryover.
- Byes have no game and no denominator contribution. Postseason participants begin POST samples at zero; do not borrow REG for first-round ranks. Optional combined mode is later approval and must be explicitly keyed/labeled.
- Postponed/resumed games follow evidenced completion relative to C, not nominal week. Same-day earlier games can qualify only if the end-before-C evidence is reliable; overlapping games cannot. Strict equality at cutoff is excluded.
- In-progress 2026 means partial-season samples, not a flawed season-total denominator. Count actual eligible games; disclose unequal sample sizes without inventing weights or minimum-game rules.
- **Proposed missing-data policy:** do not silently divide by available rows. Track completion-evidenced games separately from valid stat games. With missing required values/pairs, withhold that team's official metric rank/average and label incomplete; optionally display a separately labeled observed-sample average, not comparable as a full-coverage rank. Show rank population and league completeness; do not advertise a complete 32-team ranking when coverage is partial. Require no known unresolved omissions before publishing a complete league table.

### Historical leakage and correction modes

Default proposed mode: **reconstructed pregame** — latest accepted corrections, but only games evidenced completed before C. Label it reconstructed using today's corrected data, not what was knowable/published at the time. Do not accidentally include later-week results from precomputed season summary files.

A true **as-known-at-time** mode requires retained artifact/revision observations available by C, score/kickoff versions, and contemporaneous completion evidence. Current release files do not prove past publication availability; ingestion today cannot manufacture it. Store observed times now for future audit, but do not promise backfill of historical knowledge. Cache/result keys must include target UUID, cutoff basis/value, season/stage, metric/eligibility/definition version, stats and schedule/evidence revisions; corrections or kickoff changes invalidate affected results. No materialized ranking table/cache service is needed initially.

## 8. Update, historical correction and rollback strategy

**PROPOSED:** manually invoked staged process first, no scheduler activated. Fetch immutable full-season team snapshots through approved official URLs; record measured SHA-256/size, actual retrieval, publisher metadata and unavailable-verification distinctions. Existing DECLARED schedule provenance/checksum limitations remain independent of new team evidence. Reuse archive/receipt safety patterns while keeping a distinct dataset/config and future stats metadata; do not repurpose the schedule-only refresh status as stats freshness.

Validate outside a transaction, resolve against a locked/rechecked canonical baseline, produce row/pair/coverage diffs, then explicitly reviewed transactional acceptance. Unchanged hashes/rows are idempotent; no-op observations must not claim metric changes. Corrections to yards, scores, identities, lost rows, changed stages or historic snapshots require review; reject ambiguous/disappearing/partial replacements and preserve last-good selection. Never modify schedule fields as a side effect. Accept both team revisions and their publication pointer together or roll back all database changes. Failed retrieval/validation must not advance successful-data-change time.

Proposed operation: check after game-day processing is available, Thursday correction recheck, weekly full reconciliation of supported seasons, bounded retry/backoff and manual exception review. These are future policy proposals, not active jobs or a guaranteed source freshness interval. Restated history must identify changed rankings and retain prior revision evidence. Logical rollback selects a previously validated pair/batch under explicit review; it does not delete archives or restore a database backup without approval.

## 9. Risks and concrete gates

| Issue | Assessment | Required action before acceptance |
|---|---|---|
| Free release source/rights | Documented feasible with attribution and stated limits | Capture notices/revision with real artifacts; no direct NFL-PDF redistribution assumed |
| Complete 2024–2026 artifacts/schema/nulls/pairs | Blocked here by retrieval environment | Obtain official season CSVs in normal WSL or owner-supply immutable copies with source receipts; run offline validator |
| Gross versus net passing | Unapproved semantic choice | Owner approve net-team definition (recommended) or explicitly choose gross; verify target-file sack sign before either adapter |
| Finality/completed-before-cutoff | Blocks responsible pregame publication | Approve and supply evidence-backed eligibility/bounds; unknown must stay excluded, not inferred from schedule scores |
| Game ID/dictionary mismatch and aliases | Partially documented only | Verify exact headers/source keys and reciprocal canonical joins; review unmatched identities |
| Points source | Schedule available, not independently verified completion | Keep schedule provenance and reported label; reconcile independent evidence if used for completed metrics |
| Historical as-known reconstruction | Not available from present snapshots alone | Offer only labeled reconstructed corrected history; true historical publication mode deferred |
| Existing schedule provenance/actual start | Known unresolved checksum and scheduled/actual distinction | Preserve limitations; no stats feature silently “authenticates” or repairs schedule |
| Schema and model | Proposal only | Separate owner approval of contract/schema before migration implementation |

No full team-stat download, complete-season verification, actual PBP aggregation, real stats/database join or ranking test execution is claimed. This documentation task has no application test changes; running application suites would not validate the inaccessible data. Performed checks were official-source review, read-only CSV/hash/count/identity probes, one official gamebook arithmetic/score comparison, and document/diff checks.

## 10. Narrow next implementation task — for approval

**Proposed: Offline Team Statistics Contract Validator and Audit Report.** No PostgreSQL writes/schema/API/frontend/scheduler. Use supplied/captured official weekly CSVs, existing read-only schedule snapshot and an explicitly approved passing convention. Implement a pure validator and deterministic report, retaining source receipts and missing-evidence limitations; do not implement rankings publication or statistics ingestion yet.

Acceptance criteria:

1. Full 2024–2026 artifact readability, measured hashes, actual source receipts/metadata and observed exact schema/types/nullability; no replacement of original raw files. If retrieval is blocked, fail clearly and accept an owner-provided artifact with declared-origin limitations.
2. Historical REG/POST counts against 570 team-row targets each; actual current-season observed coverage separately; uniqueness, reciprocal pairs, canonical-source matching and quarantine/error counts. No synthetic/future game rows or zero-filled metrics.
3. Approved gross/net adapter validated against real signed sacks, rushing and score checks; representative regular/postseason, overtime, penalty/kneel and at least one game from each season. Report missing independent comparison rather than fabricating a pass.
4. Explicit completion-evidence inventory and strict cutoff eligibility demonstration on real evidence where available; no UNKNOWN-to-FINAL writes and no eligibility from scores/time alone. If evidence is absent, all affected eligibility remains unknown and the report blocks publication.
5. Synthetic tests for duplicates, partial files, null versus zero, signed/negative totals, mismatched pairs/aliases/stages, ambiguous IDs, coverage loss, same/unknown cutoff and incomplete completion evidence. No installs/new dependencies needed beyond existing stack/standard library.
6. Deliver reproducible report and final proposed artifact-backed field contract, with blockers called out. Only after owner review propose database schema/import implementation as its own gated task.

The next task is not authorized by this report. Stop for owner review; no commit, merge, push or deployment.


## Owner-approved follow-up

The owner subsequently approved NET team passing (including sacks), preserving gross and original sack values and requiring artifact-specific sign validation. The [offline validator guide](team-stats-validation.md) supersedes the net-versus-gross decision gate above and records implementation/test evidence. The earlier research findings remain historical; real artifact completeness and completed-before-cutoff evidence are not established by that approval. No statistics schema/import/rankings publication is authorized.
