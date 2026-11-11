# Task 015 — scheduled NFL refresh, prepare-only

Approved implementation on `feature/scheduled-nfl-refresh`. Owner reports both existing guarded refresh pipelines working against real data, including the Bills–Vikings statistics and reported score. Task 015 adds an **opt-in scheduler**, not automatic publication. No real scheduler, refresh, import, migration, grant or deployment was executed by the agent during this task.

## What runs

A dedicated `scheduler` Compose service reuses the existing backend image, non-root app user, restricted `nfl_ingest` credentials, private database/outbound networks, raw/docs read-only mounts and existing `schedule_snapshots` / `schedule_refresh` volumes. No ports, Docker socket, host cron, Redis, Celery, new package, external service or notification integration is added.

The only commands the scheduler constructs are:

```text
python -m ingestion.refresh --source nflverse-release --dry-run
python -m ingestion.team_stats.refresh --source nflverse-weekly --schedule=... --identity-map=... --references=... --dry-run
```

The module names, sources and explicit dry-run mode are fixed. Environment variables cannot supply commands, approval tokens, apply/recovery/import/migration flags or an administrator override. Input paths are individual absolute-path arguments, not shell strings. There is no shell evaluation. Team-specific configuration/input failures affect only that pipeline; invalid shared clock/timeout or database configuration stops scheduler startup visibly.

Both commands retain their original source, immutable archive, candidate validation, canonical/accepted-revision, approval and checkpoint guards. Scheduled preparation updates private source/check reports but never accepted schedule/statistics data. `nfl_ingest` still has its existing publication capabilities for separately approved manual operations: **prepare-only is enforced by the scheduler's fixed invocation**, not by a newly restricted role or changed permissions. Trusted Docker administrators remain able to run separately authorized commands; this service is not a new security sandbox.

## Timing and startup policy

Default local run times: **06:00 and 18:00, America/Phoenix** (13:00 UTC and 01:00 UTC the next day). Schedule parsing and time-zone conversion use Python's standard library; there is no scheduling dependency. The [official Python slim-bookworm base Dockerfile](https://raw.githubusercontent.com/docker-library/python/master/3.12/slim-bookworm/Dockerfile) includes `tzdata`. This was documentation-verified; the actual cached Docker image must still pass the owner-run zone check below. Missing/invalid time-zone data fails startup rather than silently using UTC.

Configure these non-secret variables in the existing local `.env` when needed:

| Variable | Default / meaning |
|---|---|
| `SCHEDULER_TIMES` | `06:00,18:00`: comma-separated daily local `HH:MM` times; duplicates/malformed values rejected, no cron syntax |
| `SCHEDULER_TIMEZONE` | `America/Phoenix`: valid installed IANA zone |
| `SCHEDULER_JOB_TIMEOUT_SECONDS` | `1200`: each child job, allowed range 60–7200 seconds |
| `SCHEDULER_STATS_SCHEDULE` | `/data/raw/games.csv`: separately approved full schedule snapshot |
| `SCHEDULER_STATS_IDENTITIES` | `/data/raw/team-stats-identities.json`: approved canonical UUID/alias export |
| `SCHEDULER_STATS_REFERENCES` | `/review/docs/team-stats-gamebook-references.json`: independently reviewed reference manifest |

Use the exact input paths that already pass the manual team-statistics dry-run. Paths can refer to read-only raw/docs mounts or an approved immutable snapshot in `/app/snapshots`; do not overwrite originals or hand-edit input evidence. Missing/unreadable/stale inputs remain failures under the existing admission rules; they do not suppress schedule preparation or cause guessed mappings.

The daemon checks the clock every 15 seconds. It starts no immediate startup check outside a configured minute and performs **no missed-run catch-up or retry queue**. If started inside a due minute, it may claim that minute once. A persistent claim is written before launching each pipeline. Restarting in the same minute cannot launch that pipeline again, including after an interrupted attempt. This favors at-most-once preparation over replay: a crash between claim and launch may leave a missed, explicitly unconfirmed attempt. The next normal slot or a deliberate manual trigger is required; no claim is deleted automatically.

Time-zone DST behavior is explicit: nonexistent local times are skipped, repeated local times share one claim and execute at most once (the first observed occurrence). Phoenix itself has no seasonal offset change. Claim identity includes configured zone/local date/time; changing the zone is an intentional new schedule identity and can permit a new claim in that new zone. Blank `.env` values can use Compose defaults; **stop the service to disable scheduling**, not an empty time list.

## Independence and concurrency

