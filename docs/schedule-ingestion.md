# Development schedule ingestion — Task 004

## Scope and implementation

Owner-approved scope: [Task 004](agent-task-004.md). Run only on `feature/schedule-ingestion`, against isolated development PostgreSQL. The existing four-table schema and initial migration are unchanged. No API or frontend feature was added. The importer uses existing approved dependencies and Python's standard library.

`backend/ingestion/validation.py` reads the entire UTF-8 CSV strictly before database access. Every record must have the header's width; primary IDs must be present and unique across the file. Detailed semantic checks apply to 2024–2026 only. All three seasons must be present with 272 REG games, 32 teams/17 appearances, weeks 1–18 and no repeated team/week. Historical POST must have WC/DIV/CON/SB counts 6/4/2/1 and paired reported scores. Available 2026 POST is accepted within those round limits, with complete preceding rounds before later rounds; absent matchups are not generated. This is a full-snapshot importer, not a partial-week importer.

Scoped records require canonical `season_week_away_home` game IDs, the 32 validated source team codes, valid round/week combinations and paired nullable nonnegative integer scores within PostgreSQL integer range. Optional result/total values must agree with scores when present. Source dates/times preserve unknown values; known inputs must be valid Eastern times, unambiguous across DST, with a valid season/date relationship. Unknown date/time has no derived UTC kickoff. Invalid optional location/overtime tokens and duplicate non-null external IDs within a season reject the batch. These internal checks do not independently authenticate matchup, time or score correctness.

`backend/ingestion/service.py` reconciles inside the caller's transaction. The CLI wraps the entire database operation in one transaction, checks the actual database name, and serializes importers with a PostgreSQL transaction advisory lock. Unique `(provider, source_game_id)` is the primary lookup; `old_game_id` is preserved without matching or uniqueness. No deletes occur. Any existing provider game disappearing from a new snapshot aborts the batch. An ID correction may retain its canonical UUID only through an unambiguous matching ESPN ID, season and unordered pair of team codes. Both old/new IDs appearing, ambiguous matches, and unlinked ID changes fail for review. ESPN identity stability across every future snapshot is not guaranteed; this bounded rule favors rejection over guessing.

Team UUIDs and provider aliases are reused. Conflicting aliases reject the transaction. New team names initially equal their source abbreviations because the CSV supplies no verified display-name registry; full names are deferred. Source team strings remain on every game.

All newly imported games are UNKNOWN, including games with scores or past kickoff times. Unchanged independently evidenced FINAL records are preserved; any changed source record touching FINAL is rejected pending evidence review. This importer never creates FINAL, IN_PROGRESS or POSTPONED, and never manufactures missing scores or postseason records.

## Provenance and corrections

Before database reconciliation, exact input bytes are captured under a content-addressed filename in the dedicated `schedule_snapshots` Docker volume. Existing archive files are checked against their filename digest and never overwritten. The input mount is read-only. Preserve this volume with the database when backing up; receipts refer to its container paths. A failed transaction may leave an unreferenced source archive, but never a committed partial database import. A damaged/incomplete archive blocks reuse and needs operator review; the importer does not repair or delete it automatically.

Each applied change creates a new `source_artifacts` record with measured hash/size, documented official release route, CC BY 4.0 link, attribution/modification notice, and a versioned JSON receipt in `provenance_notes`. The receipt lists prior canonical/source IDs, artifact IDs and record hashes for corrections. Previous artifacts remain; reversion A→B→A creates another receipt. Unchanged games retain their original per-record artifact reference. Repeating an unchanged import adds no artifact or game rows.

Origin stays **DECLARED**. The exact owner download URL, retrieval time and revision are unknown, so their fields remain null; the documented route is not misrepresented as an independently verified actual download route. The historical release-listing digest and observation date are retained in notes as comparison evidence, not a matching publisher checksum for these bytes. `publisher_sha256`, authentication method/time and unavailable publication/download timestamps stay null. Database `recorded_at` is observation time, not download time. Successful validation/import does not resolve the checksum discrepancy or independently establish the release license's applicability to unauthenticated bytes. Existing owner-accepted declared-origin limitations and release-route license conclusions remain in force.

