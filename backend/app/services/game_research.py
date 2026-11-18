"""Original read-only full-game research over the shared accepted history sample."""
from decimal import Decimal

from app.schemas.game_research import (GameResearchResponse, GameTotalResearch, GameTotalSummary,
    GameTotalObservation, GameResearchMeta, HistoricalTotalReference, ReferenceTotalProvenance)
from app.services.markets import compare, number, source_record_error
from app.services.team_stats import TeamStatsService, validate_matchup, view


def total_outcome(points, line):
    if points is None or line is None:
        return 'UNDETERMINED'
    return {'WIN': 'OVER', 'LOSS': 'UNDER', 'PUSH': 'PUSH'}[compare(Decimal(points)-line)]


def reference_total(row, points):
    expected = dict(game_id=row['reference_source_game_id'], away_team=row['reference_away_team'],
                    home_team=row['reference_home_team'], season=str(row['reference_season']))
    problem = source_record_error(row['reference_raw_record'], expected, row['reference_record_sha256'])
    if problem:
        return HistoricalTotalReference(unavailable_reason=problem)
    warnings = []
    line = number(row['reference_raw_record'], 'total_line', warnings)
    provenance = ReferenceTotalProvenance(artifact_id=row['reference_artifact_id'],
        artifact_sha256=row['reference_artifact_sha256'], source_record_sha256=row['reference_record_sha256'],
        artifact_retrieved_at=row['reference_retrieved_at'], artifact_recorded_at=row['reference_recorded_at'],
        origin_status=row['reference_origin_status'], source_url=row['reference_source_url'],
        license_url=row['reference_license_url'], attribution=row['reference_attribution'])
    return HistoricalTotalReference(line=line, outcome=total_outcome(points, line), provenance=provenance,
        warnings=warnings, unavailable_reason=('invalid_total_line' if warnings else 'total_line_unavailable') if line is None else None)


class GameResearchService(TeamStatsService):
    def research(self, team_id, filters):
        team = self.require_team(team_id)
        meta, rows = self.repository.research(team_id, filters)
        validate_matchup(meta, team_id, filters)
        reason = None
        if meta['matchup_scheduled_kickoff_utc'] is None:
            reason = 'matchup_kickoff_unknown'
        elif filters.window == 'H2H' and meta['matchup_opponent_id'] is None:
            reason = 'opponent_identity_unknown'
        elif not rows:
            reason = 'no_h2h_games' if filters.window == 'H2H' else 'no_eligible_games'
        observations = []
        for row in rows:
            record = view(row)
            own, other = record.reported_points_scored, record.reported_points_allowed
            points = own+other if own is not None and other is not None else None
            observations.append(GameTotalObservation(**record.model_dump(), combined_points=points,
                scores_available=points is not None, outcome=total_outcome(points, filters.line),
                outcome_unavailable_reason=('scores_unavailable' if points is None else
                                            'threshold_required' if filters.line is None else None),
                reference_total=reference_total(row, points)))
        count = len(observations)
        values = [game.combined_points for game in observations if game.scores_available]
        usable = len(values)
        counts = {side: sum(game.outcome == side for game in observations) for side in ('OVER', 'UNDER', 'PUSH')}
        threshold = filters.line is not None
        numerator = counts[filters.side] if threshold else None
        reference_count = sum(game.reference_total.line is not None for game in observations)
        complete = filters.game_limit is None or count == filters.game_limit
        unavailable = reason in ('matchup_kickoff_unknown', 'opponent_identity_unknown')
        availability = ('UNAVAILABLE' if unavailable else 'EMPTY' if count == 0 else
                        'PARTIAL' if not complete or usable < count or reference_count < count else 'AVAILABLE')
        summary = GameTotalSummary(eligible_game_count=count, games_with_usable_scores=usable,
            games_without_usable_scores=count-usable, average_combined_points=sum(values)/usable if usable else None,
            over_count=counts['OVER'] if threshold else None, under_count=counts['UNDER'] if threshold else None,
            push_count=counts['PUSH'] if threshold else None, hit_rate=numerator/usable if threshold and usable else None,
            hit_rate_numerator=numerator, hit_rate_denominator=usable if threshold else None,
            outcomes_unavailable_reason='threshold_required' if not threshold else 'no_usable_scores' if not usable else None)
        return GameResearchResponse(data=GameTotalResearch(team=team, season=filters.season,
            season_type=filters.season_type, matchup_id=filters.matchup_id, opponent_id=meta['matchup_opponent_id'],
            window=filters.window, requested_game_count=filters.game_limit, line=filters.line,
            threshold_origin='MANUAL' if threshold else None, side=filters.side, availability=availability,
            observations=observations, summary=summary), meta=GameResearchMeta(
                cutoff_utc=meta['matchup_scheduled_kickoff_utc'], unavailable_reason=reason,
                available_eligible_games=meta['eligible_count'], accepted_games_in_scope=meta['accepted_count'],
                excluded_unknown_kickoff_games=meta['unknown_kickoff_count'],
                excluded_at_or_after_matchup_games=(meta['accepted_count']-meta['unknown_kickoff_count']-meta['eligible_count']
                                                    if not unavailable else 0),
                scheduled_games_in_scope=meta['scheduled_count'],
                scheduled_games_without_accepted_statistics=meta['scheduled_count']-meta['eligible_count'],
                selected_unknown_status_games=sum(game.status == 'UNKNOWN' for game in observations),
                selected_unverified_score_games=sum(game.score_finality != 'CONFIRMED_FINAL' for game in observations),
                games_with_reference_total=reference_count, games_without_reference_total=count-reference_count,
                window_complete=complete and count > 0, scores_complete=count > 0 and usable == count,
                references_complete=count > 0 and reference_count == count))
