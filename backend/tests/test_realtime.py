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


async def test_시세_무한재연결_정지전까지(monkeypatch):
    """연결이 계속 실패해도 5회 제한 없이 정지(stop) 전까지 무한 재시도한다."""
    from app.kis import realtime as rt

    client = rt.KisRealtimeClient(_settings(), mode="paper")

    async def fake_key():
        return "K"

    monkeypatch.setattr(client._auth, "get_approval_key", fake_key)

    attempts = {"n": 0}
    statuses: list[str] = []

    class BoomCtx:
        async def __aenter__(self):
            raise ConnectionError("boom")

        async def __aexit__(self, *a):
            return False

    def fake_connect(url):
        attempts["n"] += 1
        if attempts["n"] >= 7:  # 옛 max_retries=5를 넘어서도 계속 재시도함을 증명
            client.stop()
        return BoomCtx()

    async def fast_sleep(_s):
        return None

    monkeypatch.setattr(rt.websockets, "connect", fake_connect)
    monkeypatch.setattr(rt.asyncio, "sleep", fast_sleep)

    async def on_status(ev, _detail):
        statuses.append(ev)

    async def on_tick(_t):
        pass

    await client.run(["005930"], on_tick, on_status=on_status)

    assert attempts["n"] == 7  # 5회 제한 없이 7회까지 재시도 후 정지로 종료
    assert "error" in statuses


async def test_emit_status_콜백_호출_및_오류무시():
    """상태 콜백을 호출하고, 콜백 오류는 삼켜 시세 루프를 막지 않는다."""
    from app.kis.realtime import KisRealtimeClient

    got: list[tuple[str, str]] = []

    async def ok(ev, detail):
        got.append((ev, detail))

    await KisRealtimeClient._emit_status(ok, "connected", "1종목")
    assert got == [("connected", "1종목")]

    async def boom(_ev, _detail):
        raise RuntimeError("콜백 오류")

    # 콜백 오류·None 모두 예외 없이 통과
    await KisRealtimeClient._emit_status(boom, "error", "x")
    await KisRealtimeClient._emit_status(None, "error", "x")


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
