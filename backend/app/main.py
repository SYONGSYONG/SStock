"""FastAPI 애플리케이션 진입점."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db.database import init_db

logger = logging.getLogger(__name__)

_TOKEN_PREWARM_TIMEOUT_SEC = 8.0
from app.routers import (
    account,
    audit,
    bot,
    budgets,
    charts,
    company,
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
    import httpx

    from app.kis.client import set_shared_client

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

    # KIS REST 호출용 keep-alive 공유 클라이언트를 모드별로 등록한다(모의/실전 도메인 분리).
    # 요청마다 새 클라이언트를 만들면 매번 TCP+TLS 핸드셰이크가 발생하므로 커넥션 풀을 재사용한다.
    shared_clients: dict[str, httpx.AsyncClient] = {}
    for mode in ("paper", "live"):
        creds = settings.kis_for(mode)
        client = httpx.AsyncClient(
            base_url=creds.rest_base,
            timeout=10.0,
            limits=httpx.Limits(
                max_keepalive_connections=10, max_connections=20, keepalive_expiry=30.0
            ),
        )
        shared_clients[mode] = client
        set_shared_client(mode, client)

    # KIS 접근토큰 프리워밍: 자격증명이 완비된 모드만 미리 토큰을 확보한다(첫 호출 왕복 제거).
    # 토큰 파일이 유효하면 네트워크 없이 끝난다. KIS 장애 시에도 기동은 계속(실패 무시).
    if settings.kis_token_prewarm:
        for mode in ("paper", "live"):
            if settings.has_kis_credentials(mode):
                await _prewarm_kis_token(settings, mode, shared_clients[mode])

    # KRX 스냅샷 프리워밍: 추천(KRX 모드) 첫 로드의 ~10초 페널티를 없앤다(KOSPI+KOSDAQ
    # 2770종목, 하루 캐시). KRX 데이터는 모드 무관이라 1회 프리워밍이 모의/실전 모두 커버.
    # 기동을 막지 않게 백그라운드로 띄운다(fire-and-forget, 실패 무시).
    prewarm_task: asyncio.Task[None] | None = None
    if settings.recommend_data_source == "krx" and settings.krx_api_key:
        prewarm_task = asyncio.create_task(_prewarm_krx_snapshot(settings))

    try:
        yield
    finally:
        if prewarm_task is not None and not prewarm_task.done():
            prewarm_task.cancel()
        for mode, client in shared_clients.items():
            set_shared_client(mode, None)
            await client.aclose()


async def _prewarm_kis_token(settings, mode: str, client=None) -> None:
    from app.kis.auth import KisAuth

    try:
        await asyncio.wait_for(
            KisAuth(settings, mode=mode).get_access_token(client),
            timeout=_TOKEN_PREWARM_TIMEOUT_SEC,
        )
        logger.info("KIS 토큰 프리워밍 완료(%s)", mode)
    except Exception as exc:  # 기동 차단 방지(네트워크/타임아웃/인증 오류 모두 무시)
        logger.warning("KIS 토큰 프리워밍 실패(무시): %s", exc)


async def _prewarm_krx_snapshot(settings) -> None:
    """KRX 스냅샷(KOSPI+KOSDAQ 전 종목)을 미리 받아 캐시를 데운다(백그라운드).

    추천 첫 로드의 ~10초 페널티 제거. KRX 장애/취소 시 추천은 lazy 폴백(실패 무시).
    """
    from app.stocks import krx

    try:
        snapshot = await krx.get_market_snapshot(settings)
        logger.info("KRX 스냅샷 프리워밍 완료: %d종목", len(snapshot))
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # 기동 차단 방지
        logger.warning("KRX 스냅샷 프리워밍 실패(무시): %s", exc)


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
    app.include_router(company.router)
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
