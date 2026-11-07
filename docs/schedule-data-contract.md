# Schedule Data Contract — Milestone 1

**Research date:** 2026-11-05. **Current status:** the owner approved foundation/schema implementation only after the section 12 validation; section 13 records the implementation boundary. Prior research sections retain their historical scope statements. No importer or frontend is implemented.

**Latest assessment:** see section 12 and [the local validation report](schedule-validation-report.md). Recommendation **B. CONDITIONALLY READY** to begin a separately approved Milestone 1 implementation task. The owner approved UNKNOWN status when finality is unsupported, and supplied a locally readable artifact. Primary integrity checks pass; eight secondary-ID collisions and a release-checksum mismatch require the safeguards below. Sections 1–11 record earlier research and are superseded where updated in section 12. No implementation starts in this validation task.

## 1. Evidence labels and conclusion

- **Downloaded-data verified (D):** complete bytes retrieved locally and parsed. **No schedule artifact achieved this level in this task.** No measured counts, hashes, duplicates, null rates or full integrity results are available.
- **Official-documentation verified (O):** inspected provider documentation, loader source, license or asset metadata. This establishes what is published/documented, not whether all rows conform.
- **Web sample observed (W):** actual raw CSV header/selected rows exposed by the web reader. This is stronger than a documentation example, but is not a complete local download or independent validation.
- **Proposed / unverified (P):** contract behavior, expected invariants, calculations or assumptions awaiting approval or data verification.

**Recommendation: retain the implementation hold.** Official schedule release files and a supported Python loader path are now confirmed at documentation/metadata level. Full season integrity, status/final evidence and upstream rights remain open. No conclusion below claims complete downloaded-data verification. The proposal preserves the approved stack and business rules.

## 2. Sources, retrieval and alternative methods

All accesses in this document occurred on **2026-11-05**. Links to branches and release tags are mutable; none is an immutable snapshot of the bytes inspected.

