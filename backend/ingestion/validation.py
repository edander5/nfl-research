"""Pure validation of a complete schedule snapshot. No database/network writes."""
import csv
import hashlib
import io
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SEASONS = (2024, 2025, 2026)
TEAM_CODES = tuple("ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LA LAC LV MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS".split())
REQUIRED = {"game_id", "season", "game_type", "week", "gameday", "gametime", "home_team", "away_team", "home_score", "away_score"}
ROUNDS = {"WC": (19, 6), "DIV": (20, 4), "CON": (21, 2), "SB": (22, 1)}
EXTERNAL_IDS = ("gsis", "nfl_detail_id", "pfr", "pff", "espn", "ftn")


@dataclass(frozen=True)
class Problem:
    code: str
    line: int | None
    field: str
    message: str


class ValidationFailure(ValueError):
    def __init__(self, problems: list[Problem]):
        self.problems = problems
        super().__init__(f"Schedule rejected: {len(problems)} validation problem(s)")


@dataclass(frozen=True)
class ScheduleRow:
    line: int
    raw: dict[str, str]
    sha256: str
    values: dict


@dataclass(frozen=True)
class Snapshot:
    data: bytes
    sha256: str
    rows_read: int
    rows: tuple[ScheduleRow, ...]
    warnings: tuple[str, ...]

    def score_counts(self) -> dict:
        return {str(y): dict(paired=sum(r.values['reported_home_score'] is not None for r in self.rows if r.values['season'] == y),
                             missing=sum(r.values['reported_home_score'] is None for r in self.rows if r.values['season'] == y)) for y in SEASONS}

    def counts(self) -> dict:
        return {str(y): dict(sorted(Counter(r.raw['game_type'] for r in self.rows if r.values['season'] == y).items())) for y in SEASONS}


def missing(value: str) -> bool:
    return value.strip() in ("", "NA", "NULL")


def integer(value: str, *, signed=False) -> int:
    if not re.fullmatch(r"-?(0|[1-9][0-9]*)" if signed else r"0|[1-9][0-9]*", value):
        raise ValueError("Expected an integer token")
    return int(value)


def record_hash(raw: dict) -> str:
    return hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def parse_row(raw: dict, line: int) -> ScheduleRow:
    def required(name):
        if missing(raw[name]):
            raise ValueError(f"Required field missing: {name}")
        return raw[name]

    if any(v and v != v.strip() for v in raw.values()):
        raise ValueError("Noncanonical surrounding whitespace")
    season, week = integer(required('season')), integer(required('week'))
    home, away = required('home_team'), required('away_team')
    if home not in TEAM_CODES or away not in TEAM_CODES or home == away:
        raise ValueError("Unknown or identical team codes")
    game_type = required('game_type')
    if not ((game_type == 'REG' and 1 <= week <= 18) or (game_type in ROUNDS and week == ROUNDS[game_type][0])):
        raise ValueError("Invalid stage/round/week combination")
    if required('game_id') != f'{season}_{week:02d}_{away}_{home}':
        raise ValueError("game_id does not match season/week/away/home")
    gameday = None if missing(raw['gameday']) or raw['gameday'] == 'TBD' else date.fromisoformat(raw['gameday'])
    if gameday and (gameday.isoformat() != raw['gameday'] or gameday.year not in (season, season + 1)):
        raise ValueError("Invalid season/date relationship")
    if gameday and raw.get('weekday') and not missing(raw['weekday']) and gameday.strftime('%A') != raw['weekday']:
        raise ValueError("Weekday/date disagreement")
    gametime = None
    if not missing(raw['gametime']) and raw['gametime'] != 'TBD':
        if not re.fullmatch(r'\d{2}:\d{2}', raw['gametime']):
            raise ValueError("Expected HH:MM time or unknown")
        gametime = time.fromisoformat(raw['gametime'])
    kickoff = None
    if gameday and gametime:
        local = datetime.combine(gameday, gametime)
        zone = ZoneInfo('America/New_York')
        aware = local.replace(tzinfo=zone)
        if aware.utcoffset() != local.replace(tzinfo=zone, fold=1).utcoffset():
            raise ValueError("Ambiguous or nonexistent Eastern kickoff")
        kickoff = aware.astimezone(timezone.utc)
        if kickoff.astimezone(zone).replace(tzinfo=None) != local:
            raise ValueError("Nonexistent Eastern kickoff")
    scores = [None if missing(raw[k]) else integer(raw[k]) for k in ('home_score', 'away_score')]
    if any(score is not None and score > 2147483647 for score in scores):
        raise ValueError('Score exceeds PostgreSQL integer range')
    if (scores[0] is None) != (scores[1] is None):
        raise ValueError("One-sided missing score")
    for name, expected in [('result', None if scores[0] is None else scores[0] - scores[1]), ('total', None if scores[0] is None else sum(scores))]:
        if name in raw and not missing(raw[name]):
            if expected is None or integer(raw[name], signed=True) != expected:
                raise ValueError("Score arithmetic disagreement")
    location = raw.get('location', '')
    if not missing(location) and location not in ('Home', 'Neutral'):
        raise ValueError("Unknown location code")
    overtime = raw.get('overtime', '')
    if not missing(overtime) and overtime not in ('0', '1'):
        raise ValueError("Invalid overtime flag")
    values = dict(
        source_game_id=raw['game_id'], season=season, week=week,
        season_type='REG' if game_type == 'REG' else 'POST', game_type=game_type,
        source_home_team=home, source_away_team=away,
        source_gameday=gameday, source_gametime=gametime,
        source_timezone='America/New_York', scheduled_kickoff_utc=kickoff,
        reported_home_score=scores[0], reported_away_score=scores[1],
        neutral_site=None if missing(location) else location == 'Neutral',
        overtime=None if missing(overtime) else overtime == '1',
        old_game_id=None if missing(raw.get('old_game_id', '')) else raw['old_game_id'],
        external_ids={k: raw[k] for k in EXTERNAL_IDS if k in raw and not missing(raw[k])} or None,
    )
    return ScheduleRow(line, raw, record_hash(raw), values)


