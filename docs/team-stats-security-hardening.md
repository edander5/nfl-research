# Team-statistics security hardening and development transition

**Task 011 update:** owner reports migration/role transition and the 705-pair import completed. The [read-only statistics API](team-stats-api.md) adds explicitly approved column-level API reads; earlier statements denying all API statistics access describe the Task 010 policy. Batch evidence/raw records/history and all API writes remain denied. No migration or import is repeated.

Owner-approved scope on `feature/team-stats-ingestion`, following the independent NO-GO review of Task 010. This document supersedes the original ingestion guide's privilege, approval-output and migration instructions. No development migration, role transition, statistics import, correction, rollback or deployment was executed by the agent. No credentials were changed in the owner's `.env`.

## Changes and trust boundaries

**Acceptance history:** `team_stats_selection_events` is now trigger-generated, with a unique contiguous generation per canonical game. The runtime role can SELECT events but cannot INSERT, UPDATE, DELETE or TRUNCATE them. An AFTER selection trigger records the actual OLD/NEW transition in the same transaction; a failed selection/transaction cannot leave an acceptance event. The BEFORE guard requires the old pointer to match the proven chain tip. A rollback target must have appeared as an earlier accepted target for that same game. Python independently checks the whole generation/before/after chain and current tip before planning rollback, then validates the target's original pair, statistics and archived provenance. Prior revisions are retained unchanged.

Every selection statement obtains the existing schedule advisory transaction lock **before row locks**, including independent SQL updates. The Python service obtains that same lock before loading its baseline, refreshes ORM state from PostgreSQL, and holds game/selection locks through publication. This serializes cooperating schedule/statistics writers and prevents token reuse after a generation-changing rollback cycle. Lock timeouts fail the operation; there is no automatic retry. The migration adds no trigger to schedule tables. Arbitrary privileged schedule writers are outside the cooperating-writer guarantee.

**Candidate evidence:** fingerprint version 2 includes the complete evidence JSON, canonical paired payloads and hashes of every original byte blob (audit, source CSVs, schedule, identities and gamebook references). Apply re-reads archives, reconstructs and revalidates the candidate, compares the complete fingerprint and payloads, then uses that private reconstructed copy. Mutating a shallow-frozen candidate's nested receipts, definitions, metrics or blobs fails before database access. Pending ORM writes are rejected before autoflush. The review token is recalculated under database locks against the full current baseline, including events and generation, before changing DML. A token from another candidate, stale baseline or earlier selection cycle cannot authorize a changing import. An unchanged repeat is a read-only no-op and needs no new approval.

Archive revalidation proves the bytes observed at apply, not indefinite filesystem immutability against a privileged administrator. The application does not rewrite captures; filesystem administrators and bootstrap database superusers remain trusted. Retain protected backups of both database and archives. Approval is an explicit review acknowledgement, not a cryptographic signature or a substitute for DB credentials. Do not grant untrusted users the ingestion password or access to approval reports. Reports are created mode 0600; stdout excludes the token. `--approval-stdin` avoids putting it in process arguments. Previously generated tokens/fingerprints must be discarded and a new dry-run reviewed.

**Native role separation, same infrastructure:**

| Identity | Purpose and grants |
|---|---|
| Existing bootstrap `POSTGRES_USER` | Retained administrator for explicit role provisioning; never routine API/ingestion. Changing Compose variables does not recreate roles in an existing volume |
| `nfl_owner` | NOLOGIN schema/table/function owner; explicit privileged Alembic connections SET ROLE to this identity |
| `nfl_api` | Restricted LOGIN; SELECT existing schedule tables and Alembic revision; no stats/history access or mutations |
| `nfl_ingest` | Restricted LOGIN; schedule SELECT/INSERT and games UPDATE needed by existing importer/refresh; stats SELECT/INSERT on batches/pairs/revisions/pointers, column-limited pointer UPDATE, SELECT-only events |

Runtime roles have no superuser, role creation, DB creation, replication, RLS bypass, owner membership or schema creation. They cannot disable triggers, alter tables/functions or truncate history. Trigger functions have fixed search paths; privileged functions use fully qualified table names and revoke direct execution. The administrator tool refuses unexpected role memberships, runtime-owned objects, unknown public tables/functions, unrelated database names or an already-applied older 0002 without the generation column. It does not repair unknown cluster configurations automatically. Passwords are distinct ASCII secrets of at least 24 characters; salted SCRAM verifiers are built without placing plaintext passwords in SQL. Errors and engine URLs are not printed. SQL statement logging must still be treated as privileged because verifiers are sensitive.

