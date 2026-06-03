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


def test_칸막이_한도_원금_플러스_실현손익(tmp_path):
    conn = _db(tmp_path)
    budget_service.set_principal(conn, "005930", 1_000_000)
    # 이익 실현: 10주 @1000 매수 후 10주 @1500 매도 -> 실현 +5000
    order_service.save_order(conn, "005930", "BUY", 10, 1000, "paper", status="filled")
    order_service.save_order(conn, "005930", "SELL", 10, 1500, "paper", status="filled")

    st = budget_service.envelope_status(conn, "005930")
    assert st is not None
    assert st["realized_pnl"] == 5000
    assert st["ceiling"] == 1_005_000  # 원금 100만 + 실현 5천
    assert st["available"] == 1_005_000  # 보유 없음


def test_가드_칸막이_초과시_매수_거부(tmp_path):
    conn = _db(tmp_path)
    budget_service.set_principal(conn, "005930", 100_000)  # 원금 10만
    # 이미 8만원어치 보유
    order_service.save_order(conn, "005930", "BUY", 8, 10000, "paper", status="filled")
    # 추가 3만원 매수 시도 -> 8만 + 3만 = 11만 > 10만 -> 거부
    with pytest.raises(RiskError) as e:
        check_order(conn, _settings(), OrderIntent("005930", "BUY", 3, 10000))
    assert e.value.code == "ENVELOPE_EXCEEDED"


def test_가드_실현이익으로_한도_늘면_매수_허용(tmp_path):
    conn = _db(tmp_path)
    budget_service.set_principal(conn, "005930", 100_000)
    # 10주 @10000 매수(보유원가 10만) 후 10주 @15000 매도 -> 실현 +5만, 보유 0
    order_service.save_order(conn, "005930", "BUY", 10, 10000, "paper", status="filled")
    order_service.save_order(conn, "005930", "SELL", 10, 15000, "paper", status="filled")
    # 한도 = 10만 + 5만 = 15만, 보유원가 0 -> 14만 매수 허용
    check_order(conn, _settings(), OrderIntent("005930", "BUY", 14, 10000))  # 예외 없음
    # 16만 매수는 거부
    with pytest.raises(RiskError) as e:
        check_order(conn, _settings(), OrderIntent("005930", "BUY", 16, 10000))
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
