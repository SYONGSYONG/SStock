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

# H0STASP0 호가 메시지: 헤더 3필드(종목/시간/구분) + 매도호가1~10 + 매수호가1~10
_ORDERBOOK_TR = "H0STASP0"
_IDX_OB_SYMBOL = 0
_IDX_ASKP1 = 3  # 매도호가1(최우선 매도호가)
_IDX_BIDP1 = 13  # 매수호가1(최우선 매수호가)
_MIN_OB_FIELDS = 23  # 3 + 10 + 10

TickHandler = Callable[[dict[str, Any]], Awaitable[None]]
# (event, detail) → 시세 연결 상태 변화 콜백(가시화용)
StatusHandler = Callable[[str, str], Awaitable[None]]


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


def parse_orderbook(raw: str) -> dict[str, Any] | None:
    """H0STASP0 실시간 호가 메시지에서 최우선 매도/매수호가를 파싱한다(스프레드용)."""
    if not raw or raw[0] not in ("0", "1"):
        return None
    parts = raw.split("|")
    if len(parts) < 4 or parts[1] != _ORDERBOOK_TR:
        return None
    fields = parts[3].split("^")
    if len(fields) < _MIN_OB_FIELDS:
        return None
    return {
        "kind": "orderbook",
        "symbol": fields[_IDX_OB_SYMBOL],
        "ask": to_int(fields[_IDX_ASKP1]),
        "bid": to_int(fields[_IDX_BIDP1]),
    }


def build_subscribe_message(
    approval_key: str,
    symbol: str,
    mode: str,
    subscribe: bool = True,
    tr_name: str = "realtime_price",
) -> dict:
    """실시간 구독/해지 메시지를 만든다. tr_type 1=구독, 2=해지.

    tr_name: 'realtime_price'(체결) | 'realtime_orderbook'(호가).
    """
    return {
        "header": {
            "approval_key": approval_key,
            "custtype": "P",
            "tr_type": "1" if subscribe else "2",
            "content-type": "utf-8",
        },
        "body": {"input": {"tr_id": resolve_ws_tr_id(tr_name, mode), "tr_key": symbol}},
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

    async def run(
        self,
        symbols: list[str],
        on_tick: TickHandler,
        on_status: StatusHandler | None = None,
    ) -> None:
        """연결→구독→수신 루프. **정지(`stop`) 전까지 무한 재연결**한다(지수 백오프).

        과거 `max_retries=5` 제한으로 5회 실패 후 시세가 영구 정지하던 결함을 제거했다.
        연결이 너무 빨리 끊기면 백오프를 키우고(폭주 방지), 오래 유지되면 리셋한다.
        on_status: ('connected'|'disconnected'|'error', detail) 콜백(가시화용, 선택).
        """
        self._symbols = set(symbols)
        backoff = 1
        while not self._stop.is_set():
            started = asyncio.get_event_loop().time()
            try:
                approval_key = await self._auth.get_approval_key()
                async with websockets.connect(self.url) as ws:
                    for symbol in sorted(self._symbols):
                        # 체결가 + 호가(스프레드용) 둘 다 구독
                        await ws.send(
                            json.dumps(build_subscribe_message(approval_key, symbol, self._mode))
                        )
                        await ws.send(
                            json.dumps(
                                build_subscribe_message(
                                    approval_key, symbol, self._mode, tr_name="realtime_orderbook"
                                )
                            )
                        )
                    await self._emit_status(on_status, "connected", f"{len(self._symbols)}종목")
                    await self._receive_loop(ws, on_tick)
                # 수신 루프가 정상 종료 = 서버가 연결을 닫음 → 재연결
                if not self._stop.is_set():
                    await self._emit_status(on_status, "disconnected", "연결 종료")
            except Exception as exc:  # noqa: BLE001 - 재연결을 위해 광범위 포착
                if self._stop.is_set():
                    break
                logger.warning("KIS 웹소켓[%s] 연결 오류: %s", self._mode, exc)
                await self._emit_status(on_status, "error", str(exc))
            if self._stop.is_set():
                break
            # 연결이 5초 미만으로 끊기면 백오프 증가(재연결 폭주 방지), 오래 유지됐으면 리셋
            elapsed = asyncio.get_event_loop().time() - started
            backoff = min(backoff * 2, 30) if elapsed < 5 else 1
            await asyncio.sleep(backoff)

    @staticmethod
    async def _emit_status(handler: StatusHandler | None, event: str, detail: str) -> None:
        """상태 콜백을 안전하게 호출한다(콜백 오류가 시세 루프를 막지 않게)."""
        if handler is None:
            return
        try:
            await handler(event, detail)
        except Exception as exc:  # noqa: BLE001
            logger.debug("시세 상태 콜백 오류(무시): %s", exc)

    async def _receive_loop(self, ws: Any, on_tick: TickHandler) -> None:
        async for raw in ws:
            if self._stop.is_set():
                break
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            msg = parse_tick(raw) or parse_orderbook(raw)
            if msg is not None:
                await on_tick(msg)

    def stop(self) -> None:
        self._stop.set()