Each due slot launches the two preparations independently through a two-worker executor. A slow, failed, malformed-data or unavailable-source job does not prevent the other from executing. No more than one active scheduler worker exists per pipeline. If still busy at a later slot, that later occurrence is recorded `skipped_busy`, not queued or repeatedly retried. The latest-attempt view cannot be overwritten by an older slow worker finishing late; private publication is serialized between threads.

Locks and remaining gaps:

1. `/app/refresh-state/scheduler/runner.lock` elects one scheduler/one-shot instance across processes/containers sharing the existing local volume. A second instance fails rather than becoming another leader or queue.
2. The original schedule CLI still locks `/app/refresh-state/runner.lock`; team-statistics refresh still locks `/app/snapshots/team-stats-refresh/runner.lock`. Scheduled and manual **refresh** commands using these default paths cannot overlap within the same pipeline. A manual lock collision is recorded as a failed/stopped attempt; no automatic retry is queued. These locks cover acquisition/validation as well as database comparison.
3. Schedule and statistics pipelines intentionally have distinct process locks and can overlap source work. Their existing shared PostgreSQL advisory transaction lock serializes canonical comparison with cooperating manual imports/applies. The existing five-second DB lock timeout can cause a preparation to fail under contention; it is not bypassed.
4. Original standalone ingestion commands do not take refresh filesystem locks. Their source staging can overlap refresh staging; database guards still serialize the comparison/publication phase. A later manual write can invalidate a prepared report/token, which must be re-previewed/reviewed. This task does not change those manual workflows.
5. Custom manual `--state-dir` paths or other machines/volumes bypass shared filesystem coordination. Keep documented common paths and local Compose volumes; no distributed/multi-host leader guarantee is claimed. Privileged arbitrary SQL and administrator source-file tampering remain outside cooperating-runner guarantees.

Timeout or SIGTERM/SIGINT terminates the child process group, escalates to kill after five seconds if needed and records an interrupted/timed-out attempt. `init: true` and a 30-second stop grace assist container cleanup. On restart, claims lacking confirmed completion are marked `interrupted_unconfirmed`, never successful and never automatically replayed. A killed parent can leave a child temporarily alive outside normal container cleanup; the original per-pipeline locks still prevent a replacement refresh from overlapping it. No accepted-data COMMIT exists in scheduled commands.

The service has `restart: unless-stopped` **only after explicitly created/enabled**. Pipeline errors do not crash the daemon. Invalid shared configuration/state or scheduler persistence failures stop it; Docker may restart it, but claims prevent duplicated slot jobs. Stop the container and diagnose persistent startup errors rather than deleting state or weakening guards.

## Reports, private logs and status

Existing refresh reports/checkpoints and source archives remain in their original namespaces. Scheduler operational records are separate within the existing state volume:

```text
/app/refresh-state/scheduler/daemon.json          heartbeat / daemon configuration
/app/refresh-state/scheduler/claims/<slot>.json   immutable claim before dispatch
/app/refresh-state/scheduler/jobs/<UUID>.json     private running/final attempt record
/app/refresh-state/scheduler/latest/<pipeline>.json
/app/refresh-state/scheduler/runner.lock
```

Atomic/fsynced private JSON writes reuse existing helpers; files are 0600. No pruning is activated. Preserve state/snapshot volumes with the database. Never remove claims/checkpoints to force a repeated run. A malformed scheduler ledger stops visibly rather than silently losing deduplication history.

Raw child stdout is captured privately in an unlinked temporary file, bounded to 2 MiB when read and never emitted or retained in scheduler logs. This matters because the schedule CLI's stdout includes its review token. Raw stderr is discarded to avoid accidental exception/credential leakage. Only explicit validated report projections enter scheduler records and Docker stdout. Import/module failures, unexpected output or missing/mismatched reports are **failures**, not successful checks. Original pipeline reports retain the detailed diagnostics privately; when no report was produced, the job outcome remains `runner_or_report_failed` for investigation.

Docker logs contain one sanitized completion event per executed job: pipeline, outcome, finish time, review-required boolean. No messaging/notification integration exists. Private job records link to the original private pipeline report, but do not copy tokens, batch evidence, raw source records, SQL exceptions, environment or redirect URLs. An interrupted job has no proof of completion; a healthy container is not evidence of a successful data check.

The read-only `--status` command shows:

- Latest scheduler attempt, phase, outcome, start/finish time and original report path for each pipeline.
- Whether that check succeeded and whether its valid candidate needs review; blocker count when available.
- Actual acquisition and publisher-asset update observations from the run, when available; null means unavailable, never a fabricated date.
- Sanitized existing native checkpoint timestamps, including last successful schedule check/manual ingestion and last successful statistics validation/visible import observation.
- Age/staleness of the last successful native schedule check or statistics validation (36-hour operational warning threshold). Native timestamps can include manual runs, not only scheduled attempts. No timestamp proves original source publication or game completion.
- Daemon heartbeat health, distinct from pipeline/source success. A failed pipeline never becomes success merely because the clock loop remains alive.

