# Data Model — Schedule Foundation and Future Conceptual Records

**Current schedule implementation:** Task 002 adds `teams`, `team_aliases`, `source_artifacts` and `games` in [the initial migration](../backend/alembic/versions/0001_schedule.py) and [SQLAlchemy models](../backend/app/models/schedule.py). See [development guide](development.md) for fields, constraints, identity/provenance design and unverified runtime checks. Task 010 adds the five [team-statistics tables](team-stats-ingestion.md) in migration `0002_team_stats`; runtime acceptance is pending. Player/odds and broader entities below remain conceptual.

## Core entities

| Entity | Key fields / meaning | Important constraints |
|---|---|---|
| seasons | `season`, stage labels, published schedule context | 2024–2026 MVP |
| teams | canonical `team_id`, abbreviation, display name | Maintain provider aliases and historical changes |
| games | canonical `game_id`, season, week, stage, home/away team, kickoff UTC, status, score | Unique provider mapping; valid teams; completed status governs result display |
| players | canonical `player_id`, name, position attributes | Names are not unique keys |
| external_id_mappings | provider, entity type, provider ID, canonical ID | Ambiguous name-based matching quarantined |
| player_team_memberships | player, team, effective dates / season | Supports multiple teams per season |
| player_game_stats | game, player, **team played for**, attempts/yards/TD stats, participated indicator | One canonical row per player/game/team when semantically appropriate; missing values preserved |
| team_game_stats | team, game, passing/rushing yards for/allowed, relevant denominator | Confirm source coverage and stat conventions before finalizing |
| injuries | player, team, injury designation, practice participation, report time | Last-known current data and source provenance; historical only if verified |
| depth_chart_entries | team, player, unit, position, depth rank, validity/source timestamp | Coverage may be partial; no fabricated roster entries |
| source_imports | provider, artifact, hash/version, fetched time, status | Audit ingestion history |
| source_record_revisions | record key, old/new hash or audited change, detected time | Corrections explainable |
| rejected_records | import ID, raw reference, rejection reason, disposition | No silent discard |
| odds_request_usage | provider, request key, request cost, used/remaining credits, request time | Hard cap, deduplication, cooldown |
| odds_observations (conditional) | game, player, market, sportsbook, value, observed time, last checked time | Only if storage is permitted by provider terms; never imply live |

**Note:** The table above remains conceptual. The schedule subset has migration `0001_schedule`; the Task 010 statistics pair/revision design below has additive migration `0002_team_stats`. Other conceptual entities have no physical migration. The new migration was not executed here; PostgreSQL runtime validation is still required.

**Approved schedule limitation (Decision 53):** retain explicit UNKNOWN status when source finality is unsupported. Source-reported scores are not confirmed-final scores. Do not invent in-progress/postponed states or infer finality solely from kickoff. Local validation also found eight colliding `old_game_id` values in 2026; preserve them as nonunique source attributes or quarantine ambiguous alias mappings. Provider `game_id` and canonical identities remain distinct; see [validation report](schedule-validation-report.md). These are contract constraints, not migrations.

## Statistical rules and query semantics

- Regular and postseason separate by default; optional combined scope. Week/cutoff filters apply to every aggregation and cached result.
- Team offense ranks: average passing or rushing **yards gained per game**, descending (higher = stronger offense).
- Team defense ranks: average passing or rushing **yards allowed per game**, ascending (lower = stronger defense). Sorting can reverse for matchup weakness views.
- Ranking denominator: eligible team games before cutoff, not schedule slots or byes. Define whether overtime yards included (default raw official game totals) and whether sacks/negative team passing yards affect totals; verify dataset definitions before implementing.
- Player prop windows: take latest 5 or 10 **eligible player appearances** within the selected season/stage, not calendar games. Played zeros count; DNP/byes excluded. Pushes on integer lines counted as separate outcomes; report over / under / push and disclose denominator convention.
- Multiple teams: use player across all their teams in the season by default; restrict by specific historical team only with explicit filter. Associate each game with actual team.
- Cutoff: only games **completed before selected game's kickoff** qualify for pregame statistical research; do not use current week results or future statistics. Source correction after the fact may change reconstructed values; show provenance.
- Live injury and depth-chart information is current-state data; do **not** silently join contemporary reports into historical pregame views as if original.
- Invalid/missing values do not silently coerce to zero. Source corrections revise records through audited ingestion.

## Initial model review questions for implementation

- Which official source fields support team pass yards *allowed*? Is team play-by-play aggregation required?
- What participation indicator is trustworthy for game-log denominator eligibility, including players with 0 touches?
- Do weekly data assets uniquely identify a player/game/team? How are 2024–2026 midseason transfers represented?
- How are postponements, neutral-site games, cancellations, postseason week naming and overtime recorded?
- Are real `receiving_tds`, `rushing_tds` and `passing_tds` present by game for all supported years?

These are **validation gates**, not permission to invent defaults.

## Task 004 ingestion implementation note

[Development schedule ingestion](schedule-ingestion.md) uses the existing schema without a migration. Original artifacts and structured correction/import receipts in `source_artifacts.provenance_notes` retain correction evidence; per-game raw dictionaries, canonical JSON hashes and physical source lines are populated. Canonical UUIDs survive unambiguously evidenced source-ID changes. Provider aliases are checked, legacy IDs remain nonunique, and unknown values/finality remain unchanged in meaning. Runtime tests for this importer remain pending outside the agent's restricted Docker environment.


## Approved team passing definition — offline validation follow-up

Decision 61 selects **NET team passing yards**, including sacks, for offense and opponent-derived defense. Preserve gross passing and original signed sack values. Validate each artifact convention against reviewed reference totals before adding a signed negative adjustment or subtracting a proven positive loss; never use absolute values to repair ambiguous data. See [offline validator](team-stats-validation.md). Decision 61 originally authorized offline validation only. Decision 62 and Task 010 below separately authorize the additive storage implementation; no historical eligibility inference is authorized.


## Task 010 physical team-statistics storage

[Schema and rationale](team-stats-ingestion.md) document `team_stats_batches`, `team_stats_pairs`, `team_game_stat_revisions`, `team_stats_accepted` and `team_stats_selection_events`. The game-pair pointer accepts two reciprocal, complete team revisions together. Gross, original signed sacks, NET and rushing remain versioned; allowed yards are derived from the accepted opponent. Shared artifact schema, schedule scores/statuses and historical completion eligibility are unchanged. The initial conceptual table above is superseded by this physical pair/revision design for statistics only. No development migration or real import was executed.


## Team-statistics security hardening

Security hardening adds a required unique `(game_id, generation)` to selection events. Events are emitted by the accepted-pointer AFTER trigger, not supplied by the runtime service. The pointer guard checks the proven chain tip and earlier same-game target acceptance; Python verifies contiguous history independently. Historical pairs/rows/batches/events remain append-only. See [security model and pending runtime acceptance](team-stats-security-hardening.md).


## Task 011

Task 011 introduces response schemas only; storage remains at 0002. Current accepted pair pointers select revision rows for both teams; API aggregates derive opponent allowed yards with per-metric non-null denominators. Reported schedule points and stored-evidence verified-final point aggregates are separate. See [API semantics](team-stats-api.md).
