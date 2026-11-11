# PostgreSQL team statistics — storage and guarded ingestion

**Task 011 update:** owner reports migration/role transition and the 705-pair import completed. The [read-only statistics API](team-stats-api.md) adds explicitly approved column-level API reads; earlier statements denying all API statistics access describe the Task 010 policy. Batch evidence/raw records/history and all API writes remain denied. No migration or import is repeated.

Owner-approved implementation on `feature/team-stats-ingestion`. The schema/workflow proposal was explained before implementation. This is an additive development-only step following the [offline contract](team-stats-validation.md), [gamebook review](team-stats-gamebook-review.md), [architecture](architecture.md), [data model](data-model.md) and Decision 61's approved NET definition. No unresolved statistical definition was substituted.

**Security hardening:** [role transition, adversarial tests and migration NO-GO gate](team-stats-security-hardening.md) supersede earlier privilege/approval instructions.

**Review gate:** implementation is written; PostgreSQL runtime acceptance remains pending. No development migration, real import, correction or logical rollback was executed. Commands below are prepared for owner review/approval, not a record of operations already performed. No commits, merges, pushes or deployment.

## Input evidence and actual checks

Owner's successful audit: `data/raw/team-stats-audit/audit-5b23716443d34c33b89818c30f3f524c.json`: exit 0, 285/285/135 games, 705 pairs and 1,410 team rows. The new candidate reader independently re-read its original CSVs, schedule, canonical UUID export and six-row reference manifest and recomputed the existing offline checks successfully. **This was file-only validation, with no database connection or import.** Historical pre-hardening candidate fingerprint (superseded by complete version-2 evidence binding; do not use for approval):

```text
c9551fc65c91637603a8c47384426d2540feca73f9d7f333f35e056bdd68dba7
```

The successful audit's local-input receipts explicitly have no actual retrieval timestamps or publisher metadata; they remain DECLARED, not independently authenticated downloads. Import does not upgrade that claim. The original schedule's checksum discrepancy and all existing reported-score/UNKNOWN limitations remain intact.

## Physical schema: proposal and implementation

Five new tables in migration `0002_team_stats`, following `0001_schedule`; no schedule table/constraint/status changes:

| Table | Meaning and safeguards |
|---|---|
| `team_stats_batches` | UUID, IMPORT/ROLLBACK operation, candidate hash, exact review token, evidence JSONB, database observation timestamp. Immutable successful changing-operation record; no-op/rejected attempts produce only CLI reports |
| `team_stats_pairs` | Immutable game-pair revision UUID; canonical game/home/away UUID FKs; batch and `source_artifacts` FKs; previous pair within the same game; definition version and content hash. Unique batch/game |
| `team_game_stat_revisions` | Two immutable rows per pair, keyed by pair/team UUID; canonical game/opponent FKs, HOME/AWAY role; gross pass, original signed sacks, NET pass, rush; raw source row/hash/physical line. Unique pair/side; indexes for game/team access |
| `team_stats_accepted` | One pointer per canonical game to a complete pair revision, selecting batch and monotonic generation. No direct deletion; pointer moves require a valid chain tip; the database generates the matching history event |
| `team_stats_selection_events` | Immutable UUID event, operation batch, game and before/after pair IDs constrained to that game; unique per-game generation records actual initial acceptance, correction and logical rollback through an AFTER trigger |

Existing `source_artifacts` records capture each season's bytes/hash/size, actual declared acquisition observations, optional publisher metadata, notices and license. They are linked from the immutable pair revisions; their existing schema is unchanged. Batch evidence retains the full input audit/reference/schedule/identity receipts and archive map. Archive paths are actual captured container paths; publisher-original publication time remains null. All new batch/pair/event timestamps mean database observation, never game completion.

Definition: `net_pass_negative_sacks_v1`. NET = gross + original nonpositive signed sack adjustment. No absolute values or sign repair. The database checks this equation with bigint intermediate arithmetic to avoid integer overflow; individual stored yardage fields are PostgreSQL integers. Negative NET/rush and legitimate zero remain valid. Metrics are nullable in revision storage, with NET null if an operand is missing; the existing validator and accepted-pointer guard reject incomplete accepted pairs. This supports faithful missing-value representation without weakening admission.

Reciprocal membership uses explicit foreign keys plus PostgreSQL triggers on **new tables only**. Parent insertion checks canonical game sides and nflverse artifact provider; child insertion checks the pair's home/away role and opponent. Before acceptance, the database requires exactly two non-null metric rows, current canonical membership, correct generation and proven prior acceptance chain; the AFTER trigger records the actual transition. Updates/deletes on batch/pair/team/history records are rejected by append-only triggers. Rollback selects an existing prior complete pair; it never rewrites a revision or deletes history. Direct database-owner/superuser tampering is outside these application guarantees.

