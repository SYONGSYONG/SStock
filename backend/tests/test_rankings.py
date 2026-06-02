"""KIS 수급(투자자) 조회 테스트 (HTTP는 respx로 mock)."""

from __future__ import annotations

import httpx
import respx

from app.config import Settings
from app.kis.rankings import get_investor_flow

_INVESTOR_URL = "/uapi/domestic-stock/v1/quotations/inquire-investor"


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        trading_mode="paper",
        kis_app_key="dummy_key",
        kis_app_secret="dummy_secret",
    )


def _mock_token(settings: Settings) -> None:
    respx.post(f"{settings.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(200, json={"access_token": "T", "expires_in": 86400})
    )


@respx.mock
async def test_수급_조회_파싱():
    settings = _settings()
    _mock_token(settings)
    respx.get(f"{settings.rest_base}{_INVESTOR_URL}").mock(
        return_value=httpx.Response(
            200,
            json={
                "rt_cd": "0",
                "output": [
                    {"stck_bsop_date": "20260603", "frgn_ntby_qty": "150000",
                     "orgn_ntby_qty": "-30000"},
                    {"stck_bsop_date": "20260602", "frgn_ntby_qty": "9999",
                     "orgn_ntby_qty": "9999"},
                ],
            },
        )
    )

    flow = await get_investor_flow("005930", settings)

    # 최신 영업일(첫 행) 기준
    assert flow["symbol"] == "005930"
    assert flow["foreign_net"] == 150000
    assert flow["inst_net"] == -30000


@respx.mock
async def test_수급_KIS_5xx여도_None_degrade():
    settings = _settings()
    _mock_token(settings)
    respx.get(f"{settings.rest_base}{_INVESTOR_URL}").mock(
        return_value=httpx.Response(500, json={"msg1": "일시적 오류"})
    )

    flow = await get_investor_flow("005935", settings)

    assert flow["foreign_net"] is None
    assert flow["inst_net"] is None


@respx.mock
async def test_수급_빈_output이면_None():
    settings = _settings()
    _mock_token(settings)
    respx.get(f"{settings.rest_base}{_INVESTOR_URL}").mock(
        return_value=httpx.Response(200, json={"rt_cd": "0", "output": []})
    )

    flow = await get_investor_flow("005930", settings)

    assert flow["foreign_net"] is None
    assert flow["inst_net"] is None
