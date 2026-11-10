# Schedule data freshness — Task 009

## Scope and sources

Implemented on `feature/schedule-freshness` for owner review. This is operational refresh history, not a live feed, source publication history or verification of game finality. No runner behavior, schema, migration, ingestion or existing schedule response changes.

Sources inspected: [runner checkpoint writer](../backend/ingestion/refresh_state.py), [refresh contract](schedule-refresh.md), [schedule contract](schedule-data-contract.md), [API conventions](schedule-api.md), [architecture](architecture.md), existing Compose volume and dashboard. No external source claims or new downloads are needed for this change. The owner reports a previous refresh changed 29 records including 14 new scores and a previous backend suite passed 181 tests; these remain user-reported historical evidence.

## Public contract

GET `/api/data-status/schedule`, no query parameters. Response is `{data, meta}`. HTTP 200 includes explicit availability when metadata cannot be read; request/network errors remain distinct. Unknown query parameters return 422, mutation methods 405. Responses use `Cache-Control: no-store`. OpenAPI documents the typed schema.

| `data` field | Meaning / existing source |
|---|---|
| `metadata_state` | `available`, `missing`, `incomplete`, `invalid`, `unreadable` |
| `last_attempt_at` | Existing `last_attempt_at`; start of latest checkpointed attempt |
| `last_successful_check_at` | Existing successful dry-run, applied or unchanged check |
| `last_successful_apply_at` | Existing `last_successful_ingestion_at`; includes successful unchanged reconciliation |
| `last_data_change_observed_at` | Existing `last_data_change_observed_at`; recorded applied changes |
| `latest_outcome` | Existing recognized `last_outcome` |
| `check_age_seconds` | Age of successful check at response observation, or null |
| `is_stale` | Check age exceeds configured threshold, or null when unknown |

Recognized outcomes: `dry_run`, `applied`, `unchanged`, `rejected`, `review_required`, `download_failed`, `validation_failed`, `failed`, `not_applied`. All observation fields can be null. `meta` includes UTC `as_of`, `manual: true`, scope `guarded_manual_refresh_runner`, `stale_after_seconds`, and textual apply/timestamp semantics.

The existing writer already distinguishes successful apply from changed data. A no-change apply advances successful check/apply while retaining the previous change observation. A failed attempt retains previous successful times. Neither a recent check nor an apply promises games are current or final. Reported scores and UNKNOWN remain unchanged.

## Validation and safe access

The API reads only the existing version-1 `status.json`, with a 1 MiB limit, regular-file check and symlink refusal. It neither creates directories nor imports the writer, acquires locks, inspects candidates or scans run journals. Public fields are allowlisted; paths, hashes, receipts, IDs, lock state, review tokens and raw exceptions are omitted.

Malformed JSON/UTF-8, unsupported versions/outcomes, naive or invalid dates, future timestamps and contradictory check/apply/change chronology produce invalid/unavailable observations. Missing required checkpoint fields produce incomplete metadata. Usable partial fields can remain visible, but incomplete metadata never receives a recent-check assessment. File permission/I/O errors produce unreadable metadata without leaking details. Clock skew can therefore conservatively make valid-looking metadata unavailable.

API mounts the **existing** `schedule_refresh` volume at `/app/refresh-state:ro`. Runner retains its writable mount. No independent timestamp source is created. Settings use `APP_REFRESH_STATE_DIR` (default `/app/refresh-state`) and `APP_REFRESH_STALE_AFTER_HOURS` (default 36, allowed 1–8760). Compose uses these defaults; no environment-file edit is needed. If changing them deliberately, pass settings to the API process and keep the path aligned with the shared mount. The threshold is an operational warning policy, not an unattended update cadence or data-quality guarantee.

## Dashboard behavior and limitations

The independent panel loads once, has explicit **Reload refresh history**, and does not poll or refetch on focus/reconnect/mount. Reload reads metadata only; it cannot run a refresh. Browser-local date/time and timezone labels are used, while schedule kickoffs retain Eastern display. Loading, absent/incomplete/invalid/unreadable metadata, old checks, failed attempts and HTTP errors are distinct. Cached metadata remains visible with an explicit warning after reload failure. Schedule records remain usable when this request fails.

Age is computed at API `as_of`, not continually updated in a long-open browser; reload to reassess. This avoids timers and misleading continuously fresh indicators. The UI shows when metadata was read.

**Checkpoint limitation:** only persisted `status.json` observations are exposed. A currently running or interrupted attempt that has not checkpointed is not represented; the API does not claim real-time run visibility. Recovery observations may be recorded later than the original transaction. Existing initial CSV imports outside the runner do not establish refresh history. Missing metadata therefore means no available recorded history, not proof no data was ever imported.

