# Task 014 — guarded NFL team-statistics refresh preparation

Approved branch: `feature/team-stats-refresh`. This task implements a reusable **prepare-only**, manually invoked workflow. It discovers official source bytes, validates them, reconciles against canonical PostgreSQL identities/accepted history, and creates an immutable private review report. It cannot apply updates, accept corrections, roll back selections, change schedules or activate jobs. The existing guarded importer remains the sole publication path after separate owner approval.

Owner baseline: 705 accepted pairs / 1,410 team records, existing read-only statistics/rankings APIs, rankings frontend, restricted roles and revision 0002. Those are owner-reported context. No development database or source files were modified by the agent.

## Reused components and decisions

- `team_stats.source.acquire`: approved HTTPS endpoints, host restrictions, bounded sizes/timeouts, no automatic retries, before/after publisher metadata checks, measured SHA-256 and declared-origin receipts.
- `team_stats.validation.audit`, `canonical_map`, `reference_list` and schedule `validate_bytes`: existing pairing, aliases, seasons/stages, null/type/score/coverage and independent-reference admission checks.
- `team_stats.candidate.load_candidate` and `archive_candidate`: unchanged version-1 audit admission, complete version-2 candidate fingerprint, original bytes/receipts/references binding and immutable captures. The new adapter constructs the audit envelope from these existing pure validators; it does not alter offline CLI behavior or replace validation rules.
- `team_stats.storage.inspect` and `plan_import`: existing canonical checks, stored pair/archive/receipt verification, full baseline binding, shared advisory and row locks, missing-accepted/scored-game blockers and exact before/after review plan.
- Existing `refresh_state.write_json` and `RefreshState.locked`: private atomic/fsynced files and exclusive nonblocking process locking. Statistics use their own namespace under the **existing snapshots volume**, not the schedule refresh checkpoint or another database table.

No schema, migration, permission, API, frontend, Compose service/volume/network, data definition or dependency change. The existing `refresh` container already has outbound networking, restricted `nfl_ingest` credentials and the snapshots volume. The `ingestion` service lacks outbound networking, so acquisition uses `refresh` with an explicit command override. Neither service runs an administrator role.

The new CLI has no apply/correction/rollback switch. This is intentional for the initial dry-run-first policy: preparation and publication have separate operator actions, and no second apply/recovery implementation bypasses existing service safeguards.

## Source configuration and verification

The only CLI source is `--source nflverse-weekly`. URLs come from existing `source.source_url(year)`:

| Season | Approved CSV |
|---|---|
| 2024 | `https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2024.csv` |
| 2025 | `https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2025.csv` |
| 2026 | `https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2026.csv` |

Publisher metadata: `https://api.github.com/repos/nflverse/nflverse-data/releases/tags/stats_team`. No custom URL, filename-based identity, mirror, credentials or paid source is introduced.

