from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.schedule import validate_query_keys, no_query_parameters
from app.db.session import get_session
from app.repositories.team_stats import TeamStatsRepository
from app.schemas.schedule import ErrorResponse
from app.schemas.team_stats import (GameLogFilters, SeasonFilters, TeamGameLogsResponse,
                                    GameTeamStatsResponse, TeamSeasonStatsResponse, TrendFilters, TeamTrendsResponse)
from app.services.team_stats import TeamStatsService
from app.repositories.game_research import GameResearchRepository
from app.schemas.game_research import GameResearchFilters, GameResearchResponse
from app.services.game_research import GameResearchService

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


@router.get('/teams/{team_id}/trends', response_model=TeamTrendsResponse)
def team_trends(team_id: UUID, filters: Annotated[TrendFilters, Query()],
                service: TeamStatsService = Depends(get_team_stats_service)):
    """L3/L5/L10 accepted team trends; optional matchup excludes itself and later kickoffs.

    Points are source-reported. Chronology does not verify completion before kickoff.
    """
    return service.trends(team_id, filters)


def get_game_research_service(session: Session = Depends(get_session)):
    return GameResearchService(GameResearchRepository(session))


@router.get('/teams/{team_id}/game-research', response_model=GameResearchResponse)
def game_research(team_id: UUID, filters: Annotated[GameResearchFilters, Query()],
                  service: GameResearchService = Depends(get_game_research_service)):
    """Same-season full-game totals, optional manual line, and unverified reference lines.

    Matchup chronology and accepted statistics never establish FINAL or pregame publication.
    """
    return service.research(team_id, filters)
