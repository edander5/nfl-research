# Offline NFL Team Statistics Validator and Audit Report

Owner-approved implementation on `feature/team-stats-feasibility`, following [feasibility](team-stats-feasibility.md), [architecture](architecture.md) and the [schedule contract](schedule-data-contract.md). Execution date: November 9, 2026 local; the captured run timestamp is November 10 UTC. No PostgreSQL access/writes, migrations, imports, API/frontend changes, new dependencies, scheduling or git publication occurred.

## Outcome and evidence

The offline CLI works with official downloads or three supplied CSVs, preserves captured bytes and writes unique JSON audit reports. **NET team passing is approved; the real source sack convention remains unverified here.** It cannot be selected by a flag, assumed from a column name, or repaired with absolute values.

| Evidence | Actual result |
|---|---|
| Real acquisition run | Exit 3: 2024 `network_failure`; 2025/2026 deliberately not attempted after the environmental failure |
| Actual captured team-stat CSVs | None; no real season counts, hashes, null rates or sign verification available |
| Existing schedule input | Pure existing validator passed: 842 selected games; original SHA-256 unchanged |
| PostgreSQL UUID/alias export | Not obtained; no live canonical UUID reconciliation claimed |
| Independent gamebook comparisons against real team files | Not executed; no target statistics bytes available |
| Completion-before-cutoff evidence | None established; no FINAL or ranking eligibility inferred |

The actual acquisition audit was `/tmp/nfl-team-stats-audit/audit-0f829e1f329d4405afaa877f80f873b8.json`, created at `2026-11-10T00:40:48.032130+00:00`. It records requested URLs and skipped seasons, not fabricated hashes/retrieval times. `/tmp` is temporary evidence, not a retained project source archive. The current failure is consistent with this execution environment's previously measured DNS restrictions; the new downloader reports a sanitized network code, not a fresh DNS-specific diagnosis. Source availability is unresolved, not declared broken.

### Real source coverage by season

| Season | Official dataset documented/listed | Team-stat body validated this task | Local schedule reconciliation baseline |
|---|---|---|---|
| 2024 | Weekly team CSV | **No** | 285 games: 272 REG + 13 POST; expected complete stats = 570 team rows |
| 2025 | Weekly team CSV | **No** | Same 285/272/13 and expected 570 team rows |
| 2026 | Weekly team CSV | **No** | 272 scheduled REG games; POST absent; 121 paired reported scores in original baseline |

Schedule counts are from the original local artifact, not current PostgreSQL or completion certification. Full 2026 REG could eventually have 544 team rows; current completed-stat row count is unknown. Future scheduled games must not be treated as missing completed statistics. The original schedule hash remains:

```text
66f7a71b12eeb8da8a5c332cfadb245da693aa66e2064fba734983dc41e68fd5
```

Its existing declared-origin/published-checksum discrepancy is unchanged. A current stats file may legitimately contain scores missing from this older baseline. Use a separately captured, approved current schedule snapshot when needed; never replace the original to force agreement.

## Source acquisition and provenance

