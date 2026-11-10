# Team statistics gamebook reference review

Scope: independently inspect one official NFL gamebook per 2024–2026 season, supply both team rows in the existing reference contract, and rerun the unchanged offline validator. No validator/application changes, database connection, migrations, schedule edits, APIs/frontend or git publication.

## References confirmed

All three official PDFs were accessible through the web reader. Values were read from the **Final Team Statistics** table, not halftime statistics, snippets alone or nflverse-derived net totals. Page numbers below are one-based PDF page positions. Table visitor/home columns establish side assignments. PDF table screenshots were requested as an additional check; extracted PDF text supplied the reviewed values. No original PDF bytes were downloaded/hashed locally and no independent cryptographic PDF authentication is claimed.

The actual clock was read after reviewing all three tables: **2026-11-10T04:49:47+00:00**. This batch review observation is recorded for all six manifest rows. It is neither game completion nor source publication time.

| Season / game | Official source / location | Team | Gross pass | Sack loss magnitude | Net pass | Rush | Final points |
|---|---|---|---:|---:|---:|---:|---:|
| 2024 REG1, September 5 | [BAL at KC gamebook](https://static.www.nfl.com/gamecenter/7d3e8f84-1312-11ef-afd1-646009f18b2e.pdf), p.4, Final Team Statistics | BAL (visitor) | 273 | 6 | 267 | 185 | 20 |
| Same | Same table, home column | KC | 291 | 10 | 281 | 72 | 27 |
| 2025 REG1, September 4 | [DAL at PHI gamebook](https://static.www.nfl.com/image/upload/v1757046615/gamecenter/f5908b6d-311e-11f0-b670-ae1250fadad1.pdf), p.3, Final Team Statistics | DAL (visitor) | 188 | 0 | 188 | 119 | 20 |
| Same | Same table, home column | PHI | 152 | 8 | 144 | 158 | 24 |
| 2026 REG8, November 2 | [CHI at SEA gamebook](https://static.www.nfl.com/image/upload/v1793693186/gamecenter/ab37feaa-4feb-11f1-abca-2c54536568a9.pdf), p.4, Final Team Statistics | CHI (visitor) | 247 | 10 | 237 | 126 | 34 |
| Same | Same table, home column | SEA | 188 | 17 | 171 | 81 | 17 |

The sack-loss magnitudes above come from the table's times-thrown/lost-yardage row. They are **not** substitutions for the source CSV's signed field. The 2025 PHI row establishes a nonzero anchor even though DAL's zero is non-informative about sign. The selected 2026 game belongs to the 2026 NFL season, not a January playoff game from the previous season.

These are independently reviewed documents relative to the CSV artifacts, not independent underlying NFL statistical providers. Existing gamebook use/redistribution restrictions remain; only limited reference facts and URLs are retained, no PDF copying or automated gamebook ingestion. `use: reference_only` does not purport to grant redistribution permission.

## Manifest and actual validation

Manifest: [team-stats-gamebook-references.json](team-stats-gamebook-references.json), version 1, six references (both teams for each game). It uses the existing validator without additions, waived requirements or fabricated completion fields. Exact URLs, locations, review timestamps and integer totals are in the manifest.

Evidence summary: [team-stats-gamebook-validation-evidence.json](team-stats-gamebook-validation-evidence.json). The source artifacts and canonical export are now present locally. The owner previously reported zero-error canonical checks; this task independently reran the offline file-based check against that supplied export. It did **not** query live PostgreSQL or independently attest the export's current database state.

Actual CLI run: **exit 0**, report created `2026-11-10T04:50:06.721534+00:00` at:

```text
/tmp/nfl-team-stats-reference-review/audit-2753a18a488e4ae4974edc3ed7a223f7.json
```

The full temporary report's hash and input/manifest hashes are retained in the evidence summary. Temporary files may expire; rerun below for a durable new local audit. Original inputs were read only; the command captured duplicate source bytes into its temporary archive and created a new report.

| Season | Team rows | Canonical paired games | Errors | Reference rows matched | Negative sacks / zero / positive |
|---|---:|---:|---:|---:|---|
| 2024 | 570 | 285 | 0 | 2 | 488 / 82 / 0 |
| 2025 | 570 | 285 | 0 | 2 | 491 / 79 / 0 |
| 2026 | 270 | 135 | 0 | 2 | 225 / 45 / 0 |

All six reference comparisons matched gross passing, rushing and reported schedule scores; nonzero net differences matched the original **negative** sack field. Each artifact reports `negative_validated_against_reviewed_reference`. For these measured artifacts, the validated formula is:

```text
NET team passing = gross passing_yards + original negative sack_yards_lost
```

Examples: 273 + (-6) = 267; 152 + (-8) = 144; 247 + (-10) = 237. Both 2024 sides, both 2026 sides and the zero-sack 2025 side also reconcile. Gross and original sack values remain separate; no absolute values/sign repairs were used. Opponent-derived allowed yards use the same validated definition.

The audit's `net_metrics_validated_games` counts are 285/285/135. This means the artifact-wide sign checks and sampled independent anchors permit the formula on valid pairs; **it is not independent gamebook verification of every game**. The 2026 snapshot is partial-season coverage. No game statuses were changed. Completion-before-historical-cutoff verification remains zero in all three seasons; these references do not establish reliable actual end instants or historic publication availability.

## Exact WSL rerun command

From repository root, using the actual existing content-addressed inputs and identity export:

```bash
PYTHONPATH=backend python3 -m ingestion.team_stats \
  --schedule data/raw/games.csv \
  --output-dir data/raw/team-stats-audit \
  --file 2024=data/raw/team-stats-audit/snapshots/b207a1430c2715d03bbf1844c4eae98695f364851ff6025f422febc2c13f5255.csv \
  --file 2025=data/raw/team-stats-audit/snapshots/91058a59d894855377b2f39f40c4e7bdbeef96d12144289dc68215209a1c93cb.csv \
  --file 2026=data/raw/team-stats-audit/snapshots/941837b79ef4735a625de3394fc07381ab0bfd9a31891920071284d7ab62c590.csv \
  --identity-map data/raw/team-stats-identities.json \
  --references docs/team-stats-gamebook-references.json
```

Expected exit 0 and all season states `audited`. The newly printed `report` path is unique. Inspect `errors`, all six reference matches, each sack convention, and canonical paired counts. This is a local-file re-audit: newly created receipts retain null download times and declared origin; preserve the original acquisition receipts. If inputs change, review new findings rather than overriding them. No Docker, database, downloads or dependencies are needed for this rerun.

## Files and review gate

Created manifest, compact validation-evidence JSON, and this review document. Appended a follow-up link to the existing validation guide. All other pre-existing worktree changes belong to earlier tasks; no validator or application code was changed for this review.

No new unit tests are warranted for reference-only inputs; the unchanged real-artifact CLI passed, and manifest parsing/hashes/local links/original input immutability are checked separately. Next action: owner review of these reference facts and audit evidence. Do not begin statistics database implementation or ranking eligibility changes without separate approval.
