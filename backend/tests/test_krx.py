"""KRX 일별매매 스냅샷 테스트 (respx mock)."""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from app.config import Settings
from app.stocks import krx


@pytest.fixture
def krx_settings():
    """KRX API 키를 포함한 설정."""
    return Settings(
        krx_api_key="test_krx_key_12345",
        recommend_data_source="krx",
    )


@pytest.fixture
def sample_kospi_data():
    """샘플 KOSPI 데이터 (일부 종목)."""
    return {
        "OutBlock_1": [
            {
                "ISU_CD": "005930",
                "ISU_NM": "삼성전자",
                "MKT_NM": "유가증권",
                "TDD_CLSPRC": "70000",
                "FLUC_RT": "1.5",
                "ACC_TRDVOL": "5000000",
                "TDD_OPNPRC": "69000",
                "HGPRC": "70500",
                "LWPRC": "68500",
            },
            {
                "ISU_CD": "000660",
                "ISU_NM": "SK하이닉스",
                "MKT_NM": "유가증권",
                "TDD_CLSPRC": "120000",
                "FLUC_RT": "-0.8",
                "ACC_TRDVOL": "3000000",
                "TDD_OPNPRC": "121000",
                "HGPRC": "121500",
                "LWPRC": "119500",
            },
        ]
    }


@pytest.fixture
def sample_kosdaq_data():
    """샘플 KOSDAQ 데이터."""
    return {
        "OutBlock_1": [
            {
                "ISU_CD": "090430",
                "ISU_NM": "디모션",
                "MKT_NM": "코스닥",
                "TDD_CLSPRC": "5000",
                "FLUC_RT": "2.0",
                "ACC_TRDVOL": "500000",
                "TDD_OPNPRC": "4900",
                "HGPRC": "5100",
                "LWPRC": "4800",
            }
        ]
    }


@pytest.mark.asyncio
async def test_fetch_market_kospi_success(krx_settings, sample_kospi_data):
    """KOSPI 시장 데이터 정상 조회."""
    with respx.mock(base_url="https://data-dbg.krx.co.kr") as respx_mock:
        respx_mock.get(
            "/svc/apis/sto/stk_bydd_trd",
            params={"basDd": "20240301"},
        ).mock(return_value=httpx.Response(200, json=sample_kospi_data))

        async with httpx.AsyncClient() as client:
            result = await krx._fetch_market(
                "stk_bydd_trd",
                "20240301",
                krx_settings,
                client,
            )

        assert len(result) == 2
        assert result[0]["ISU_CD"] == "005930"
        assert result[1]["ISU_NM"] == "SK하이닉스"


@pytest.mark.asyncio
async def test_fetch_market_empty_response(krx_settings):
    """빈 응답 처리 (장중 등)."""
    with respx.mock(base_url="https://data-dbg.krx.co.kr") as respx_mock:
        respx_mock.get(
            "/svc/apis/sto/stk_bydd_trd",
            params={"basDd": "20240301"},
        ).mock(return_value=httpx.Response(200, json={"OutBlock_1": []}))

        async with httpx.AsyncClient() as client:
            result = await krx._fetch_market(
                "stk_bydd_trd",
                "20240301",
                krx_settings,
                client,
            )

        assert result == []


