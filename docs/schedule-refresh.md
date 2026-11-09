# Guarded development schedule refresh — Task 007

## Scope and guarantees

Approved scope: [Task 007](agent-task-007.md), informed by the [feasibility report](schedule-auto-update-feasibility.md). Work is on `feature/schedule-auto-updates`. This is a **manual, one-shot CLI**, not an unattended updater. No timers, worker service loops, API triggers, frontend changes, database schema or migrations were added. No dependency installation is required beyond the existing backend requirements.

The existing manually supplied original file is neither overwritten nor used as the new-download destination. All actual runner download receipts retain **DECLARED** origin. A matching publisher digest is recorded as such, not equated to independent NFL result authentication. Games remain UNKNOWN; the runner never assigns FINAL, in-progress or postponed states. New scores may be partial/unconfirmed, so operator review is mandatory before publishing them as **reported values**, never automatically certified postgame/final results.

The old ingestion API/CLI remains compatible. The refresh runner calls the existing reconciliation function and cannot override its primary-ID/team/FINAL/deletion/constraint safeguards. Score removals and other hard blockers are deliberately stricter here. There is no `--force`, allow-removal or ignore-FINAL option.

## Source configuration and retrieval

`backend/ingestion/source.py` declares the only supported source configuration, selected explicitly with `--source nflverse-release`:

- CSV: `https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv`.
- Metadata: `https://api.github.com/repos/nflverse/nflverse-data/releases/tags/schedules`, selecting exactly the uploaded `games.csv` asset and its documented download URL.
- Public requests without credentials, with a descriptive User-Agent; HTTPS-only redirects restricted to the GitHub/API/release-asset/object hosts in the source module. No mirrors, raw-repository substitution or saved signed URLs.
- Socket timeout 15 seconds, elapsed body-read budget 60 seconds per request, at most three redirects, full CSV limit 32 MiB and metadata limit 2 MiB. Socket/DNS/redirect handling is bounded by the underlying urllib behavior, not a hard real-time process deadline. No automatic retries or conditional/304 optimization.

When metadata is available it must be well formed; size/digest are checked, and metadata is fetched again after the CSV to reject publication races. A missing digest remains explicit. An unavailable metadata request is recorded and can fall back to the approved CSV URL with DECLARED origin; it is not fabricated from the feasibility report's old advertised hash. Available-but-invalid, mismatching or changing metadata fails closed. A previously recorded source revision also prevents applying an older/missing revision.

Completed bodies are captured by SHA-256, including rejected complete CSVs and complete integrity-failure bodies for inspection. The archive/receipt marks a failed integrity check and cannot later be approved into validity. Incomplete transport reads are rejected; a partial read is not represented as a complete source snapshot. Unsupported content encodings, HTML/error bodies and oversize/truncated transfers are rejected. New metadata fields are read only from the actual response; no old release listing is used as the expected new checksum.

Receipts record measured bytes/hash, actual completed retrieval time, initial source URL, available publisher asset identity/update time/digest, non-secret validators and verification outcome. Signed redirect URLs and exception details are not logged. SourceAsset update metadata is distinct from retrieval and database observation times. `provider_published_at` stays null because no independently established publication-time semantics were added.

## Comparison and review policy

Whole-file parsing and the existing 2024–2026 REG/POST completeness/identity/week/score/time contracts run on every candidate load. No partial snapshot can be imported. For a readable but incomplete CSV, the validation-failure report additionally attempts a **read-only diagnostic** listing source IDs absent relative to development PostgreSQL; this is not an importable comparison plan. If parsing or database access prevents that diagnostic, it says unavailable rather than guessing.

A valid candidate is compared to the actual current PostgreSQL records under the same transaction advisory lock used by the original importer. Reports include field-level raw before/after values, canonical IDs/source-ID mappings, counts and categories:

| Change | Handling |
|---|---|
| Newly populated scores, including scored new games | Explicit review token required; UNKNOWN retained |
| Corrected non-null scores | Explicit review, including historical corrections; no monotonic-score rule invented |
| Any changed 2024/2025 record | Labeled historical; explicit review |
| Kickoff/matchup or unambiguously ESPN-linked source-ID change | Reported and requires explicit review; canonical UUID preserved when original matching rules allow |
| Any other raw-record change, including optional source columns | Reported; requires explicit review; no new odds/stat feature is derived |
| Removed scores | Hard rejection, even with a token |
| Changed FINAL record | Hard rejection, preserving original importer guard; even optional-field changes can block |
| Disappearing game, ambiguous identity or conflicting team alias/mapping | Hard rejection; no deletion, old-ID matching or guessed repair |
| Known kickoff removed, unexpected schema keys, missing raw baseline or stored-record drift | Hard rejection for separate review/remediation |
| Known superseded refresh hash or older/missing previously recorded publisher revision | Hard rejection; no replay override |
| No scoped changes and consistent baseline | Idempotent no-op; no new game/artifact rows |

