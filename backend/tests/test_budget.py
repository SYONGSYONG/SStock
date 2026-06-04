"""종목별 자본 칸막이(capital envelope) 테스트."""

from __future__ import annotations

import sqlite3

import pytest

from app.config import Settings
from app.db.database import connect, init_db
from app.services import budget_service, order_service
from app.services.risk_guard import OrderIntent, RiskError, check_order


def _db(tmp_path) -> sqlite3.Connection:
    init_db(str(tmp_path / "t.db"))
    return connect(str(tmp_path / "t.db"))


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        trading_mode="paper",
        kis_paper_app_key="k",
        kis_paper_app_secret="s",
        daily_max_orders=999,
        daily_max_amount=10**12,
    )


def test_effective_ceiling_이익미반영_손실반영():
    # 이익은 한도를 키우지 않고(min(0,+)=0), 손실만 한도를 줄인다.
    assert budget_service.effective_ceiling(1_000_000, 0) == 1_000_000
    assert budget_service.effective_ceiling(1_000_000, 21_500) == 1_000_000  # 이익 무시
    assert budget_service.effective_ceiling(1_000_000, -50_000) == 950_000  # 손실 반영


def test_보유원가_실현손익_평균원가(tmp_path):
    conn = _db(tmp_path)
    # 10주 @1000, 10주 @1200 매수 -> 평균 1100, 보유원가 22000
    order_service.save_order(conn, "005930", "BUY", 10, 1000, "paper", status="filled")
    order_service.save_order(conn, "005930", "BUY", 10, 1200, "paper", status="filled")
    # 5주 @1500 매도 -> 실현 (1500-1100)*5 = 2000, 보유 15주, 보유원가 16500
    order_service.save_order(conn, "005930", "SELL", 5, 1500, "paper", status="filled")

    s = budget_service.compute_symbol_state(conn, "005930")
    assert round(s["realized_pnl"]) == 2000
    assert round(s["holding_cost"]) == 16500
    assert s["holding_qty"] == 15


def test_실현이익은_한도에_미반영(tmp_path):
    conn = _db(tmp_path)
    budget_service.set_principal(conn, "005930", 1_000_000)
    # 이익 실현: 10주 @1000 매수 후 10주 @1500 매도 -> 실현 +5000, 보유 0(flat)
    order_service.save_order(conn, "005930", "BUY", 10, 1000, "paper", status="filled")
    order_service.save_order(conn, "005930", "SELL", 10, 1500, "paper", status="filled")

    st = budget_service.envelope_status(conn, "005930")
    assert st is not None
    assert st["realized_pnl"] == 5000  # 실현이익은 정보로만 표시
    assert st["ceiling"] == 1_000_000  # 한도는 원금 그대로(이익 미반영)
    assert st["available"] == 1_000_000  # 보유 0 -> 가용 = 원금


def test_실현손실은_한도를_축소(tmp_path):
    conn = _db(tmp_path)
    budget_service.set_principal(conn, "005930", 100_000)
    # 손실 실현: 10주 @10000 매수 후 10주 @9000 매도 -> 실현 -1만, 보유 0
    order_service.save_order(conn, "005930", "BUY", 10, 10000, "paper", status="filled")
    order_service.save_order(conn, "005930", "SELL", 10, 9000, "paper", status="filled")

    st = budget_service.envelope_status(conn, "005930")
    assert st["realized_pnl"] == -10000
    assert st["ceiling"] == 90_000  # 원금 10만 + 손실(-1만) = 9만
    assert st["available"] == 90_000
    # 9만까지만 매수 허용, 10만은 거부(손실로 한도 축소)
    check_order(conn, _settings(), OrderIntent("005930", "BUY", 9, 10000))  # 예외 없음
    with pytest.raises(RiskError) as e:
        check_order(conn, _settings(), OrderIntent("005930", "BUY", 10, 10000))
    assert e.value.code == "ENVELOPE_EXCEEDED"


def test_가드_칸막이_초과시_매수_거부(tmp_path):
    conn = _db(tmp_path)
    budget_service.set_principal(conn, "005930", 100_000)  # 원금 10만
    # 이미 8만원어치 보유
    order_service.save_order(conn, "005930", "BUY", 8, 10000, "paper", status="filled")
    # 추가 3만원 매수 시도 -> 8만 + 3만 = 11만 > 10만 -> 거부
    with pytest.raises(RiskError) as e:
        check_order(conn, _settings(), OrderIntent("005930", "BUY", 3, 10000))
    assert e.value.code == "ENVELOPE_EXCEEDED"


def test_실현이익은_매수한도를_늘리지_않음(tmp_path):
    conn = _db(tmp_path)
    budget_service.set_principal(conn, "005930", 100_000)
    # 10주 @10000 매수(보유원가 10만) 후 10주 @15000 매도 -> 실현 +5만, 보유 0
    order_service.save_order(conn, "005930", "BUY", 10, 10000, "paper", status="filled")
    order_service.save_order(conn, "005930", "SELL", 10, 15000, "paper", status="filled")
    # 실현이익이 있어도 한도는 원금 10만 그대로 -> 10만(=원금)까지만 매수 허용
    check_order(conn, _settings(), OrderIntent("005930", "BUY", 10, 10000))  # 10만 OK
    # 11만 매수는 거부(실현이익으로 한도가 늘지 않음)
    with pytest.raises(RiskError) as e:
        check_order(conn, _settings(), OrderIntent("005930", "BUY", 11, 10000))
    assert e.value.code == "ENVELOPE_EXCEEDED"


def test_칸막이_미설정_종목은_매매_금지(tmp_path):
    conn = _db(tmp_path)
    # 칸막이 미등록 종목 -> 매수·매도 모두 금지
    with pytest.raises(RiskError) as e:
        check_order(conn, _settings(), OrderIntent("000660", "BUY", 100, 100000))
    assert e.value.code == "ENVELOPE_REQUIRED"


def test_매도는_칸막이_금액한도_안받음(tmp_path):
    conn = _db(tmp_path)
    budget_service.set_principal(conn, "005930", 1000)  # 아주 작은 원금
    order_service.save_order(conn, "005930", "BUY", 10, 100, "paper", status="filled")
    # 매도는 칸막이 금액 한도(ceiling) 대상이 아니다. 봇 보유 10주 이내이므로 통과.
    check_order(conn, _settings(), OrderIntent("005930", "SELL", 10, 200))
