"""KIS 시세 조회 테스트 (HTTP는 respx로 mock)."""

from __future__ import annotations

import httpx
import respx

from app.config import Settings
from app.kis.quotes import get_current_price


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        trading_mode="paper",
        kis_app_key="dummy_key",
        kis_app_secret="dummy_secret",
    )


@respx.mock
async def test_현재가_조회_파싱():
    settings = _settings()
    respx.post(f"{settings.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(200, json={"access_token": "T", "expires_in": 86400})
    )
    respx.get(
        f"{settings.rest_base}/uapi/domestic-stock/v1/quotations/inquire-price"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "rt_cd": "0",
                "output": {
                    "stck_prpr": "70000",
                    "prdy_vrss": "1000",
                    "prdy_ctrt": "1.45",
                    "prdy_vrss_sign": "2",
                    "acml_vol": "1000000",
                    "stck_oprc": "69000",
                    "stck_hgpr": "70500",
                    "stck_lwpr": "68900",
                },
            },
        )
    )

    data = await get_current_price("005930", settings)

    assert data["symbol"] == "005930"
    assert data["price"] == 70000
    assert data["change"] == 1000
    assert data["change_rate"] == 1.45
    assert data["volume"] == 1000000


@respx.mock
async def test_현재가_빈값_None_처리():
    settings = _settings()
    respx.post(f"{settings.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(200, json={"access_token": "T", "expires_in": 86400})
    )
    respx.get(
        f"{settings.rest_base}/uapi/domestic-stock/v1/quotations/inquire-price"
    ).mock(return_value=httpx.Response(200, json={"rt_cd": "0", "output": {"stck_prpr": ""}}))

    data = await get_current_price("005930", settings)

    assert data["price"] is None
    assert data["volume"] is None
