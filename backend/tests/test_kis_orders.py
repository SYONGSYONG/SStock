"""KIS 주문/잔고 API 테스트 (HTTP는 respx로 mock)."""

from __future__ import annotations

import httpx
import respx

from app.config import Settings
from app.kis.orders import cancel_order, get_balance, place_order


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        trading_mode="paper",
        kis_app_key="k",
        kis_app_secret="s",
        kis_account_no="50191231",
    )


@respx.mock
async def test_매수주문_성공():
    s = _settings()
    respx.post(f"{s.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(200, json={"access_token": "T", "expires_in": 86400})
    )
    route = respx.post(f"{s.rest_base}/uapi/domestic-stock/v1/trading/order-cash").mock(
        return_value=httpx.Response(
            200, json={"rt_cd": "0", "msg1": "주문 완료", "output": {"ODNO": "0001"}}
        )
    )
    result = await place_order("005930", "BUY", 1, 70000.0, s)

    assert result.ok is True
    assert result.kis_order_no == "0001"
    # 모의투자 매수 TR_ID(VTTC0012U) 확인
    assert route.calls[0].request.headers["tr_id"] == "VTTC0012U"


@respx.mock
async def test_주문취소():
    s = _settings()
    respx.post(f"{s.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(200, json={"access_token": "T", "expires_in": 86400})
    )
    route = respx.post(f"{s.rest_base}/uapi/domestic-stock/v1/trading/order-rvsecncl").mock(
        return_value=httpx.Response(
            200, json={"rt_cd": "0", "msg1": "취소 완료", "output": {"ODNO": "0002"}}
        )
    )
    result = await cancel_order("005930", "0001", 1, settings=s)

    assert result.ok is True
    assert route.calls[0].request.headers["tr_id"] == "VTTC0013U"


@respx.mock
async def test_잔고조회_파싱():
    s = _settings()
    respx.post(f"{s.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(200, json={"access_token": "T", "expires_in": 86400})
    )
    respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/trading/inquire-balance").mock(
        return_value=httpx.Response(
            200,
            json={
                "rt_cd": "0",
                "output1": [
                    {
                        "pdno": "005930",
                        "prdt_name": "삼성전자",
                        "hldg_qty": "10",
                        "pchs_avg_pric": "68000",
                        "prpr": "70000",
                        "evlu_amt": "700000",
                        "evlu_pfls_amt": "20000",
                        "evlu_pfls_rt": "2.94",
                    },
                    {"pdno": "000660", "hldg_qty": "0"},  # 수량 0은 제외
                ],
            },
        )
    )
    holdings = await get_balance(s)

    assert len(holdings) == 1
    assert holdings[0]["symbol"] == "005930"
    assert holdings[0]["qty"] == 10
    assert holdings[0]["pl_amount"] == 20000