The normal engine rejects excessive runtime credentials. `compose.admin.yaml` is an explicit owner-only override for the existing ingestion service, not a new service or infrastructure. The test profile retains bootstrap credentials only for provisioning **isolated** `nfl_research_test`; adversarial tests then make real connections as `nfl_ingest` and `nfl_api`, rather than disguising a superuser with SET ROLE.

Readiness now recognizes both known additive revisions, and the API can read `alembic_version`. This prevents migration 0002 from breaking existing readiness; JSON responses and schedule APIs are unchanged. No statistics finality, ranking eligibility, schedule score/status or statistical-definition changes are introduced.

## Exact normal-WSL validation commands

From repository root, with the existing trusted `.env`. Add distinct random `API_DB_PASSWORD` and `INGEST_DB_PASSWORD` values locally using an editor/password manager; never paste credentials into reports or commands. Do not replace `POSTGRES_USER`, `POSTGRES_PASSWORD` or `POSTGRES_DB`. Do not overwrite `.env` with `.env.example`.

```bash
docker compose config --quiet
docker compose -f compose.yaml -f compose.admin.yaml config --quiet
.venv/bin/python -m pytest backend/tests/test_team_stats_security.py backend/tests/test_team_stats_ingestion.py -q -ra
```

Reset **only the ephemeral test container**, since a previous test run may contain the earlier 0002 definition. These commands do not remove the development database or named volumes:

```bash
docker compose --profile test stop db_test
docker compose --profile test rm -f db_test
docker compose --profile test run --build --rm tests
docker compose --profile test stop db_test
```

Expected: no failed tests, no database tests skipped, migrations succeed only in `nfl_research_test`. Keep the actual pytest summary; do not expect the old count of 317 because security tests have been added. Restricted-login tests must demonstrate SQLSTATE 42501 for prohibited writes/history fabrication/TRUNCATE/trigger manipulation, 23514 for an unaccepted rollback target and 55P03 for the competing selection statement. Genuine import, correction, reviewed rollback, idempotence, rollback-on-failure and existing schedule suites must all pass. A failure means stop; do not weaken roles or triggers to make tests pass.

Offline SQL inspection is safe and does not execute a migration:

```bash
(cd backend && ../.venv/bin/python -m alembic upgrade 0001_schedule:0002_team_stats --sql) > /tmp/team-stats-hardened-migration.sql
```

## Existing development volume: explicit owner-only transition

These are **future instructions requiring owner approval**, not operations performed during this task. Editing the unapplied migration is appropriate only while development remains at 0001. If inspection shows any 0002 already applied, STOP: changing that file will not upgrade the database. A separately reviewed forward migration is required; never stamp, drop tables or fake the Alembic revision.

1. Review code, offline SQL and the complete isolated WSL test result first. Add local runtime secrets as above. Coordinate so no ingestion/refresh/migration is in flight. Keep the bootstrap secret private and available for administration. Stop routine API/frontend connections before changing ownership:

   ```bash
   docker compose stop frontend api
   docker compose up -d db
   ```

2. Make an owner-managed backup outside the repository, with private permissions. This reads the existing DB and changes no records:

   ```bash
   umask 077
   mkdir -p "$HOME/nfl-research-backups"
   stats_backup="$HOME/nfl-research-backups/pre-team-stats-$(date -u +%Y%m%dT%H%M%SZ).dump"
   docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$stats_backup"
   test -s "$stats_backup"
   docker compose exec -T db pg_restore --list < "$stats_backup" > /dev/null
   ```

   Stop if any command fails. Listing a backup is not a restore test. Also retain existing snapshot/refresh volumes using the approved backup workflow; do not remove or recreate them.

3. Inspect using the explicit admin override (default is read-only):

   ```bash
   docker compose -f compose.yaml -f compose.admin.yaml --profile ingestion run --build --rm ingestion python -m admin.roles
   ```

   Expect `inspection_only`, revision `0001_schedule`, known public table owners and reserved role flags if roles already exist. Investigate unexpected objects or revision before proceeding. Do not print fully resolved Compose configuration or connection URLs.

