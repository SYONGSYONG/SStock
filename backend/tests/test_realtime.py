"""실시간 체결 파싱 / 구독 메시지 / approval_key 테스트."""

from __future__ import annotations

import httpx
import respx

from app.config import Settings
from app.kis.auth import KisAuth
from app.kis.realtime import build_subscribe_message, parse_orderbook, parse_tick


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        trading_mode="paper",
        kis_paper_app_key="dummy_key",
        kis_paper_app_secret="dummy_secret",
    )


def test_체결메시지_파싱():
    raw = "0|H0STCNT0|001|005930^093015^70000^2^1000^1.45^69500^69000^70500^68900^70100^69900^10^1000000"
    tick = parse_tick(raw)

    assert tick is not None
    assert tick["symbol"] == "005930"
    assert tick["price"] == 70000
    assert tick["change"] == 1000
    assert tick["change_rate"] == 1.45
    assert tick["volume"] == 1000000


def test_비체결_메시지는_None():
    assert parse_tick('{"header":{"tr_id":"PINGPONG"}}') is None
    assert parse_tick("") is None
    assert parse_tick("0|H0STASP0|001|005930^...") is None  # 다른 TR


def test_호가메시지_파싱():
    asks = "^".join(str(70100 + i * 100) for i in range(10))  # 매도호가1~10
    bids = "^".join(str(70000 - i * 100) for i in range(10))  # 매수호가1~10
    raw = f"0|H0STASP0|001|005930^093015^0^{asks}^{bids}"
    ob = parse_orderbook(raw)
    assert ob is not None
    assert ob["kind"] == "orderbook"
    assert ob["symbol"] == "005930"
    assert ob["ask"] == 70100  # 최우선 매도호가
    assert ob["bid"] == 70000  # 최우선 매수호가
    # 체결 메시지는 호가 파서가 무시
    assert parse_orderbook("0|H0STCNT0|001|005930^...") is None


def test_구독_메시지_구성():
    msg = build_subscribe_message("APPROVAL123", "005930", "paper", subscribe=True)

    assert msg["header"]["approval_key"] == "APPROVAL123"
    assert msg["header"]["tr_type"] == "1"
    assert msg["body"]["input"]["tr_id"] == "H0STCNT0"
    assert msg["body"]["input"]["tr_key"] == "005930"


def test_구독해지_메시지():
    msg = build_subscribe_message("K", "005930", "paper", subscribe=False)
    assert msg["header"]["tr_type"] == "2"


@respx.mock
async def test_approval_key_발급():
    settings = _settings()
    route = respx.post(f"{settings.rest_base}/oauth2/Approval").mock(
        return_value=httpx.Response(200, json={"approval_key": "WS_APPROVAL_KEY"})
    )
    auth = KisAuth(settings)
    key = await auth.get_approval_key()

    assert key == "WS_APPROVAL_KEY"
    assert route.call_count == 1
    # body 필드명이 secretkey 인지 확인
    sent = route.calls[0].request
    assert b"secretkey" in sent.content
