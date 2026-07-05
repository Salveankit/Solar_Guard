from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import analysis, data, health, operations, reports, routes
from app.core.config import get_settings
from app.core.errors import DataValidationError, SolarGuardError


def create_app() -> FastAPI:
    app = FastAPI(title="SolarGuard API", version="1.0.0")
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.resolved_frontend_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(data.router)
    app.include_router(analysis.router)
    app.include_router(operations.router)
    app.include_router(routes.router)
    app.include_router(reports.router)

    @app.exception_handler(DataValidationError)
    async def data_validation_exception_handler(
        request: Request,
        exc: DataValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": [issue.as_dict() for issue in exc.issues],
                    "request_id": request.headers.get("x-request-id"),
                }
            },
        )

    @app.exception_handler(SolarGuardError)
    async def solarguard_exception_handler(
        request: Request,
        exc: SolarGuardError,
    ) -> JSONResponse:
        status_code = 503 if exc.code.startswith("DB_") else 500
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": [],
                    "request_id": request.headers.get("x-request-id"),
                }
            },
        )

    return app


app = create_app()