4. **Only after approval of the role transition**, provision roles, ownership and ACLs transactionally. This does not migrate schema or import data:

   ```bash
   docker compose -f compose.yaml -f compose.admin.yaml --profile ingestion run --rm ingestion python -m admin.roles --apply
   ```

   Expect database `nfl_research_dev`, schema owner `nfl_owner`, runtime names and table count; no passwords/verifiers. Existing schedule rows remain unchanged. An error rolls back provisioning; stop and diagnose reserved roles/memberships/objects privately. Do not fall back to superuser application credentials. This intentionally changes SQL ownership/grants, and the new Compose passwords alone are insufficient without this step.

5. **Only after separate migration approval**, apply the reviewed, hardened additive migration through the owner override:

   ```bash
   docker compose -f compose.yaml -f compose.admin.yaml --profile ingestion run --rm ingestion alembic upgrade 0002_team_stats
   docker compose -f compose.yaml -f compose.admin.yaml --profile ingestion run --rm ingestion python -m admin.roles
   ```

   Expect revision `0002_team_stats`; all project tables owned by `nfl_owner`. This migration seeds no statistics. Downgrade drops all five statistics tables and their history/functions: **destructive, separately gated, never a logical data rollback**. Migration 0001's existing downgrade prohibition is unchanged.

6. Restart ordinary services **without** the admin override and verify existing endpoints:

   ```bash
   docker compose up -d --build --force-recreate api frontend
   curl --fail http://127.0.0.1:8000/api/health
   curl --fail http://127.0.0.1:8000/api/ready
   curl --fail http://127.0.0.1:8000/api/seasons
   ```

   Health/readiness should return HTTP 200 with their existing responses; seasons should retain existing coverage. Failure requires stopping for diagnosis, not weakening permissions. No real statistics import is approved by this sequence.

