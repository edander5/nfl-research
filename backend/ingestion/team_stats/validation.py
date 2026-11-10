"""Pure artifact/identity validation. No finality inference and no database imports."""
import csv
import hashlib
import io
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
from uuid import UUID

from ingestion.validation import TEAM_CODES

REQUIRED = {'season', 'week', 'season_type', 'team', 'opponent_team',
            'passing_yards', 'sack_yards_lost', 'rushing_yards'}
METRICS = ('passing_yards', 'sack_yards_lost', 'rushing_yards')
OPTIONAL_NUMBERS = ('sacks_suffered', 'points_scored', 'points_allowed')
NULLS = {'', 'NA', 'NULL'}


def number(token):
    if token in NULLS:
        return None
    if not re.fullmatch(r'-?\d+(?:\.\d+)?', token):
        raise ValueError('invalid_numeric_token')
    value = Decimal(token)
    if value != value.to_integral_value() or not -(2**31) <= value < 2**31:
        raise ValueError('nonintegral_or_out_of_range')
    return int(value)


def aware_time(value):
    if not isinstance(value, str) or 'T' not in value or not re.search(r'(Z|[+-]\d{2}:\d{2})$', value):
        raise ValueError('timezone_required')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() is None:
        raise ValueError('timezone_required')
    return parsed.astimezone(timezone.utc)


def canonical_map(raw, schedule):
    """Validate a declared read-only PostgreSQL identity export; never synthesize UUIDs."""
    if not isinstance(raw, dict) or type(raw.get('version')) is not int or raw['version'] != 1:
        raise ValueError('invalid_identity_export')
    teams, aliases, games, used = {}, {}, {}, set()
    for row in raw['teams']:
        uid, code = str(UUID(row['id'])), row['code']
        if code not in TEAM_CODES or code in teams or uid in used:
            raise ValueError('ambiguous_team_identity')
        teams[code] = uid
        used.add(uid)
    for row in raw['aliases']:
        if row['provider'] != 'nflverse':
            continue
        code, uid = row['source_team_code'], str(UUID(row['team_id']))
        if code in aliases or uid not in used or not re.fullmatch(r'[A-Z]{2,3}', code):
            raise ValueError('ambiguous_alias')
        if code in teams and teams[code] != uid:
            raise ValueError('conflicting_alias')
        aliases[code] = uid
    by_source = {r['game_id']: r for r in schedule}
    game_ids = set()
    for row in raw['games']:
        key, uid = row['source_game_id'], str(UUID(row['id']))
        if key in games or uid in game_ids:
            raise ValueError('ambiguous_game_identity')
        home, away = str(UUID(row['home_team_id'])), str(UUID(row['away_team_id']))
        if home == away or home not in used or away not in used:
            raise ValueError('invalid_game_sides')
        if key in by_source:
            source = by_source[key]
            if (aliases.get(source['home_team']) != home or aliases.get(source['away_team']) != away
                    or teams.get(source['home_team']) != home or teams.get(source['away_team']) != away):
                raise ValueError('identity_export_schedule_drift')
        games[key] = {'id': uid, 'home_team_id': home, 'away_team_id': away}
        game_ids.add(uid)
    return {'teams': teams, 'aliases': aliases, 'games': games}


