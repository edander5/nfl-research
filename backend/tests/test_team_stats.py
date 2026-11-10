"""Synthetic stats/reference fixtures only; no downloaded data, network or database."""
import csv
import hashlib
import io
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from ingestion.team_stats import __main__ as cli
from ingestion.team_stats.source import AcquisitionError, acquire, capture, describe, source_url
from ingestion.team_stats.validation import audit, canonical_map, number, reference_list


def encode(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


@pytest.fixture
def sample():
    games = [dict(game_id='2024_01_BAL_KC', season='2024', week='1', game_type='REG',
                  home_team='KC', away_team='BAL', home_score='27', away_score='20')]
    rows = [dict(season='2024', week='1', season_type='REG', team=t, opponent_team=o,
                 game_id=games[0]['game_id'], passing_yards=p, sack_yards_lost=s, rushing_yards=r,
                 sacks_suffered=n, points_scored=pf, points_allowed=pa)
            for t,o,p,s,r,n,pf,pa in [('BAL','KC','300','-20','100','2','20','27'),
                                      ('KC','BAL','200','-10','80','1','27','20')]]
    refs = [dict(season=2024, game_id=games[0]['game_id'], team='BAL',
                 source_url='https://static.www.nfl.com/synthetic-example.pdf', locator='synthetic test p4',
                 reviewed_at='2026-01-01T00:00:00Z', use='reference_only', gross_passing_yards=300,
                 net_passing_yards=280, rushing_yards=100, points_scored=20, points_allowed=27)]
    team_ids = {t: str(uuid4()) for t in ('BAL','KC')}
    mapping = dict(version=1, teams=[dict(id=v, code=k) for k,v in team_ids.items()],
                   aliases=[dict(provider='nflverse',source_team_code=k,team_id=v) for k,v in team_ids.items()],
                   games=[dict(id=str(uuid4()),source_game_id=games[0]['game_id'],
                               home_team_id=team_ids['KC'],away_team_id=team_ids['BAL'])])
    return games, rows, refs, mapping


def run(sample, refs=True, canonical=True):
    games, rows, references, mapping = sample
    return audit(encode(rows), 2024, games,
                 canonical_map(mapping, games) if canonical else None, references if refs else [])


def codes(result):
    return {e['code'] for e in result['errors']}


def test_negative_sign_and_opponent_metrics_with_canonical_uuids(sample):
    result = run(sample)
    assert result['structural_integrity_passed']
    assert result['canonical_identity_paired_games'] == 1
    assert result['sack_convention'] == 'negative_validated_against_reviewed_reference'
    bal,kc = result['matched_games'][0]['teams']
    assert (bal['net_passing_yards'],bal['original_sack_yards'],bal['passing_yards_allowed']) == (280,-20,190)
    assert bal['rushing_yards_allowed'] == 80
    assert kc['gross_passing_yards'] == 200
    assert bal['status'] == 'UNKNOWN'
    assert result['completion_evidence']['eligible_games_verified'] == 0


def test_positive_sign_requires_actual_reference(sample):
    for r in sample[1]:
        r['sack_yards_lost'] = str(-int(r['sack_yards_lost']))
    result = run(sample)
    assert result['sack_convention'] == 'positive_validated_against_reviewed_reference'
    assert result['matched_games'][0]['teams'][0]['net_passing_yards'] == 280


def test_no_reference_does_not_assume_negative_sign(sample):
    result = run(sample, refs=False, canonical=False)
    assert result['sack_sign_counts'] == {'negative': 2}
    assert result['sack_convention'] == 'unverified'
    assert result['canonical_identity_paired_games'] is None
    assert result['matched_games'][0]['teams'][0]['net_passing_yards'] is None


def test_zero_and_negative_rush_preserved(sample):
    sample[1][1]['passing_yards'] = '0'
    sample[1][1]['rushing_yards'] = '-3'
    result = run(sample)
    kc = result['matched_games'][0]['teams'][1]
    assert kc['net_passing_yards'] == -10
    assert kc['rushing_yards'] == -3
    assert kc['gross_passing_yards'] == 0


def test_mixed_sacks_never_use_absolute_value(sample):
    sample[1][1]['sack_yards_lost'] = '10'
    result = run(sample)
    assert 'mixed_sack_signs' in codes(result)
    assert result['sack_convention'] == 'unverified'
    assert all(t['net_passing_yards'] is None for t in result['matched_games'][0]['teams'])


def test_zero_only_no_informative_anchor(sample):
    for r in sample[1]:
        r['sack_yards_lost'] = '0'
    sample[2][0]['net_passing_yards'] = 300
    assert run(sample)['sack_convention'] == 'unverified'


@pytest.mark.parametrize('field,value', [('passing_yards','NaN'),('rushing_yards','Infinity'),
    ('passing_yards','1.5'),('sack_yards_lost','-2147483649'),('week','19'),('season_type','PRE'),
    ('season','2025'),('team',''),('opponent_team','BAL'),('points_scored','-1'),('week','NA'),
    ('passing_yards',' 300'),('passing_yards','1e2')])
def test_invalid_tokens_are_reported(sample,field,value):
    sample[1][0][field] = value
    assert 'invalid_value' in codes(run(sample,refs=False))


@pytest.mark.parametrize('token', ['', 'NA','NULL'])
def test_null_not_zero(sample,token):
    sample[1][0]['rushing_yards'] = token
    result = run(sample,refs=False)
    assert 'missing_metric' in codes(result)
    assert result['matched_games'] == []
    assert result['columns']['rushing_yards']['null'] == 1


@pytest.mark.parametrize('data',[b'',b'wrong,header\n1,2\n',b'\xff',b'season,season\n2024,2024\n'])
def test_bad_csv_headers(data,sample):
    result = audit(data,2024,sample[0])
    assert codes(result) & {'invalid_headers','invalid_csv'}


def test_truncated_csv_and_width(sample):
    data = encode(sample[1])
    result = audit(data + b'2024,1\n',2024,sample[0])
    assert 'row_width' in codes(result)
    result = audit(data + b'"unterminated',2024,sample[0])
    assert 'invalid_csv' in codes(result)


def test_duplicate_records_never_accepted(sample):
    sample[1].append(sample[1][0].copy())
    result = run(sample)
    assert 'duplicate_record' in codes(result)
    assert result['matched_games'] == []


def test_missing_pair_and_historical_coverage(sample):
    sample[1].pop()
    result = run(sample,refs=False)
    assert {'missing_or_duplicate_game_side','historical_coverage_missing'} <= codes(result)
    assert result['coverage']['REG']['missing_reported_score_games'] == ['2024_01_BAL_KC']


def test_opponent_and_id_mismatches(sample):
    sample[1][0]['opponent_team'] = 'SF'
    assert 'missing_or_ambiguous_schedule_match' in codes(run(sample,refs=False,canonical=False))
    sample[1][0]['opponent_team'] = 'KC'
    sample[1][0]['game_id'] = 'legacy-id'
    assert 'source_game_id_mismatch' in codes(run(sample,refs=False))


def test_game_id_absent_unique_composite_join(sample):
    for r in sample[1]:
        del r['game_id']
    assert run(sample)['canonical_identity_paired_games'] == 1


def test_unapproved_alias_rejected(sample):
    sample[1][0]['team'] = 'BLT'
    assert 'unknown_or_unmapped_alias' in codes(run(sample,refs=False,canonical=False))


def test_explicit_alias_resolves_to_same_uuid(sample):
    uid = sample[3]['teams'][0]['id']
    sample[3]['aliases'].append(dict(provider='nflverse',source_team_code='BLT',team_id=uid))
    sample[1][0]['team'] = 'BLT'
    sample[1][1]['opponent_team'] = 'BLT'
    assert run(sample)['canonical_identity_paired_games'] == 1


@pytest.mark.parametrize('change',['alias','uuid','sides','missing_game'])
def test_bad_identity_export(sample,change):
    m = sample[3]
    if change == 'alias':
        m['aliases'].append(m['aliases'][0].copy())
    elif change == 'uuid':
        m['teams'][0]['id'] = 'invalid'
    elif change == 'sides':
        m['games'][0]['home_team_id'] = m['games'][0]['away_team_id']
    else:
        m['games'] = []
        assert 'canonical_game_missing' in codes(run(sample,refs=False))
        return
    with pytest.raises(ValueError):
        canonical_map(m,sample[0])


def test_postseason_and_current_season_separate(sample):
    for g in sample[0]:
        g.update(season='2026', game_type='WC',week='19',game_id='2026_19_BAL_KC',home_score='',away_score='')
    for r in sample[1]:
        r.update(season='2026',season_type='POST',week='19',game_id='2026_19_BAL_KC')
    result = audit(encode(sample[1]),2026,sample[0])
    assert result['coverage']['REG']['paired_games'] == 0
    assert result['coverage']['POST']['paired_games'] == 1
    assert 'reported_score_mismatch' not in codes(result)
    assert result['warnings']  # missing schedule scores are unknown, not contradictory
    for r in sample[1]:
        r['points_scored'] = r['points_allowed'] = ''
    result = audit(encode(sample[1]),2026,sample[0])
    assert result['coverage']['POST']['paired_games'] == 1
    assert result['matched_games'][0]['teams'][0]['reported_points_scored'] is None


def test_reference_mismatch_disables_formula(sample):
    sample[2][0]['net_passing_yards'] = 279
    result = run(sample)
    assert 'reference_totals_mismatch' in codes(result)
    assert result['sack_convention'] == 'unverified'


def test_score_reconciliation(sample):
    sample[1][1]['points_scored'] = '28'
    result = run(sample)
    assert 'reported_score_mismatch' in codes(result)
    assert result['matched_games'] == []


def test_reference_manifest_and_no_completion_inference(sample):
    assert len(reference_list(dict(version=1,references=sample[2]))) == 1
    sample[2][0]['reviewed_at'] = '2026-01-01'
    with pytest.raises(ValueError):
        reference_list(dict(version=1,references=sample[2]))


@pytest.mark.parametrize('token,value',[('0',0),('-3',-3),('100.0',100),('NA',None)])
def test_exact_numeric_conversion(token,value):
    assert number(token) == value


def publisher(data,season=2024):
    return json.dumps(dict(assets=[dict(name=f'stats_team_week_{season}.csv',id=10,size=len(data),
        updated_at='2026-11-09T10:00:00Z',digest='sha256:'+hashlib.sha256(data).hexdigest(),
        browser_download_url=source_url(season))])).encode()


def test_retrieval_receipt_and_archive_no_overwrite(tmp_path,sample):
    data=encode(sample[1])
    def get(url,**kwargs):
        return publisher(data) if '/tags/' in url else data
    body,receipt=acquire(2024,get)
    assert receipt['integrity']=='publisher_digest_matched'
    assert receipt['retrieved_at'] and not receipt['independently_authenticated']
    path=Path(capture(tmp_path,body))
    assert capture(tmp_path,body)==str(path)
    assert path.read_bytes()==data
    path.write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='archive_collision'):
        capture(tmp_path,body)


