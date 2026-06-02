"""FastAPI 애플리케이션 진입점."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db.database import init_db
from app.routers import (
    account,
    audit,
    bot,
    budgets,
    charts,
    health,
    market,
    orders,
    quotes,
    recommend,
    signals,
    stocks,
    strategies,
    watchlist,
    ws,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    init_db(settings.database_path)
    # 종목명이 비어 있는 기존 관심종목을 마스터에서 채운다
    from app.db.database import connect
    from app.services.watchlist_service import backfill_names
    from app.stocks.master import get_name

    conn = connect(settings.database_path)
    try:
        backfill_names(conn, get_name)
    finally:
        conn.close()
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
    app.include_router(account.router)
    app.include_router(charts.router)
    app.include_router(watchlist.router)
    app.include_router(stocks.router)
    app.include_router(quotes.router)
    app.include_router(recommend.router)
    app.include_router(market.router)
    app.include_router(strategies.router)
    app.include_router(signals.router)
    app.include_router(budgets.router)
    app.include_router(orders.router)
    app.include_router(bot.router)
    app.include_router(audit.router)
    app.include_router(ws.router)
    return app


app = create_app()
