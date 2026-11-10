from fastapi import APIRouter, Depends, Request, Response

from app.api.schedule import no_query_parameters
from app.schemas.freshness import FreshnessResponse
from app.schemas.schedule import ErrorResponse
from app.services.freshness import FreshnessService

router = APIRouter(prefix='/api/data-status', tags=['data status'])


async def get_freshness_service(request: Request) -> FreshnessService:
    return request.app.state.freshness_service


@router.get('/schedule', response_model=FreshnessResponse, dependencies=[Depends(no_query_parameters)], responses={
    422: {'model': ErrorResponse}, 405: {'model': ErrorResponse},
})
async def schedule_freshness(response: Response, service: FreshnessService = Depends(get_freshness_service)):
    """Read the manual runner checkpoint. Missing/invalid metadata is a 200 domain state.

    Successful apply includes no-change reconciliation. Observed changes, checks and attempts
    are separate. This does not fetch source data, infer FINAL, or report live worker activity.
    """
    response.headers['Cache-Control'] = 'no-store'
    return service.read()