Historical means 2024/2025 under the fixed approved contract, not an inference from the wall clock. Missing scores stay null, zero stays zero, and `old_game_id` stays nonunique. A fresh full-file hash can change with zero scoped record changes (other years/formatting), which creates an operational receipt but no artificial game correction.

Every **changing apply**, not just score changes, requires `--approve-review` containing the exact `review_token` from a dry-run plan. The token binds candidate bytes, acquisition evidence, all stored game columns and relevant team/alias/artifact baseline data plus the differential. Apply uses an archived candidate, never a fresh download in the same step, repeats validation and comparison under the DB lock, and recomputes the token. A changed baseline invalidates old review; a new report is saved. The token is an operator acknowledgement, not an authentication secret, access-control system or assertion that scores are final.

Hard blockers cannot be waived by that acknowledgement. They need explicit owner review and a separately scoped remediation that preserves source evidence and the existing contracts. An empty database is also blocked: use the previously approved original backfill procedure, not this update runner, to establish a baseline. The runner is not a way to silently bootstrap or reset a database.

The candidate's publisher revision may be unavailable initially, particularly with the original DECLARED baseline. The tool cannot prove source freshness in that case; comparison/review remains mandatory. Replay history is maintained for successfully accepted refresh hashes, not inferred from a new download time. Manual imports performed outside the refresh workflow are not retrospectively authenticated.

## Files, transactions and receipts

Compose adds opt-in profile/service **refresh**, with no published ports. It uses the existing backend image and default network for outbound HTTPS plus the internal database network. It is manually run; the default Compose stack does not start it. It retains the existing dev DB environment, mounts raw data read-only, reuses `schedule_snapshots:/app/snapshots` and adds `schedule_refresh:/app/refresh-state`. The image prepares both writable directories for its existing non-root app user.

State layout:

```text
/app/snapshots/<SHA256>.csv                  immutable source bytes
/app/refresh-state/candidates/<UUID>.json   immutable acquisition receipt
/app/refresh-state/runs/<UUID>.json         running/prepared/final report
/app/refresh-state/status.json              latest outcome and accepted checkpoint
/app/refresh-state/runner.lock              exclusive process lock
```

Archives use temporary files, flush/fsync and atomic no-replace links, verify existing content and never overwrite corrupted evidence. This also improves `capture()` for the original manual importer; no validation rule was weakened. JSON receipts/reports/checkpoints are atomically published; original and incoming files are never edited to “fix” a rejection. Keep archive/state volumes together with the database; there is no automatic pruning.

The runner holds a shared-volume process lock across the operation. Network/file staging finishes before taking DB locks. Comparison/apply uses the original PostgreSQL advisory lock, row locks and a five-second lock timeout. Within one database transaction it invokes existing reconciliation, including a second safeguard pass, then flushes artifact/game updates. Any ordinary pre-commit error rolls back all changes. Refreshed artifacts retain actual acquisition metadata plus the operator review/run ID in existing provenance notes; old artifacts and correction receipts remain unchanged. No schema change was required.

Before attempting a changing COMMIT, a durable `commit_pending` run includes the proposed result and artifact ID. Lost acknowledgement, process death or a final journal-write error may leave the outcome indeterminate. Subsequent normal runs stop. Recovery acquires the same DB lock so the old transaction has finished, then checks the exact artifact/run/hash receipt: a match confirms applied; absence confirms not applied; contradictory evidence stops for owner review. Recovery only reads PostgreSQL and repairs the operational journal; it does not repeat imports or delete data.

Successful no-op applies add only run/checkpoint records, not database artifacts or games. Status includes last attempt/outcome, successful check/ingestion times, last data-change **observed** time, accepted hashes and available asset revision. Failed or rejected runs preserve previous success fields. Recovery timestamps are observation times, not reconstructed original commit/publication/completion instants. These timestamps cover this runner, not all possible legacy/manual ingestion. No freshness API or frontend status display is added.

A lost/corrupted success checkpoint with completed history fails closed rather than inventing a new baseline. Missing/corrupt evidence, filesystem permission or capacity problems need operator investigation/restoration, not volume deletion or a safety override. A prior full snapshot is not a universal rollback after a successful change: it can omit added games or trigger FINAL/identity/replay guards. Stop and review a corrective forward import or separately approved recovery; no automatic destructive restoration exists.