@pytest.mark.asyncio
async def test_get_market_snapshot_single_flight(krx_settings, sample_kospi_data, sample_kosdaq_data):
    """동시 호출이 모두 같은 스냅샷을 반환하는지 확인 (단일비행으로 캐시)."""
    krx.clear_snapshot_cache()

    with respx.mock(base_url="https://data-dbg.krx.co.kr") as respx_mock:
        # 모든 가능한 날짜에 대해 KOSPI/KOSDAQ mock (최대 7일 lookback)
        respx_mock.get("/svc/apis/sto/stk_bydd_trd").mock(
            return_value=httpx.Response(200, json=sample_kospi_data)
        )
        respx_mock.get("/svc/apis/sto/ksq_bydd_trd").mock(
            return_value=httpx.Response(200, json=sample_kosdaq_data)
        )

        # 동시에 5개 호출 — 모두 같은 캐시를 기다림
        tasks = [krx.get_market_snapshot(krx_settings) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # 모두 같은 결과
        assert len(results) == 5
        for result in results:
            assert len(result) == 3
            assert "005930" in result
            assert "000660" in result
            assert "090430" in result
            # 모든 결과가 동일한지 확인 (참조 또는 값 비교)
            assert result == results[0]


@pytest.mark.asyncio
async def test_get_market_snapshot_lookback(krx_settings, sample_kospi_data, sample_kosdaq_data):
    """빈 응답 날짜 건너뛰고 다음 날짜로 재시도."""
    krx.clear_snapshot_cache()

    with respx.mock(base_url="https://data-dbg.krx.co.kr") as respx_mock:
        # 첫 두 basDd는 빈 응답, 세 번째는 데이터
        respx_mock.get("/svc/apis/sto/stk_bydd_trd").mock(
            side_effect=[
                httpx.Response(200, json={"OutBlock_1": []}),
                httpx.Response(200, json={"OutBlock_1": []}),
                httpx.Response(200, json=sample_kospi_data),
            ]
        )

        respx_mock.get("/svc/apis/sto/ksq_bydd_trd").mock(
            return_value=httpx.Response(200, json=sample_kosdaq_data)
        )

        result = await krx.get_market_snapshot(krx_settings)

        assert len(result) == 3
        assert "005930" in result
        assert "090430" in result


@pytest.mark.asyncio
async def test_snapshot_data_parsing(krx_settings, sample_kospi_data, sample_kosdaq_data):
    """스냅샷 데이터 형식 검증: {symbol: {price, change_rate, volume}}."""
    krx.clear_snapshot_cache()

    with respx.mock(base_url="https://data-dbg.krx.co.kr") as respx_mock:
        respx_mock.get("/svc/apis/sto/stk_bydd_trd").mock(
            return_value=httpx.Response(200, json=sample_kospi_data)
        )
        respx_mock.get("/svc/apis/sto/ksq_bydd_trd").mock(
            return_value=httpx.Response(200, json=sample_kosdaq_data)
        )

        snapshot = await krx.get_market_snapshot(krx_settings)

        # 삼성전자 (005930) 검증
        assert "005930" in snapshot
        samsung = snapshot["005930"]
        assert samsung["price"] == 70000  # int
        assert samsung["change_rate"] == 1.5  # float
        assert samsung["volume"] == 5000000  # int

        # SK하이닉스 (000660) 검증: 음수 등락률
        assert "000660" in snapshot
        hynix = snapshot["000660"]
        assert hynix["price"] == 120000
        assert hynix["change_rate"] == -0.8
        assert hynix["volume"] == 3000000

        # 디모션 (090430, KOSDAQ) 검증
        assert "090430" in snapshot
        dimotion = snapshot["090430"]
        assert dimotion["price"] == 5000
        assert dimotion["change_rate"] == 2.0


@pytest.mark.asyncio
async def test_snapshot_cache_hit(krx_settings, sample_kospi_data, sample_kosdaq_data):
    """캐시 히트: 첫 호출 후 캐시에서 반환, 데이터 동일성 확인."""
    krx.clear_snapshot_cache()

    with respx.mock(base_url="https://data-dbg.krx.co.kr") as respx_mock:
        respx_mock.get("/svc/apis/sto/stk_bydd_trd").mock(
            return_value=httpx.Response(200, json=sample_kospi_data)
        )
        respx_mock.get("/svc/apis/sto/ksq_bydd_trd").mock(
            return_value=httpx.Response(200, json=sample_kosdaq_data)
        )

        # 첫 호출 (캐시에 저장됨)
        result1 = await krx.get_market_snapshot(krx_settings)
        assert len(result1) == 3

        # 캐시 상태 확인
        assert len(krx._snapshot_cache) > 0, "캐시에 데이터가 저장되지 않음"

        # 두 번째 호출 (캐시에서 바로 반환)
        result2 = await krx.get_market_snapshot(krx_settings)

        # 캐시된 데이터와 동일
        assert result1 == result2


@pytest.mark.asyncio
async def test_snapshot_cache_avoids_refetch(krx_settings, sample_kospi_data, sample_kosdaq_data):
    """캐시 히트 시 네트워크를 재호출하지 않는다 (요청 간 캐시 유효 — 클럭 버그 회귀 방지)."""
    krx.clear_snapshot_cache()

    with respx.mock(base_url="https://data-dbg.krx.co.kr") as respx_mock:
        kospi_route = respx_mock.get("/svc/apis/sto/stk_bydd_trd").mock(
            return_value=httpx.Response(200, json=sample_kospi_data)
        )
        respx_mock.get("/svc/apis/sto/ksq_bydd_trd").mock(
            return_value=httpx.Response(200, json=sample_kosdaq_data)
        )

        await krx.get_market_snapshot(krx_settings)
        await krx.get_market_snapshot(krx_settings)

        # 두 번째 호출은 캐시에서 반환되어야 한다 → KOSPI 라우트는 첫 조회 1회만 호출
        assert kospi_route.call_count == 1


@pytest.mark.asyncio
async def test_missing_fields_parsed_as_none(krx_settings):
    """필드 누락이나 비문자열은 None으로 변환."""
    krx.clear_snapshot_cache()

    sparse_data = {
        "OutBlock_1": [
            {
                "ISU_CD": "999999",
                "ISU_NM": "테스트",
                # TDD_CLSPRC 없음
                "FLUC_RT": "abc",  # 파싱 불가
                # ACC_TRDVOL 없음
            }
        ]
    }

    with respx.mock(base_url="https://data-dbg.krx.co.kr") as respx_mock:
        respx_mock.get("/svc/apis/sto/stk_bydd_trd").mock(
            return_value=httpx.Response(200, json=sparse_data)
        )
        respx_mock.get("/svc/apis/sto/ksq_bydd_trd").mock(
            return_value=httpx.Response(200, json={"OutBlock_1": []})
        )

        snapshot = await krx.get_market_snapshot(krx_settings)

        assert "999999" in snapshot
        assert snapshot["999999"]["price"] is None
        assert snapshot["999999"]["change_rate"] is None
        assert snapshot["999999"]["volume"] is None


@pytest.mark.asyncio
async def test_resolved_date_exposed(krx_settings, sample_kospi_data, sample_kosdaq_data):
    """스냅샷 조회 후 거래일(시세 기준일)이 노출되고, 캐시 클리어 시 초기화된다."""
    krx.clear_snapshot_cache()
    assert krx.get_resolved_date() is None

    with respx.mock(base_url="https://data-dbg.krx.co.kr") as respx_mock:
        respx_mock.get("/svc/apis/sto/stk_bydd_trd").mock(
            return_value=httpx.Response(200, json=sample_kospi_data)
        )
        respx_mock.get("/svc/apis/sto/ksq_bydd_trd").mock(
            return_value=httpx.Response(200, json=sample_kosdaq_data)
        )

        await krx.get_market_snapshot(krx_settings)

    resolved = krx.get_resolved_date()
    assert resolved is not None and len(resolved) == 8 and resolved.isdigit()

    krx.clear_snapshot_cache()
    assert krx.get_resolved_date() is None


@pytest.mark.asyncio
async def test_clear_snapshot_cache():
    """캐시 클리어 함수."""
    krx._snapshot_cache["test_date"] = (0.0, {"test": "data"})
    assert len(krx._snapshot_cache) > 0

    krx.clear_snapshot_cache()
    assert len(krx._snapshot_cache) == 0