Per-record hashes use SHA-256 of UTF-8 JSON for the original column/value dictionary, with sorted keys, compact separators and `ensure_ascii=False`. Original strings, including empty tokens and optional source columns, are preserved in `raw_source_record`; exact CSV formatting stays in the artifact. `source_line` is the first physical CSV line of the record. Optional-column corrections also create an auditable update. No betting functionality is derived from retained raw columns.

No correction-history schema existed in the foundation. This task uses immutable artifacts plus append-only import receipts instead of adding tables or modifying the migration. Rejected attempts emit structured diagnostics to stderr and make no database audit writes; retain that output externally if needed. This is not a general queryable audit subsystem. The low-level reconciliation function requires a prevalidated snapshot and caller-managed rollback; use the CLI for operations.

## Normal WSL commands

Run from the repository root with the existing `.env` and Docker Desktop/WSL integration. Do not print `.env` or connection credentials. The development name must be `nfl_research_dev`, consistent with the approved configuration; the CLI additionally requires Compose host `db`. Do not bypass guards to target another environment.

```bash
git branch --show-current
docker compose --profile ingestion config --quiet
docker compose --profile test run --build --rm tests
docker compose --profile test stop db_test
```

Expected branch: `feature/schedule-ingestion`. Compose configuration succeeds with no output. All tests must pass before importing; database tests must run rather than skip. Tests use separate tmpfs `nfl_research_test`, and the existing test fixture applies the initial migration there. Stop on failures and retain sanitized output. The previous 45-test result predates these additions and does not validate them.

Validate bytes without starting or accessing a database:

```bash
docker compose --profile ingestion run --build --rm --no-deps ingestion
```

The default command is dry-run. It prints one JSON summary and exits zero; no archive or database writes occur. A local equivalent with already installed approved dependencies is:

```bash
cd backend
../.venv/bin/python -m ingestion.schedule --file ../data/raw/games.csv --dry-run
cd ..
```

Only after successful tests/dry-run, start the existing development database and apply the import:

```bash
docker compose up -d --wait db
docker compose --profile ingestion run --rm ingestion python -m ingestion.schedule --file /data/raw/games.csv --apply
```

This assumes the initial development migration has already been applied, as reported by the owner. The importer neither initializes nor migrates the schema. If PostgreSQL reports a missing schema, stop and use the existing migration procedure in [development.md](development.md) against development only; do not recreate databases or reset volumes.

Successful apply prints `mode: committed` with inserted/updated/unchanged counts, seasonal coverage, score-pair counts, source hash and warnings. For an empty development schedule and the current bytes, expected counts are 842 inserted, zero updated/unchanged. This is an expectation, **not an executed import result**. Repeating the exact apply command should report zero inserted/updated and 842 unchanged. To import a future approved snapshot, retain this original file and mount the new file/directory read-only through a reviewed Compose override; supply its path using `--file`. Do not edit the original CSV to test corrections. Each new snapshot undergoes the same full validation and provenance limitations; source authentication is not inferred.

Optional read-only verification after a successful import:

```bash
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT season, season_type, count(*) FROM games WHERE provider = '\''nflverse'\'' GROUP BY season, season_type ORDER BY season, season_type;"'
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT status, count(*) FROM games GROUP BY status;"'
```

Exit 2 means source validation, identity reconciliation or database guard rejection; diagnostics identify the category and source line where applicable (first 100 problems, with total count). Exit 3 means input/archive/configuration failure. Exit 4 means database failure and rollback. Check database health, existing migration, credentials or permissions as indicated; never paste credentials. No automatic retry, privileged workaround, source download or destructive repair occurs. Archive-volume write permission failure requires reviewing volume ownership, not changing the raw input's permissions. Do not remove database/archive volumes to solve an import error.

## Actual verification — 2026-11-06

The agent executed the local dry-run on the original file. All 7,548 rows parsed; 842 scoped records passed. SHA-256 stayed `66f7a71b12eeb8da8a5c332cfadb245da693aa66e2064fba734983dc41e68fd5`.