def test_metadata_absent_keeps_declared_origin(sample):
    data=encode(sample[1])
    def get(url,**kwargs):
        if '/tags/' in url:
            raise AcquisitionError('http_403')
        return data
    _,receipt=acquire(2024,get)
    assert receipt['integrity']=='unverified'
    assert receipt['metadata_error']=='http_403'
    assert describe(data,2024,'operator_local_file')['retrieved_at'] is None


def test_publisher_digest_mismatch_and_race(sample):
    data=encode(sample[1]); count=0
    def get(url,**kwargs):
        nonlocal count
        if '/tags/' not in url:
            return data
        count+=1
        raw=json.loads(publisher(data))
        raw['assets'][0]['digest']='sha256:'+'0'*64
        raw['assets'][0]['id']=count
        return json.dumps(raw).encode()
    _,receipt=acquire(2024,get)
    assert set(receipt['acquisition_errors'])=={'publisher_digest_mismatch','publisher_metadata_changed_or_unavailable'}


def test_failed_network_and_bad_publisher(sample):
    def fail(*a,**kw):
        raise AcquisitionError('network_failure')
    with pytest.raises(AcquisitionError,match='network_failure'):
        acquire(2024,fail)
    with pytest.raises(AcquisitionError,match='invalid_publisher_metadata'):
        acquire(2024,lambda *a,**kw:b'{}')


