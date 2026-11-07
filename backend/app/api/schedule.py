from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.repositories.schedule import ScheduleRepository
from app.schemas.schedule import ErrorResponse, GameResponse, ScheduleFilters, ScheduleResponse, SeasonsResponse
from app.services.schedule import ScheduleService


async def validate_query_keys(request: Request):
    keys = list(request.query_params.keys())
    for key in keys:
        if len(request.query_params.getlist(key)) != 1:
            raise RequestValidationError([dict(type='duplicate_query_parameter', loc=('query', key), msg='Query parameters must appear only once')])


async def no_query_parameters(request: Request):
    if request.query_params:
        raise RequestValidationError([dict(type='extra_forbidden', loc=('query', key), msg='Extra inputs are not permitted')
                                      for key in request.query_params.keys()])


router = APIRouter(prefix='/api', tags=['schedule'], dependencies=[Depends(validate_query_keys)], responses={
    422: {'model': ErrorResponse, 'description': 'Invalid path/query, unsupported stage/week or unknown query parameter'},
    405: {'model': ErrorResponse, 'description': 'Read-only endpoint; method not allowed'},
    503: {'model': ErrorResponse, 'description': 'Database unavailable; no partial schedule is returned'},
})


def get_schedule_service(session: Session = Depends(get_session)) -> ScheduleService:
    return ScheduleService(ScheduleRepository(session))


@router.get('/seasons', response_model=SeasonsResponse, dependencies=[Depends(no_query_parameters)])
def seasons(service: ScheduleService = Depends(get_schedule_service)):
    """Available imported seasons with REG and POST counts, weeks and score/status/origin coverage."""
    return service.seasons()


@router.get('/seasons/{season}/schedule', response_model=ScheduleResponse)
def schedule(
    season: Annotated[int, Path(ge=2024, le=2026)],
    filters: Annotated[ScheduleFilters, Query()],
    service: ScheduleService = Depends(get_schedule_service),
):
    """Select REG/POST explicitly. Empty valid selections return 200 with an empty data array.

    Ordered by week, known UTC kickoff ascending (null last within week), source ID, internal UUID.
    Both week and round may be supplied only when consistent; omitted week/round returns the stage.
    """
    return service.schedule(season, filters)


@router.get('/games/{game_id}', response_model=GameResponse, dependencies=[Depends(no_query_parameters)], responses={404: {'model': ErrorResponse}})
def game(game_id: UUID, service: ScheduleService = Depends(get_schedule_service)):
    """Look up the internal canonical UUID; source and legacy IDs are not accepted as UUID aliases."""
    return service.game(game_id)