| Ref | Official source | Evidence and result |
|---|---|---|
| S1 | [nfldata games.csv](https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv) | W: header and selected 2024–2026 rows readable through web; local curl failed DNS, exit 6 |
| S2 | [nflreadr loader source](https://raw.githubusercontent.com/nflverse/nflreadr/main/R/load_schedules.R) | O: loads nfldata `data/games.rds`; no package installed/run |
| S3 | [Schedule dictionary CSV](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_schedules.csv) | O: field meanings, Eastern time, stages and scores; type errors noted below |
| S4 | [nflreadr reference](https://nflreadr.nflverse.com/reference/load_schedules.html) | O: typed output example for 2020, not a 2024–2026 data probe |
| S5 | [Schedule release](https://github.com/nflverse/nflverse-data/releases/tag/schedules) and [expanded assets](https://github.com/nflverse/nflverse-data/releases/expanded_assets/schedules) | O: CSV, CSV.gz, Parquet, RDS and timestamp files listed; bodies not validated |
| S6 | [nflreadpy schedule loader](https://raw.githubusercontent.com/nflverse/nflreadpy/main/src/nflreadpy/load_schedules.py) and [downloader](https://raw.githubusercontent.com/nflverse/nflreadpy/main/src/nflreadpy/downloader.py) | O: uses release path `schedules/games`, filters seasons; CSV reader accepts empty/NA/NULL as nulls |
| S7 | [Update availability](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html) | O: schedule update interval documented as five minutes in season; not a measured freshness guarantee |
| S8 | [Team aliases](https://nflreadr.nflverse.com/reference/team_abbr_mapping.html), [normalization](https://nflreadr.nflverse.com/reference/clean_team_abbrs.html), [team loader](https://raw.githubusercontent.com/nflverse/nflreadr/main/R/load_teams.R) | O: alias support and team lookup artifact; actual lookup body not tested |
| S9 | [NFL schedule structure](https://operations.nfl.com/calendar-events/nfl-schedule/making-the-schedule), [playoff expansion](https://amp.nfl.com/news/owners-approve-expanding-postseason-to-14-teams-0ap3000001107961) | O: league schedule/format references for expected-count checks, not source completeness |
| S10 | [nflverse-data license](https://raw.githubusercontent.com/nflverse/nflverse-data/main/LICENSE.md), [nflverse terms notice](https://nflverse.nflverse.com/), [nfldata README](https://raw.githubusercontent.com/nflverse/nfldata/master/README.md) | O: rights evidence and limits; see section 8 |

### Public download alternatives examined

| Method / exact URL | Outcome / limitation |
|---|---|
| [Release CSV](https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv) | Web fetch failed on release-assets redirect; not downloaded |
| [Release Parquet](https://github.com/nflverse/nflverse-data/releases/download/schedules/games.parquet) | Same redirect failure; physical column types/nulls unverified |
| [Release gzip CSV](https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv.gz), [release RDS](https://github.com/nflverse/nflverse-data/releases/download/schedules/games.rds) | Listed by S5; individual body downloads not tested |
| [GitHub raw CSV route](https://github.com/nflverse/nfldata/raw/refs/heads/master/data/games.csv) | Web redirects to raw.githubusercontent.com and exposes samples; local curl failed DNS |
| [Loader's raw RDS](https://github.com/nflverse/nfldata/raw/master/data/games.rds) | Web reports unsupported application/octet-stream; not parsed |
| [GitHub Contents API](https://api.github.com/repos/nflverse/nfldata/contents/data/games.csv) | Local curl failed DNS; web root contents probe inaccessible. File-level API body not web-verified |
| [Repository ZIP](https://codeload.github.com/nflverse/nfldata/zip/refs/heads/master) | Local curl failed DNS; archive not retrieved |
| [Release metadata API](https://api.github.com/repos/nflverse/nflverse-data/releases/tags/schedules) | Web tool inaccessible; no asset API retrieval completed |

S5 lists `games.csv` at **2026-11-05T17:36:37Z**, with publisher SHA256 `0284c8bfa49ee3707d5d77844d264919c29a586378bb0304734e38ca65654583`. This is an observed metadata anchor, **not a locally verified digest**. Release and raw repository versions were not compared. A tag's source commit does not identify mutable asset bytes.

P: prefer the public release CSV for the first reproducible inspection, subject to rights closure and owner approval; compare against raw CSV before adopting either. This is a download recommendation within nflverse, not an approved provider change. CSV avoids needing a new parser dependency during research. Supported loaders are documented alternatives, not proof that installing one would bypass DNS failure. No access controls were bypassed and no authenticated/paid endpoint was used.

A request to NFL.com for a 2026 postseason schedule redirected to its generic schedule page. It did not establish historical/current postseason coverage. NFL.com is not certified here as an alternative machine-readable feed. No undocumented NFL/ESPN endpoint is adopted for status enrichment.

## 3. Coverage and completeness

S1 web samples show 2024/2025 REG and postseason records, and 2026 REG opening games plus future week-18 rows. The web-rendered file ends with `2026_18_DAL_WAS`. This supports apparent coverage, not exhaustive per-stage totals or current-week freshness. It does not verify the separate release body.

| Season | REG expected baseline (P, informed by S9) | POST expected baseline (P) | What was observed (W) | Complete downloaded-data status |
|---|---|---|---|---|
| 2024 | 272 games; 32 teams × 17 appearances | 13 games: WC 6, DIV 4, CON 2, SB 1 | Opening REG; WC/DIV/CON examples in prior audit; SB boundary rechecked | Unverified; no parsed counts |
| 2025 | 272 games; same team-game baseline | Same 13-game baseline | Opening REG, CON and SB boundary; other postseason examples in prior audit | Unverified; no parsed counts |
| 2026 | 272 scheduled REG games expected even while results are partial | Same format baseline, subject to current rules verification | Opening REG and future week 18; no POST after end of returned file | REG integrity unverified; POST not available in inspected view |

Expected totals describe the normal format, not measured results. NFL documentation supports 17 games over 18 weeks and the 14-team postseason; the 13-game total follows single-elimination arithmetic. Confirm exceptional cancellations/format changes before making baselines unconditional. Do not claim 285 verified rows per historical season from these expectations or from line-number boundaries.

Season is the football season, not calendar year: January/February playoff games retain the preceding season label. For 2026, future playoff participants cannot be supplied in November. P: allow the postseason selector to report “matchups not yet published” with a source check time; do not create games, teams or dates for missing bracket slots. A missing 2024/2025 round is instead a historical coverage failure. Owner must approve this future-coverage behavior for Milestone 1.

## 4. Schema and proposed mappings

### Observed source header (W, S1)

CSV has text tokens without embedded type/nullability declarations. The observed header contains these **46 names**, in this order; this is not Parquet schema verification:

```text
game_id,season,game_type,week,gameday,weekday,gametime,away_team,away_score,home_team,home_score,location,result,total,overtime,old_game_id,gsis,nfl_detail_id,pfr,pff,espn,ftn,away_rest,home_rest,away_moneyline,home_moneyline,spread_line,away_spread_odds,home_spread_odds,total_line,under_odds,over_odds,div_game,roof,surface,temp,wind,away_qb_id,home_qb_id,away_qb_name,home_qb_name,away_coach,home_coach,referee,stadium_id,stadium
```

S3 labels several identifiers numeric despite alphanumeric examples. S4 explicitly shows `game_id` as character, season/week/scores as integers, and distinguishes character from numeric provider IDs. Do not treat the dictionary's numeric label as an ID parser contract. Exact physical types for 2024–2026 RDS/Parquet remain unverified.

### Minimum schedule contract (all target types/rules are P)

“Required column” differs from “non-null value.” Preserve source tokens and normalized values separately in future ingestion. No field below is a SQL migration proposal.

| Source | Proposed domain field / type | Null / validation contract | Evidence |
|---|---|---|---|
| `game_id` | provider game ID: string | Required nonblank; unique per provider snapshot; never parse as number | O/W |
| `season` | season: integer | Required; only 2024/2025/2026 in this slice | O/W |
| `game_type` | source round: string; derived stage | Required known code; map REG→REG, WC/DIV/CON/SB→POST; preserve round | O/W |
| `week` | source week: integer | Required; check stage/round compatibility; do not renumber silently | O/W |
| `home_team`, `away_team` | provider team code: string; canonical references | Both required, known, distinct; designated sides retained at neutral sites | O/W |
| `gameday` | Eastern date: date or null | Column required; ISO date when present; unknown date preserved as null | O/W; null permission P |
| `gametime` | Eastern scheduled kickoff time: time or null | Column required; valid HH:MM when known; unknown/TBD allowed, no midnight default | O/W; scoped null rate unknown |
| date + time | `scheduled_kickoff_utc`: aware instant or null | Derived only when both known and valid; no UTC source column | P from O |
| `home_score`, `away_score` | reported scores: nullable integers | Columns required; nonnegative, pair consistency; blanks remain null; zero valid | O/W |
| `location` | neutral-site indicator: nullable boolean | Home→false, Neutral→true; unknown→null with diagnostic, never swap sides | O/W; target P |
| `overtime` | nullable boolean | 0/1 only when present; blank is unknown | O/W; target P |
| `result`, `total` | optional consistency checks: nullable integers | If present require home−away and home+away; neither proves final | O/W; validation P |
| `old_game_id`, `gsis`, `nfl_detail_id`, `pfr`, `pff`, `espn`, `ftn` | external game mappings: nullable strings | Optional; preserve lexical form; conflicts investigated, not overwritten | Header W; meanings partly O |
| `stadium_id`, `stadium` | optional venue ID/name: nullable strings | Unknown venue allowed; venue change does not create new game | O/W; target P |
| none | canonical game/team IDs | Stable application-owned identities mapped to provider aliases | Approved architecture; matching rules P |
| none | game status / status evidence | Nullable or UNKNOWN until supported; see section 6 | Header absence W; target P |
| none | actual kickoff / actual completion instants | Unknown; scheduled kickoff is not actual start/end evidence | Unverified |

Source `weekday` is redundant display context; derive/check against the Eastern date. Remaining betting, weather, coaching, QB and surface fields are outside the minimum Milestone 1 mapping. Do not infer additional features from their presence. A full artifact may retain them for provenance only after permission is settled.

Null policy P: align CSV normalization with S6's empty/NA/NULL handling, retaining original tokens; field-aware whitespace/TBD handling must be recorded. Malformed nonempty values are errors, not silently null. Actual null counts and lexical variants for each season are **not verified**. Future rows observed through the web have blank scores and some blank external IDs; global non-null guarantees are unsupported.

## 5. Stable identities and corrections

O: S3 defines the human-readable game ID from season/week/away/home. Neither documentation nor one snapshot proves permanence through rescheduling, team-code fixes or provider corrections.

P: use application-owned immutable game IDs for deep links. Maintain `(provider, provider_game_id)` mappings and history. A change in kickoff/venue is a revision of the same game when identity matches. If a source ID changes, use corroborating external IDs and season/sides to propose reconciliation; ambiguous matches are quarantined. Never merge solely by date, team names or guessed ID decomposition. Reversed sides and conflicting external IDs require review. Optional provider IDs must not be globally required before their coverage is measured.

O: team identifiers in the schedule are abbreviations, not universal numeric franchise IDs. S8 documents normalization including LAR→LA and legacy relocation aliases; actual 32-team lookup bytes are unverified. P: persist source codes with a versioned mapping to canonical teams; reject unknown codes instead of fuzzy matching. Keep LA (Rams) separate from LAC (Chargers). Scope aliases by provider/season and retain original labels. Do not rewrite game IDs after alias normalization. Stable franchise semantics must not depend on display names, logos or stadium IDs.

## 6. Status, kickoff and score handling

### Time contract (P based on S3)

Combine Eastern date/time using IANA `America/New_York`, then convert to UTC. Use date-specific daylight-saving rules, never a fixed UTC−5 offset or stadium-local timezone. Display a named/explicit timezone, including when UTC conversion changes the date. Store the original schedule inputs and conversion provenance. Unknown/TBD kickoff stays unknown; ambiguous/nonexistent local times need review. Future kickoff is provisional and must remain correctable, especially flex games.

Derived examples, **not downloaded-data tests**: a documented sample kickoff of 2024-09-05 20:20 Eastern converts to 2024-09-06T00:20:00Z; 2025-02-09 18:30 Eastern converts to 2025-02-09T23:30:00Z. Both calculations were checked successfully using installed Python 3 timezone rules. Future importer tests must also cover international venues and schedule changes. Current scheduled values are not guaranteed original or actual kickoff times.

### Evidence-driven status proposal

No source `status`/`completed`/`completed_at` column was observed. The contract must distinguish source facts from derived display state:

| Evidence available | Proposed handling (P) |
|---|---|
| No scores; future scheduled kickoff | “Scheduled — status inferred” is possible only with owner approval; preserve UNKNOWN authoritative status |
| No scores; past/unknown kickoff | UNKNOWN / result unavailable; do not call cancelled, postponed or DNP |
| Both scores present; finality unconfirmed | Retain reported scores; do not label final or render them as confirmed completed scores |
| Explicit reliable final evidence plus valid scores | FINAL; publish final scores with evidence/source/as-of metadata |
| Reliable explicit in-progress/postponed/cancelled evidence | Map to that state; no certified enrichment source currently exists |
| One score missing, negative/nonintegral score, contradictory evidence | Validation failure; preserve last-good publication and flag affected record |

Do not infer FINAL because kickoff was hours ago, because scores stopped changing, or because an arbitrary duration elapsed. A historical completed-season reconciliation could establish final scores, but it has not been performed. Do not erase legitimate 0 scores. Regular-season ties may be valid; postseason ties require investigation. Revisions to previously final scores retain correction history.

A source upload/fetch timestamp is not completion time. Milestone 1 need not implement rankings, but its contract must not invent future cutoff evidence. Actual completion timestamps and historical scheduled-versus-actual kickoff reconciliation remain unresolved for later cutoff-safe research; they do not authorize relaxing the approved rule.

## 7. Integrity and publication acceptance checks

All checks below are **proposed requirements, not executed results**. No application tests were written/run.

| Check | Required behavior / acceptance |
|---|---|
| Transport and provenance | Reject HTML/error pages/partial downloads; record requested/resolved URL, retrieval time, content length, revision/asset metadata, own SHA256 and license reference |
| Schema drift | Require contract columns; reject missing/duplicate headers; log additional columns; validate types before publication |
| Duplicate records | Compute raw and normalized duplicate counts. Identical repeated rows reported and deterministically collapsed; conflicting rows for one provider ID block publication pending reconciliation |
| Secondary identity conflict | Check non-null external IDs within provider namespace and season; do not collapse missing IDs together; collisions/sides disagreement quarantined |
| Schedule structure | Check season/stage/week, distinct valid sides, one game per team/week as a diagnostic; documented rescheduling exceptions need review, not deletion |
| Full REG coverage | For each season check 272 unique scheduled games, 32 canonical teams, 17 appearances each and expected bye structure; compare actual matchup set against independent official records, not just totals |
| Historical POST coverage | Verify counts 6/4/2/1, round progression, participants and unique games; a duplicate cannot compensate for a missing game |
| Future POST | Track unpublished coverage separately from historical missing data; no synthetic rows to reach expected totals |
| Times | Validate formats, DST-aware conversion, unknown values, changes and date boundaries; timestamps need not be non-null for every published matchup |
| Results | Check paired scores, zero preservation, final evidence, ties and arithmetic; quarantine contradictions |
| Revision behavior | Reimport same bytes idempotently; retain kickoff/venue/score changes and identity aliases; disappearance never silently deletes a game |
| Atomic publication | Invalid/truncated replacement must not overwrite last-good data; publish a complete validated import or explicitly reviewed partition, with visible coverage/staleness |
| Freshness | Distinguish fetched time, provider publication time and per-record time; no row timestamp can be fabricated. Keep approved daily schedule ingestion; five-minute upstream cadence does not authorize a scheduler change |

Before closure, produce measured per-season/per-round counts, duplicate/conflict counts, every required-field null count, team-game counts, unknown aliases, malformed timestamps, score-pair inconsistencies and unresolved statuses. Expected values above are not substitutes for that report.

## 8. Licensing, attribution and permitted use

O: S10 shows CC BY 4.0 on nflverse-data. Its grant allows reproduction/adaptation/sharing for rights the licensor holds, including commercial use, subject to conditions. Retain supplied creator/copyright notices, source/license links, relevant disclaimers and modification notices; do not imply endorsement. No attribution removal is proposed.

O: nflverse's site separately states that accessed NFL data belong to their respective owners and are governed by their terms. nfldata's inspected README supplies credits but no explicit data-use grant; probes of both raw `LICENSE.md` and GitHub `LICENSE.md` returned 404. Failure to find those files does not prove no license exists elsewhere.

**Unresolved:** the exact upstream grant covering nfldata schedules, and how it applies to the release copy. The release's existence in a CC-BY repository improves license evidence but does not by itself resolve upstream rights or certify byte equivalence. Software licenses of nflreadr/nflreadpy do not license downloaded data. No maintainer permission request was sent.

P: retain attribution such as “Schedule data: nflverse / Lee Sharpe (nfldata); source [artifact URL]; retrieved [UTC]; license [verified applicable license]; transformations: team normalization and Eastern-to-UTC conversion.” This is a template, not a claim that CC BY has been established for nfldata. Until the applicable grant is resolved, do not mark private storage/display, redistribution or future public release fully cleared. No logo/headshot/trademark rights are inferred. Private Tailscale access and $0 availability do not override terms.

## 9. Open risks and review decisions

| Priority | Unresolved issue | Recommendation |
|---|---|---|
| Blocking | Complete bytes unavailable; actual counts/types/nulls/duplicates not tested | Obtain public artifact in a working permitted environment, retain hash/revision and measured validation report |
| Blocking | Applicable upstream schedule rights | Establish explicit schedule grant/terms or owner-reviewed clarification before ingestion; no automated outreach |
| Blocking for promised status/finals | No explicit status/final evidence contract | Approve an evidence-backed reconciliation/enrichment source, or explicitly approve reduced unknown-status behavior; this research does not change requirements |
| Required review | Future 2026 POST not published in inspected view | Approve empty/unpublished state while retaining stage navigation; never fabricate matchups |
| Required validation | Provider ID changes, aliases and source-copy equivalence | Validate full bytes and successive snapshots; retain canonical IDs and correction history |
| Later-cutoff risk | No actual start/end timestamps | Preserve unknowns; separately resolve before historical pregame computations |

**Next proposed task, for approval:** a research-only evidence closure limited to the three blocking items: full public artifact integrity, applicable rights and final/status confirmation. Do not start another task or Milestone 1 implementation without owner approval. A decision to approve only parts of this contract must identify which mappings and limitations are accepted.

## 10. Verification performed and files changed

Performed: repository-document review; four local public-download probes (all DNS failures); web inspection of official loaders, dictionaries, release metadata, license notices and raw schedule samples; alternative CSV/Parquet/RDS/API probes. No full downloaded file, local data parsing, measured row assertions or application test passed. No dependencies, code, tables, services, accounts, secrets or deployment changes occurred.

Document verification: Python 3 checks passed for 46 distinct copied header names, existence of local Markdown link targets in all three changed documents, and the two illustrative UTC conversions. These are document/calculation checks, not dataset integrity or application tests. An initial `python` invocation failed because its existing Windows shim has an invalid interpreter; `python3` succeeded without changing the environment. External links were inspected as recorded above, not exhaustively link-tested.

Files: created this contract; added a schedule-only follow-up note to `data-sources.md` and a pointer to `feasibility-results.md`. Older audit findings remain historical; non-schedule research was not reopened. No new architecture/statistical decision was approved, so `decisions.md` remains unchanged. Work stops for owner review.

## 11. Final readiness assessment — 2026-11-05

This section supersedes earlier readiness recommendations, license uncertainty for the **release-distributed schedule dataset**, and suggestions for another general research task. The owner authorized a final bounded investigation of the three blockers. No implementation is authorized or performed.

### Retrieval boundary and evidence

Three official retrieval families were attempted in this final task:

| Method | Exact public target | Result | Classification |
|---|---|---|---|
| Direct release CSV via local curl | `https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv` | Exit 6: could not resolve github.com; retries disabled | Environmental DNS failure before source connection |
| Compressed release via web reader | `https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv.gz` | Redirect fetch rejected by web reader; no body obtained | Tool/access-path failure; origin availability unresolved |
| GitHub Contents API via web reader | `https://api.github.com/repos/nflverse/nfldata/contents/data/games.csv` | Inaccessible via this tool | Tool/access-path limitation; no origin response verification |

The latter two probes were inadvertently duplicated once while extracting the first tool output; no new method or evidence resulted and no further download retries were made. No mirrors, alternate credentials, access-control workarounds or package installations were used. Official documentation, repository pages and release metadata remained readable. The [release listing](https://github.com/nflverse/nflverse-data/releases/expanded_assets/schedules) still exposes the CSV and compressed CSV assets. This does not demonstrate successful byte retrieval.

**Downloaded-data verified:** none. The table below explicitly records unmeasured results rather than substituting format expectations for observations.

| Season | Phase context | Game count / unique IDs | Weeks / stage counts | Scores / missing / duplicate records |
|---|---|---|---|---|
| 2024 | Completed season; REG + POST required | Not measured | Not measured | Not measured; finality not independently reconciled |
| 2025 | Completed season; REG + POST required | Not measured | Not measured | Not measured; finality not independently reconciled |
| 2026 | In progress; scheduled future REG games distinct from completed results | Not measured | Not measured | Not measured; future missing scores are expected, not zero |

The earlier expected baselines (272 REG; historical POST 6/4/2/1) remain validation targets only. Unpublished 2026 playoff participants must not be fabricated or counted as historical missing games. No full-coverage claim is made for either repository or release copy.

### Status and final scores: confirmed source limitation

The official [schedule field dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_schedules.csv), rechecked in this task, defines scores and schedule context but does not document scheduled/in-progress/postponed/final flags or a completion timestamp. The prior raw header observation agrees. Official-source searches did not establish a documented status enrichment contract. Search results from third-party dashboards were not adopted or queried as data sources.

| Requested state | Reliable automatic identification from this schedule contract? | Safe handling |
|---|---|---|
| Scheduled | A future schedule record is evidence of a planned matchup, not a confirmed current operational state | Preserve scheduled kickoff, label any inference; authoritative state can remain UNKNOWN |
| In progress | No explicit supported field | UNKNOWN; do not infer live play from time or score presence |
| Postponed | No explicit supported field | UNKNOWN unless separately evidenced; revised kickoff alone is not a postponement flag |
| Completed / final | No explicit final flag or documented finality guarantee established | Keep reported scores distinct from confirmed final scores; require explicit final evidence |

A usable final-evidence record would identify the game, an official final result/gamebook or other approved explicit final indicator, final scores, source URL and verification/as-of time. No such game-by-game reconciliation was completed. A final result confirms completion but not the actual end timestamp needed for later historical cutoffs. Time elapsed since kickoff, unchanged scores, upload time and fetch time cannot substitute for finality. Unknown status is an honest fallback, but changing the promised Milestone 1 status behavior needs owner approval.

### Licensing: release-specific grant now documented

New primary evidence: the [official nflverse organization licensing statement](https://github.com/nflverse#licensing) explicitly applies CC BY 4.0 to data stored in nflverse-data releases, except named datasets such as FTN. The [schedule release](https://github.com/nflverse/nflverse-data/releases/tag/schedules) has no separate restrictive notice observed. Together with the [repository CC BY 4.0 license](https://raw.githubusercontent.com/nflverse/nflverse-data/main/LICENSE.md), this supplies a published dataset-level grant for using the release-distributed schedule in the private MVP. This is stronger evidence than merely seeing a repository license.

**Resolved for the recommended release route at the published-terms level:** local storage, transformation and display can rely on that grant, with attribution. Retain creator/source/license notices, identify modifications and avoid implying endorsement; no additional restrictions may be imposed on licensed rights when redistributing. CC BY does not impose a noncommercial-only or general no-redistribution restriction. It grants only rights held by the licensor and supplies no warranty; it does not authorize unrelated logos/trademarks. Those ordinary limits are not treated as a demand for bespoke permission for this private factual schedule use.

The direct `nfldata` repository's grant remains less explicit: [issue #33](https://github.com/nflverse/nfldata/issues/33) is an open request for an explicit license, not itself a grant. [Issue #35](https://github.com/nflverse/nfldata/issues/35) requests commercial clarification and was closed as not planned, which is neither permission nor refusal. The organization statement provides the relevant release grant; no further permission inquiry was sent. Direct-repository adoption and future public/commercial distribution need their own reviewed scope. Do not silently substitute raw nfldata bytes when the accepted license evidence is release-specific. No byte equivalence has been proved.

Attribution template for the release: “Schedule data: nflverse / Lee Sharpe (nfldata), via nflverse-data schedules release; CC BY 4.0 [license link]; source [exact artifact]; retrieved [UTC]. Modified: team normalization and Eastern-to-UTC conversion.” Retain supplied notices as well; this example is not a replacement for them.

### Final blocker table and concrete exit conditions

| Blocker | Result | Evidence | Concrete next action |
|---|---|---|---|
| Complete integrity | **Blocked** | No full bytes; local DNS failure and web asset/API access failures; every requested measured check remains unverified | Owner/environment operator obtains the official release CSV or CSV.gz through a normally working network and makes the unchanged artifact available locally, with URL/retrieval time/publisher digest. Validate its own digest, per-season/round counts, unique IDs, weeks, score pairs, nulls and duplicates before accepting data. Do not keep retrying this environment. |
| Status/finality | **Partially resolved** | Unsupported states are documented precisely; the source contract lacks explicit operational/final flags | Owner must choose: explicitly approve UNKNOWN/unconfirmed-score behavior for unsupported states, or supply an approved explicit status/final-evidence source before committing to those features. Preserve the prohibition on kickoff-only final inference. |
| License/usage | **Resolved — release route only** | Official organization statement plus release page and CC BY 4.0 license | Approve the release as the acquisition route, retain attribution/license/modification notices, and keep the direct-repository fallback unapproved. No new permission request is necessary on the evidence found. |

**C. BLOCKED.** Current evidence does not support starting Milestone 1 as specified. The exact unblock inputs are a complete official release artifact with a passing integrity report and an owner-approved status/final-evidence contract (or an explicit approved limitation). License evidence for the release is now sufficient at the published-terms level. Do not commission another general source audit: these are specific external inputs and acceptance decisions. No implementation, source substitution or reduced requirement is approved here.

Final-task verification: documentation/source inspection and the bounded retrieval attempts above. No dataset integrity check or application test ran successfully. Only documentation changed: this contract and follow-up notes in `data-sources.md` and `feasibility-results.md`. No code, dependencies, service initialization, tables, credentials, spending or deployment. Stop for owner review.

## 12. Local artifact validation and approved status limitation — 2026-11-05

This is the current assessment. The owner supplied `data/raw/games.csv`, approved the limited status contract, and authorized validation/documentation only. Decision 53 records that approval. Earlier download failures, unmeasured-count tables and implementation-hold recommendations are historical, not the result of this task.

Full evidence, all column null counts, week counts, collision pairs, check definitions and limitations: [Downloaded schedule validation report](schedule-validation-report.md).

### Artifact and measured coverage

The complete **2,188,859-byte** UTF-8 CSV parsed successfully to EOF: **7,548 records**, 46 distinct columns, seasons 1999–2026. No malformed-width rows, blank records, duplicate headers, missing required columns, duplicate primary game IDs or exact duplicate records were found. Full-file readability/primary duplicate checks cover all rows; detailed semantic checks cover only the 842 records in 2024–2026.

Independently calculated local SHA-256:

```text
66f7a71b12eeb8da8a5c332cfadb245da693aa66e2064fba734983dc41e68fd5
```

The owner states the file was downloaded from official nflverse. The exact download URL/time/revision was not supplied. The official release CSV listing rechecked on this date reports `0284c8bfa49ee3707d5d77844d264919c29a586378bb0304734e38ca65654583`, which **does not match**. No independent official-origin or snapshot-equivalence claim is made. Snapshot changes or transfer differences are possible explanations, not findings. Record owner-declared origin separately from byte-verified local integrity. The raw file was never modified.

| Season | Unique games | REG | WC / DIV / CON / SB | Both scores present / absent | Context |
|---|---|---|---|---|---|
| 2024 | 285 | 272 | 6 / 4 / 2 / 1 | 285 / 0 | Completed-season archive; individual finality unverified |
| 2025 | 285 | 272 | 6 / 4 / 2 / 1 | 285 / 0 | Completed-season archive; individual finality unverified |
| 2026 | 272 | 272 | 0 / 0 / 0 / 0 | 121 / 151 | In progress; scores weeks 1–8, absent weeks 9–18; POST absent |

Each season has all 32 expected team codes and 17 REG games per team, one bye week and no duplicate team/week appearances. All source IDs match their season/week/sides; REG weeks 1–18 and POST round/week mappings pass. No missing core identity/date/time values, invalid dates/times, unknown team codes, invalid score pairs, negative/noninteger scores or result/total arithmetic errors were found. Eastern-to-UTC round-trips pass for all 842 inputs. These are internal consistency checks, not an independent official matchup/time/score reconciliation. Source future kickoff slots are revisable, not certified broadcast times.

### Remaining integrity/provenance limitations

- Eight 2026 `old_game_id` values each map to two distinct games (16 records); all primary `game_id` values remain unique. **Do not merge these games or use `old_game_id` as a unique key.** Preserve the original value as nonunique or quarantine only the ambiguous alias. Exact pairs are in the report. No source repair is invented.
- No scoped non-null duplicates were found in the other inspected provider ID namespaces; many optional IDs are null. Nullable identifiers remain optional.
- Exact official-release origin is not authenticated because the local digest differs from the listing. Before claiming verified release provenance, establish the matching source snapshot/checksum; alternatively retain explicit owner-accepted declared provenance without calling it verified. License conclusions remain those for the documented official release route, not a newly discovered artifact grant.
- 2026 POST is absent, and no fixtures/participants/results may be manufactured. Keep stage navigation and disclose source coverage. Historical external correctness and identity stability across snapshots are not proven by one file.

### Approved operational status behavior

Use explicit **UNKNOWN** whenever finality is not reliably established. This applies to all **842** scoped games with this CSV alone, including the **691** records with paired scores. Preserve those as **reported scores, finality unverified** if displayed; 151 absent score pairs stay null. Never infer FINAL from kickoff, the calendar season, score presence or an elapsed-duration threshold. Do not invent IN_PROGRESS or POSTPONED. Source schedule date/time establishes planned fixture information, not a verified operational state. No confirmed-final records or actual completion instants were independently established in this task.

This owner-approved limitation resolves the previous status-contract decision gate for Milestone 1. It does not change later historical cutoff requirements or approve a new status provider.

### Readiness and mandatory checkpoints

**B. CONDITIONALLY READY** to begin a separately scoped, owner-approved Milestone 1 implementation task. Complete local structural validation is now possible and passed the primary checks; supported coverage matches the expected structure. The known optional-ID issue and declared-origin limitation are bounded, visible conditions rather than reasons to keep doing general research.

Implementation must preserve source bytes/digest/provenance, distinguish declared from authenticated origin, handle the eight alias collisions without game loss, preserve UNKNOWN status and nullable/reported scores, disclose absent 2026 postseason coverage, retain attribution and rerun meaningful validation on each new snapshot. Do not claim verified origin until the digest discrepancy is resolved; do not silently accept ambiguous identifiers. No changes to architecture or historical statistical definitions are approved.

Validation was performed with installed Python 3 standard-library tools; no dependency installation, application code, services, tables or migrations. These are dataset/document checks, not application tests. Work stops for owner review; the next approval may authorize only a narrow Milestone 1 task, not the whole roadmap.

Final verification passed: reread the entire raw file, confirmed its size and SHA-256 unchanged, repeated scoped count/unique-ID assertions and verified team/bye assertions and local document link targets. Documentation changed: this contract, `schedule-validation-report.md`, `decisions.md`, `product-requirements.md`, `data-model.md`, `implementation-plan.md`, `data-sources.md` and `feasibility-results.md`. The additional document edits synchronize Decision 53 and replace stale readiness pointers; no raw data was edited.

## 13. Foundation/schema implementation boundary — 2026-11-05

After reviewing section 12, the owner approved Task 002: development foundation and PostgreSQL schedule schema, not the importer/frontend or the entire milestone. [Models](../backend/app/models/schedule.py), [initial Alembic migration](../backend/alembic/versions/0001_schedule.py) and [development guide](development.md) are the concrete deliverables. Internal game UUIDs map to a unique provider/source game ID; optional old IDs are nonunique. Artifact and per-record provenance retain declared versus verified origin and nullable unknown timestamps. Defaults never authenticate origin or finalize a game. FINAL requires explicit evidence fields; UNKNOWN remains the default regardless of scores/kickoff.

No raw data was changed or ingested, no production database was accessed, and no migration was applied. Docker/Compose is unavailable in this WSL distro; dependency setup failed PyPI DNS resolution. Health/settings/PostgreSQL tests are authored but could not run; Python syntax and frozen migration/model constraint text checks passed. Runtime migration/schema/Compose validation remains mandatory. Source/statistical definitions, cutoff rules and the unresolved CSV release checksum discrepancy are unchanged. Stop at owner review before ingestion or frontend work.

## 14. Approved development ingestion — 2026-11-06

Owner approval of [Task 004](agent-task-004.md) supersedes the earlier importer hold without changing the source/status contract. [Implementation, import/reimport procedure and verification](schedule-ingestion.md) describe strict full-snapshot validation, PostgreSQL transaction rollback, idempotency, canonical UUID reconciliation, immutable artifact bytes and correction receipts. Exact actual download URL/time remain unknown; artifacts stay DECLARED and scores remain reported with UNKNOWN status. The historical checksum discrepancy is unresolved. No schema migration or raw CSV modification is part of this task. Database runtime validation remains pending in normal WSL; local CSV dry-run success is not evidence of an executed database import.
