from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse


class NotFoundException(Exception):
    status_code = 404

    def __init__(self, message: str):
        self.message = message


class BadRequestException(Exception):
    status_code = 400

    def __init__(self, message: str):
        self.message = message


class UnauthorizedException(Exception):
    status_code = 401

    def __init__(self, message: str):
        self.message = message


class ForbiddenException(Exception):
    status_code = 403

    def __init__(self, message: str):
        self.message = message


def exception_handler(
    request: Request,
    exc: Exception
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "statusCode": exc.status_code,
            "message": exc.message,
            "data": None,
            "error": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path
        }
    )