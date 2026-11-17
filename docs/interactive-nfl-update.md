# Tasks 020–021 — interactive NFL data update

Task 021 improves presentation and guidance only: normal interaction uses readable text and sequential review with separate default-no approvals; `--status` retains its machine-readable JSON contract. Task 020 established the guarded orchestration.

Owner-approved scope: one operator command for the existing schedule and team-statistics workflows, with independent review and approval. No automatic imports, recurring enablement, new data sources/services/dependencies, frontend, schema, role/permission, finality or ranking changes. No development import, migration, commit, push or deployment was executed during implementation.

## Setup and normal use

Use WSL Ubuntu with Bash and Docker Compose v2, the existing private `.env`, healthy existing `db` and `api` services, and the already provisioned restricted `nfl_ingest` role/schema. Host Python is unnecessary for normal operation. The existing scheduler service supplies the backend image, approved networking, read-only raw/docs inputs and durable snapshots/refresh volumes; `compose.yaml` is unchanged.

Build the current CLI into that image once after updating code:

```bash
cd /home/edander5/nfl-research-planning
docker compose --profile scheduler config --quiet
docker compose --profile scheduler build scheduler
docker compose ps db api
```

If the existing app is stopped, use its normal startup procedure. The update command checks readiness and never starts, resets, recreates or migrates databases. Do not use the administration override.

If the recurring scheduler is enabled, coordinate a pause first:

```bash
docker compose --profile scheduler stop scheduler
```

The updater never stops or restarts recurrence itself. A stopped scheduler stays stopped. Never delete locks or claims. If recurrence was previously authorized and is still desired, restarting it afterward is a separate deliberate operator action using the existing scheduler runbook.

Run:

```bash
./scripts/update-nfl-data.sh
```

An absolute path to this script also works from another directory. Preparation downloads the existing approved full schedule and 2024–2026 team-stat snapshots, retaining all private receipts. It uses the scheduler's fixed one-shot preparation components, not its daemon loop. Both checks run independently; unavailable or invalid data is reported as failed, never unchanged. Preparation then reuses the saved schedule candidate and runs the original statistics ingestion dry run against the archived refresh handoff.

The CLI shows `NFL DATA UPDATE`, checks both sources, then displays each pipeline as up to date, changes available, validation blocked or failed. Counts come from actual validated game changes; categories may overlap. New score games and betting-line reference changes are separate from new statistics games and corrections to previously accepted statistics. A concise affected-game list shows up to ten IDs per pipeline, followed by all games during review. Existing reports provide team codes in source game IDs and changed identity fields when available; no full team names are invented or new identity queries added.

Unchanged pipelines never request approval. With no changes, the CLI explains that accepted storage matches the candidates from this check and asks only `Press Enter to exit.` This does not claim complete upstream coverage or verify HTTP delivery/browser caches.

For changes, the guided sequence is schedule first, then statistics:

1. `Review proposed changes? [Y/n]` — Enter shows details; `n` skips this pipeline.
2. A new dry run checks that the exact candidate and current baseline still match the reviewed plan. If the plan changed, the operator is guided back through review before any import prompt.
3. Detailed game IDs/change types and safe before/after values are displayed. Schedule includes scores, line references, kickoff and identity fields. Other source values stay private. Statistics includes both teams' stored yardage and changed source field names. A source-only correction explicitly says stored yardage is unchanged; changes involving EPA say that EPA source values or precision changed, without claiming a rounding-only change has been proven.
4. `Approve import? [y/N]` (shown separately under each pipeline heading, after its change details) — only `y` or `yes` (case insensitive, with surrounding whitespace ignored) approves that pipeline. Enter, `n`, unrecognized text, EOF or Ctrl+C never imports.
5. The guarded apply runs once, followed by the existing read-only verification. Only a confirmed apply **and** successful verification produces `IMPORT SUCCESSFUL`. The next pipeline then gets its own independent review and approval.

No menu keys, report-path copying, token entry or raw JSON interpretation is needed. Task 021 supersedes Task 020's typed-phrase interaction only; tokens remain internal and out of terminal output, process arguments and CLI journals. Statistics tokens still use `--approval-stdin`; schedule still calls `refresh.execute` under the original filesystem lock. Scheduler worker JSON completion events are captured during preparation rather than printed into the guided interaction; original durable scheduler job reports/log records are preserved. No scheduler implementation or behavior changed.

After approval, importers revalidate candidate evidence and compare the live baseline again under their original transaction locks. A concurrent write during the prompt still invalidates approval. Hard blockers cannot be overridden. A previously reviewed statistics plan can change after a schedule import; follow the repeated statistics review prompt to see the new plan and then approve it separately. Identity or coverage failures may require separately reviewed newer schedule/identity/reference inputs; the CLI never rewrites those files or invents mappings.

## Status and verification

```bash
./scripts/update-nfl-data.sh --status
```

