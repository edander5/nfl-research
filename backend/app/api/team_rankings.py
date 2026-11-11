from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.schedule import validate_query_keys
from app.db.session import get_session
from app.repositories.team_rankings import TeamRankingsRepository
from app.schemas.schedule import ErrorResponse
from app.schemas.team_rankings import RankingFilters, TeamRankingsResponse
from app.services.team_rankings import TeamRankingsService

router=APIRouter(prefix='/api',tags=['team rankings'],dependencies=[Depends(validate_query_keys)],responses={
    404:{'model':ErrorResponse},405:{'model':ErrorResponse},422:{'model':ErrorResponse},503:{'model':ErrorResponse}})


def get_team_rankings_service(session: Session=Depends(get_session)):
    return TeamRankingsService(TeamRankingsRepository(session))


@router.get('/team-rankings',response_model=TeamRankingsResponse)
def team_rankings(filters: Annotated[RankingFilters,Query()],
                  service: TeamRankingsService=Depends(get_team_rankings_service)):
    """Current accepted reconstructed season ranks; not verified historical pregame rankings.

    REG default; POST and explicit COMBINED supported. No cutoff/completion inference.
    """
    return service.rankings(filters)
