"""FastAPI 애플리케이션 진입점."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db.database import init_db
from app.routers import health, market, quotes, signals, strategies, watchlist, ws


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    init_db(settings.database_path)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="SStock", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        # 04-conventions.md의 실패 응답 형식 { "error", "code" }로 통일
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": str(exc.detail), "code": "ERROR"},
        )

    app.include_router(health.router)
    app.include_router(watchlist.router)
    app.include_router(quotes.router)
    app.include_router(market.router)
    app.include_router(strategies.router)
    app.include_router(signals.router)
    app.include_router(ws.router)
    return app


app = create_app()