**Official documentation reviewed during Task 014:** the [nflreadr update schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html) describes nightly team-stat processing after game days plus some game-day updates, and recommends Thursday rechecks for upstream corrections. This is documentation, not measured latency or an availability guarantee. The [official stats_team release](https://github.com/nflverse/nflverse-data/releases/tag/stats_team) was accessible as a web page, but its dynamically loaded asset list did not establish complete current file availability. The [repository license](https://raw.githubusercontent.com/nflverse/nflverse-data/main/LICENSE.md) remains CC BY 4.0; retain attribution, license links and transformation notices. This does not extend nflverse licensing to independently reviewed NFL PDFs or authenticate upstream statistics independently.

**Actual acquisition attempt:** one existing `acquire(2024)` probe returned bounded `network_failure` in the agent environment. No download succeeded, no new real CSV hash or report was fabricated, and the failing method was not repeatedly retried. Full 2024–2026 retrieval/current content remains a normal-WSL validation requirement, not an agent-verified source fact.

Every run downloads and hashes all three full snapshots; a prior identical hash never skips validation or canonical comparison. Available publisher digest/size/recheck metadata must agree. Missing metadata stays explicitly unavailable and origin remains DECLARED under the already approved contract. A publisher digest match is integrity evidence, not independent authentication. Receipts distinguish actual acquisition time from provider asset-update metadata; neither proves original publication or game completion. First observation has `changed_since_previous_check: null`, not a fabricated prior change. Subsequent checks compare measured hashes, not times or filenames. Accepted source hash sets are reported separately because legitimate corrections can leave accepted games referencing several immutable artifacts per season.

## Validation, classification and safety

Operator inputs are a separately approved full schedule snapshot, canonical UUID/alias export and the existing independently reviewed gamebook manifest. The runner captures stable copies, then audits original source bytes using the unchanged contracts. NET = gross + original signed nonpositive sack adjustment (`net_pass_negative_sacks_v1`); no absolute-value/sign repair, time-based eligibility or FINAL inference. A correction to an independently calibrated reference game can require a newly reviewed reference manifest; it cannot be waived by this runner.

New source games must already resolve uniquely in the provided schedule/export **and** current database. The runner neither invents identities nor updates schedules. If source IDs, sides, aliases, weeks or stages drift, preparation rejects. A stale file can remain useful where its existing identities still agree; it is not an independently attested current export. Final live comparison checks every incoming pair and preserves reported-score coverage blockers. Coordinate any needed schedule refresh through its separately approved workflow before preparing statistics; do not hand-edit the original CSV or automatically mutate schedule data here.

The report classifies:

- **Newly available pairs**: no prior accepted selection, exact canonical identity and both valid sides. Always operator-reviewed in this implementation.
- **Unchanged accepted pairs**: identical content hash, including raw source records. No publication or new batch is performed.
- **Historical corrections**: any previously accepted pair whose source/metric payload changes, including current-season corrections. The existing underlying plan may label past/current seasons separately; this review policy treats both as corrections requiring review.
- **Missing previously accepted pairs**: hard blockers. Nothing is deleted or unpublished.
- **Invalid/ambiguous records**: validator errors retained by season/line/code. For an invalid audit, missing-pair diagnostics mean **absent or rejected by the validator**, not proof of deliberate upstream withdrawal. Diagnostic locally matched counts are explicitly separate from admitted/ready counts.

A valid local snapshot may still be blocked by live accepted-history coverage or identity state. Only admitted, blocker-free plans receive a `handoff`. Invalid/blocked snapshots retain diagnostic evidence but cannot claim a ready candidate. Unreadable inputs/archive permissions produce a bounded diagnostic and phase/input label, without echoing exception text or filesystem secrets to stdout.

All network/CSV work precedes the short database comparison transaction. The existing schedule advisory lock and game/selection locks protect baseline inspection; the dry-run performs no DML. A later operator apply revalidates archived evidence and the complete live baseline under the original importer locks. Substitution, changed receipts/files, stale generations and replayed approvals retain their existing rejection behavior. Immutable revisions, generated acceptance history and logical rollback controls are unchanged. This task does not perform or add rollback actions.

Repeated identical checks reuse content-addressed source files and produce distinct operational observations/reports, with no accepted-data changes. Receipts/timestamps may make candidate fingerprints differ across real checks even when bytes and accepted statistics are unchanged; fingerprints are full evidence identities, not source-change oracles. Never automate token extraction/application from a fresh preview.

## Persistence and freshness

Default namespace: `/app/snapshots/team-stats-refresh/`, in the existing durable `schedule_snapshots` volume:

- `snapshots/<measured_sha256>.csv`: no-replace captured source and input bytes (the existing generic capture suffix also stores JSON bytes).
- `acquisitions/<run_uuid>-<season>.json`: immutable acquisition observations, saved immediately after capture so a later validation failure/interruption does not erase download evidence.
- `audits/<run_uuid>.json`: unchanged offline admission report schema.
- `runs/<run_uuid>.json`: immutable full private review report, including source receipts, classification, candidate, baseline-bound plan and handoff when permitted.
- `status.json`: atomic operational checkpoint. It contains no review token and does not replace the immutable evidence.
- `runner.lock`: cooperating process lock; contention fails immediately, without overlapping refreshes or retries.

Files use the existing private write/capture primitives (0600). No source/input or prior report is overwritten. The checkpoint alone is intentionally replaced atomically. A malformed checkpoint or a missing checkpoint with retained prior runs stops for review; it is not silently reset. Interrupted prepare-only runs are safe to recheck because there is no database publication phase. A crash before checkpoint completion can leave it conservatively behind the immutable report; preserve evidence and investigate rather than deleting/resetting state or guessing a successful apply.

Freshness records distinguish:

| Field | Meaning |
|---|---|
| `last_attempt_at` | Start of the latest manual preparation attempt |
| `last_refresh_check_at` | Latest completed attempt, including failures; not necessarily a successful validation |
| `last_successful_source_check_at` | All three source receipts/bytes passed acquisition integrity; CSV/database admission can still fail |
| `last_successful_validation_at` | Complete local admission and live comparison with no blockers |
| `last_successfully_applied_import_at` | Existing latest visible immutable IMPORT batch `recorded_at`; queried from PostgreSQL, never advanced by a dry-run |
| `import_timestamp_observed_at`, `last_import_timestamp_rechecked` | Whether/when that existing database import observation was refreshed; null/unrechecked must not be read as proof no imports exist |
| `source_observations` | Measured hash, configured URL, actual retrieval timestamp and optional `publisher_asset_updated_at` per season |
| `latest_counts`, `last_validated_counts` | Latest admitted plan counts (null on failed admission), and separately retained last-good plan counts |
| `validation_age_seconds`, `validation_stale` | Age at this attempt's completion, using a disclosed 36-hour operational warning threshold; null if never validated |
| `latest_warnings`, `latest_error`, `last_outcome` | Missing publisher metadata, partial 2026 coverage, stale/no validation, source/validation/DB failure and uncertainty |

The 36-hour threshold describes time since successful checking, not a source freshness SLA. The stored age is measured when the runner finishes; it does not keep ticking without another invocation. IMPORT batch `recorded_at` is a database observation, not exact commit, game completion or source-publication time. Rollbacks are not relabeled as fresh imports. If database inspection is blocked/unavailable, an earlier import observation is retained and marked unrechecked.

Freshness is **recorded only**; no API endpoint/frontend or independent timestamp store is added. The schedule-only refresh status is untouched. Future public exposure would require a separately approved sanitized read projection.

## Exact normal-WSL tests

From repository root, using the existing private `.env`:

```bash
# Local synthetic acquisition, audit/admission, classification, checkpoint and CLI tests.
.venv/bin/python -m pytest backend/tests/test_team_stats_refresh.py -m 'not database' -q -ra

# Isolated PostgreSQL tests, including real restricted ingest/API credentials and existing guards.
docker compose --profile test run --build --rm tests python -m pytest \
  tests/test_team_stats_refresh.py tests/test_team_stats_ingestion.py \
  tests/test_team_stats_security.py tests/test_team_rankings.py \
  tests/test_team_stats_api.py tests/test_refresh_database.py tests/test_schedule_api.py -q -ra

# Full regression suite, only nfl_research_test.
docker compose --profile test run --build --rm tests
docker compose --profile test stop db_test
```

The new PostgreSQL case seeds only synthetic test fixtures under actual `nfl_ingest` credentials, verifies repeat refreshes and correction preparation leave counts, accepted statistics, rankings and schedule values intact, and checks the existing importer rejects an unapproved handoff. Existing security/ingestion tests cover genuine reviewed publication/rollback atomicity and token/history/permissions safeguards. No test is pointed at development. Database tests must execute rather than skip in normal WSL; failures require diagnosis, not weakened validators or privileges.

## Safe owner-run development preparation

These commands are provided for validation, **not executed by the agent**. Use a matching approved schedule snapshot/export and the reviewed manifest. The baseline paths below exist in the repository; substitute a separately captured approved schedule/export if current identities/known scores have moved. Preserve original `data/raw/games.csv` and old exports/artifacts.

```bash
# Uses existing refresh container, normal runtime credentials and no administrator override.
docker compose --profile refresh run --build --rm \
  -v "$PWD/docs:/review/docs:ro" refresh \
  python -m ingestion.team_stats.refresh \
  --source nflverse-weekly \
  --schedule /data/raw/games.csv \
  --identity-map /data/raw/team-stats-identities.json \
  --references /review/docs/team-stats-gamebook-references.json \
  --dry-run
```

Success stdout contains only outcome, private report path and counts; never tokens or raw/private evidence. Exit 0 means either `unchanged` or a fully checked `review_required` preview; **it does not mean applied**. Exit 2 means source/validation/comparison failure or blockers. Exit 3 means configuration/checkpoint/lock/report-persistence failure. No `--apply` flag is accepted. Stop on failures; do not repeat a failing network route without diagnosing it, change permissions broadly, substitute a mirror or import partial seasons.

Review the entire report privately. To inspect counts/warnings/classification sizes without printing approval secrets, enter the exact printed container report path and run this allowlisted summary:

```bash
read -r stats_refresh_report
docker compose --profile refresh run --no-deps -T --rm refresh \
  python - "$stats_refresh_report" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
print(json.dumps({
    'outcome':r.get('outcome'), 'error':r.get('error'), 'counts':r.get('counts'),
    'diagnostic_counts':r.get('diagnostic_counts'), 'warnings':r.get('warnings'),
    'missing_previously_accepted_count':len(r.get('missing_previously_accepted',[])),
    'admitted_handoff_available':'handoff' in r,
},indent=2))
PY
```

Full source receipts, raw diffs, baseline hashes, tokens and private history references remain in the private report for secure operator review. Do not paste it into shared logs. Status can similarly be inspected through a deliberately sanitized projection; no automatic public export is authorized.

### Later publication — separate approval, original importer only

No actual import is authorized by this task. After a separate review/approval, take the exact `handoff` paths from the private report and use the existing [guarded ingestion procedure](team-stats-ingestion.md). Always perform another dry-run against the live baseline first:

```bash
# Enter the five exact handoff paths privately; no glob/"latest report" selection.
read -r stats_audit
read -r stats_artifact_dir
read -r stats_schedule
read -r stats_identity_map
read -r stats_references

docker compose --profile ingestion run --rm ingestion \
  python -m ingestion.team_stats.ingest \
  --audit "$stats_audit" --artifact-dir "$stats_artifact_dir" \
  --schedule "$stats_schedule" --identity-map "$stats_identity_map" \
  --references "$stats_references" --dry-run
```

A changed baseline/candidate requires a new reviewed token. Existing explicit stdin approval and all hard blockers still apply; no automatic publish wrapper is added. Preserve both source and database history; logical rollback remains its own reviewed original-ingester action. After any separately approved import, a later refresh observes its database timestamp; refresh does not guess successful publication from a filesystem report.

## Recommended future unattended policy — not activated

Keep **all** changes reviewed for now. After isolated/runtime acceptance and explicit owner policy/runtime authorization, only previously unseen, fully admitted, reciprocal pairs might be considered for automatic acceptance. Required gates would include all-three-season acquisition/admission, valid original references/provenance, exact current canonical identities, no missing accepted/scored games, no ambiguous/invalid records, no corrections anywhere in the snapshot, and the unchanged original transactional importer/baseline safeguards. Source metadata unavailability and incomplete current-season coverage must remain explicitly disclosed under the approved contract; they must never be silently upgraded to independent authentication or completion evidence.

Any changed previously accepted raw/statistical row, withdrawn game, identity drift, calibration conflict or integrity error must stop for operator review, with no deletion. Never infer FINAL or completed-before-kickoff eligibility from acceptance. A future unattended *reconstructed-statistics* policy must explicitly accept this limitation; verified postgame/pregame eligibility requires independent evidence. Jobs, recurring schedules, auto-token acknowledgement, publication recovery and external API exposure require separate approval and testing. Nightly postgame checks and a Thursday/weekly full reconciliation are reasonable future candidates given documented provider timing, not configured timers or guarantees.

## Complete changed-file inventory

- New `backend/ingestion/team_stats/refresh.py`: prepare-only source integration, audit adapter, guarded comparison, classifications, private handoff and durable operational metadata.
- New `backend/tests/test_team_stats_refresh.py`: synthetic acquisition/admission/classification/immutability/failure/staleness/locking/CLI tests and isolated restricted-ingest/database/rankings compatibility checks.
- New `docs/team-stats-refresh.md`: source evidence, policy, operational semantics, commands, review and limitations.
- `AGENTS.md`, `README.md`, `docs/architecture.md`, `docs/implementation-plan.md`, `docs/decisions.md`, `docs/team-stats-ingestion.md`: Task 014 scope/reuse/manual handoff and current-state links.

Existing validators, source acquisition, candidate admission, import/apply/rollback service, migrations, model/permissions, schedule refresh, ranking calculations, API/frontend, package configuration and Compose are unchanged.

## Executed results and review gate

Final agent results are recorded below. Docker-backed and real-source preparation must be verified in normal WSL before relying on the workflow. No actual statistics update was performed or scheduled.

Executed agent validation:

| Check | Actual result |
|---|---|
| Broad available backend suite | **310 passed, 80 skipped, 35 deselected**, one existing TestClient deprecation warning; `.venv/bin/python -m pytest backend/tests -m 'not api' --ignore=backend/tests/test_health.py -q` |
| Final refresh-only local tests | **23 passed, 1 PostgreSQL case deselected**; `.venv/bin/python -m pytest backend/tests/test_team_stats_refresh.py -m 'not database' -q` |
| Existing async schedule API regression subset | **23 passed, 10 deselected**, existing deprecation warning |
| Existing additive readiness check | **1 passed, 3 deselected**, existing deprecation warning |
| Compilation / diff whitespace checks | Passed |
| Actual official-source acquisition probe | Failed: bounded `network_failure` for 2024, no repeated retry or successful downloaded-data claim |
| Docker/PostgreSQL/live preparation | Blocked: permission denied on Docker socket; no real database queries, dry-run plan or import was executed here |

The broad suite preceded the final source-method guard/test; the final refresh subset reran after that change. Counts overlap and must not be added. PostgreSQL skips reflect unavailable/enabled test infrastructure, not passes. Synchronous TestClient transport cases were left for normal WSL because their existing environment hang is already documented; no new API transport was introduced. Frontend files are unchanged, so no frontend tests/builds were needed. No dependencies were installed.

Tests cover repeated identical snapshots, one newly arriving pair among accepted pairs, correction raw/metric diffs, missing historical/current-season accepted games, metadata versus acquisition time, partial downloads/source failure stopping, malformed/truncated/invalid-sign inputs, provenance/source method enforcement, missing/invalid checkpoint and lock handling, input validation before network access, stale metadata, private stdout, handoff archive tampering and failed database-transaction cleanup. A failed transaction cannot leave a ready handoff or advance successful validation. The isolated PostgreSQL case checks actual restricted ingestion login, unchanged schedule/statistics counts and rankings, and original unapproved-import rejection; it remains unexecuted here.

**Recommendation: ready for owner code review; NO-GO for unattended acceptance or a real update based on this agent run.** Run the full isolated WSL suite and the documented prepare-only command, review actual source/coverage/canonical diffs, then request separate approval for any original-ingester apply. The next narrowly scoped task is owner review of that real prepared report and runtime evidence; no general research, automatic scheduling or publication is implied.