`review_required: true` means a validated candidate has differences, **not permission to apply**. Full diffs and approvals remain in the existing private reports/runbooks. A later apply must bind the exact reviewed archived candidate to the current live baseline through its original importer. Neither scheduler restart nor a fresh report auto-acknowledges a token. All scores/statuses, including UNKNOWN, remain unchanged by scheduled runs.

## Owner-run validation before enabling

The agent has **not enabled the scheduler**. From repository root with the existing private `.env`, review the diff and run:

```bash
# Does not start containers or print resolved credentials.
docker compose --profile scheduler config --quiet
docker compose config --services
# Without profiles, expected application services remain db, api, frontend (no scheduler).

.venv/bin/python -m pytest backend/tests/test_scheduler.py -q

# Full existing isolated test profile. Never point tests at development.
docker compose --profile test run --build --rm tests
docker compose --profile test stop db_test

# Build only; do not enable the daemon yet.
docker compose --profile scheduler build scheduler

# Verify installed time-zone support without network or database operations.
docker compose --profile scheduler run --rm --no-deps scheduler \
  python -c 'from zoneinfo import ZoneInfo; print(ZoneInfo("America/Phoenix"))'
```

Review/approve runtime validation before the next command. With the existing development DB running and the daemon stopped, a **single manual prepare-only cycle** tests both actual workflows without enabling recurrence:

```bash
docker compose --profile scheduler run --rm --no-deps scheduler \
  python -m ingestion.scheduler --once

docker compose --profile scheduler run --rm --no-deps scheduler \
  python -m ingestion.scheduler --status
```

Exit 0 means both preparations produced confirmed valid checks; exit 2 means at least one failed/unconfirmed check; exit 3 means scheduler configuration/lock/persistence failure. Container imports/build/network errors can also prevent the command from starting. Confirm both per-pipeline outcomes and original reports, native freshness, no blockers and unchanged accepted records. Do not infer newly available scores/stats are final. A pre-existing manual lock, pending commit-recovery requirement, malformed inputs, source outage or stale canonical export remains a visible stop, not an override opportunity.

## Enable, disable and manual operations — after owner approval

Only after the above passes and you approve enabling recurrence:

```bash
# Explicit opt-in. First startup waits until a configured minute; no immediate backfill.
docker compose --profile scheduler up -d --build scheduler

docker compose --profile scheduler ps scheduler
docker compose --profile scheduler logs --tail=30 scheduler
docker compose --profile scheduler exec -T scheduler python -m ingestion.scheduler --status
```

The healthcheck is **daemon heartbeat only**; inspect individual pipeline status and reports even when Docker says healthy. Native schedule freshness displayed by the existing frontend can now reflect scheduled checks, but no frontend/statistics status endpoint was changed.

To disable:

```bash
docker compose --profile scheduler stop scheduler
```

Removing the profile from later commands does not stop a previously enabled container. Explicitly stop it. `unless-stopped` respects that stop; an enabled running container can otherwise restart with Docker. Do not remove volumes or source evidence.

To trigger both pipelines manually without a queue/overlap:

```bash
# Stop an enabled daemon first; do not launch a competing --once leader.
docker compose --profile scheduler stop scheduler
docker compose --profile scheduler run --rm --no-deps scheduler \
  python -m ingestion.scheduler --once

docker compose --profile scheduler run --rm --no-deps scheduler \
  python -m ingestion.scheduler --status
# Restart recurrence only if you still intend it enabled:
# docker compose --profile scheduler up -d scheduler
```

Alternatively, the original [manual schedule refresh](schedule-refresh.md) and [manual statistics refresh](team-stats-refresh.md) commands remain unchanged. They use their original locks; running them while a scheduled counterpart is busy will stop rather than overlap. Do not supply apply/approval flags to scheduled jobs, change shared state paths to bypass locks or automatically extract tokens.

After editing times/zone/input-path variables, recreate the explicitly enabled service with `docker compose --profile scheduler up -d --force-recreate scheduler` only when recurrence is approved. Do not print full `docker compose config` or `.env` values.

## Troubleshooting and remaining risks