This mode reads sanitized scheduler observations and the latest CLI journal only. It does not download, compare, mint approvals or import. It works without a terminal and while the recurring scheduler is running. The launcher still requires healthy app prerequisites. Scheduler status describes prepare-only checks; the additional CLI record describes guarded apply/verification outcomes. Exit 0 means inspection succeeded, not that every pipeline is current or successful.

After each confirmed successful import, the CLI starts a PostgreSQL read-only transaction and uses existing repositories:

- Schedule: compare every changed game's accepted scores and canonical values, source-record hash and artifact hash with the reviewed archived candidate.
- Statistics: compare complete two-team accepted rows, all four stored yardage measures and accepted pair content hash with the reviewed plan.

Verification checks the current accepted database view used by existing APIs. It does not certify source authenticity, FINAL, completion-before-kickoff, upstream completeness or browser cache freshness. API HTTP transport remains a host smoke check. Missing/null and zero stay distinct. Unchanged pipelines perform no apply; repeated checks do not fabricate new revisions.

The final plain-text summary distinguishes updated-and-verified, up to date, skipped, validation blocked, check/import failed, verification failed and unknown apply outcome. It reports imported-and-verified score/statistics/correction counts and database verification scope. Skipped or failed pipelines produce an incomplete/partial-update explanation and next safe step, never an all-updated claim. Only verified imports are described as newly available to the website; refresh your browser to see them. No HTTP/browser verification is implied. Interrupted/unconfirmed applies and verification failures have explicit separate states. Exit codes: 0 for a completed session with no failed pipelines (including intentional skips); 2 for pipeline check/rejection failures; 3 for prerequisite/configuration/lock/report/uncertain apply or verification failure; 130 for interruption before apply. An interruption during apply is conservatively unconfirmed (3).

## Reports, coordination and errors

Original source archives, schedule candidates/runs/checkpoints, team-stat refresh handoffs and ingestion reports retain their original locations and privacy. The updater adds only private mode-0600 atomic JSON records:

```text
/app/refresh-state/update-cli/latest.json
/app/refresh-state/update-cli/runs/<session-UUID>.json
```

These contain phases, pipeline states, observation time and reviewed/importer report references, never approval tokens or raw payloads. The session record is updated through review/apply/verification; earlier sessions are retained. No pruning or log deletion occurs.

The original `/app/refresh-state/scheduler/runner.lock` is held for the whole interactive session. This coordinates other updater instances and the recurring/one-shot scheduler across the shared Compose volume. Original per-pipeline refresh locks and shared PostgreSQL advisory/row locks remain authoritative. Standalone importers can still change a baseline while the operator reviews, so re-preview and guarded apply remain mandatory. Different volumes or customized state directories are outside the existing local coordination guarantee.

Troubleshooting:

- **Docker/Compose/socket unavailable:** fix the existing Docker Desktop/WSL integration through the owner's normal procedure. The CLI does not alter packages, socket permissions or WSL networking.
- **Service unhealthy/missing:** inspect `docker compose ps db api` and existing health diagnostics. The updater does not provision roles, apply migrations or repair the database.
- **Module missing in cached image:** rebuild the scheduler image using the setup command. No recurring scheduler is launched by building or by `run --no-deps`.
- **Busy:** allow the competing operation to finish, or coordinate stopping the recurring scheduler using the documented command. Do not delete lock files, pending receipts or claims.
- **Source/download/audit/input failure:** retain accepted data. The other pipeline remains reviewable. Review the existing private report and approved input paths configured by `SCHEDULER_STATS_*`; missing sources are never treated as zero changes. Retry only as a deliberate new check after diagnosis.
- **Blocked/stale candidate/token rejection:** inspect summary and detailed blockers, obtain valid inputs or review a new baseline. The CLI never auto-retries an apply or silently uses an old token.
- **Ctrl+C/EOF during review:** exit without further imports. Completed earlier approved imports remain accepted. During preparation, the existing child worker termination logic is signaled and its original reports are retained.
- **Uncertain COMMIT/report loss/verification failure:** STOP. The durable `applying`, `indeterminate` or `verification_failed` CLI record blocks subsequent interactive imports. `--status` remains available. Use original schedule `--recover`/pending-receipt investigation or statistics batch/selection-history investigation from the linked runbooks; neither is automatically executed. A verification failure does not imply rollback. Do not delete/edit journals or blindly retry. Reopening an uncertain CLI session after the original outcome has been established requires a separately reviewed recovery step; this task deliberately adds no uncertainty override or generalized repair command.

## Validation commands for normal WSL

These commands avoid development writes until an explicit `y` or `yes` is entered at a pipeline import prompt:

