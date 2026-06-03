"""KIS 실시간(웹소켓) 체결가 구독 및 메시지 파싱.

메시지 형식(예): `0|H0STCNT0|001|005930^093000^70000^2^1000^1.45^...`
  - `|` 로 헤더 분리: [암호화여부, TR_ID, 레코드수, 데이터]
  - 데이터는 `^` 로 필드 분리 (H0STCNT0 필드 순서 고정)
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import websockets

from app.config import Settings, get_settings
from app.kis.auth import KisAuth
from app.kis.constants import resolve_ws_tr_id
from app.kis.numbers import to_float, to_int

logger = logging.getLogger(__name__)

_PRICE_TR = "H0STCNT0"
_WS_PATH = "/tryitout/H0STCNT0"

# H0STCNT0 체결가 필드 인덱스 (KIS 명세 기준)
_IDX_SYMBOL = 0
_IDX_TIME = 1
_IDX_PRICE = 2
_IDX_SIGN = 3
_IDX_CHANGE = 4
_IDX_RATE = 5
_IDX_OPEN = 7
_IDX_HIGH = 8
_IDX_LOW = 9
_IDX_ACML_VOL = 13
_MIN_FIELDS = 14

TickHandler = Callable[[dict[str, Any]], Awaitable[None]]


def parse_tick(raw: str) -> dict[str, Any] | None:
    """H0STCNT0 실시간 체결 메시지를 파싱한다. 형식이 아니면 None."""
    if not raw or raw[0] not in ("0", "1"):
        return None
    parts = raw.split("|")
    if len(parts) < 4 or parts[1] != _PRICE_TR:
        return None
    fields = parts[3].split("^")
    if len(fields) < _MIN_FIELDS:
        return None
    return {
        "symbol": fields[_IDX_SYMBOL],
        "time": fields[_IDX_TIME],
        "price": to_int(fields[_IDX_PRICE]),
        "sign": fields[_IDX_SIGN],
        "change": to_int(fields[_IDX_CHANGE]),
        "change_rate": to_float(fields[_IDX_RATE]),
        "open": to_int(fields[_IDX_OPEN]),
        "high": to_int(fields[_IDX_HIGH]),
        "low": to_int(fields[_IDX_LOW]),
        "volume": to_int(fields[_IDX_ACML_VOL]),
    }


def build_subscribe_message(approval_key: str, symbol: str, mode: str, subscribe: bool = True) -> dict:
    """체결가 구독/해지 메시지를 만든다. tr_type 1=구독, 2=해지."""
    return {
        "header": {
            "approval_key": approval_key,
            "custtype": "P",
            "tr_type": "1" if subscribe else "2",
            "content-type": "utf-8",
        },
        "body": {"input": {"tr_id": resolve_ws_tr_id("realtime_price", mode), "tr_key": symbol}},
    }


class KisRealtimeClient:
    """KIS 웹소켓에 연결해 관심종목 체결가를 구독하고 콜백으로 전달한다.

    모드별로 다른 도메인/인증을 사용한다.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        auth: KisAuth | None = None,
        mode: str | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._mode = mode or self._settings.trading_mode
        self._auth = auth or KisAuth(self._settings, mode=self._mode)
        self._symbols: set[str] = set()
        self._stop = asyncio.Event()

    @property
    def url(self) -> str:
        """모드별 ws_base를 반환한다."""
        creds = self._settings.kis_for(self._mode)
        return f"{creds.ws_base}{_WS_PATH}"

    async def run(self, symbols: list[str], on_tick: TickHandler, max_retries: int = 5) -> None:
        """연결→구독→수신 루프. 끊기면 재연결(지수 백오프)."""
        self._symbols = set(symbols)
        retries = 0
        while not self._stop.is_set() and retries < max_retries:
            try:
                approval_key = await self._auth.get_approval_key()
                async with websockets.connect(self.url) as ws:
                    retries = 0
                    for symbol in sorted(self._symbols):
                        await ws.send(
                            json.dumps(build_subscribe_message(approval_key, symbol, self._mode))
                        )
                    await self._receive_loop(ws, on_tick)
            except Exception as exc:  # noqa: BLE001 - 재연결을 위해 광범위 포착
                retries += 1
                logger.warning("KIS 웹소켓[%s] 연결 오류(%d/%d): %s", self._mode, retries, max_retries, exc)
                await asyncio.sleep(min(2**retries, 30))

    async def _receive_loop(self, ws: Any, on_tick: TickHandler) -> None:
        async for raw in ws:
            if self._stop.is_set():
                break
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            tick = parse_tick(raw)
            if tick is not None:
                await on_tick(tick)

    def stop(self) -> None:
        self._stop.set()
