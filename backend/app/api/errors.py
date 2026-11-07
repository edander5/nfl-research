from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.services.schedule import GameNotFound


def error(status: int, code: str, message: str, details=None, headers=None):
    return JSONResponse(status_code=status, headers=headers, content={'error': {
        'code': code, 'message': message, 'details': details or [],
    }})


async def invalid_request(request: Request, exc: RequestValidationError):
    # Exclude raw input and validator contexts, which may contain sensitive values.
    details = [dict(location=list(item['loc']), type=item['type'],
                    message='REG uses weeks 1–18 with no round; POST uses weeks 19–22 and round/week must agree' if item['type'] == 'value_error' else item['msg'])
               for item in exc.errors()]
    return error(422, 'VALIDATION_ERROR', 'Invalid request parameters', details)


async def missing_game(request: Request, exc: GameNotFound):
    return error(404, 'GAME_NOT_FOUND', 'Game not found')


async def database_unavailable(request: Request, exc: SQLAlchemyError):
    return error(503, 'DATABASE_UNAVAILABLE', 'Schedule data is temporarily unavailable')


async def http_error(request: Request, exc):
    if exc.status_code == 405:
        return error(405, 'METHOD_NOT_ALLOWED', 'Method not allowed', headers=exc.headers)
    if exc.status_code == 404:
        return error(404, 'RESOURCE_NOT_FOUND', 'Resource not found', headers=exc.headers)
    return error(exc.status_code, 'HTTP_ERROR', 'Request could not be completed', headers=exc.headers)