```bash
cd /home/edander5/nfl-research-planning
bash -n scripts/update-nfl-data.sh
.venv/bin/python -m pytest backend/tests/test_update_cli.py backend/tests/test_scheduler.py \
  backend/tests/test_refresh.py backend/tests/test_team_stats_ingestion.py \
  backend/tests/test_team_stats_refresh.py -q -ra

# Isolated PostgreSQL profile only; never point tests at development.
docker compose --profile test run --build --rm tests
docker compose --profile test stop db_test

docker compose --profile scheduler build scheduler
./scripts/update-nfl-data.sh --status
# If enabled, coordinate stopping recurrence before interactive validation.
./scripts/update-nfl-data.sh
# First inspect details and answer n (or Enter) at each IMPORT prompt. Confirm nothing was imported.
# Repeat and approve each desired pipeline separately only after reviewing its diff.
./scripts/update-nfl-data.sh --status
# Read-only API smoke checks; inspect game-specific endpoints in the existing API guides.
curl --fail --silent --show-error http://127.0.0.1:8000/api/health
curl --fail --silent --show-error http://127.0.0.1:8000/api/data-status/schedule
# A subsequent interactive check should report unchanged, subject to upstream changes.
./scripts/update-nfl-data.sh
```

Synthetic tests cover separate approvals, dry runs/no-op repeats, new pairs and historical/source-only corrections, failed sources, blockers/stale reviews, importer rejection/token mismatch, skips, Ctrl+C, uncertain applies, concurrency adapters, verification mismatch, private tokens/payloads and noninteractive refusal. Existing scheduler/importer tests cover their original locks, admission, idempotency and transactional guards. New verification tests exercise real adapter comparisons with synthetic repository results; live PostgreSQL/API behavior still requires WSL validation. No synthetic data is used for accepted features.

Historical Task 020 validation: the five-file targeted command above completed with **157 passed, 13 skipped**. All 13 skips are existing isolated PostgreSQL cases requiring `RUN_DATABASE_TESTS=1`; they are not passes. Bash syntax, Python compilation and `git diff --check` passed. Docker, live-source acquisition, development database/API verification and real imports were not executed. The launcher was exercised with a synthetic Docker executable, including invocation from another directory and unhealthy-service rejection.

## Source references and modified files

This task uses existing local contracts and approved sources; no new external source/license claim or network research was needed. References: [schedule refresh](schedule-refresh.md), [team refresh and handoff](team-stats-refresh.md), [statistics ingestion/approval/uncertain commit](team-stats-ingestion.md), [restricted-role contract](team-stats-security-hardening.md), [scheduler coordination](scheduled-nfl-refresh.md), and existing read-only repository implementations. Source attribution/license receipts are preserved by those workflows.

Implementation: `scripts/update-nfl-data.sh`, `backend/ingestion/update_cli.py`, `backend/tests/test_update_cli.py`. Documentation: this guide, `AGENTS.md`, `README.md`, `docs/architecture.md`, `docs/decisions.md`, plus links from the three refresh runbooks. No original importer/scheduler implementation or Compose configuration changed.

Next proposed task **for owner approval**: normal-WSL runtime acceptance, starting with isolated tests and an exit-without-import session; any real import remains explicitly pipeline-approved with y/yes after review. Recovery tooling for an indeterminate interactive session is separately scoped after concrete outcome evidence.


## Task 021 validation and changed files

Task 021 changes `backend/ingestion/update_cli.py`, `backend/tests/test_update_cli.py`, this guide, `AGENTS.md`, `README.md`, `docs/architecture.md` and `docs/decisions.md`. The Bash launcher, guarded importer contracts/adapters, Compose, schema/roles, scheduler and React frontend are unchanged. The existing `--status` JSON-lines interface is the machine-readable mode; an additional `--json` flag is unnecessary.

Synthetic coverage includes no-change/no-approval, scores only, statistics only, both pipelines, historical/source-only/EPA corrections, separate approvals and skips, failed sources, blockers/stale candidates, verification mismatch/errors, Ctrl+C/terminal failures, default-no, private tokens, terminal-control escaping and JSON status compatibility. Run the WSL commands above with the rebuilt scheduler image. Stop a recurring scheduler as documented before interactive validation. First validate by declining both imports, then separately approve only the reviewed desired pipeline(s). Live-source and database/API/browser checks remain host-side runtime acceptance work; no real import is implied by unit tests.

Actual Task 021 validation: **54 CLI tests passed**. The five-file regression command completed with **167 passed, 13 skipped**; those skips require the existing isolated PostgreSQL environment. Python compilation, Bash syntax and `git diff --check` passed. No Docker/live-source/development-database/API/browser run or real import was executed in this task. No commit, merge, push or deployment occurred.


Task 021 confirmation wording follow-up: both independent reviews now use the exact
`Approve import? [y/N]` prompt. Added 21 synthetic cases covering both pipelines,
Enter/default-No, rejected legacy phrases, y/yes variants, and schedule approval
followed by declining statistics. The targeted five-file regression suite ran with
**188 passed, 13 skipped** (the existing isolated PostgreSQL cases). Bash syntax,
Python compilation and `git diff --check` passed. This follow-up changed only
`backend/ingestion/update_cli.py`, `backend/tests/test_update_cli.py`, this guide
and `docs/decisions.md`; it preserved the pre-existing guided presentation work.
No Docker/live-source/database/API/browser check or real import was performed.