## Normal WSL: tests, dry-run, review and apply

Run from the repository root, with the existing `.env` intact. No development migration, reimport of the original CSV, new package or WSL/Docker setting change is needed. Do not print `.env` or supply production credentials. The CLI requires **APP_DB_HOST=db / APP_DB_NAME=nfl_research_dev**, and verifies the connected database name. The isolated test DB is only accepted by the internal test adapter, not as a CLI override.

### 1. Verify the implementation first

```bash
git branch --show-current
docker compose --profile refresh config --quiet
docker compose --profile test run --build --rm tests
docker compose --profile test stop db_test
```

Expected branch: `feature/schedule-auto-updates`. Tests must run their PostgreSQL cases, not skip. They use the established isolated tmpfs `nfl_research_test` fixture and its original migration; no development schema is changed. Stop on failures and capture sanitized output before attempting real apply.

### 2. Download, validate and compare (default dry-run)

```bash
docker compose up -d --wait db
docker compose --profile refresh run --build --rm refresh
```

Default command is `python -m ingestion.refresh --source nflverse-release`. It archives a full download, validates it and compares development records, without writing schedule/team/artifact rows. It prints a bounded JSON summary: outcome, run ID, candidate ID, hash, report path, review token, category counts and blockers. Full before/after data is in the report. A failed retrieval writes an operational failure; it does not become an empty successful import.

Assign the actual printed IDs below (they may differ when rechecking a candidate):

```bash
REFRESH_RUN_ID='paste-the-run_id'
REFRESH_CANDIDATE_ID='paste-the-candidate_id'
docker compose --profile refresh run --rm --no-deps refresh python -m json.tool "/app/refresh-state/runs/${REFRESH_RUN_ID}.json"
```

Review **all** changes/categories and blockers, score pairs, historical/canonical identity changes, source URL/hash, actual retrieval evidence and metadata failures. Never interpret populated scores or elapsed kickoff as final. Inspect the actual archive if needed; do not edit its bytes or receipt. A downloaded candidate with an integrity error stays invalid even when reused.

If a candidate needs rechecking against a newer DB baseline without downloading again:

```bash
docker compose --profile refresh run --rm refresh python -m ingestion.refresh --source nflverse-release --candidate "$REFRESH_CANDIDATE_ID"
```

This is still a dry-run. Review its new report/token. Do not work around blockers with the original manual ingestion CLI. That legacy path lacks these refresh-specific review/regression gates.

### 3. Explicitly apply only the reviewed candidate

Only after full tests, a successful real-source dry-run, no hard blockers and operator review:

```bash
REFRESH_REVIEW_TOKEN='paste-the-exact-reviewed-token'
docker compose --profile refresh run --rm refresh python -m ingestion.refresh --source nflverse-release --candidate "$REFRESH_CANDIDATE_ID" --apply --approve-review "$REFRESH_REVIEW_TOKEN"
```

`applied` means COMMIT was observed and the receipt recorded; it does not mean game finality was established. With the original baseline, counts may remain 842, but real source updates can add available POST games. This task did **not** execute an actual import, so there are no observed real import counts to report. Newly reported/corrected scores remain UNKNOWN.

Reapplying the same candidate when the DB already matches it should be unchanged:

```bash
docker compose --profile refresh run --rm refresh python -m ingestion.refresh --source nflverse-release --candidate "$REFRESH_CANDIDATE_ID" --apply
```

Omitting the token is safe only for zero changes. Otherwise the runner saves `review_required` and applies nothing; it cannot act as an approval bypass. Reusing an old token is not a universal reapply authorization if records changed meanwhile.

### 4. Inspect outcome/status, or recover an indeterminate commit

```bash
docker compose --profile refresh run --rm --no-deps refresh python -m json.tool /app/refresh-state/status.json
```

Exit 0: clean dry-run, applied, unchanged, or a successfully resolved not-applied recovery. Exit 2: a recorded rejection/review requirement, download/validation/database/state failure; read its report. Exit 3: configuration/lock/journal/indeterminate stop; `pending_run_ids` is included where readable. Argparse usage errors also exit 2, without starting work.

Only if the stop identifies a `commit_pending` run:

```bash
REFRESH_PENDING_RUN_ID='paste-a-pending_run_id'
docker compose --profile refresh run --rm refresh python -m ingestion.refresh --source nflverse-release --recover "$REFRESH_PENDING_RUN_ID"
```

Recovery confirms `applied` or `not_applied` without republishing. A contradictory receipt, unresolved lock or damaged state must be investigated; do not remove volumes/receipts, restore databases, change safety checks or “force” a retry. An interrupted pre-commit run may also recover as not_applied after the old DB lock is released. All these checks stay within development.

