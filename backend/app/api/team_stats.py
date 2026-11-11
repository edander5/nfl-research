from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.schedule import validate_query_keys, no_query_parameters
from app.db.session import get_session
from app.repositories.team_stats import TeamStatsRepository
from app.schemas.schedule import ErrorResponse
from app.schemas.team_stats import (GameLogFilters, SeasonFilters, TeamGameLogsResponse,
                                    GameTeamStatsResponse, TeamSeasonStatsResponse)
from app.services.team_stats import TeamStatsService

router = APIRouter(prefix='/api', tags=['team statistics'], dependencies=[Depends(validate_query_keys)],
    responses={404: {'model': ErrorResponse}, 422: {'model': ErrorResponse},
               405: {'model': ErrorResponse}, 503: {'model': ErrorResponse}})


def get_team_stats_service(session: Session = Depends(get_session)):
    return TeamStatsService(TeamStatsRepository(session))


@router.get('/teams/{team_id}/games', response_model=TeamGameLogsResponse)
def team_games(team_id: UUID, filters: Annotated[GameLogFilters, Query()],
               service: TeamStatsService = Depends(get_team_stats_service)):
    """Accepted logs in kickoff order, null kickoffs last, then week/source ID/UUID. REG/POST explicit."""
    return service.logs(team_id, filters)


@router.get('/games/{game_id}/team-stats', response_model=GameTeamStatsResponse,
            dependencies=[Depends(no_query_parameters)])
def game_stats(game_id: UUID, service: TeamStatsService = Depends(get_team_stats_service)):
    """Home then away accepted statistics. Existing game without statistics returns an empty array."""
    return service.game(game_id)


@router.get('/teams/{team_id}/stats', response_model=TeamSeasonStatsResponse)
def team_stats(team_id: UUID, filters: Annotated[SeasonFilters, Query()],
               service: TeamStatsService = Depends(get_team_stats_service)):
    """Reconstructed season aggregates; not pregame rankings or evidence of game completion."""
    return service.summary(team_id, filters)
