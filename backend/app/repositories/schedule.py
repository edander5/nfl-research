"""Read-only, provider-scoped queries; never commit, flush or trigger ingestion."""
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Game, SourceArtifact

PROVIDER = 'nflverse'


def game_query():
    return select(Game).where(Game.provider == PROVIDER).options(
        joinedload(Game.home_team), joinedload(Game.away_team), joinedload(Game.source_artifact),
    )


class ScheduleRepository:
    def __init__(self, session: Session):
        self.session = session

    def coverage(self, season: int | None = None):
        statement = select(
            Game.season, Game.season_type, Game.week, Game.game_type,
            func.count().label('game_count'),
            func.sum(case((Game.reported_home_score.is_not(None), 1), else_=0)).label('reported_score_pairs'),
            func.sum(case((Game.status == 'UNKNOWN', 1), else_=0)).label('unknown_status_games'),
            func.sum(case((Game.status == 'FINAL', 1), else_=0)).label('final_status_games'),
            func.sum(case((Game.scheduled_kickoff_utc.is_(None), 1), else_=0)).label('unknown_kickoff_games'),
            func.sum(case((SourceArtifact.origin_status != 'VERIFIED', 1), else_=0)).label('unverified_origin_games'),
        ).join(SourceArtifact, (Game.source_artifact_id == SourceArtifact.id) & (Game.provider == SourceArtifact.provider))
        statement = statement.where(Game.provider == PROVIDER)
        if season is not None:
            statement = statement.where(Game.season == season)
        return self.session.execute(statement.group_by(
            Game.season, Game.season_type, Game.week, Game.game_type,
        ).order_by(Game.season, Game.week, Game.game_type)).mappings().all()

    def games(self, season: int):
        # Bounded single-season read gives service filters and coverage one statement snapshot.
        statement = game_query().where(Game.season == season)
        statement = statement.order_by(Game.week, Game.scheduled_kickoff_utc.asc().nulls_last(),
                                       Game.source_game_id, Game.id)
        return self.session.scalars(statement).all()

    def game(self, game_id: UUID):
        return self.session.scalar(game_query().where(Game.id == game_id))