| Season | REG | WC/DIV/CON/SB | Paired / missing scores | Operational interpretation |
|---|---:|---|---|---|
| 2024 | 272 | 6/4/2/1 | 285 / 0 | Completed archive; finality remains unknown |
| 2025 | 272 | 6/4/2/1 | 285 / 0 | Completed archive; finality remains unknown |
| 2026 | 272 | 0/0/0/0 | 121 / 151 | In progress; absent postseason not invented |

Eight nonunique 2026 legacy IDs remain accepted as nonunique metadata. These are validation counts, not database row counts. **No actual database import, migration or container startup was performed by this task.**

Executed checks:

- `.venv/bin/python -m pytest backend/tests/test_settings.py backend/tests/test_schedule_database.py backend/tests/test_ingestion.py -q -ra`: **27 passed, 48 skipped**. Skips comprise 38 existing PostgreSQL tests and ten new ingestion PostgreSQL tests, because `RUN_DATABASE_TESTS` is not enabled without an accessible isolated server. The 23 new ingestion unit tests pass; they cover complete/invalid/duplicate/truncated CSVs, required columns, nullable versus zero scores, time conversion/DST, score arithmetic, available POST, external-ID collisions, archive immutability and dry-run/errors.
- The ten authored ingestion database test cases cover successful import/idempotency, correction and reversion, source-ID reconciliation, missing-existing rejection, FINAL correction rejection, fresh-import rollback, invalid-snapshot preservation correction rollback, and rejection of stored game/alias drift even on unchanged imports. They were **not run** against PostgreSQL here.
- A full-suite attempt was interrupted after it stalled in the first unchanged health test. Bounded diagnostic rerun: `timeout 20 .venv/bin/python -m pytest backend/tests/test_health.py -vv -o faulthandler_timeout=8` exited **124**. The trace shows Starlette TestClient waiting in the AnyIO thread portal; no health assertion completed. Root cause is unresolved in this agent environment. Do not treat the three health tests as passed or as assertion failures.
- `docker version`: client available, daemon socket access denied. Container startup/import/integration tests could not run; no privileged workaround attempted.
- `docker compose --profile ingestion --profile test config --quiet`: **passed** without daemon access.
- Python compilation of new importer/tests and `git diff --check`: **passed**.
- The original CSV hash matches the prior local validation hash. No source bytes, schema, dependencies, production data, commits or merges were changed.

 The complete suite collects 78 cases; 27 passed, 48 database cases were skipped, and three health cases remain unverified here. The owner-reported foundation validation remains separate evidence. PostgreSQL integration/idempotency/rollback behavior requires the normal-WSL test run above before operational use.

Remaining risks: unauthenticated source origin/published checksum discrepancy; unsupported operational statuses; no independent external matchup/score reconciliation; bounded source-ID correction matching; Docker-volume artifact retention; new database paths not yet runtime-verified here. Proposed next task for owner approval after these checks: a read-only schedule API with coverage/provenance and reported-score/UNKNOWN labeling. No such endpoint or frontend is implemented or approved by Task 004.

## Changed-file inventory

| Files | Purpose |
|---|---|
| `backend/ingestion/__init__.py`, `validation.py`, `service.py`, `schedule.py` | Separate pipeline package, pure full-file validator, transactional reconciliation/archive capture, safe CLI |
| `backend/tests/test_ingestion.py` | 23 pure unit cases and ten PostgreSQL integration cases using synthetic full schedules |
| `backend/Dockerfile`, `compose.yaml` | Non-root archive directory, opt-in ingestion service, read-only raw mount and persistent snapshot volume |
| `AGENTS.md`, `docs/agent-task-004.md`, `docs/decisions.md` | Record the owner's approved ingestion scope and safeguards |
| `docs/schedule-ingestion.md` | Commands, design, actual measured results, failure handling and limitations |
| `docs/development.md`, `docs/implementation-plan.md`, `docs/data-model.md`, `docs/schedule-data-contract.md` | Synchronize current scope/status and link ingestion details while preserving historical research records |

No application API/model or Alembic migration files were changed. No dependency manifests were changed. Stop for owner review before committing, merging or starting the next feature task.
