"""Exact-ratio competition rankings over SQL-aggregated accepted statistics."""
from fractions import Fraction
from app.repositories.team_rankings import CATEGORIES
from app.schemas.team_rankings import RankedTeam, CategoryRankings, RankingsMeta, TeamRankingsResponse
from app.services.team_stats import TeamNotFound


def rank_category(rows, category):
    direction = CATEGORIES[category][1]
    eligible, unranked = [], []
    for row in rows:
        count = row[category+'_count'] or 0
        total = row[category+'_total']
        item = RankedTeam(team=dict(id=row['team_id'],code=row['code'],name=row['name']),
            rank=None, eligible=count>0, average=None,
            total_yards=total if count else None, games_with_values=count,
            games_with_accepted_statistics=row['accepted_count'], scheduled_games=row['scheduled_games'],
            missing_statistics_games=row['scheduled_games']-row['accepted_count'],
            missing_metric_games=row['accepted_count']-count)
        if count:
            eligible.append((Fraction(total,count),item))
        else:
            unranked.append(item)
    eligible.sort(key=lambda pair: (pair[0] if direction=='ascending' else -pair[0],
                                    pair[1].team.code, str(pair[1].team.id)))
    previous = None
    rank = 0
    for position,(ratio,item) in enumerate(eligible,1):
        if ratio != previous:
            rank = position
        item.rank = rank
        previous = ratio
    # Display conversion happens only after all exact sorting and tie comparisons.
    for ratio, item in eligible:
        item.average = float(ratio)
    unranked.sort(key=lambda item:(item.team.code,str(item.team.id)))
    return CategoryRankings(category=category,direction=direction,eligible_team_count=len(eligible),
                            teams=[item for _,item in eligible]+unranked)


class TeamRankingsService:
    def __init__(self, repository):
        self.repository = repository

    def rankings(self, filters):
        rows = self.repository.league(filters)
        if filters.team_id is not None and not any(row['team_id']==filters.team_id for row in rows):
            raise TeamNotFound()
        categories = [filters.category] if filters.category else list(CATEGORIES)
        data = [rank_category(rows,category) for category in categories]
        # Never reduce the rank population before calculating positions/ties.
        if filters.team_id is not None:
            for category in data:
                category.teams = [team for team in category.teams if team.team.id==filters.team_id]
        scheduled=sum(row['scheduled_games'] for row in rows)//2
        accepted=sum(row['accepted_count'] for row in rows)//2
        missing={category:sum(row['accepted_count']-(row[category+'_count'] or 0) for row in rows)
                 for category in CATEGORIES}
        return TeamRankingsResponse(data=data,meta=RankingsMeta(filters=filters,league_team_count=len(rows),
            scheduled_games=scheduled,accepted_games=accepted,missing_statistics_games=scheduled-accepted,
            unknown_status_accepted_games=sum(row['unknown_count'] for row in rows)//2,
            unverified_origin_team_games=sum(row['unverified_count'] for row in rows),
            missing_metric_team_games=missing,
            coverage_complete_for_stored_schedule=(scheduled>0 and scheduled==accepted and not any(missing.values()))))