Defensive passing/rushing allowed is derived by joining the other row of the same accepted pair. No independently editable allowed-yard columns, rankings, completed-game flags, scores or completion evidence are stored in the statistics tables. Scores retain their original schedule provenance. Future queries should join canonical season/stage through `games`, keeping REG/POST separate.

## Guarded workflow

1. Require a successful version-1 offline audit for all three seasons, fixed approved source URLs, measured byte hashes/sizes, valid provenance receipts, exact schedule/export/reference hashes, no acquisition-integrity failure and negative convention established through reviewed references. DECLARED local provenance is permitted under the approved contract, clearly labeled. Missing receipts/files, contradictory available publisher metadata, forged download times and unsuccessful audits reject.
2. Re-read each supplied content-addressed CSV, rerun the existing validator and compare its identity/coverage/reference/derived results to the audit. Never trust only its `audit_exit_code` or derived NET fields. Both teams must map exactly and have complete metrics. No legacy-ID or fuzzy-identity fallback.
3. Capture exact audit, original schedule, identity export, reference manifest and three CSVs with no-replace content-addressed archive operations. The generic capture primitive uses `.csv` suffixes for these byte blobs, including JSON; their type is explicit in the evidence archive map. Existing bytes are checked, not overwritten.
4. Check actual database name (`nfl_research_dev`, or isolated `nfl_research_test` in test adapter). CLI additionally requires the existing Compose `db` host and development name. Acquire the **existing** schedule advisory transaction lock and game/selection row locks. Set a bounded lock wait. This coordinates identity reads with existing schedule import/refresh without modifying them.
5. Verify incoming UUIDs, source IDs, aliases, season/week/stage and reciprocal sides against the live database. Validate existing accepted pairs, their hashes and original source receipts/archives. Reject disappearing accepted games, missing currently reported-score games, source/alias drift, missing evidence and ambiguous mappings. A reported score is a coverage cross-check, not finality evidence.
6. Dry-run produces complete pair-level before/after metrics, original/next content hashes, insertion/correction counts, blockers and a token bound to candidate evidence, the schedule/team/alias/accepted/history baseline. Raw source-record changes count as a revision even when the selected metrics stay the same; line-order/whole-file-only changes alone do not force a revision.
7. Explicit apply revalidates captured bytes and candidate output again, recomputes the live plan under lock, and requires the exact current review token for **every changing import**, including initial import. No force flag or review acknowledgement bypasses a hard blocker. Historical (2024/2025) and current-season corrections are both reviewed. A stale token rejects rather than using the old diff.
8. One caller-owned transaction writes the batch, source provenance, pair and two team revisions, immutable history and accepted pointers for **all** changing games. Any exception rolls back that transaction. Unchanged reimports perform no database writes. One-side correction still creates a complete two-team revision, retaining the old pair.

The original raw files and schedule records are never updated. All acquisition is upstream of this command: no downloads, schedulers, recurring jobs, APIs or frontend changes. Failed validation leaves the accepted database state intact; unused source captures can remain as evidence.

### Logical rollback

Rollback is batch-scoped and always previewed/reviewed. It requires a prior pair for every event in the target batch, validates those prior pairs/archives and requires current selections still match the batch being reversed (or already equal their prior targets). A new ROLLBACK batch and selection events move the pointers back. Repeating an already restored target is a no-op. A mixed initial-and-correction batch containing games with no prior accepted pair **cannot** be unpublished this way: no valid history/data is removed. An initial import has no earlier revision to restore. Source archives and all revisions remain retained.

Lost commit acknowledgement or report-write failure is a separate operational uncertainty: database batch/history records remain authoritative. The CLI reports the transaction phase and does not automatically retry. Re-run dry-run and inspect batch/selection history before deciding what occurred. This task does not add the schedule runner's independent filesystem commit-recovery journal or claim rollback on a connection failure during COMMIT.

## Exact normal-WSL verification and operation commands

Run from repository root. No commands in this section have been executed against development PostgreSQL by the agent. First follow the [restricted-role test and existing-volume transition runbook](team-stats-security-hardening.md). Reset only the ephemeral test container if it holds the earlier 0002 definition.

### 1. Unit and isolated PostgreSQL tests

```bash
.venv/bin/python -m pytest backend/tests/test_team_stats_ingestion.py -q -ra
docker compose --profile test run --build --rm tests python -m pytest \
  tests/test_team_stats_ingestion.py tests/test_schedule_database.py \
  tests/test_ingestion.py tests/test_refresh_database.py -q -ra
docker compose --profile test run --rm tests
docker compose --profile test stop db_test
```