def reference_list(raw):
    if not isinstance(raw, dict) or type(raw.get('version')) is not int or raw['version'] != 1:
        raise ValueError('invalid_reference_manifest')
    refs, keys = [], set()
    for r in raw['references']:
        if not isinstance(r, dict):
            raise ValueError('invalid_reference')
        key = (r['season'], r['game_id'], r['team'])
        if (type(r['season']) is not int or r['season'] not in (2024, 2025, 2026) or key in keys
                or r['team'] not in TEAM_CODES or not isinstance(r['game_id'], str)):
            raise ValueError('invalid_reference_identity')
        url = urlsplit(r['source_url'])
        if (url.scheme != 'https' or url.hostname not in {'static.www.nfl.com', 'www.nfl.com', 'media.nfl.com'}
                or url.username or url.password or url.query or url.fragment
                or not isinstance(r['locator'], str) or not r['locator'].strip()
                or r['use'] != 'reference_only'):
            raise ValueError('invalid_reference_source')
        if aware_time(r['reviewed_at']) > datetime.now(timezone.utc):
            raise ValueError('future_reference_review')
        for name in ('gross_passing_yards', 'net_passing_yards', 'rushing_yards', 'points_scored', 'points_allowed'):
            if type(r[name]) is not int or not -(2**31) <= r[name] < 2**31:
                raise ValueError('invalid_reference_number')
        if r['points_scored'] < 0 or r['points_allowed'] < 0 or r['net_passing_yards'] > r['gross_passing_yards']:
            raise ValueError('invalid_reference_totals')
        keys.add(key)
        refs.append(r)
    return refs