## Tests and actual results

The new synthetic suite covers source retrieval and complete validation, publisher size/digest/race checks, network/truncation/oversize failures, URL restrictions, immutable archive/receipt checks, review binding, new/corrected/removed scores, missing/ambiguous games, kickoff/matchup/schema changes, FINAL rejection, atomic journal outcomes, lock/checkpoint loss and commit recovery. PostgreSQL cases additionally cover successful reviewed apply, no-op/idempotency, real provenance fields, historical corrections/removals, changed-baseline review rejection and rollback after writes. Existing tests/contracts were retained.

Actual executed checks:

| Check | Result |
|---|---|
| `.venv/bin/python -m pytest backend/tests/test_refresh.py backend/tests/test_refresh_database.py backend/tests/test_ingestion.py backend/tests/test_schedule_service.py backend/tests/test_settings.py backend/tests/test_schedule_database.py -q -ra` | **90 passed, 55 skipped**. Includes 35 new pure refresh unit cases; seven new PostgreSQL refresh cases and 48 existing database cases skipped because no isolated server is accessible. |
| `.venv/bin/python -m pytest backend/tests/test_schedule_api.py -k 'invalid_request or read_only or async_error_handler_transport' -q -ra` | **23 passed, 10 deselected, one deprecation warning**. Existing API regression subset, not a full HTTP/database run. |
| `.venv/bin/python -m pytest backend/tests --collect-only -q` | **181 cases collected**; collection is not execution. The full PostgreSQL/synchronous-HTTP suite remains unverified here. |
| Python compilation of ingestion/new tests; `docker compose --profile refresh config --quiet`; `git diff --check` | **Passed**. These checks do not establish real download/DB compatibility. |

 A single real acquisition attempt using `retrieve(SourceConfig())` failed `network_failure` in this execution environment, without connecting to PostgreSQL. Docker client exists but socket access is denied. No full real-source candidate, real DB comparison/apply, container startup or PostgreSQL integration assertion was verified here. The original raw CSV hash remains `66f7a71b12eeb8da8a5c332cfadb245da693aa66e2064fba734983dc41e68fd5`.

## Remaining blockers and next approval

There is still no reliable completion signal in the approved schedule CSV. Manual operator review is the supported alternative for new score publication in this task; it does not certify FINAL. All actual source changes require review, and hard blockers remain unresolved until reviewed remediation. Do not activate unattended postgame applies by merely placing this CLI in cron.

Real-source and PostgreSQL acceptance must first run in normal WSL with the commands above. A durable local journal is not a distributed audit database or a frontend freshness endpoint. Package/runtime availability and actual current-source compatibility remain environment acceptance risks, not claimed passing results.

Next proposed implementation task **for approval after runner acceptance**: expose a read-only operational refresh-status API and dashboard disclosure, using these timestamps without equating checks to data changes/finality. Scheduling remains a separate approval requiring a trustworthy completion policy/evidence and an explicit decision about guarded corrections, not a consequence of this manual runner.

## Changed-file inventory

- `backend/ingestion/source.py`: explicit approved source, bounded retrieval, metadata verification and acquisition evidence.
- `backend/ingestion/refresh_policy.py`: typed-data comparison categories, hard blockers, baseline-bound review and transactional adapter.
- `backend/ingestion/refresh_state.py`: atomic operational receipts/checkpoints and process lock.
- `backend/ingestion/refresh.py`: default dry-run CLI, immutable candidate reuse, apply/recovery and sanitized outcomes.
- `backend/ingestion/service.py`: atomic archive capture, optional measured refresh provenance; original reconciliation safeguards retained.
- `backend/tests/test_refresh.py`, `backend/tests/test_refresh_database.py`: new synthetic unit and isolated PostgreSQL tests.
- `backend/Dockerfile`, `compose.yaml`: non-root state directory and manually invoked opt-in refresh profile/volume; no ports/scheduler.
- `AGENTS.md`, `docs/agent-task-007.md`, `docs/decisions.md`: current approved scope and rationale.
- `README.md`, `docs/development.md`, `docs/architecture.md`, `docs/implementation-plan.md`, `docs/schedule-ingestion.md`, `docs/schedule-data-contract.md`, this guide: safe usage, boundaries and review/testing evidence.

The existing untracked `docs/schedule-auto-update-feasibility.md` from the research task was read and preserved, not rewritten. No frontend, model, migration, API contract, dependency manifest or original CSV changed. No commit, merge, push or deployment performed. Stop for review.
