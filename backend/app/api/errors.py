from fastapi import Request
from fastapi.responses import JSONResponse

from app.services.errors import ServiceError


async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )

