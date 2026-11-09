# Automatic NFL schedule and reported-score updates — feasibility

Research date: **2026-11-07 UTC**. Branch inspected: `feature/schedule-auto-updates`; initial worktree clean. Owner-approved scope is research only. The owner reports the dashboard completed and merged to main; older documentation still records its earlier validation holds. Those historical holds were not treated as a new implementation authorization. This report is the only repository file changed.

## Recommendation

**Conditionally feasible for a delayed, reported-score batch updater; not safe to schedule the current import command unchanged.** Reuse the separate Python pipeline and atomic reconciliation, with download verification, snapshot comparison, regression quarantine, actual retrieval provenance and durable run/check records added in a separately approved task. Keep all source-only games UNKNOWN, even after new scores arrive.

**A strict guarantee that every updated score is from an already finished game remains unsupported by the verified CSV contract.** A daily next-morning run avoids a live-scoring feature, but a clock schedule is not completion evidence. If “after games finish” means a hard per-game publication guarantee, automatic score publication must remain disabled until an approved completion signal or a verified upstream final-only publication guarantee exists. Do not silently replace this requirement with elapsed-time inference. The owner must explicitly accept the delayed reported-score/unknown-finality batch limitation before activating it.

No current full release CSV was successfully downloaded. Consequently, exact new-versus-imported game/field changes and compatibility of that particular incoming snapshot remain **unverified**. A successful verified retrieval and comparison in normal WSL is a mandatory acceptance checkpoint, not another general research project.

## 1. Evidence and boundaries

Evidence labels used below:

- **Measured locally:** actual bytes read or an existing pure validator/test executed here.
- **Official documentation/source inspected:** published pages, release metadata or upstream code; not proof of downloaded data contents or measured update latency.
- **Repository inspection:** behavior established from existing code, with database behavior unexecuted in this task.
- **Proposal / unverified:** future design, policy choice or behavior not demonstrated with a fresh release and PostgreSQL.

Inspected project references: [AGENTS.md](../AGENTS.md), [README](../README.md), [requirements](product-requirements.md), [architecture](architecture.md), [decisions](decisions.md), [implementation plan](implementation-plan.md), [schedule data contract](schedule-data-contract.md), [local validation report](schedule-validation-report.md), [ingestion guide](schedule-ingestion.md), [data model](data-model.md), and [API guide](schedule-api.md). Relevant implementation: [validator](../backend/ingestion/validation.py), [capture/reconciliation](../backend/ingestion/service.py), [CLI](../backend/ingestion/schedule.py), [models](../backend/app/models/schedule.py), [ingestion tests](../backend/tests/test_ingestion.py), [Compose](../compose.yaml), [API schemas](../backend/app/schemas/schedule.py), and [frontend query defaults](../frontend/src/main.tsx).

No database connection, import, migration, service startup, application/schema/test-code change, dependency installation, original CSV replacement, deployment or git commit/merge/push was performed. Existing non-database tests and in-memory data probes were allowed verification, not implementation.

## 2. Official source, update behavior and usage rights

### Verified route and metadata

Use the existing public release endpoint:

```text
https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv
```