Rechecked official [loader](https://raw.githubusercontent.com/nflverse/nflreadr/main/R/load_stats.R), [dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_team_stats.json), [release](https://github.com/nflverse/nflverse-data/releases/tag/stats_team) and [licensing](https://github.com/nflverse#licensing). Exact approved sources:

```text
https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2024.csv
https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2025.csv
https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2026.csv
```

Metadata: `https://api.github.com/repos/nflverse/nflverse-data/releases/tags/stats_team`. No provider replacement, mirrors, credentials or paid services. The repository's release-data CC BY 4.0 grant supports this private audit with attribution, license links and modification notices; retain applicable upstream notices. Direct NFL gamebooks are not automatically licensed by nflverse; no PDF scraper/download/import is implemented.

Standard-library HTTPS has bounded response sizes (32 MiB CSV, 2 MiB metadata), timeouts/deadline, redirect count and approved HTTPS host restrictions. Requests have no automatic retries. Available metadata must match the exact asset URL/size and optional SHA-256; rechecking rejects publication races. Unavailable metadata remains explicit and permits a declared-origin CSV acquisition; malformed available metadata blocks acquisition. Complete bytes with failed size/hash/recheck integrity are retained but not accepted. Incomplete transports are failures, not complete snapshots.

Capture uses content-addressed `snapshots/<measured-SHA256>.csv`, atomic no-replace links, fsync and verification of an existing archive. It never overwrites an input or a prior archive. This is application-enforced immutability, not protection against an operator altering filesystem permissions/content. Unique `audit-<random-id>.json` reports retain receipts, errors, actual retrieval/capture observations, publisher fields and hashes. A repeated unchanged local audit reuses the archive and creates a separate report; it performs no data mutation. No retention pruning is active.

Local inputs have `retrieved_at: null`, `method: operator_local_file`, and `source_url_basis: documented_expected_url_not_verified_origin`. Their capture time is not a fabricated download time. Publisher-digest match is integrity evidence, not independent origin authentication: receipts always state `origin: DECLARED` and `independently_authenticated: false`. Signed redirects/raw network exceptions are not recorded. Publisher update metadata is not called a game completion or source-original-publication time.

## Validation and mapping contract

- Read UTF-8/BOM CSV strictly through EOF; reject bad/duplicate/blank headers, missing required columns, malformed width/quotes, duplicate rows, invalid identities and nonintegral/nonfinite/out-of-range numbers. Extra columns are profiled, not assigned invented semantics.
- Required: `season`, `week`, `season_type`, `team`, `opponent_team`, `passing_yards`, `sack_yards_lost`, `rushing_yards`. Optional `game_id` must match if present; a blank/wrong value cannot silently fall back. Optional `sacks_suffered`, `points_scored`, `points_allowed` are checked when present; these names are supported inputs, **not newly verified claims that the real release contains points fields**.
- Exact integer-valued decimal tokens (e.g. `100.0`) are accepted without rounding; scientific notation, fractional values and values outside signed 32-bit range reject. `''`, `NA`, `NULL` remain missing. Missing required yardage is reported, blocks the pair and is never zero-filled. Signed rushing/net passing and legitimate zero remain valid.
- REG weeks 1–18, POST 19–22, correct season per artifact; canonical schedule validation supplies WC/DIV/CON/SB limits. Both teams must match reciprocal schedule identities. Exactly two unique sides are required before a game appears in `matched_games`.
- Prefer matching source game ID plus full composite cross-check; when the column is absent, require a unique season/stage/week/team/opponent match. Never use `old_game_id` or fuzzy names. A corrected/stale ID rejects rather than guessing.
- Without a canonical export, only the schedule's approved team codes are accepted and UUID fields remain null. Reports explicitly say `schedule_source_identifiers_only`; these are source-identity matches, not PostgreSQL UUID verification.
- With `--identity-map`, validate UUID uniqueness, provider aliases, canonical sides and schedule agreement. Explicit export aliases may map a different source label to an existing UUID; no built-in LAR/JAC substitution or alias creation exists. Conflicts, duplicate aliases, unknown labels and missing canonical games reject. The export is operator-supplied evidence, not a live database attestation or guarantee of current DB contents.
- Coverage reports REG/POST row/week counts, matched pairs, all missing scheduled games and missing **reported-score** games. Historical missing games are errors. Current-season future/unverified omissions remain visible without calling them completed. Duplicate/invalid/unmatched rows cannot disappear silently from diagnostics. A partially readable current CSV cannot be certified complete solely from the rows present; publisher integrity plus external completion coverage still matter.

`matched_games` means valid source/canonical identity pairs within the audit, not complete authoritative statistics or final games. Inspect global errors/receipt/state before using individual rows. A download integrity failure clears derived game output. Structural errors prevent the report's validated-net game count from claiming success; diagnostic comparisons on otherwise valid pairs are not publication approval.

### NET passing safeguard

Each artifact reports counts of negative/zero/positive/missing sack values. Mixed nonzero signs block a uniform convention. Merely observing all-negative/all-positive values does **not** enable net calculations.

`--references` supplies reviewed independent gamebook facts with exact game/team identity, gross/net passing, rushing, scores, source URL, locator and review time. At least one nonzero-loss reference must match each season artifact and establish how the source's sack field relates to its documented net-minus-gross difference. Other supplied references must not conflict. A zero-only reference cannot distinguish signs. References are operator-supplied, reference-only observations; the tool validates consistency, not PDF authenticity, permissions or transcription truth.

Once established, negative signed adjustments are **added** to gross; proven positive losses are **subtracted**. Original gross and signed sack integers remain separate. No absolute values, sign repairs or net derivation from score/time. Missing/unmatched/conflicting reference or mixed signs leaves net and net-allowed **null**. Rushing allowed comes from the other valid team row.

Points remain the schedule's reported points, with source-specific points retained separately if supplied. A different known score is a conflict; an unknown schedule score is an unavailable comparison, not proof the other score is wrong. Reference yardage can validate signs even when schedule scores are missing; the score comparison remains explicitly unavailable. All result records retain UNKNOWN and unverified completed-before-cutoff eligibility.

The [feasibility report's official 2024 gamebook spot-check](team-stats-feasibility.md#4-actual-local-validation-and-completeness-findings) distinguishes gross/net and matches the original schedule scores. **This task did not compare that gamebook to downloaded team-stat rows**, nor obtain 2025/2026 comparisons. Do not use the synthetic fixture values as actual NFL evidence. An operator must consult only permitted references, supply accurate independently documented values, and retain their review trail; do not redistribute restricted PDFs.

## Commands from a normal WSL terminal

Run from the repository root. These commands require Python's standard library only; no application initialization, package installation, Docker or database is needed for the audit/download.

```bash
PYTHONPATH=backend python3 -m ingestion.team_stats \
  --schedule data/raw/games.csv \
  --output-dir data/raw/team-stats-audit \
  --download
```

This is the exact command to download all three approved CSVs and capture available metadata. It does not overwrite `data/raw/games.csv`. Successful downloads can still return exit 2 because canonical export/reference evidence is missing. The printed JSON gives the report path and per-season states; inspect that report and its receipts rather than assuming exit 2 means network failure. A network failure stops later season requests. Fix normal-terminal connectivity first; do not repeatedly rerun a failing route or substitute a mirror.

To accept existing owner-downloaded files, place them at the explicit paths below (new inputs, never over the schedule CSV), then:

```bash
PYTHONPATH=backend python3 -m ingestion.team_stats \
  --schedule data/raw/games.csv \
  --output-dir data/raw/team-stats-audit \
  --file 2024=data/raw/stats_team_week_2024.csv \
  --file 2025=data/raw/stats_team_week_2025.csv \
  --file 2026=data/raw/stats_team_week_2026.csv
```

The CLI demands all three season selections. Missing files still produce a failure report. To re-audit downloaded archives, use each receipt's captured path with the same `--file YEAR=PATH` syntax. New local-input receipts do not retroactively claim the previous download time; retain the original download audit alongside them. Source metadata hashes may change legitimately between downloads; compare each receipt's actual contemporaneous metadata, not old feasibility hashes.

Exit codes:

- **0:** requested data/identity/reference checks passed; completion eligibility and rankings are still unverified/unpublished.
- **2:** data-integrity errors or verification/coverage gaps; read the full report.
- **3:** acquisition, file/configuration or manifest failure; no successful import is implied.

### Optional canonical identity export — read-only

The validator cannot manufacture existing UUIDs from the raw schedule. If your development `db` container is already running, the following **read-only SELECT** captures the actual identities. It guards the configured database name and forces a read-only session. These commands were **not executed here**. They do not start services or run migrations. Run once into a new file; `noclobber` prevents replacing an existing export.

```bash
(
  set -o noclobber
  docker compose exec -T db sh -c '
    test "$POSTGRES_DB" = nfl_research_dev || exit 2
    exec env PGOPTIONS="-c default_transaction_read_only=on" psql -X -qAt \
      -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"
  ' > data/raw/team-stats-identities.json <<'SQL'
SELECT jsonb_build_object(
  'version', 1,
  'exported_from', current_database(),
  'exported_at', now(),
  'teams', COALESCE((SELECT jsonb_agg(jsonb_build_object('id', id, 'code', code) ORDER BY code) FROM teams), '[]'::jsonb),
  'aliases', COALESCE((SELECT jsonb_agg(jsonb_build_object('provider', provider, 'source_team_code', source_team_code, 'team_id', team_id) ORDER BY source_team_code) FROM team_aliases WHERE provider = 'nflverse'), '[]'::jsonb),
  'games', COALESCE((SELECT jsonb_agg(jsonb_build_object('id', id, 'source_game_id', source_game_id, 'home_team_id', home_team_id, 'away_team_id', away_team_id) ORDER BY source_game_id) FROM games WHERE provider = 'nflverse' AND season BETWEEN 2024 AND 2026), '[]'::jsonb)
);
SQL
)
```

If export fails it can leave an empty file: preserve the error and use a new filename on the corrected attempt. Do not feed an empty/stale export as successful canonical evidence. If schedule IDs/sides changed since the original raw file, the audit reports drift; select the approved captured schedule version matching the export, not a hand-edited repair. Add `--identity-map data/raw/team-stats-identities.json` to the audit command. The validator only reads that file.

### Optional reviewed reference manifest

Create a new JSON input at `data/raw/team-stats-references.json` after reviewing permitted official reference material. Shape (placeholders must be replaced with actual facts; this is **not a valid reference**):

```json
{
  "version": 1,
  "references": [
    {
      "season": 2024,
      "game_id": "<exact schedule source game_id>",
      "team": "<canonical source code>",
      "source_url": "https://static.www.nfl.com/<actual reference>",
      "locator": "<page/table>",
      "reviewed_at": "<actual timezone-aware review timestamp>",
      "use": "reference_only",
      "gross_passing_yards": "<integer>",
      "net_passing_yards": "<integer>",
      "rushing_yards": "<integer>",
      "points_scored": "<nonnegative integer>",
      "points_allowed": "<nonnegative integer>"
    }
  ]
}
```

Numbers must be JSON integers, not placeholder strings. Supported reference hosts are `static.www.nfl.com`, `www.nfl.com`, `media.nfl.com`, HTTPS without credentials/query tokens. No reference URL is fetched by the command. Do not silently use another provider/domain; ask for a scoped source review if necessary. Include at least one nonzero-loss game from **each** season and more representative REG/POST/overtime/penalty/kneel cases when permitted/available. Add `--references data/raw/team-stats-references.json` alongside `--identity-map` and either acquisition mode. Missing references leave formulas gated, with useful raw/identity/coverage diagnostics still available.

## Tests and executed validation

All new test records, identity UUIDs, URLs and reference totals are **synthetic fixtures**, including those using familiar team codes/game IDs. They are not independent statistical evidence.

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_team_stats.py -q -ra
```

No installation is necessary in the existing approved virtual environment. The CLI also passed its `--help` invocation with `python3 -S` (site packages disabled), confirming the execution path needs only the standard library. Tests use existing pytest; no new dependency was added.

Tests cover both signed conventions with evidence, unverified/mixed/zero-only signs, negative/zero values, nulls, invalid/duplicate/truncated data, identity/alias/sides/UUID drift, stage/season coverage, score/reference conflicts versus unknown scores, no finality inference, full synthetic 842-game schedule reconciliation, official source receipts, metadata races/mismatches/unavailability, transport restrictions, archive collision/idempotency, immutable inputs and CLI reports/failures. Actual final results:

- `.venv/bin/python -m pytest backend/tests/test_team_stats.py -q -ra`: **64 passed**.
- `.venv/bin/python -m pytest backend/tests/test_team_stats.py backend/tests/test_freshness.py backend/tests/test_settings.py backend/tests/test_schedule_service.py backend/tests/test_refresh.py backend/tests/test_refresh_database.py backend/tests/test_ingestion.py backend/tests/test_schedule_database.py -q`: **191 passed, 55 skipped** (isolated PostgreSQL cases not enabled).
- Python parsing, local report link targets, `git diff --check` and unchanged original schedule hash passed.
- Real CLI acquisition: exit **3**, failed before any team CSV capture; subsequent seasons skipped. This verifies failure reporting, not source statistics.

Early development runs included one test-fixture expectation failure (a deliberately absent alias was correctly diagnosed before opponent matching); the fixture expectation was corrected, and the final runs above passed. No existing tests were weakened.

The existing PostgreSQL tests are skipped without their explicit test-environment flag. No database tests, live canonical exports or new migrations were executed. The complete backend suite's synchronous TestClient cases were not rerun; prior reports document their sandbox stall. No frontend checks are needed for this backend-only offline addition.

## Recommended model, remaining gates and next task

No model or migration was created. Retain the [feasibility model proposal](team-stats-feasibility.md#6-proposed-postgresql-model--no-migration-authorized): artifact/import batches; immutable team-game revisions with gross passing, original signed sacks, net/rushing definitions and row provenance; atomic accepted pair pointers; separate completion/cutoff evidence. Derive allowed yards from the reciprocal accepted opponent revision. Keep schedule scores/version provenance distinct, nullable values intact, canonical UUID foreign keys and no use of legacy IDs as unique keys. Separate statistical-quality validation from game finality and completion-before-target evidence.

Before a schema/import implementation can be accepted: run the real artifact audit in normal WSL, review exact schema/sign/reference results for all seasons, reconcile actual canonical exports, disposition current-season missing coverage and corrections, and approve the resulting physical model. Completed-game rankings remain blocked until an evidence-backed completion-before-cutoff policy/data path is approved; score presence, scheduled kickoff, source upload/review time and latest refresh time do not supply that history. This validator deliberately publishes no rankings and verifies no completed-game eligibility.

**Proposed next task, for approval:** execute and review the real-artifact audit with the explicit WSL commands and canonical/reference inputs above; resolve concrete reported gaps. Once accepted, a separate narrowly scoped development statistics schema/import task can implement validated pair storage with idempotency, correction revisions and rollback tests. No schema/import work is authorized now, and no unattended collection is proposed.

## Changed-file inventory

- `backend/ingestion/team_stats/__init__.py`: offline namespace.
- `backend/ingestion/team_stats/source.py`: fixed official source acquisition, metadata checks, provenance and no-replace capture.
- `backend/ingestion/team_stats/validation.py`: pure CSV/type/null/sign/reference/identity/pair/coverage audit.
- `backend/ingestion/team_stats/__main__.py`: offline orchestration, unique reports and exit codes.
- `backend/tests/test_team_stats.py`: synthetic unit/transport/CLI/full-schedule tests.
- `docs/team-stats-validation.md`: this report, commands, limitations and recommended next gate.
- `AGENTS.md`, `docs/decisions.md`, `docs/data-model.md`, `docs/architecture.md`, `docs/implementation-plan.md`: approved task/NET definition and offline architecture synchronization.
- `docs/team-stats-feasibility.md`: existing untracked report from the preceding task, retained and appended with the owner's approved follow-up; earlier research remains labeled historical.

Original schedule, schedule/refresh logic, Compose, API, frontend, ORM and migrations are unchanged. No commit, merge, push or deployment. Stop for owner review.

## Independent gamebook reference follow-up

The owner subsequently supplied real 2024–2026 artifacts and a canonical identity export. The [reference review](team-stats-gamebook-review.md), [six-row manifest](team-stats-gamebook-references.json) and [executed audit evidence](team-stats-gamebook-validation-evidence.json) supersede the earlier blocked-artifact/sign-verification results for those specific captured files. The unchanged offline CLI now exits 0 with 285/285/135 canonical paired games, no errors and negative signed sack adjustments validated against reviewed gamebook anchors. Completed-before-cutoff eligibility and statistics database implementation remain unapproved/unverified as described in the follow-up; no historical evidence above is rewritten.