def audit(data, season, schedule, canonical=None, references=()):
    problems, warnings, parsed = [], [], []
    def issue(code, line=None, field=None):
        problems.append(dict(code=code, line=line, field=field))
    result = dict(season=season, sha256=hashlib.sha256(data).hexdigest(), byte_size=len(data),
                  rows_read=0, headers=[], columns={}, errors=problems, warnings=warnings,
                  matched_games=[], references=[], sack_convention='unverified',
                  completion_evidence={'supported_by_weekly_stats': False, 'eligible_games_verified': 0,
                                       'reason': 'No authoritative completion timestamp or final indicator validated; no ranking eligibility inferred.'})
    try:
        reader = csv.reader(io.StringIO(data.decode('utf-8-sig'), newline=''), strict=True)
        header = next(reader)
        if (len(header) != len(set(header)) or not REQUIRED <= set(header)
                or any(not h or h.strip() != h for h in header)):
            issue('invalid_headers')
            return result
        result['headers'] = header
        counts = {h: Counter() for h in header}
        seen_records = set()
        for values in reader:
            line = reader.line_num
            result['rows_read'] += 1
            if len(values) != len(header):
                issue('row_width', line)
                continue
            record = tuple(values)
            if record in seen_records:
                issue('duplicate_record', line)
            seen_records.add(record)
            raw = dict(zip(header, values))
            for k, token in raw.items():
                if token in NULLS:
                    counts[k]['null'] += 1
                else:
                    try:
                        number(token)
                        counts[k]['integral_numeric'] += 1
                    except (ValueError, InvalidOperation):
                        counts[k]['text_or_other_numeric'] += 1
            try:
                if any(v != v.strip() for v in values):
                    raise ValueError()
                year, week = number(raw['season']), number(raw['week'])
                stage, team, opponent = raw['season_type'], raw['team'], raw['opponent_team']
                if (year != season or stage not in ('REG', 'POST') or week is None
                        or not (1 <= week <= 18 if stage == 'REG' else 19 <= week <= 22)
                        or not team or not opponent or team == opponent):
                    raise ValueError()
                nums = {k: number(raw[k]) for k in (*METRICS, *OPTIONAL_NUMBERS) if k in raw}
                if any(nums[k] is None for k in METRICS):
                    issue('missing_metric', line)
                if any(nums.get(k) is not None and nums[k] < 0 for k in OPTIONAL_NUMBERS):
                    raise ValueError()
                if nums.get('sacks_suffered') == 0 and nums['sack_yards_lost'] not in (None, 0):
                    issue('sack_count_yards_conflict', line)
                parsed.append(dict(line=line, raw=raw, year=year, week=week, stage=stage,
                                   team=team, opponent=opponent, nums=nums))
            except (ValueError, InvalidOperation):
                issue('invalid_value', line)
        result['columns'] = {h: dict(counts[h]) for h in header}
    except (UnicodeError, csv.Error, StopIteration):
        issue('invalid_csv')
        return result
    if not parsed:
        issue('empty_or_no_valid_records')

    # Alias mapping is accepted only from the explicit export, never hardcoded LAR/JAC substitutions.
    team_by_uuid = {v: k for k, v in canonical['teams'].items()} if canonical else {}
    def code(source):
        if canonical:
            uid = canonical['aliases'].get(source)
            if uid not in team_by_uuid:
                raise ValueError()
            return team_by_uuid[uid]
        if source not in TEAM_CODES:
            raise ValueError()
        return source

    games = {r['game_id']: r for r in schedule if int(r['season']) == season}
    candidates = defaultdict(list)
    for g in games.values():
        stage = 'REG' if g['game_type'] == 'REG' else 'POST'
        for side, other in ((g['home_team'], g['away_team']), (g['away_team'], g['home_team'])):
            candidates[(int(g['week']), stage, side, other)].append(g['game_id'])
    grouped, key_counts = defaultdict(list), Counter()
    for row in parsed:
        try:
            team, opponent = code(row['team']), code(row['opponent'])
        except ValueError:
            issue('unknown_or_unmapped_alias', row['line'])
            continue
        row['code'], row['opponent_code'] = team, opponent
        matches = candidates[(row['week'], row['stage'], team, opponent)]
        if len(matches) != 1:
            issue('missing_or_ambiguous_schedule_match', row['line'])
            continue
        gid = matches[0]
        if 'game_id' in row['raw'] and row['raw']['game_id'] != gid:
            issue('source_game_id_mismatch', row['line'], 'game_id')
            continue
        if canonical and gid not in canonical['games']:
            issue('canonical_game_missing', row['line'])
            continue
        row['game_id'] = gid
        key_counts[(gid, team)] += 1
        grouped[gid].append(row)
    pairs = {}
    for gid, rows in grouped.items():
        if len(rows) != 2 or len({r['code'] for r in rows}) != 2:
            issue('missing_or_duplicate_game_side', field=gid)
            continue
        if any(key_counts[(gid, r['code'])] != 1 for r in rows):
            issue('duplicate_game_team', field=gid)
            continue
        if any(any(r['nums'][k] is None for k in METRICS) for r in rows):
            continue
        pairs[gid] = rows

    # No formula is enabled just by observing positive/negative values or a CLI flag.
    signs = Counter('negative' if r['nums']['sack_yards_lost'] < 0 else 'positive' if r['nums']['sack_yards_lost'] > 0 else 'zero'
                    for r in parsed if r['nums']['sack_yards_lost'] is not None)
    result['sack_sign_counts'] = dict(signs)
    anchor_signs = set()
    references_failed = False
    for ref in references:
        if ref['season'] != season:
            continue
        rows = pairs.get(ref['game_id'], [])
        match = next((r for r in rows if r['code'] == ref['team']), None)
        observation = {'game_id': ref['game_id'], 'team': ref['team'], 'source_url': ref['source_url'],
                       'locator': ref['locator'], 'reviewed_at': ref['reviewed_at'],
                       'authentication': 'operator_supplied_reference_not_independently_authenticated'}
        if match is None:
            observation['state'] = 'unmatched'
            issue('reference_unmatched', field=ref['game_id'])
            references_failed = True
        else:
            n = match['nums']
            g = games[ref['game_id']]
            home = ref['team'] == g['home_team']
            own, opp = (g['home_score'], g['away_score']) if home else (g['away_score'], g['home_score'])
            delta = ref['net_passing_yards'] - ref['gross_passing_yards']
            sack = n['sack_yards_lost']
            score_conflict = any(token not in NULLS and int(token) != expected
                                 for token, expected in ((own, ref['points_scored']), (opp, ref['points_allowed'])))
            observation['schedule_score_comparison'] = ('unavailable' if own in NULLS or opp in NULLS
                                                        else 'mismatch' if score_conflict else 'matched')
            equal = (n['passing_yards'] == ref['gross_passing_yards']
                     and n['rushing_yards'] == ref['rushing_yards'] and not score_conflict)
            if not equal or (sack != delta and -sack != delta):
                observation['state'] = 'mismatch'
                issue('reference_totals_mismatch', match['line'])
                references_failed = True
            else:
                observation['state'] = 'matched'
                if delta < 0:
                    anchor_signs.add('negative' if sack == delta else 'positive')
        result['references'].append(observation)
    if signs['negative'] and signs['positive']:
        issue('mixed_sack_signs')
    elif len(anchor_signs) == 1 and not references_failed:
        convention = next(iter(anchor_signs))
        if (convention == 'negative' and not signs['positive']) or (convention == 'positive' and not signs['negative']):
            result['sack_convention'] = convention + '_validated_against_reviewed_reference'
    if result['sack_convention'] == 'unverified':
        warnings.append('Sack convention unverified for this artifact; all net passing/allowed values remain null.')

    bad_lines = {p['line'] for p in problems if p['line'] is not None}
    for gid, rows in sorted(pairs.items()):
        if any(r['line'] in bad_lines for r in rows):
            continue
        details = []
        for row in sorted(rows, key=lambda r: r['code']):
            opponent = next(r for r in rows if r is not row)
            n, o = row['nums'], opponent['nums']
            def net(values):
                if result['sack_convention'].startswith('negative_'):
                    return values['passing_yards'] + values['sack_yards_lost']
                if result['sack_convention'].startswith('positive_'):
                    return values['passing_yards'] - values['sack_yards_lost']
                return None
            g = games[gid]
            home = row['code'] == g['home_team']
            own, opp = (g['home_score'], g['away_score']) if home else (g['away_score'], g['home_score'])
            own_score, opp_score = number(own), number(opp)
            for k, expected in (('points_scored', own_score), ('points_allowed', opp_score)):
                if n.get(k) is not None:
                    if expected is None:
                        warnings.append(f"Schedule score unavailable for source line {row['line']} field {k}; not a conflicting score.")
                    elif n[k] != expected:
                        issue('reported_score_mismatch', row['line'], k)
            details.append(dict(team=row['code'], source_team=row['team'], opponent=opponent['code'],
                                canonical_team_id=canonical['teams'][row['code']] if canonical else None,
                                source_line=row['line'], gross_passing_yards=n['passing_yards'],
                                original_sack_yards=n['sack_yards_lost'], net_passing_yards=net(n),
                                rushing_yards=n['rushing_yards'], passing_yards_allowed=net(o),
                                rushing_yards_allowed=o['rushing_yards'], reported_points_scored=own_score,
                                reported_points_allowed=opp_score, source_points_scored=n.get('points_scored'),
                                source_points_allowed=n.get('points_allowed'), points_source='schedule_reported_not_independent',
                                status='UNKNOWN', completed_before_cutoff='unverified'))
        if not any(p['line'] in {r['line'] for r in rows} for p in problems):
            result['matched_games'].append(dict(source_game_id=gid,
                canonical_game_id=canonical['games'][gid]['id'] if canonical else None, teams=details))

    accepted = {g['source_game_id'] for g in result['matched_games']}
    result['coverage'] = {}
    for stage in ('REG', 'POST'):
        expected = {gid for gid, g in games.items() if ('REG' if g['game_type'] == 'REG' else 'POST') == stage}
        found = accepted & expected
        scored = {gid for gid in expected if games[gid]['home_score'] not in NULLS and games[gid]['away_score'] not in NULLS}
        missing = sorted(expected - found)
        if season < 2026 and missing:
            issue('historical_coverage_missing', field=stage)
        result['coverage'][stage] = dict(schedule_games=len(expected), paired_games=len(found),
            observed_team_rows=sum(r['stage'] == stage for r in parsed),
            weeks=dict(sorted(Counter(str(r['week']) for r in parsed if r['stage'] == stage).items(), key=lambda x: int(x[0]))),
            missing_schedule_games=missing, missing_reported_score_games=sorted(scored-found),
            note='Missing scheduled games are not certified completed or due; scored games are not finality evidence.')
    result['source_identity_paired_games'] = len(accepted)
    result['canonical_identity_paired_games'] = len(accepted) if canonical else None
    result['net_metrics_validated_games'] = len(accepted) if result['sack_convention'] != 'unverified' and not problems else 0
    result['structural_integrity_passed'] = not problems
    return result