The official [nflreadpy schedule loader](https://raw.githubusercontent.com/nflverse/nflreadpy/main/src/nflreadpy/load_schedules.py) requests the full `schedules/games` dataset, then filters seasons. Its [downloader](https://raw.githubusercontent.com/nflverse/nflreadpy/main/src/nflreadpy/downloader.py) constructs CSV URLs under the nflverse-data release download root. No Python SDK installation is necessary for this route.

The [schedules release](https://github.com/nflverse/nflverse-data/releases/tag/schedules) identifies the maintained schedule dataset and says the release updates when its linked data changes. The [nflreadr availability documentation](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html) describes in-season game/schedule updates every five minutes. These are published behavior statements, **not** an availability SLA, measured delivery lag or assurance that every five-minute check yields new bytes.

The inspected [upstream release workflow](https://github.com/nflverse/nfldata/blob/master/.github/workflows/release_games.yml) runs on changes to `data/games.rds` or manual dispatch. It compares upstream/released data, upserts by `game_id`, and writes RDS/CSV/Parquet/CSV.gz. **Inference from this code:** a changed source ID can potentially leave both old and new rows in the release, because upsert alone does not remove the old key. This was not observed in a newly downloaded snapshot. The importer must reject resulting duplicates/conflicts for review rather than guessing which game to delete.

The [expanded official asset listing](https://github.com/nflverse/nflverse-data/releases/expanded_assets/schedules), inspected on this date, advertises:

| Asset | Advertised SHA-256 | Displayed size / asset timestamp |
|---|---|---|
| games.csv | `07d5cb4b553c7d737e06e91653467968db62dc1b896096b4835999d9ac93ad3c` | 2.09 MB; 2026-11-07T18:46:24Z |
| games.csv.gz | `58d8f83dd9a39488351c0983ea4eda67e591e84ec91853e6a605279ccbfd97d1` | 504 KB; 2026-11-07T18:46:24Z |

The listing also advertises `timestamp.json` and `timestamp.txt`. Their contents/semantics were not verified: the JSON body could not be retrieved. These are web-observed metadata, potentially subject to caching, not locally verified asset bytes. The rounded CSV size is not an exact byte count.

[GitHub's official asset API documentation](https://docs.github.com/en/rest/releases/assets) documents public unauthenticated retrieval, browser download URLs, binary responses/redirects, and metadata including asset ID, digest, size and update time. The recommended metadata request is `GET https://api.github.com/repos/nflverse/nflverse-data/releases/tags/schedules`, selecting the uploaded `games.csv` asset by exact name; API access to this repository response was blocked here. Per-asset binary download is an official fallback once its actual asset ID is known; no asset ID or successful API download is invented.

ETag/Last-Modified/304 support for this **specific** CSV route was not measured. Treat these as optional optimization inputs only after observing real responses; hashes remain the content-change test. Do not use release tag creation time or its old repository commit as the revision/freshness of a repeatedly replaced asset. Timestamp sidecars and the CSV are separate requests and need not describe one atomic publication.

### Retrieval attempts and environmental limits

| Attempt this task | Actual result | Conclusion |
|---|---|---|
| Local `curl --fail --location --connect-timeout 8 --max-time 25 --retry 0 --output /tmp/nfl-auto-update-candidate-20261107.csv.part …/schedules/games.csv` | Exit 6, could not resolve github.com; HTTP 000, zero bytes. `getent hosts github.com` also failed. No candidate file exists. | Local execution-environment DNS limitation; not evidence the upstream source is down. |
| Web tool: official release CSV URL | Release-asset redirect rejected as unsafe/non-retryable by the tool | Web-tool redirect/cache handling limitation; successful CSV retrieval remains unverified. |
| Web tool: official release metadata API | URL inaccessible via tool | No verified API metadata body or alternative asset-body access. |
| Web tool: release/expanded listing, source docs and workflow | Readable | Documentation/metadata evidence only. |
| Web tool: timestamp.json sidecar | Asset redirect rejected | No verified source timestamp body. |

No repeated identical download attempts, unapproved mirrors, signed-redirect URL reuse, raw-repository dataset substitution or source restrictions bypass. The optional gzip asset was listed but not downloaded. It remains an official alternative, not a proven workaround. Compressed bytes require their own publisher digest; preserve/check those bytes before decompression, and hash/validate the decompressed CSV separately. Do not equate the gzip digest with the CSV digest or assume exact equivalence without measurement.

### Licensing

The [official nflverse licensing statement](https://github.com/nflverse#licensing) applies CC BY 4.0 broadly to nflverse-data releases, with separately identified dataset exceptions. The schedule release showed no separate restrictive license notice. The [nflverse-data license](https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md) is CC BY 4.0. This supports the existing release-route storage/transformation/display conclusion, not an unrestricted grant for every other dataset or logo.

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) permits copying/adaptation and redistribution subject to appropriate credit, license link, retained supplied notices and indication of changes, without suggesting endorsement or imposing extra restrictions on licensed rights. Keep nflverse/Lee Sharpe attribution and describe normalization/time conversion/corrections. No paid data tier or permission message is needed for the published schedule release terms. The license supplies no warranty and grants only rights the licensor holds. Automatic downloads do not authenticate the old owner-supplied bytes or resolve their earlier hash discrepancy. No source substitution is recommended.

## 3. Actual snapshot comparison: known and unknown

The unchanged local file is the available baseline. Its correspondence to the current database is **owner-reported**, not independently checked here; the database may only be called the baseline after a read-only comparison in the approved development environment.

| Measurement | Local original (measured again) | Current advertised release |
|---|---|---|
| SHA-256 | `66f7a71b12eeb8da8a5c332cfadb245da693aa66e2064fba734983dc41e68fd5` | `07d5cb4b553c7d737e06e91653467968db62dc1b896096b4835999d9ac93ad3c` (metadata only) |
| Exact bytes / whole-file rows | 2,188,859 / 7,548 | Not downloaded; unknown |
| Scoped 2024 games | 272 REG + 13 POST; 285 paired scores | Unknown |
| Scoped 2025 games | 272 REG + 13 POST; 285 paired scores | Unknown |
| Scoped 2026 games | 272 REG, zero POST; 121 paired scores, 151 missing pairs | Unknown |
| Scoped IDs / original legacy issue | 842 unique primary IDs; eight nonunique 2026 old_game_id values retained | New IDs, removed IDs and collision changes unknown |
| Changed rows/fields, new scores, kickoff corrections | Baseline established | Exact counts and examples unknown |

The hash difference establishes that the advertised asset bytes differ from the baseline, **not** that any scoped score or game changed. Formatting, other years, optional fields or actual schedule/score corrections are all possible; none was established. The older 2026-11-05 published digest `0284c8bfa49ee3707d5d77844d264919c29a586378bb0304734e38ca65654583` remains historical comparison evidence, not the expected digest for a future download.

A first real comparison must retain both files, match the candidate's own contemporaneous publisher digest, parse the complete CSV, and report: all-file/scoped counts; added/missing primary IDs; ESPN-assisted candidate identity changes; per-year/round/week coverage; per-field old/new values; new/missing/changed score pairs; kickoff/date/time changes; optional-field-only changes; artifact and record hashes. Compare both to the preserved accepted artifact **and current database state**. Never replace `data/raw/games.csv` or infer a new-versus-DB delta from a global hash alone.

## 4. Compatibility with the existing importer

The following is established by repository inspection, except where a parser probe is explicitly stated. It is not a fresh-candidate PostgreSQL import result.

| Incoming difference | Existing behavior | Additional unattended-update rule |
|---|---|---|
| 2026 missing scores become a valid pair | Parser accepts; reconciliation updates row/provenance while UNKNOWN stays UNKNOWN | Suitable for reported-score batches under the stated completion limitation; do not label final |
| Known kickoff changes, same primary ID | All mapped fields update, with a correction receipt; source timezone/date validation still applies | Record field-level change; reject unexplained removal of a known timestamp for review |
| Primary ID changes with stable ESPN + season/same teams | Canonical UUID can survive if the match is unique; otherwise rejection | Quarantine ambiguous matches, missing ESPN, dual old/new records or duplicate team/week; never use old_game_id |
| Available 2026 postseason games added | Parser permits round maxima and requires complete preceding rounds; new rows inserted UNKNOWN | Accept only valid real records; retain existing-game preservation checks |
| Historical score/kickoff correction on UNKNOWN | Structurally valid correction applies | Require newer publisher evidence and reviewed regression policy; historical season does not mean FINAL |
| Any raw source column changes | Record hash changes, even if displayed schedule fields do not | Counts are source-record revisions, not necessarily score updates; preserve raw evidence without implementing odds/stat features |
| Existing 2026 paired scores disappear | **Parser accepts two nulls; UNKNOWN row can be overwritten** | **Quarantine by default**; removals need explicit owner-reviewed correction, not automatic zero-fill or silent retention |
| Older, structurally valid snapshot arrives | No monotonic source-version/staleness guard; prior values can be reapplied | Quarantine previously superseded hashes and stale/replayed metadata against accepted checkpoint; never use download time as proof of source freshness |
| Existing game disappears / malformed or incomplete batch | Validator/reconciliation rejects; CLI transaction rolls back | Preserve last good data and expose failure; no deletion or automatic guard bypass |
| Changed row already FINAL | Whole batch rejected; unchanged evidenced FINAL preserved | Keep this safeguard; even optional-field-only changes can require review |
| Exact same rows reapplied | No game/artifact writes; returned unchanged counts | Still record successful check in an operational journal; do not mistake old artifact time for failed refresh |

Measured **in-memory parser probes**, using temporary dictionaries derived from the original file and never writing them back:

1. One previously unscored 2026 row received synthetic 20–17 scores plus matching result/total: full validator accepted 842 scoped records.
2. One previously scored 2026 row had both scores/result/total cleared: full validator also accepted 842 scoped records.

These prove parser acceptance only, not real source behavior or database updates. Reconciliation's all-fields assignment establishes the erasure risk by code inspection. Existing pure tests passed (section 9); no PostgreSQL test was executed in this task.

Other gaps: the CLI’s generic database error says rollback, but a lost connection during COMMIT can leave the commit outcome indeterminate; an automated controller must verify its run receipt rather than trusting that message. Added optional columns are retained rather than schema-pinned; omitted optional columns can remove prior mapped metadata; required-header checks do not detect every semantic upstream schema change. Require a schema-drift comparison and quarantine unexpected added/removed/renamed columns until reviewed. Score decreases and non-null historical score corrections can be legitimate, so do not invent “scores only increase” as a business rule. Initially quarantine changed previously non-null scores for review; allow newly reported pairs only within the approved batch policy. Choose numeric/volume thresholds from the first measured diff and owner approval, not fabricated tolerances in this report.

## 5. Proposed download, verification and publication flow

**Proposal, not implemented:**

1. Acquire a single-run lock before network work. Load the last **accepted/committed** checkpoint, not merely the last downloaded file. A rejected candidate must never become the “unchanged” comparison baseline.
2. Read official asset metadata; capture exact asset identity/name, size, digest and update time if available. Use a real User-Agent, bounded connect/read/total timeout, limited redirects/response size and verified HTTPS. Do not hard-code a signed redirect URL or log its query tokens.
3. Download the full CSV to a unique staging `.part` file outside `data/raw`. Reject transport errors, non-success status, HTML/error content, unexpected encoding/oversize and incomplete byte counts when the transport provides a comparable size. A missing Content-Length alone is not corruption; full parse/digest checks remain necessary.
4. Compute SHA-256. Recheck metadata if publication raced the transfer; require one coherent metadata/body pair before accepting. Digest mismatch or metadata churn is a deferred/quarantined run, not permission to ignore integrity checks. Proposed default: require the publisher digest for automated publication; missing evidence needs explicit policy review.
5. Parse/validate every row and all 2024–2026 semantics, then produce the full differential/regression report against accepted artifacts and DB records. Quarantine missing existing games, score removals, unexpected existing-score corrections, known-time loss, schema drift and suspicious mass changes. Do not claim a threshold is already approved.
6. Archive exact original bytes by digest with a retrieval receipt. For the future downloader/capture path, use a temporary file, flush/sync and atomic no-replace publication; verify an existing target's hash. Current `capture()` writes its final filename directly with exclusive creation: safe from overwriting, but a crash can leave a partial archive blocking future reuse. Do not silently overwrite such an artifact.
7. After validation, open a short isolated development transaction, acquire the existing PostgreSQL advisory lock and re-evaluate the baseline/diff under that lock (another importer may have committed meanwhile). Apply existing canonical reconciliation and required new safety gates together. No network access while holding the transaction. Commit games and artifact/correction evidence atomically; no partial publication.
8. Only after confirmed commit record the successful apply/no-change result. On pre-commit failure retain the prior accepted checkpoint and last-good data; on ambiguous commit outcome stop publication/checkpoint advancement until receipt reconciliation. Record bounded diagnostics. Classify transport/validation/digest/database failures separately.

Initial implementation should use Python standard-library networking/scheduling/file tools plus existing SQLAlchemy, rather than installing an SDK, message queue, Redis or scheduler library. Conditional requests may later reduce transfers: a 304 is a successful source check only when a prior accepted artifact/checkpoint exists and the validator refers to that same resource. It is not a newly downloaded/validated file. An unchanged file digest may skip nightly mutation, but a weekly pass must still validate the archive and reconcile current DB integrity rather than relying forever on hashes.

Provenance must stop using the current manual-import hard-coded acquisition notes for fresh downloads. Existing SourceArtifact columns can store the actual completed retrieval time, declared/documented URL, publisher digest, source revision evidence and verification method/time. Store asset ID/update metadata separately in structured notes; do not call release creation time or a sidecar completion time “game completed at.” Leave unavailable metadata null. Origin starts DECLARED and can become VERIFIED only under the existing matching-publisher-hash/evidence contract. That verifies publisher artifact correspondence, not independent NFL matchup/score truth. New evidence must not retroactively upgrade the old mismatching original artifact.

## 6. Scheduler, cadence and no-live-scoring limit

The architecture already plans a **dedicated scheduler container independent of FastAPI**; Compose currently implements only manual ingestion. The ingestion service is on the internal-only database network, so it is not currently configured as an internet downloader. Do not assume WSL DNS recovery alone makes that service suitable for source retrieval.

Propose a separate, opt-in non-root development updater service using the existing backend image/package, on the existing default network for outbound HTTPS and the internal database network for development PostgreSQL. No host ports, paid platform or API request-triggered jobs. Mount original raw input read-only, archives and operational journal in durable volumes. A standard-library UTC timer is sufficient; handle shutdown, one missed-run catch-up and overlapping invocations without a backlog storm. Keep DB-name/host guards. Production scheduling/deployment is outside the first task.

| Proposed job | UTC cadence | Purpose |
|---|---|---|
| Delayed daily batch | Every day at **10:00 UTC** (05:00 EST / 06:00 EDT) | Retrieve one full snapshot; apply only policy-approved reported-score/schedule changes; normally next-morning availability rather than live updates |
| Weekly reconciliation | Thursday **11:00 UTC** | Unconditional full retrieval/validation and all three scoped seasons reconciled, including unchanged-record/database integrity and historical corrections; replace that day's daily run to avoid duplicate work |
| Transport retry | Up to two bounded delayed retries, e.g. +15/+60 minutes, respecting Retry-After/rate-limit responses | Recover transient failure; do not retry validation/digest/regression rejection as though it were a transient DB error |

These times are a proposed operational policy, not an approved changed statistical definition or a provider guarantee. No game-day five-minute polling, live score notifications, WebSockets or in-progress status. Weekly Thursday is a convenient pre-weekend audit slot; the documentation's PBP/stat correction guidance is not proof of a schedule-score correction deadline. Daily polling also catches schedule changes on non-game days; expected freshness is roughly the next successful daily run plus upstream lag, not a guaranteed upper bound.

A rare unfinished/delayed game or an upstream partial score can still appear at the batch time. No fixed kickoff delay, unchanged-score duration, round/week, timestamp sidecar or calendar rollover proves finality. If strict finished-only score publication is mandatory, **do not activate it with this source alone**. Download/archive/check-only operation can proceed; score publication needs an approved explicit completion signal or owner acceptance of the stated delayed reported-only limitation. This report does not approve either alternative or introduce a new status source.

## 7. Last check, last update and frontend freshness

**Current limitation:** source_artifacts records changed imports, not successful no-ops, 304 responses or failed attempts. Game `updated_at` and artifact `recorded_at` are database observations, not the last successful source check. Existing `/api/health` and `/api/ready` do not report data freshness. Frontend Query staleTime/refetching only reloads PostgreSQL-backed API data; it does not refresh the upstream schedule.

For an initial no-schema runner, propose a durable versioned run journal and atomically replaced status/checkpoint file in its own volume. Record run ID, attempt/completion times, outcome, sanitized failure, metadata validators, accepted digest/artifact, counts and last success. Use separate fields:

| Proposed field | Meaning |
|---|---|
| last_attempt_at | Most recent run started, even if failed |
| last_successful_check_at | Source was successfully checked; may be 304 or same bytes tied to a previously accepted snapshot |
| last_downloaded_at | Actual completed successful body retrieval; not updated for 304 |
| last_validated_at | Full content/integrity validation completed |
| last_successful_ingestion_at | Candidate was reconciled successfully, including a no-op; not synonymous with data changed |
| last_data_change_at | Committed schedule/score/raw-record changes; unchanged when source bytes/game records are unchanged |
| source_asset_updated_at | Publisher metadata, nullable; not proof of per-game completion or data completeness |
| last_weekly_reconciliation_at | Full validation/DB consistency audit, separate from conditional nightly checks |
| outcome / accepted_sha256 | Changed, unchanged, not-modified, rejected, failed, or indeterminate; associated accepted baseline |

Accepted download identity and applied artifact identity must be separate: a full-file change confined to other seasons/CSV formatting may yield zero scoped changes and no new SourceArtifact row; the existing no-op result has no artifact_id. Keep the new archive/retrieval receipt in the journal and allow applied_artifact_id to be null. Games can legitimately retain mixed older artifact references. A newly verified download never silently upgrades the origin or retrieval timestamp of those older artifacts.

The database/file journal cannot share one transaction. Use a run ID also retained in committed artifact receipt evidence for changed runs; write “running” first and only mark applied after commit. Crash after commit but before file update must display indeterminate/stale until recovered by checking DB receipt identity, not falsely report success or reapply an old checkpoint. For successful no-op checks the durable journal records the event; missing journal evidence remains unknown. File loss must not infer success from the newest artifact alone. Existing conceptual `source_imports` tables are not implemented; adding them later requires separate schema approval.

**Proposed later additive API/UI task**, requiring explicit approval: `GET /api/data-status/schedule`, read-only, serving a sanitized journal projection through FastAPI with a read-only volume mount. Return server-as-of time, the separate timestamps, latest outcome, source digest and operational stale/error state. Do not expose local paths, raw exception details or credentials; do not change the existing game/schedule response contracts incidentally.

UI wording: “Source checked …”, “Schedule records changed …”, “Latest check failed; showing last successful records …”. Missing evidence must say unknown/never checked. Proposed initial overdue threshold: more than **36 hours** since a successful check; latest failure is visible immediately, and overdue weekly reconciliation is a separate condition. This is an owner-review operational threshold, not proof that scores are stale or final. A recent unchanged check plus an old publisher asset means “source unchanged,” not “scores up to date” or “live.” Preserve the underlying historical schedule during updater failure. The future UI can fetch this operational status on focus/manual refresh; when its committed data-version token changes, invalidate the existing seasons/schedule/game Query caches so the visible records match the displayed publication version. Reading status must never start a job or call nflverse from the browser. This is operational refresh, not live game polling. No freshness endpoint or UI change was implemented here.

## 8. Risks, tests and rollback

| Risk / blocker | State | Concrete resolution |
|---|---|---|
| Fresh complete snapshot and actual field diff unavailable | **Blocked in agent environment** | One successful normal-WSL official download with contemporaneous publisher digest, preserved candidate and full comparison before enabling apply |
| Strict completed-only score guarantee | **Unresolved source limitation** | Accept delayed reported-only/UNKNOWN limitation explicitly, or approve explicit completion evidence; otherwise no automatic score publication |
| Valid stale snapshot / 2026 score erasure | **Verified missing protection** | Add source-version/replay and reviewed delta-regression gates with quarantine; do not schedule bare CLI |
| Actual automated acquisition provenance | **Missing in current manual importer** | Pass measured retrieval/asset evidence into existing provenance columns/notes; preserve old DECLARED artifact |
| No-op/failure/update timestamps and crash recovery | **Not implemented** | Durable journal/checkpoint plus commit-aware recovery; later approved status API/UI |
| Scheduler egress, process/download overlap and archive crash safety | **Not implemented** | Dedicated opt-in service, run lock, bounded retry, atomic archives/status and existing DB lock |
| Source-ID rewrite or coexisting old/new upstream IDs | **Bounded/possibly rejected** | Keep identity/completeness rejection; reviewed mapping/correction, no automatic delete or legacy-ID matching |
| Real latest-candidate DB compatibility | **Untested** | Isolated PostgreSQL fixtures and controlled development acceptance after preflight; no import in this research task |

Future tests must cover:

- HTTP success/redirect, 304 with/without a baseline, timeout, DNS, 404/403/429/5xx, interrupted/truncated/oversized/HTML bodies, wrong digest, metadata/body race and missing publisher evidence.
- Same bytes/no-op; different full-file hash but unchanged scoped records; new reported pairs; non-null score correction/removal; old snapshot replay; changed optional fields/schema; new valid POST; missing games; kickoff correction/removal; ESPN-matched identity changes; dual source IDs; repeated old_game_id.
- No score/time-driven FINAL; unchanged evidenced FINAL remains; changed FINAL rejects publication; missing != zero.
- Real isolated PostgreSQL transactions: all-or-nothing games/artifacts, correction audit, UUID stability, stale-baseline recheck under lock, concurrent manual/scheduled runs, lock timeout, process death during staging/archive/commit/journal and last-good API availability.
- UTC/DST timing, restart catch-up, retry budget and weekly unconditional reconciliation. Freshness tests distinguish 304/no-op from changed-data time; failed refresh keeps historical data and shows honest operational status.

Rollback before commit is already transactional: leave the last good schedule and record failure. File archives can remain unreferenced and must not be mistaken for committed imports. After a committed but incorrect update, stop future runs and retain all before/after artifacts and receipts; review a corrective forward import or separately approved database recovery.

**Do not promise that reimporting the prior archive is a universal rollback.** It may omit newly added postseason games and hit `missing_existing_games`; identity or FINAL guards can also block it. Database restoration/deletion is destructive and requires explicit owner approval. No rollback, import or restore was attempted here. Archive/journal/database backups must remain coordinated; no automatic archive pruning in the first version.

## 9. Verification performed and narrowly scoped next task

Executed locally:

- Read the entire original CSV through the existing pure validator: 7,548 full rows, 842 scoped rows; original counts/hash unchanged as shown above.
- Two explicitly synthetic, in-memory score-change/removal probes passed parsing. Original file rehashed unchanged afterward.
- `.venv/bin/python -m pytest backend/tests/test_ingestion.py -m 'not database' -q -ra`: **23 passed, 10 deselected**. Database cases were deliberately excluded; no PostgreSQL fixture/import/migration ran. This is existing unit evidence, not a new-source acceptance test.
- Bounded retrieval failures and official metadata/source/license inspection recorded above. No full candidate download or row-level diff succeeded.

Recommended next implementation task, **for approval**: **Controlled development snapshot refresh runner, unscheduled initially.** Add a separate fetch/check CLI with dry-run comparison as default, stable publisher-digest verification, durable accepted checkpoint/journal, complete differential/regression quarantine, atomic archives, actual acquisition provenance and isolated tests. An explicitly enabled apply mode must reuse transactional reconciliation with its safeguards and recheck against the locked DB baseline. Keep the original file immutable, scope 2024–2026, retain UNKNOWN, add no schema or game API contract changes, and do not enable timers/production automatically.

Acceptance checkpoints: a real verified candidate and exact diff captured in normal WSL; reviewed score-removal/correction/schema/replay rules; explicit resolution of the delayed-versus-strict-postgame policy; passing transport/unit/PostgreSQL/rollback tests; a controlled development apply followed by an unchanged recheck. If access stays blocked, build/test with synthetic transport fixtures but leave apply activation unaccepted. This is a concrete implementation scope, not permission to proceed now.

Only after accepting that runner should a separately approved change activate the dedicated daily/weekly scheduler and add the operational status endpoint/frontend display described above. No updater has been implemented by this feasibility task. Stop for owner review.
