"""Exact, bounded source-reference comparisons; never mutate scores/status or certify settlement."""
import hashlib
import json
import re
from decimal import Decimal

from app.schemas.markets import MarketReference, MarketSide, MarketsData, MarketsResponse
from app.services.schedule import GameNotFound, game_view

FIELDS = ('away_moneyline', 'home_moneyline', 'spread_line', 'away_spread_odds',
          'home_spread_odds', 'total_line', 'over_odds', 'under_odds')


def number(raw, field, warnings):
    value = raw.get(field)
    if value is None or isinstance(value, str) and value.strip().upper() in ('', 'NA', 'NAN', 'NULL'):
        return None
    # Original CSV cells are strings. Bound precision/size to preserve exact arithmetic and safe output.
    if not isinstance(value, str) or not re.fullmatch(r'[+-]?\d{1,7}(?:\.\d{1,6})?', value.strip()):
        warnings.append('invalid_' + field)
        return None
    result = Decimal(value.strip())
    if abs(result) > 1000000 or (field == 'total_line' and result < 0) or (field not in ('spread_line', 'total_line') and result == 0):
        warnings.append('invalid_' + field)
        return None
    return result


def compare(delta):
    return 'WIN' if delta > 0 else 'LOSS' if delta < 0 else 'PUSH'


def reference_sides(raw, away_score, home_score):
    warnings = []
    values = {field: number(raw, field, warnings) for field in FIELDS}
    available_scores = (type(away_score) is int and type(home_score) is int and away_score >= 0 and home_score >= 0)
    rows = []
    for side, own, other, price_key, spread_key in (
        ('AWAY', away_score, home_score, 'away_moneyline', 'away_spread_odds'),
        ('HOME', home_score, away_score, 'home_moneyline', 'home_spread_odds'),
    ):
        line = values['spread_line']
        if line is not None and side == 'HOME':
            line = -line
        for market, point, price in (('MONEYLINE', None, values[price_key]), ('SPREAD', line, values[spread_key])):
            result, reason = 'UNDETERMINED', 'market_value_unavailable'
            if (market == 'MONEYLINE' and price is not None) or (market == 'SPREAD' and point is not None):
                if not available_scores:
                    reason = 'scores_unavailable'
                elif market == 'MONEYLINE' and own == other:
                    reason = 'moneyline_tie_rules_unknown'
                else:
                    result = compare(Decimal(own) - Decimal(other) + (point if market == 'SPREAD' else Decimal(0)))
                    reason = 'provisional_source_reference_comparison'
            rows.append(MarketSide(market=market, side=side, line=point, price=price, result=result, reason=reason))
    for side, key in (('OVER', 'over_odds'), ('UNDER', 'under_odds')):
        line = values['total_line']
        result, reason = 'UNDETERMINED', 'market_value_unavailable'
        if line is not None:
            if not available_scores:
                reason = 'scores_unavailable'
            else:
                delta = Decimal(away_score) + Decimal(home_score) - line
                result, reason = compare(delta if side == 'OVER' else -delta), 'provisional_source_reference_comparison'
        rows.append(MarketSide(market='TOTAL', side=side, line=line, price=values[key], result=result, reason=reason))
    return rows, warnings


class MarketsService:
    def __init__(self, repository):
        self.repository = repository

    def game(self, game_id):
        game = self.repository.game(game_id)
        if game is None:
            raise GameNotFound()
        view = game_view(game)
        response = MarketsResponse(data=MarketsData(game=view, references=[]))
        raw = game.raw_source_record
        if not isinstance(raw, dict):
            response.data.unavailable_reason = 'source_record_unavailable'
            return response
        expected = dict(game_id=game.source_game_id, away_team=game.source_away_team,
                        home_team=game.source_home_team, season=str(game.season))
        digest = hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        if any(raw.get(key) != value for key, value in expected.items()) or digest != game.source_record_sha256:
            response.data.unavailable_reason = 'source_record_identity_or_hash_mismatch'
            return response
        sides, warnings = reference_sides(raw, game.reported_away_score, game.reported_home_score)
        source = game.source_artifact
        response.data.references = [MarketReference(
            snapshot_id=f'{source.id}:{game.source_record_sha256}', artifact_id=source.id,
            artifact_sha256=source.sha256, source_record_sha256=game.source_record_sha256,
            artifact_retrieved_at=source.retrieved_at, artifact_recorded_at=source.recorded_at,
            origin_status=source.origin_status, source_url=source.documented_source_url,
            license_url=source.license_url, attribution=source.attribution, sides=sides, warnings=warnings)]
        if all(row.line is None and row.price is None for row in sides):
            response.data.unavailable_reason = 'market_values_unavailable'
        return response