- **No job yet:** check Phoenix local time, configured daily times and daemon heartbeat. There is no startup catch-up; a job may wait until the next due minute. Explicit `--once` is the manual alternative while stopped.
- **One pipeline fails:** inspect its latest outcome and linked original private report. The other pipeline still runs. Do not cat token-bearing reports into shared logs; use existing sanitized review procedures.
- **Both fail / module output invalid:** rebuild the current backend image, verify private input mounts and restricted credentials through the approved configuration. Use original manual diagnostics with protected output; no administrator credentials for runtime jobs.
- **Busy/lock stop:** let the original refresh finish or stop the competing scheduler. A skipped occurrence is not queued. Standalone imports can serialize only at the database lock and invalidate previews.
- **Network or invalid/partial source:** keep accepted data and all original validation guards. No repeated in-slot retry, mirror substitution, deletion or partial acceptance occurs. The next configured slot is a new check, not an apply.
- **Child timed out / container restart:** an attempt remains failed/unconfirmed; check original runner journals. Do not automatically recover/apply/delete receipts. Default timeouts may need owner configuration for slower machines, within documented bounds.
- **Clock/TZ:** ZoneInfo must load the configured zone. Missing cached-image time-zone data is a build/runtime blocker; never fall back silently to another zone. System clock changes cannot replay the same claimed local slot, but forward jumps/downtime may miss slots.
- **Storage/persistence corruption:** stop and review. Operational state is essential for deduplication; do not reset volumes to make jobs run. Disk exhaustion and configuration crash loops require owner diagnosis. There is no retention policy/pruning in this task.
- **Freshness:** acquisition, successful checking, recorded imports and source publication are different observations. Coverage may remain partial and stats may be published before independently supported finality. Scheduled success is never automatic publication or pregame eligibility.

## Complete changed-file inventory

- New `backend/ingestion/scheduler.py`: strict daily/TZ configuration, fixed commands, bounded isolated child lifecycle, durable at-most-once slots, worker isolation, private structured records and read-only status/health.
- New `backend/tests/test_scheduler.py`: time zones/DST, startup/restart claims, safe commands, failure isolation, private output/status, subprocess termination, manual/global locking and concurrent publication tests.
- `compose.yaml`: disabled-by-default `scheduler` profile/service using existing image/networks/volumes and restricted role, init/shutdown/heartbeat healthcheck.
- `.env.example`: non-secret scheduler timing/TZ/input/timeout defaults; actual `.env` untouched.
- New `docs/scheduled-nfl-refresh.md`: scope, policy, source freshness, concurrency gaps, commands, risks and validation evidence.
- `AGENTS.md`, `README.md`, `docs/architecture.md`, `docs/decisions.md`, `docs/implementation-plan.md`, `docs/development.md`, `docs/schedule-refresh.md`, `docs/team-stats-refresh.md`: approved scope and opt-in prepare-only wrapper integration.

No original runner commands/validators/acceptance contracts, database models/migrations/roles, source files, schedule/statistics/rank calculations, APIs/frontend, dependencies or paid infrastructure changed. No actual scheduler or data refresh was enabled/executed by the agent; no import/apply/grant/migration, commit/merge/push or deployment occurred.

## Actual results and review gate

Final executed checks are recorded below. Owner-reported earlier real-source success does not certify scheduler/container integration. Full isolated WSL checks and the approved one-shot runtime preparation must pass before enabling recurrence. Stop here for review; no enablement is implied by implementation.

| Check executed in Codex | Result |
| --- | --- |
| Scheduler unit/adversarial tests (`pytest backend/tests/test_scheduler.py -q`) | 32 passed, including final metadata-only change |
| Broad backend regression (`pytest backend/tests -m 'not api' --ignore=backend/tests/test_health.py -q`) | 343 passed, 80 skipped, 35 deselected; one existing TestClient deprecation warning |
| Selected existing schedule API validation/read-only/async-error tests | 23 passed, 10 deselected; existing warning |
| Existing additive team-statistics readiness test | 1 passed, 3 deselected; existing warning |
| Python compile check and `git diff --check` | Passed |
| Compose profile configuration validation (synthetic passwords only) | Passed; default service list excludes scheduler |
| Docker runtime, image build, full PostgreSQL suite and real-source scheduler run | Not executed: Docker socket permission denied; no permissions workaround attempted |

The suites overlap; these counts are not additive. PostgreSQL-dependent skipped tests and deselected API tests are not claimed as passed. The broad run preceded the final metadata-only exit-code projection change; the scheduler suite and compile/diff checks were rerun afterward.

Recommendation: **GO for owner review and isolated WSL validation; NO-GO for recurring enablement until the documented full suite and explicitly approved one-shot runtime check pass.** No new source snapshots or database import results were generated by this task. Validated statistics input paths and canonical identity coverage must be checked on the owner host; stale or missing inputs should produce a failed preparation rather than weakened admission.