def validate_bytes(data: bytes) -> Snapshot:
    problems, selected, seen = [], [], set()
    try:
        reader = csv.reader(io.StringIO(data.decode('utf-8-sig'), newline=''), strict=True)
        header = next(reader)
        if len(set(header)) != len(header) or not REQUIRED <= set(header):
            raise ValidationFailure([Problem('header', 1, 'header', 'Missing required or duplicate column names')])
        count = 0
        while True:
            line = reader.line_num + 1
            try:
                cells = next(reader)
            except StopIteration:
                break
            count += 1
            if len(cells) != len(header):
                problems.append(Problem('row_width', line, 'record', 'Row width differs from header'))
                continue
            raw = dict(zip(header, cells))
            if missing(raw['game_id']) or raw['game_id'] in seen:
                problems.append(Problem('duplicate_or_missing_id', line, 'game_id', 'Missing or repeated primary source ID'))
            seen.add(raw['game_id'])
            try:
                season = integer(raw['season'])
                if season in SEASONS:
                    selected.append(parse_row(raw, line))
            except (ValueError, OverflowError):
                # No untrusted raw values or credential-bearing data in diagnostics.
                problems.append(Problem('invalid_row', line, 'record', 'Invalid required identity, time, stage, team or score; inspect this source line locally'))
    except ValidationFailure:
        raise
    except (UnicodeError, csv.Error, StopIteration):
        raise ValidationFailure([Problem('csv', None, 'file', 'CSV is empty, malformed or not UTF-8')]) from None
    if problems:
        raise ValidationFailure(problems)
    warnings = []
    for year in SEASONS:
        rows = [r for r in selected if r.values['season'] == year]
        reg = [r for r in rows if r.values['game_type'] == 'REG']
        appearances = Counter(t for r in reg for t in (r.values['source_home_team'], r.values['source_away_team']))
        team_weeks = Counter((t, r.values['week']) for r in rows for t in (r.values['source_home_team'], r.values['source_away_team']))
        rounds = Counter(r.values['game_type'] for r in rows)
        if len(reg) != 272 or set(appearances) != set(TEAM_CODES) or set(appearances.values()) != {17} or {r.values['week'] for r in reg} != set(range(1, 19)) or any(n != 1 for n in team_weeks.values()):
            problems.append(Problem('incomplete_regular_season', None, str(year), 'Expected 272 REG games, 32 teams/17 games each, weeks 1–18 and no repeated team/week'))
        for round_name, (_, maximum) in ROUNDS.items():
            if rounds[round_name] > maximum or (year < 2026 and rounds[round_name] != maximum):
                problems.append(Problem('postseason_coverage', None, str(year), 'Historical POST must be 6/4/2/1; available 2026 rounds must not exceed those counts'))
        round_names = list(ROUNDS)
        if year == 2026:
            for index, name in enumerate(round_names):
                if rounds[name] and any(rounds[earlier] != ROUNDS[earlier][1] for earlier in round_names[:index]):
                    problems.append(Problem('postseason_progression', None, str(year), 'Later postseason rounds require complete preceding rounds'))
        if year < 2026 and any(r.values['reported_home_score'] is None for r in rows):
            problems.append(Problem('historical_scores_missing', None, str(year), 'Completed-season archive must retain paired reported scores'))
        if year == 2026 and not rounds['WC']:
            warnings.append('2026 postseason matchups absent; no games fabricated')
        for key in EXTERNAL_IDS:
            ids = Counter(r.raw[key] for r in rows if key in r.raw and not missing(r.raw[key]))
            if any(n > 1 for n in ids.values()):
                problems.append(Problem('ambiguous_external_id', None, key, 'Repeated non-null external game ID in a season'))
        legacy = Counter(r.values['old_game_id'] for r in rows if r.values['old_game_id'])
        if any(n > 1 for n in legacy.values()):
            warnings.append(f'{year}: {sum(n > 1 for n in legacy.values())} nonunique old_game_id values preserved; never used for matching')
    if problems:
        raise ValidationFailure(problems)
    warnings.append('Origin remains DECLARED; score presence and kickoff never establish FINAL')
    return Snapshot(data, hashlib.sha256(data).hexdigest(), count, tuple(selected), tuple(warnings))


def load_snapshot(path: Path) -> Snapshot:
    return validate_bytes(path.read_bytes())