def test_cli_capture_report_and_input_unchanged(tmp_path,sample,monkeypatch,capsys):
    schedule_path=tmp_path/'schedule.csv'; schedule_path.write_bytes(b'synthetic_schedule')
    snapshot=SimpleNamespace(rows=[SimpleNamespace(raw=r) for r in sample[0]],sha256='s'*64)
    monkeypatch.setattr(cli,'validate_bytes',lambda data:snapshot)
    args=['--schedule',str(schedule_path),'--output-dir',str(tmp_path/'output')]
    for year in (2024,2025,2026):
        rows=deepcopy(sample[1])
        for r in rows: r['season']=str(year)
        path=tmp_path/f'{year}.csv'; path.write_bytes(encode(rows)); args+=['--file',f'{year}={path}']
    assert cli.main(args)==2
    summary=json.loads(capsys.readouterr().out)
    report=json.loads(Path(summary['report']).read_text())
    assert not report['database_access'] and not report['rankings_published']
    assert report['identity_scope']=='schedule_source_identifiers_only'
    assert report['seasons']['2024']['receipt']['retrieved_at'] is None
    assert schedule_path.read_bytes()==b'synthetic_schedule'
    first=Path(summary['report']).read_bytes()
    assert cli.main(args)==2
    assert Path(summary['report']).read_bytes()==first


