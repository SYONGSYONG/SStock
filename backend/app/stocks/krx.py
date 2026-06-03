"""KRX 일별매매 스냅샷 조회 서비스.

KRX 데이터 OpenAPI에서 KOSPI와 KOSDAQ 일별매매 데이터를 조회하고 병합한다.
- 엔드포인트: https://data-dbg.krx.co.kr/svc/apis/sto/{stk_bydd_trd|ksq_bydd_trd}
- 인증: HTTP 헤더 AUTH_KEY (시크릿)
- 응답: {"OutBlock_1": [...]} 형태
- 사용 목적: 분야별 추천에서 시세(종가, 등락률, 거래량) 제공

특징:
- 장중(오전장 시간대)는 빈 응답 가능 → 최대 7일 거슬러 가장 최근 거래일 찾기
- 스냅샷 1회로 전 종목 데이터를 받으므로 캐시(하루 TTL) + 단일비행(asyncio.Lock)으로 성능 최적화
- 수급 정보(외국인/기관 순매수) 없음 → 추천 파이프라인에서 중립(50) 처리
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.kis.numbers import to_float, to_int

logger = logging.getLogger(__name__)

_BASE = "https://data-dbg.krx.co.kr/svc/apis/sto"
_ENDPOINT_KOSPI = "stk_bydd_trd"
_ENDPOINT_KOSDAQ = "ksq_bydd_trd"

# 스냅샷 캐시: resolved_date → (타임스탐프, snapshot_dict)
_snapshot_cache: dict[str, tuple[float, dict[str, dict[str, Any]]]] = {}
_snapshot_lock = asyncio.Lock()
_SNAPSHOT_TTL_SEC = 86400.0  # 하루


def clear_snapshot_cache() -> None:
    """스냅샷 캐시를 비운다 (테스트용)."""
    _snapshot_cache.clear()


async def _fetch_market(
    endpoint: str,
    bas_dd: str,
    settings: Settings,
    client: httpx.AsyncClient,
) -> list[dict[str, Any]]:
    """KRX 시장 데이터를 조회한다.

    Args:
        endpoint: "stk_bydd_trd" (KOSPI) 또는 "ksq_bydd_trd" (KOSDAQ)
        bas_dd: 기준일 (YYYYMMDD 형식)
        settings: 설정 (KRX_API_KEY 포함)
        client: httpx 비동기 클라이언트

    Returns:
        응답의 OutBlock_1 배열 또는 빈 배열
    """
    url = f"{_BASE}/{endpoint}"
    headers = {
        "AUTH_KEY": settings.krx_api_key,
        "Accept": "application/json",
    }
    params = {"basDd": bas_dd}

    try:
        resp = await client.get(url, headers=headers, params=params, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        return data.get("OutBlock_1") or []
    except httpx.HTTPError as e:
        logger.error("KRX API 호출 실패 (%s, %s): %s", endpoint, bas_dd, e)
        raise


async def get_market_snapshot(
    settings: Settings | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, dict[str, Any]]:
    """KRX KOSPI + KOSDAQ 일별매매 스냅샷을 조회한다.

    오늘부터 최대 7일 거슬러 올라가며 KOSPI 데이터가 존재하는 가장 최근 거래일을 찾는다.
    (장중이나 휴장일에는 당일 데이터가 없을 수 있음)

    스냅샷은 1회 조회로 전 종목(KOSPI 948종목 + KOSDAQ 1822종목)을 받으므로,
    단일비행(asyncio.Lock)으로 동시 요청을 1회로 직렬화하고 하루 동안 캐시한다.

    Returns:
        {symbol: {"price": int, "change_rate": float, "volume": int}}
        - symbol: ISU_CD (6자리 단축코드)
        - price: TDD_CLSPRC (종가, 정수)
        - change_rate: FLUC_RT (등락률 %, float)
        - volume: ACC_TRDVOL (거래량, 정수)

    Raises:
        httpx.HTTPError: KRX API 호출 실패
    """
    settings = settings or get_settings()
    client = client or httpx.AsyncClient()

    # 단일비행: 동시 요청이 여러 개 들어오면 락을 획득한 첫 요청만 API를 타고,
    # 나머지는 그 결과를 기다린다.
    async with _snapshot_lock:
        now_kst = datetime.now()  # 한국시간 가정
        resolved_date = None
        snapshot = {}

        # 캐시 확인 (이전 실행의 resolved_date 사용)
        for cached_date in _snapshot_cache.keys():
            ts, _ = _snapshot_cache[cached_date]
            if datetime.now().timestamp() - ts < _SNAPSHOT_TTL_SEC:
                resolved_date = cached_date
                _, snapshot = _snapshot_cache[cached_date]
                logger.debug("KRX 스냅샷 캐시 히트 (기준일: %s)", resolved_date)
                return snapshot

        # 캐시 미스: 최대 7일 거슬러 올라가며 KOSPI 데이터 찾기
        logger.debug("KRX 스냅샷 캐시 미스, API 조회 시작")
        async with httpx.AsyncClient() as http_client:
            for days_back in range(7):
                check_date = now_kst - timedelta(days=days_back)
                bas_dd = check_date.strftime("%Y%m%d")

                try:
                    kospi_data = await _fetch_market(_ENDPOINT_KOSPI, bas_dd, settings, http_client)
                except httpx.HTTPError:
                    logger.warning("KRX KOSPI 조회 실패, 이전 날짜 시도: %s", bas_dd)
                    continue

                if not kospi_data:
                    logger.debug("KRX KOSPI 데이터 빈 응답: %s", bas_dd)
                    continue

                # KOSPI 데이터 있음: KOSDAQ도 같은 날짜로 조회
                logger.debug("KRX 데이터 발견 (기준일: %s)", bas_dd)
                resolved_date = bas_dd

                try:
                    kosdaq_data = await _fetch_market(_ENDPOINT_KOSDAQ, bas_dd, settings, http_client)
                except httpx.HTTPError:
                    logger.warning("KRX KOSDAQ 조회 실패: %s", bas_dd)
                    kosdaq_data = []

                # 데이터 병합: symbol → {price, change_rate, volume}
                snapshot = {}
                for row in kospi_data + kosdaq_data:
                    symbol = row.get("ISU_CD")
                    if not symbol:
                        continue
                    price = to_int(row.get("TDD_CLSPRC"))
                    change_rate = to_float(row.get("FLUC_RT"))
                    volume = to_int(row.get("ACC_TRDVOL"))
                    snapshot[symbol] = {
                        "price": price,
                        "change_rate": change_rate,
                        "volume": volume,
                    }

                # 캐시 저장
                import time

                _snapshot_cache[resolved_date] = (time.monotonic(), snapshot)
                logger.debug("KRX 스냅샷 캐시 저장 (%d 종목, 기준일: %s)", len(snapshot), resolved_date)
                return snapshot

    logger.warning("KRX 데이터 조회 실패 (7일 조회 모두 빈 응답)")
    return {}