7. After schema acceptance, use the existing [ingestion guide's exact inputs](team-stats-ingestion.md#3-guarded-dry-run-against-development--after-schema-acceptance) with **base Compose only** for dry-run/review. It writes private file reports/captures but no DB rows. Review the complete report privately. Apply/corrections/rollback still require separate approval. For a reviewed apply, use the guide's `stats_args` array and stdin transport:

   ```bash
   read -rs stats_review_token
   printf '%s\n' "$stats_review_token" | docker compose --profile ingestion run -T --rm \
     -v "$PWD/docs:/review/docs:ro" ingestion \
     python -m ingestion.team_stats.ingest "${stats_args[@]}" --apply --approval-stdin
   unset stats_review_token
   ```

Never pipe automatically extracted tokens into apply. Do not use `compose.admin.yaml` for routine imports. If migration/transition fails, leave services stopped and retain backups; neither downgrade nor restore is an automatic recovery action.

## Validation evidence and original nine findings

Agent checks on 2026-11-09: selected offline/backend suite **231 passed, 74 skipped**; existing async schedule API validation/read-only/error subset **23 passed, 10 deselected, one existing deprecation warning**. Offline SQL rendering and Python compilation succeeded. Docker daemon probe failed with socket permission denied, so no role provisioning, PostgreSQL-backed tests, migrations or real ingestion ran here. The owner's **317 passed, two warnings** predates this hardening and is not proof of the new ACL/trigger behavior. A separate readiness compatibility unit check passed (one passed, three deselected; existing deprecation warning). Compose base/admin configuration validated with `--quiet` and synthetic runtime secrets, without exposing resolved configuration. Real file-only candidate revalidation returned **705 pairs / 1,410 rows**, complete version-2 fingerprint `6ad7496a6336477b1601e9beec6adae5eb05ba51b9324ff29b6b693b519b1445`. Measured original CSV/identity/reference hashes and all three content-addressed season hashes remain unchanged. No archives or real source artifacts were rewritten. Final security/ingestion subset after the CLI admin-purpose guard: **41 passed, 19 skipped** (overlaps the larger suite, do not add counts). The new CLI guard rejects the admin override before opening a DB connection. No PostgreSQL test was claimed as passed.

PASS below means source/unit/static review; it does **not** certify skipped PostgreSQL acceptance. FAIL means the acceptance evidence is still missing, not that the exploit is known to remain functional.

| Original review item | PASS/FAIL and evidence |
|---|---|
| 1. Python independently checks baseline-bound approval before writes | PASS: `storage.apply_import/apply_rollback`, clean session, live locked plan; mutation-before-DB and stale-token tests |
| 2. Substitution/stale baseline/replay | PASS: full candidate fingerprint/reconstruction, event-inclusive baseline; candidate mutation and generation-cycle tests; DB cycle case pending |
| 3. Immutable prior revisions | PASS design/static: no revision updates; append-only triggers and denied runtime UPDATE/DELETE; PostgreSQL denial tests pending |
| 4. Rollback to actually accepted same-game pair | PASS design/unit: contiguous chain validator, generated events, same-game earlier-generation database guard; never-accepted and fabricated-chain tests; DB cases pending |
| 5. Atomic pair/transition transactions | PASS design: caller transaction plus AFTER event; existing and new transaction-interruption tests authored; PostgreSQL execution pending |
| 6. Batch/artifact provenance association | PASS source/unit: pair retains original artifact/import batch on rollback, selection/event retain selecting rollback batch; complete receipt/bytes fingerprint and source tests |
| 7. Intended runtime permissions | FAIL acceptance evidence: role separation implemented and actual-login denial tests authored, but not executed against PostgreSQL here |
| 8. Destructive downgrade documented | PASS: migration downgrade drops five stats tables; warning and separate approval above |
| 9. Safe to apply now | FAIL: isolated PostgreSQL tests and reviewed existing-volume transition still required |

**Recommendation: NO-GO for development migration today.** The three blockers have implementation fixes and regression tests, but the ACL/PLpgSQL behavior must pass the full isolated WSL suite under real restricted credentials. Next narrowly scoped approval: owner-run isolated runtime acceptance and review of the explicit role-transition plan, then separate permission for development role provisioning/migration. No additional general research, real import or ranking work is proposed.

## Changed-file inventory for this hardening

- `backend/ingestion/team_stats/candidate.py`, `storage.py`, `ingest.py`: complete evidence binding, reconstructed apply candidate, current baseline/chain validation, trigger-managed events and private approval/report transport.
- `backend/app/models/team_stats.py`, `backend/alembic/versions/0002_team_stats.py`: event generation/uniqueness, ordered guards, generated history, restricted ACLs and fixed function search paths.
- New `backend/app/db/roles.py`, `backend/admin/__init__.py`, `backend/admin/roles.py`: explicit native role transition/inspection with private credentials.
- `backend/app/db/session.py`, `backend/app/core/config.py`: purpose-separated owner migration versus restricted runtime engine.
- `backend/app/api/health.py`: readiness compatibility with the additive revision, unchanged response contract.
- `compose.yaml`, new `compose.admin.yaml`, `.env.example`: runtime credentials separate from existing bootstrap credentials; explicit administrative override; existing volumes/ports retained.
- `backend/tests/conftest.py`, `test_team_stats_ingestion.py`, new `test_team_stats_security.py`, `test_health.py`: owner migration fixture, real restricted-logins, adversarial evidence/history/permissions/concurrency and readiness tests.
- `AGENTS.md`, `README.md`, `docs/architecture.md`, `data-model.md`, `decisions.md`, `development.md`, `team-stats-ingestion.md`, and this document: synchronized scope, schema, roles, commands and review gates. The earlier Task 010 implementation files were already present in the uncommitted worktree; this list describes hardening changes, not a clean-base inventory of that earlier task.

No source artifact, original schedule file, schedule model/migration, refresh/ingestion logic, frontend or public schedule response contract was changed.

## References

Reviewed official PostgreSQL 17 guidance for [ownership and privileges](https://www.postgresql.org/docs/17/ddl-priv.html), [GRANT and column/parameter permissions](https://www.postgresql.org/docs/17/sql-grant.html), and [SECURITY DEFINER function safety](https://www.postgresql.org/docs/17/sql-createfunction.html). Runtime database administrators remain outside application-role enforcement. Repository contracts remain [schedule](schedule-data-contract.md), [NET/source validation](team-stats-validation.md) and [Task 010](agent-task-010.md).
