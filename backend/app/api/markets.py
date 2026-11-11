"""Read-only projection of existing nflverse source-reference fields; no provider fetches."""
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.schedule import no_query_parameters, validate_query_keys
from app.db.session import get_session
from app.repositories.schedule import ScheduleRepository
from app.schemas.markets import MarketsResponse
from app.schemas.schedule import ErrorResponse
from app.services.markets import MarketsService

router = APIRouter(prefix='/api', tags=['game markets'], dependencies=[Depends(validate_query_keys)],
    responses={404: {'model': ErrorResponse}, 405: {'model': ErrorResponse},
               422: {'model': ErrorResponse}, 503: {'model': ErrorResponse}})


def get_markets_service(session: Session = Depends(get_session)):
    return MarketsService(ScheduleRepository(session))


@router.get('/games/{game_id}/markets', response_model=MarketsResponse, dependencies=[Depends(no_query_parameters)])
def game_markets(game_id: UUID, service: MarketsService = Depends(get_markets_service)):
    """Unverified reference lines and provisional arithmetic only. Never current offers or certified settlement."""
    return service.game(game_id)