def test_cli_download_stops_after_environment_failure(tmp_path,sample,monkeypatch,capsys):
    path=tmp_path/'games.csv'; path.write_bytes(b'fixture')
    monkeypatch.setattr(cli,'validate_bytes',lambda _:SimpleNamespace(rows=[SimpleNamespace(raw=r) for r in sample[0]],sha256='x'))
    calls=[]
    def fail(year):
        calls.append(year)
        raise AcquisitionError('network_failure')
    monkeypatch.setattr(cli,'acquire',fail)
    assert cli.main(['--schedule',str(path),'--output-dir',str(tmp_path/'out'),'--download'])==3
    report=json.loads(Path(json.loads(capsys.readouterr().out)['report']).read_text())
    assert calls==[2024]
    assert report['seasons']['2025']['state']=='not_attempted_after_network_failure'


def test_cli_full_synthetic_schedule_and_all_season_rows(tmp_path,monkeypatch,capsys):
    # Reuse the existing complete synthetic schedule factory, not a real raw dataset.
    from test_ingestion import source_rows
    games = source_rows.__wrapped__()
    schedule_path = tmp_path/'schedule.csv'
    schedule_path.write_bytes(encode(games))
    args = ['--schedule',str(schedule_path),'--output-dir',str(tmp_path/'out')]
    for year in (2024,2025,2026):
        records=[]
        for g in games:
            if g['season'] != str(year):
                continue
            for team,opponent in ((g['home_team'],g['away_team']),(g['away_team'],g['home_team'])):
                records.append(dict(season=g['season'],week=g['week'],season_type='REG' if g['game_type']=='REG' else 'POST',
                    game_id=g['game_id'],team=team,opponent_team=opponent,passing_yards='100',
                    sack_yards_lost='-5',rushing_yards='0'))
        path=tmp_path/f'stats_{year}.csv'; path.write_bytes(encode(records))
        args+=['--file',f'{year}={path}']
    # A real full schedule passes existing validation. No DB/environment settings are needed.
    assert cli.main(args)==2  # references and canonical UUID export deliberately absent
    report=json.loads(Path(json.loads(capsys.readouterr().out)['report']).read_text())
    assert report['schedule']['selected_games']==842
    for year in ('2024','2025'):
        result=report['seasons'][year]
        assert result['rows_read']==570
        assert result['coverage']['REG']['paired_games']==272
        assert result['coverage']['POST']['paired_games']==13
        assert not result['errors']
    assert report['seasons']['2026']['rows_read']==544
    assert report['seasons']['2026']['coverage']['POST']['schedule_games']==0
    assert schedule_path.read_bytes()==encode(games)


@pytest.mark.parametrize('case',['truncated','oversize','encoding','redirect'])
def test_transport_failures_are_sanitized(monkeypatch,case):
    from ingestion.team_stats import source
    class Response:
        status=200
        url=source_url(2024)
        headers={'Content-Length':'5'}
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,n):
            data=self.data
            self.data=b''
            return data
        data=b'hi'
    response=Response()
    if case=='oversize': response.headers={'Content-Length':str(source.MAX_BYTES+1)}
    if case=='encoding': response.headers={'Content-Encoding':'gzip'}
    if case=='redirect': response.url='https://unapproved.invalid/private?secret=do-not-print'
    class Opener:
        def open(self,*args,**kwargs): return response
    monkeypatch.setattr(source,'build_opener',lambda *args:Opener())
    with pytest.raises(AcquisitionError) as exc:
        source.fetch(source_url(2024))
    assert 'secret' not in str(exc.value)
    assert str(exc.value) in ('truncated_download','invalid_content_length','unexpected_response','unapproved_url')


def test_reference_manifest_refuses_unapproved_url_and_duplicate(sample):
    refs=deepcopy(sample[2]); refs[0]['source_url']='https://unapproved.invalid/game.pdf'
    with pytest.raises(ValueError): reference_list(dict(version=1,references=refs))
    with pytest.raises(ValueError): reference_list(dict(version=1,references=sample[2]*2))


