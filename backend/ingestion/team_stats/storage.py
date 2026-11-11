"""Development-only guarded selection of immutable team-stat pairs. Caller owns transaction."""
import json
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select, text

from app.models import (Game, SourceArtifact, Team, TeamAlias, TeamStatsBatch, TeamStatsPair,
                        TeamGameStatRevision, TeamStatsAccepted, TeamStatsSelectionEvent)
from ingestion.team_stats.candidate import DEFINITION, StatsRejected, digest, fingerprint, pair_hash, require, load_candidate, validate_receipt, candidate_fingerprint
from ingestion.team_stats.source import read_input
from ingestion.validation import record_hash


def columns(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def clean_session(session):
    require(not session.new and not session.dirty and not session.deleted, 'pending_session_changes')


def validate_history(selections, events):
    grouped = {}
    for event in events:
        grouped.setdefault(str(event.game_id), []).append(event)
    require(set(grouped) == set(selections), 'orphan_or_missing_acceptance_history')
    for gid, history in grouped.items():
        previous = None
        ordered = sorted(history, key=lambda e: e.generation)
        for generation, event in enumerate(ordered, 1):
            require(event.generation == generation and event.before_pair_id == previous, 'broken_acceptance_chain')
            previous = event.after_pair_id
        selected = selections[gid]
        require(selected.generation == len(ordered) and selected.pair_id == previous
                and selected.batch_id == ordered[-1].batch_id, 'acceptance_tip_mismatch')
    return grouped


def inspect(session):
    clean_session(session)
    require(session.scalar(text('select current_database()')) in ('nfl_research_dev', 'nfl_research_test'), 'database_guard')
    session.execute(text("SET LOCAL lock_timeout = '5s'"))
    # Same lock as schedule importer/refresh: identities cannot change mid-publication.
    session.execute(text('select pg_advisory_xact_lock(202426, 1)'))
    games = {str(g.id): g for g in session.scalars(select(Game).where(Game.provider == 'nflverse').with_for_update().execution_options(populate_existing=True))}
    teams = {str(t.id): t for t in session.scalars(select(Team).execution_options(populate_existing=True))}
    aliases = {(a.source_team_code): str(a.team_id) for a in session.scalars(select(TeamAlias).where(TeamAlias.provider == 'nflverse').execution_options(populate_existing=True))}
    selections = {str(s.game_id): s for s in session.scalars(select(TeamStatsAccepted).with_for_update().execution_options(populate_existing=True))}
    pairs = {str(p.id): p for p in session.scalars(select(TeamStatsPair).execution_options(populate_existing=True))}
    rows = {}
    for row in session.scalars(select(TeamGameStatRevision).execution_options(populate_existing=True)):
        rows.setdefault(str(row.pair_id), []).append(row)
    artifacts = {str(a.id): a for a in session.scalars(select(SourceArtifact).where(SourceArtifact.id.in_(
        {p.source_artifact_id for p in pairs.values()})).execution_options(populate_existing=True))} if pairs else {}
    events = list(session.scalars(select(TeamStatsSelectionEvent).execution_options(populate_existing=True)))
    history = validate_history(selections, events)
    validated_sources = set()
    for gid, selected in selections.items():
        validate_stored_pair(str(selected.pair_id), games, pairs, rows, artifacts, validated_sources)
    baseline = fingerprint(dict(events=sorted([columns(e) for e in events], key=lambda e: (str(e['game_id']), e['generation'])), games=sorted([columns(g) for g in games.values()], key=lambda g: str(g['id'])),
        teams=sorted([columns(t) for t in teams.values()], key=lambda t: str(t['id'])), aliases=aliases,
        selections=sorted([columns(s) for s in selections.values()], key=lambda s: str(s['game_id'])),
        pairs=sorted([columns(p) for p in pairs.values()], key=lambda p: str(p['id'])),
        rows=sorted([columns(r) for values in rows.values() for r in values], key=lambda r: (str(r['pair_id']), str(r['team_id']))),
        artifacts=sorted([columns(a) for a in artifacts.values()], key=lambda a: str(a['id']))))
    return dict(games=games, teams=teams, aliases=aliases, selections=selections, pairs=pairs,
                rows=rows, artifacts=artifacts, history=history, baseline_sha256=baseline)


def validate_stored_pair(identifier, games, pairs, rows, artifacts, validated_sources=None):
    pair = pairs.get(identifier)
    require(pair is not None and str(pair.game_id) in games, 'missing_stored_pair')
    game = games[str(pair.game_id)]
    require(pair.definition_version == DEFINITION and pair.home_team_id == game.home_team_id
            and pair.away_team_id == game.away_team_id, 'stored_pair_identity_drift')
    sides = rows.get(identifier, [])
    require(len(sides) == 2 and {r.team_id for r in sides} == {pair.home_team_id, pair.away_team_id}, 'incomplete_stored_pair')
    payload = []
    for row in sorted(sides, key=lambda r: str(r.team_id)):
        values = {k: getattr(row, k) for k in ('gross_passing_yards', 'original_sack_yards', 'net_passing_yards', 'rushing_yards')}
        require(all(type(v) is int for v in values.values()) and row.original_sack_yards <= 0
                and row.net_passing_yards == row.gross_passing_yards + row.original_sack_yards
                and row.opponent_team_id in {pair.home_team_id, pair.away_team_id} - {row.team_id}
                and record_hash(row.raw_source_record) == row.source_record_sha256, 'invalid_stored_values')
        payload.append(dict(team_id=str(row.team_id), values=values, raw=row.raw_source_record))
    require(pair_hash(dict(game_id=str(pair.game_id), definition=DEFINITION, teams=payload)) == pair.content_sha256, 'stored_pair_hash_mismatch')
    artifact = artifacts.get(str(pair.source_artifact_id))
    require(artifact is not None and artifact.provider == 'nflverse' and artifact.origin_status == 'DECLARED', 'stored_provenance_invalid')
    if validated_sources is not None and (str(artifact.id), game.season) in validated_sources:
        return
    try:
        path = Path(artifact.artifact_path)
        require(not path.is_symlink(), 'stored_archive_mismatch')
        data = read_input(path)
        require(digest(data) == artifact.sha256 and len(data) == artifact.byte_size, 'stored_archive_mismatch')
        provenance = json.loads(artifact.provenance_notes or '{}')
        require(provenance.get('kind') == 'team_stats', 'stored_provenance_invalid')
        validate_receipt(provenance['receipt'], data, game.season)
    except OSError:
        raise StatsRejected('stored_archive_missing') from None
    except (KeyError, ValueError) as exc:
        if isinstance(exc, StatsRejected):
            raise
        raise StatsRejected('stored_provenance_invalid') from None
    if validated_sources is not None:
        validated_sources.add((str(artifact.id), game.season))


def plan_import(state, candidate):
    changes, blockers = [], []
    incoming = {p['game_id']: p for p in candidate.pairs}
    require(len(incoming) == len(candidate.pairs), 'duplicate_incoming_game')
    for gid, pair in sorted(incoming.items()):
        game = state['games'].get(gid)
        require(game is not None and game.source_game_id == pair['source_game_id'] and game.season == pair['season'], 'live_game_identity_mismatch')
        require(len(pair['teams']) == 2 and {t['team_id'] for t in pair['teams']} ==
                {str(game.home_team_id), str(game.away_team_id)}, 'live_team_identity_mismatch')
        for team in pair['teams']:
            raw = team['raw']
            require(state['aliases'].get(raw['team']) == team['team_id']
                    and state['teams'][team['team_id']].code == team['code']
                    and state['aliases'].get(raw['opponent_team']) in
                    {str(game.home_team_id), str(game.away_team_id)} - {team['team_id']}
                    and int(raw['week']) == game.week and raw['season_type'] == game.season_type, 'live_alias_or_stage_drift')
        selection = state['selections'].get(gid)
        previous = state['pairs'][str(selection.pair_id)] if selection else None
        if previous is None or previous.content_sha256 != pair['content_sha256']:
            before = state['rows'].get(str(previous.id), []) if previous else []
            old_raw = {str(r.team_id): r.raw_source_record for r in before}
            raw_changes = [dict(team_id=t['team_id'], fields=[dict(field=k, before=old_raw[t['team_id']].get(k), after=t['raw'].get(k))
                for k in sorted(set(old_raw[t['team_id']]) | set(t['raw']))
                if old_raw[t['team_id']].get(k) != t['raw'].get(k)]) for t in pair['teams']] if previous else []
            changes.append(dict(game_id=gid, raw_changes=raw_changes, source_game_id=pair['source_game_id'], season=pair['season'],
                kind='initial_pair' if previous is None else 'historical_correction' if pair['season'] < 2026 else 'correction',
                before_pair_id=str(previous.id) if previous else None,
                before=[dict(team_id=str(r.team_id), **{k: getattr(r, k) for k in ('gross_passing_yards','original_sack_yards','net_passing_yards','rushing_yards')}) for r in sorted(before, key=lambda r: str(r.team_id))],
                after=[dict(team_id=t['team_id'], **t['values']) for t in pair['teams']],
                before_sha256=previous.content_sha256 if previous else None, after_sha256=pair['content_sha256']))
    for gid in sorted(set(state['selections']) - set(incoming)):
        blockers.append(dict(code='missing_accepted_game', game_id=gid))
    for gid, game in state['games'].items():
        if game.reported_home_score is not None and gid not in incoming:
            blockers.append(dict(code='missing_reported_score_game', game_id=gid))
    blockers.sort(key=lambda b: (b['code'], b['game_id']))
    plan = dict(operation='IMPORT', candidate_sha256=candidate.sha256, baseline_sha256=state['baseline_sha256'],
                changes=changes, blockers=blockers, selected_pairs=len(incoming),
                inserted_pairs=sum(c['before_pair_id'] is None for c in changes),
                corrected_pairs=sum(c['before_pair_id'] is not None for c in changes), unchanged_pairs=len(incoming)-len(changes))
    plan['review_token'] = fingerprint(plan)
    return plan


def verify_archives(candidate, archives):
    require(set(archives) == set(candidate.blobs), 'incomplete_archives')
    for name, data in candidate.blobs.items():
        try:
            path = Path(archives[name])
            require(not path.is_symlink() and read_input(path) == data, 'archive_hash_mismatch')
        except OSError:
            raise StatsRejected('archive_missing') from None
    verified = load_candidate(archives['audit.json'], Path(archives['2024.csv']).parent,
                              archives['schedule.csv'], archives['identities.json'], archives['references.json'])
    require(verified.sha256 == candidate.sha256 == candidate_fingerprint(candidate.evidence, candidate.pairs, candidate.blobs)
            and verified.pairs == candidate.pairs and verified.evidence == candidate.evidence
            and verified.blobs == candidate.blobs, 'candidate_changed_after_validation')
    return verified


def publish(session, game, pair, batch, previous):
    if previous:
        previous.pair_id, previous.batch_id, previous.generation = pair.id, batch.id, previous.generation + 1
    else:
        session.add(TeamStatsAccepted(game_id=game.id, pair_id=pair.id, batch_id=batch.id, generation=1))
    session.flush()


def apply_import(session, candidate, archives, approval):
    clean_session(session)
    archives = dict(archives)
    candidate = verify_archives(candidate, archives)
    state = inspect(session)
    plan = plan_import(state, candidate)
    require(not plan['blockers'], 'blocked_snapshot')
    if not plan['changes']:
        return dict(outcome='unchanged', plan=plan)
    require(approval == plan['review_token'], 'review_required_or_stale')
    batch = TeamStatsBatch(id=uuid4(), kind='IMPORT', candidate_sha256=candidate.sha256, review_token=approval,
        evidence=dict(candidate=candidate.evidence, archives=archives, summary={k: plan[k] for k in ('inserted_pairs','corrected_pairs','unchanged_pairs')}))
    session.add(batch)
    artifacts = {}
    for year, receipt in candidate.evidence['receipts'].items():
        meta = receipt.get('publisher_metadata') or {}
        artifact = SourceArtifact(provider='nflverse', artifact_path=archives[year+'.csv'], sha256=receipt['sha256'],
            byte_size=receipt['byte_size'], documented_source_url=receipt['source_url'],
            declared_source_url=receipt['source_url'] if receipt['method'] == 'official_download' else None,
            retrieved_at=datetime.fromisoformat(receipt['retrieved_at']) if receipt['retrieved_at'] else None,
            origin_status='DECLARED', publisher_sha256=(meta.get('digest') or '').removeprefix('sha256:') or None,
            source_revision=str(meta['id']) if meta else None, license_url=receipt['license_url'], attribution=receipt['attribution'],
            provenance_notes=json.dumps(dict(kind='team_stats', receipt=receipt, batch_id=str(batch.id)), sort_keys=True))
        session.add(artifact)
        artifacts[int(year)] = artifact
    session.flush()
    incoming = {p['game_id']: p for p in candidate.pairs}
    for change in plan['changes']:
        payload = incoming[change['game_id']]
        game = state['games'][payload['game_id']]
        previous = state['selections'].get(payload['game_id'])
        pair = TeamStatsPair(id=uuid4(), game_id=game.id, home_team_id=game.home_team_id, away_team_id=game.away_team_id,
            batch_id=batch.id, source_artifact_id=artifacts[payload['season']].id,
            previous_pair_id=previous.pair_id if previous else None, definition_version=DEFINITION,
            content_sha256=payload['content_sha256'])
        session.add(pair)
        session.flush()
        for team in payload['teams']:
            home = team['team_id'] == str(game.home_team_id)
            session.add(TeamGameStatRevision(pair_id=pair.id, game_id=game.id, team_id=UUID(team['team_id']),
                opponent_team_id=game.away_team_id if home else game.home_team_id, side='HOME' if home else 'AWAY',
                **team['values'], source_record_sha256=team['row_sha256'], source_line=team['line'], raw_source_record=team['raw']))
        session.flush()
        publish(session, game, pair, batch, previous)
    return dict(outcome='applied', batch_id=str(batch.id), plan=plan)


def plan_rollback(session, state, target_id):
    batch = session.get(TeamStatsBatch, UUID(str(target_id)))
    require(batch is not None, 'rollback_batch_missing')
    events = list(session.scalars(select(TeamStatsSelectionEvent).where(TeamStatsSelectionEvent.batch_id == batch.id)))
    require(bool(events) and all(e.before_pair_id is not None for e in events), 'rollback_has_no_prior_pair')
    changes = []
    for event in sorted(events, key=lambda e: str(e.game_id)):
        gid = str(event.game_id)
        selection = state['selections'].get(gid)
        require(selection is not None, 'rollback_missing_selection')
        if selection.pair_id == event.before_pair_id:
            continue
        require(selection.pair_id == event.after_pair_id, 'rollback_baseline_changed')
        require(any(e.after_pair_id == event.before_pair_id and e.generation < event.generation
                    for e in state['history'][gid]), 'rollback_target_never_accepted')
        validate_stored_pair(str(event.before_pair_id), state['games'], state['pairs'], state['rows'], state['artifacts'])
        changes.append(dict(game_id=gid, before_pair_id=str(selection.pair_id), after_pair_id=str(event.before_pair_id)))
    plan = dict(operation='ROLLBACK', target_batch_id=str(batch.id), candidate_sha256=fingerprint(str(batch.id)),
                baseline_sha256=state['baseline_sha256'], changes=changes, blockers=[])
    plan['review_token'] = fingerprint(plan)
    return plan


def apply_rollback(session, target_id, approval):
    state = inspect(session)
    plan = plan_rollback(session, state, target_id)
    if not plan['changes']:
        return dict(outcome='unchanged', plan=plan)
    require(approval == plan['review_token'], 'review_required_or_stale')
    batch = TeamStatsBatch(id=uuid4(), kind='ROLLBACK', candidate_sha256=plan['candidate_sha256'],
        review_token=approval, evidence=dict(target_batch_id=str(target_id)))
    session.add(batch)
    session.flush()
    for change in plan['changes']:
        publish(session, state['games'][change['game_id']], state['pairs'][change['after_pair_id']],
                batch, state['selections'][change['game_id']])
    return dict(outcome='rolled_back', batch_id=str(batch.id), plan=plan)