## Verification evidence

Executed in the agent environment:

- New backend freshness suite: **37 passed** (repository, actual checkpoint writer integration, projection, async ASGI contract/security/OpenAPI; no PostgreSQL required).
- Combined freshness/settings/schedule-service/refresh/ingestion/database suites: **127 passed, 55 skipped**. Skips require isolated PostgreSQL.
- Existing API async validation/read-only/error transport subset: **23 passed**, 10 deselected, one existing TestClient deprecation warning.
- Frontend: **66 passed** across three files, including 18 new freshness cases; all 66 also passed with `TZ=Asia/Tokyo`.
- TypeScript check and Vite production build passed.
- Compose resolved configuration confirms API mount is read-only; `git diff --check` passed.

Docker daemon access is denied in this execution environment. PostgreSQL-backed tests, live volume permissions/readability, actual owner refresh history, running API/frontend proxy and browser acceptance are **not verified here**. Existing synchronous TestClient transport also stalls in this environment: `timeout 15 .venv/bin/python -m pytest backend/tests/test_schedule_api.py::test_seasons_json -q -o faulthandler_timeout=8` exited 124, with the stack waiting in the AnyIO portal during fixture setup, before application assertions. This test did not pass; other synchronous TestClient cases were not retried. Async HTTPX ASGI tests do run. No real import, migration, refresh or production access was performed.

## Normal-WSL verification

From the repository root, run existing isolated test services (never point tests at the development database):

```bash
docker compose config --quiet
docker compose --profile test run --build --rm tests
docker compose --profile test stop db_test
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
docker compose up -d --build --wait db api frontend
curl --fail-with-body -sS http://127.0.0.1:8000/api/data-status/schedule
curl --fail-with-body -sS http://127.0.0.1:5173/api/data-status/schedule
```

Both GETs should return the same public shape; `as_of`/age may differ between calls. Existing checkpoint fields should match the runner observations. Missing history safely returns `metadata_state: missing`. Check `/docs` for the new endpoint. Open the dashboard at `http://127.0.0.1:5173`, verify local-time formatting, manual label and reload, and confirm historical navigation still works. A failed command is not a pass: retain its output, inspect service health/logs locally with credentials redacted, and resolve the specific failure before claiming acceptance. No reimport is needed to test this display.

Verify the mount without attempting any writes:

```bash
docker inspect "$(docker compose ps -q api)" --format '{{range .Mounts}}{{if eq .Destination "/app/refresh-state"}}read_write={{.RW}}{{end}}{{end}}'
docker compose exec -T api python - <<'PY'
import os
assert os.statvfs('/app/refresh-state').f_flag & os.ST_RDONLY
print('refresh-state mount is read-only')
PY
```

Expected `read_write=false` and the confirmation line. If missing/unreadable metadata is unexpected, verify the existing runner and API use the same named volume and inspect permissions locally; do not make the API mount writable or dump private journal contents into reports.

## Complete changed-file inventory

- `backend/app/api/freshness.py`, `schemas/freshness.py`, `repositories/refresh_status.py`, `services/freshness.py`: new read-only endpoint, typed projection and bounded reader (all under `backend/app/`).
- `backend/app/main.py`, `backend/app/core/config.py`: service/router wiring and settings.
- `backend/tests/test_freshness.py`: 37 new tests.
- `compose.yaml`: read-only API mount of existing volume.
- `frontend/src/api/freshness.ts`, `api/types.ts`, `api/client.ts`: guarded typed client and local timestamp formatter (all under `frontend/src/`).
- `frontend/src/components/FreshnessIndicator.tsx`, `pages/Schedule.tsx`, `styles.css`: independent responsive panel and placement (all under `frontend/src/`).
- `frontend/src/test/freshness.test.tsx`, `test/fixtures.ts`, `test/dashboard.test.tsx`: new coverage and existing test fixture routing (all under `frontend/src/`).
- `AGENTS.md`, `README.md`: approved scope and guide link.
- `docs/agent-task-009.md`, `docs/schedule-freshness.md`: scope, contract, inventory and verification.
- `docs/decisions.md`, `docs/architecture.md`, `docs/implementation-plan.md`, `docs/development.md`, `docs/schedule-api.md`, `docs/schedule-refresh.md`, `docs/schedule-dashboard.md`: synchronized decision, integration and usage references.

## Review gate

Implementation is ready for owner review, subject to normal-WSL full-suite and runtime acceptance above. Proposed next task: complete the focused runtime/browser acceptance against the real refresh volume and review any remaining UI issues. Unattended postgame updating remains separately gated by finality/review policy and is not enabled here. No commit, merge, push or deployment performed.