def test_sack_count_conflict_does_not_accept_pair(sample):
    sample[1][0]['sacks_suffered']='0'
    result=run(sample)
    assert 'sack_count_yards_conflict' in codes(result)
    assert result['matched_games']==[]


def test_current_missing_scored_game_is_not_called_final(sample):
    games,rows,_,_=sample
    for g in games:
        g.update(season='2026',game_id='2026_01_BAL_KC')
    for r in rows:
        r.update(season='2026',game_id='2026_01_BAL_KC')
    result=audit(encode(rows[:1]),2026,games)
    assert result['coverage']['REG']['missing_reported_score_games']==['2026_01_BAL_KC']
    assert result['completion_evidence']['eligible_games_verified']==0


def test_cli_input_failure_still_saves_report(tmp_path,capsys):
    assert cli.main(['--schedule',str(tmp_path/'absent'),'--output-dir',str(tmp_path/'out'),'--download'])==3
    report=json.loads(Path(json.loads(capsys.readouterr().out)['report']).read_text())
    assert report['errors'][0]['code']=='invalid_input_or_manifest'


def test_publisher_size_mismatch_archives_as_failed(sample):
    data=encode(sample[1])
    raw=json.loads(publisher(data)); raw['assets'][0]['size']+=10
    _,receipt=acquire(2024,lambda url,**kw:json.dumps(raw).encode() if '/tags/' in url else data)
    assert 'publisher_size_mismatch' in receipt['acquisition_errors']
    assert receipt['integrity']=='failed'


def test_bad_metadata_after_download_retains_complete_bytes(sample):
    data=encode(sample[1]); count=0
    def get(url,**kw):
        nonlocal count
        if '/tags/' not in url: return data
        count+=1
        return publisher(data) if count==1 else b'not-json'
    body,receipt=acquire(2024,get)
    assert body==data
    assert receipt['metadata_recheck_error']=='invalid_publisher_metadata'
    assert receipt['integrity']=='failed'


def test_missing_schedule_scores_do_not_prevent_yardage_reference_validation(sample):
    sample[0][0]['home_score']=sample[0][0]['away_score']=''
    for row in sample[1]:
        row['points_scored']=row['points_allowed']=''
    result=run(sample)
    assert result['sack_convention']=='negative_validated_against_reviewed_reference'
    assert result['references'][0]['schedule_score_comparison']=='unavailable'
    assert result['matched_games'][0]['teams'][0]['reported_points_scored'] is None
    assert result['completion_evidence']['eligible_games_verified']==0


def test_cli_success_requires_references_and_canonical_export(tmp_path,sample,monkeypatch,capsys):
    all_games=[]; all_refs=[]; mapping=deepcopy(sample[3]); mapping['games']=[]
    schedule=tmp_path/'schedule.csv'; schedule.write_bytes(b'synthetic')
    args=['--schedule',str(schedule),'--output-dir',str(tmp_path/'out')]
    for year in (2024,2025,2026):
        game=deepcopy(sample[0][0]); gid=f'{year}_01_BAL_KC'
        game.update(season=str(year),game_id=gid); all_games.append(game)
        records=deepcopy(sample[1])
        for r in records: r.update(season=str(year),game_id=gid)
        p=tmp_path/f'{year}.csv'; p.write_bytes(encode(records)); args+=['--file',f'{year}={p}']
        ref=deepcopy(sample[2][0]); ref.update(season=year,game_id=gid); all_refs.append(ref)
        identity=deepcopy(sample[3]['games'][0]); identity.update(id=str(uuid4()),source_game_id=gid)
        mapping['games'].append(identity)
    monkeypatch.setattr(cli,'validate_bytes',lambda _:SimpleNamespace(rows=[SimpleNamespace(raw=r) for r in all_games],sha256='x'))
    ids=tmp_path/'identities.json'; ids.write_text(json.dumps(mapping))
    refs=tmp_path/'references.json'; refs.write_text(json.dumps(dict(version=1,references=all_refs)))
    assert cli.main(args+['--identity-map',str(ids),'--references',str(refs)])==0
    report=json.loads(Path(json.loads(capsys.readouterr().out)['report']).read_text())
    assert all(s['net_metrics_validated_games']==1 for s in report['seasons'].values())
    assert report['completion_eligibility']=='unverified'
    assert not report['rankings_published']