The existing test profile targets only ephemeral `nfl_research_test` on its isolated network. Its fixture applies migrations **there**, not to development. All authored PostgreSQL cases and schema/ORM comparison must pass before accepting storage behavior. A failure/skip is not a pass; retain/redact diagnostics and resolve it before real apply. Do not change the test database name or point tests at development.

Offline DDL review is possible without connecting to a database:

```bash
(cd backend && ../.venv/bin/python -m alembic upgrade 0001_schedule:0002_team_stats --sql) \
  > /tmp/team-stats-migration.sql
```

Review this together with `backend/alembic/versions/0002_team_stats.py`, including constraints/triggers. No PostgreSQL execution is implied by rendering SQL.

### 2. Development migration — only after owner approval

This command changes development schema. It is provided for review and **must not be executed by the agent without that approval**. The existing development database must already be healthy and backed up according to the owner's workflow; no backup restore or database reset is part of this task.

After the separately approved explicit role transition, use the owner override (never the API/runtime credentials):

```bash
docker compose -f compose.yaml -f compose.admin.yaml --profile ingestion run --build --rm ingestion alembic upgrade 0002_team_stats
```

The guard prevents proceeding on mismatched settings. Expected current Alembic revision afterward: `0002_team_stats`. No seed/import step is in this migration. Do not use downgrade as a logical statistics rollback; schema removal is destructive and separately gated.

### 3. Guarded dry-run against development — after schema acceptance

Reuse the existing ingestion service, read-only raw input mount and durable `schedule_snapshots` volume. A read-only docs bind supplies the reviewed reference manifest; no Compose service/volume change is necessary.

```bash
stats_args=(
  --audit /data/raw/team-stats-audit/audit-5b23716443d34c33b89818c30f3f524c.json
  --artifact-dir /data/raw/team-stats-audit/snapshots
  --schedule /data/raw/games.csv
  --identity-map /data/raw/team-stats-identities.json
  --references /review/docs/team-stats-gamebook-references.json
)

docker compose --profile ingestion run --rm \
  -v "$PWD/docs:/review/docs:ro" ingestion \
  python -m ingestion.team_stats.ingest "${stats_args[@]}"
```

Dry-run is the default; `--dry-run` is also accepted. No stats/schedule/artifact database writes occur. Source byte captures and a unique report are written under `/app/snapshots/team-stats/`. The printed output contains `outcome`, report path and optional batch ID/error. The token is only in the private mode-0600 report, not stdout. Exit 0 means a successful preview/no-op; exit 2 means rejected/blocked; exit 3 means configuration/database/report failure. A blocked preview cannot be applied with approval.

For an empty stats store and this unchanged admitted baseline, expected preview counts are **705 inserted pairs, 0 corrected, 0 unchanged** (1,410 team rows). These are expectations, not an executed database result. Source omissions or live UUID/alias changes cause rejection. A live database with more scored games than this snapshot may legitimately reject it as incomplete; audit a newer approved snapshot rather than bypassing that safeguard.

Review the entire saved report, not just the token:

```bash
read -r stats_report_path
docker compose --profile ingestion run --rm ingestion \
  python -c 'import json,sys; r=json.load(open(sys.argv[1])); r.get("plan",{}).pop("review_token",None); print(json.dumps(r,indent=2))' "$stats_report_path"
```

Enter the exact container report path printed by the dry-run. This view redacts the approval token; access that value privately only after review, without sending it to logs or shared output. Inspect blockers, candidate/baseline hashes, definitions, all before/after pair changes, missing coverage and historical corrections. This token is a snapshot acknowledgement, not a password or proof of source authenticity.

### 4. Explicit apply — requires separate owner approval

After that review and approval, enter the token from the reviewed report manually; do not automate token extraction into an apply:

```bash
read -rs stats_review_token
printf '%s\n' "$stats_review_token" | docker compose --profile ingestion run -T --rm \
  -v "$PWD/docs:/review/docs:ro" ingestion \
  python -m ingestion.team_stats.ingest "${stats_args[@]}" \
  --apply --approval-stdin
unset stats_review_token
```

Expected successful changing outcome: `applied`, with a new batch ID and full report. Repeating identical inputs after a confirmed apply should report `unchanged` without new artifacts/revisions/batches. A changed baseline requires a new dry-run/review. Do not mistake actual ingestion observation time for a game end or source publication time.

### 5. Correction and logical rollback review

A correction requires a **new successful offline audit**, retaining old CSVs/reports/references; use its new `--audit` and hashes, preview, inspect historical changes, obtain owner approval and apply the exact review token. Do not edit a captured CSV, audit, old revision or original schedule to force acceptance.

For a correction batch with valid prior pairs (never an initial batch), enter its actual UUID, then preview:

```bash
read -r stats_batch_id
docker compose --profile ingestion run --rm ingestion \
  python -m ingestion.team_stats.ingest --rollback-batch "$stats_batch_id"
```

Review that report and obtain explicit rollback approval before:

```bash
read -rs stats_rollback_token
printf '%s\n' "$stats_rollback_token" | docker compose --profile ingestion run -T --rm ingestion \
  python -m ingestion.team_stats.ingest --rollback-batch "$stats_batch_id" \
  --apply --approval-stdin
unset stats_rollback_token
```

The CLI never deletes initial accepted data, repairs missing archives or restores backups automatically. Preserve the shared snapshots volume with the database: rollback validation requires those original bytes and receipts.

## Historical Task 010 tests and actual agent results

These results precede security hardening; current results and PostgreSQL acceptance requirements are in the [hardening report](team-stats-security-hardening.md).

- New candidate/planning/CLI/frozen-DDL tests: **23 passed**; **12 new PostgreSQL cases skipped**, because isolated PostgreSQL was not available/enabled.
- Combined selected backend suites: **214 passed, 67 skipped**. Includes existing offline validator, ingestion, refresh, settings, freshness and schedule services plus new tests; skips are PostgreSQL cases.
- Existing async schedule API validation/read-only/error transport subset: **23 passed**, 10 deselected, one existing TestClient deprecation warning.
- New migration rendered offline successfully; frozen table/index DDL matches ORM metadata in the executed test. PL/pgSQL triggers were **not executed** or certified at runtime here.
- Read-only real candidate revalidation: **705 pairs / 1,410 team rows**, without PostgreSQL, source capture or real apply.
- Docker daemon probe: socket permission denied. No development migration, DB-backed dry-run, real import/correction/rollback or live API/database smoke test was attempted afterward.
- Full synchronous TestClient suite was not repeated; earlier environment reports document its thread-portal stall. Use the WSL full test-profile command above. No frontend files changed or frontend tests needed.

Authored PostgreSQL cases cover initial acceptance and idempotency, required review/stale-token rejection, canonical integrity, all-pair transaction rollback after a flushed pointer, historical correction and reviewed rollback/idempotency, append-only rows/deletes, complete-pair/event guards, null/zero/negative values and bad membership/arithmetic, missing old archives, rollback interruption and unchanged schedule state. Existing migration/model comparison and ingestion/API tests remain intact.

## Complete changed-file inventory

- `backend/app/models/team_stats.py`: five additive models and constraints/indexes.
- `backend/app/models/__init__.py`: register new mappings for Alembic.
- `backend/alembic/versions/0002_team_stats.py`: frozen PostgreSQL table/index DDL and new-table-only triggers.
- `backend/ingestion/team_stats/candidate.py`: successful-audit admission, receipt/byte/reference validation and complete source captures.
- `backend/ingestion/team_stats/storage.py`: guarded live reconciliation, immutable revisions, reviewed transactional selection and logical rollback.
- `backend/ingestion/team_stats/ingest.py`: development-only CLI, dry-run default, explicit apply/approval and unique reports.
- `backend/tests/test_team_stats_ingestion.py`: synthetic unit/plan/DDL/CLI and isolated PostgreSQL tests.
- `docs/team-stats-ingestion.md`, `docs/agent-task-010.md`: scope, schema proposal, implemented behavior, commands and review gate.
- `AGENTS.md`, `README.md`, `docs/architecture.md`, `docs/data-model.md`, `docs/decisions.md`, `docs/implementation-plan.md`, `docs/development.md`: current scope/architecture/model/runbook links and decision synchronization.

Task 010 originally left Compose unchanged. Subsequent security hardening separates runtime credentials and adds an explicit admin override; see the hardening inventory. Original source/audit files, schedule models/migration, schedule ingestion/refresh logic, public response contracts and frontend remain unchanged.

## Remaining risks and next proposed task

Runtime migration/constraint/transaction behavior and ORM/schema parity must pass against isolated PostgreSQL in normal WSL. The accepted-state check cannot prove upstream current-season completeness for games with neither stats nor reliable completion evidence; it enforces the admitted snapshot, historical schedule contract, current reported-score coverage and no loss of previously accepted games. Partial-season coverage must stay labeled. Declared provenance, sampled gamebook calibration, original schedule checksum uncertainty and unavailable completion-before-cutoff evidence remain unchanged. New schedule identity corrections can invalidate stats membership; the guarded command stops for review rather than silently remapping accepted history.

Proposed next task **for approval**: isolated PostgreSQL runtime acceptance of this migration/ingester, followed by owner review of a development dry-run. Only after that evidence and separate explicit permission should the first real 705-pair import occur. No rankings or new API/frontend scope is implied.
