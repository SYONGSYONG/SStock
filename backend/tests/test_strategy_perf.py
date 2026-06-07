"""섀도우 성과 보드(가상 성과) 계산·엔드포인트 테스트.

신호(`signals`)만으로 (종목,전략)별 가상 성과를 시뮬레이션한다(완결 거래 = BUY→SELL 페어).
"""

from __future__ import annotations

import sqlite3

from starlette.testclient import TestClient

from app.db.database import connect, get_db, init_db
from app.main import app
from app.services import strategy_perf_service as perf


def _db(tmp_path) -> sqlite3.Connection:
    path = str(tmp_path / "t.db")
    init_db(path)
    return connect(path)


def _sig(conn, symbol, strategy, side, price, created_at, mode="paper", observe=0):
    """신호를 직접 삽입(created_at 지정)."""
    conn.execute(
        "INSERT INTO signals (symbol, strategy, side, price, reason, mode, observe, created_at) "
        "VALUES (?, ?, ?, ?, '', ?, ?, ?)",
        (symbol, strategy, side, price, mode, observe, created_at),
    )
    conn.commit()


def test_완결거래_수익률_집계(tmp_path):
    conn = _db(tmp_path)
    # BUY 1000 → SELL 1200 = +20%, BUY 1000 → SELL 900 = -10%
    _sig(conn, "005930", "rsi_ma", "BUY", 1000, "2026-06-01 10:00:00")
    _sig(conn, "005930", "rsi_ma", "SELL", 1200, "2026-06-01 11:00:00")
    _sig(conn, "005930", "rsi_ma", "BUY", 1000, "2026-06-01 12:00:00")
    _sig(conn, "005930", "rsi_ma", "SELL", 900, "2026-06-01 13:00:00")

    rows = perf.compute_strategy_performance(conn, mode="paper")["rows"]
    assert len(rows) == 1
    r = rows[0]
    assert r["symbol"] == "005930"
    assert r["strategy"] == "rsi_ma"
    assert r["trades"] == 2
    assert r["wins"] == 1
    assert r["win_rate"] == 50.0
    assert r["sum_return"] == 10.0  # +20 - 10
    assert r["avg_return"] == 5.0
    assert r["open_position"] == 0


def test_보유중_BUY는_무시하고_미보유_SELL도_무시(tmp_path):
    conn = _db(tmp_path)
    # 미보유 SELL(무시) → BUY → 보유중 BUY(무시) → SELL(첫 진입가로 청산) → 미청산 BUY 1건
    _sig(conn, "000660", "ma_cross", "SELL", 5000, "2026-06-01 09:00:00")  # 미보유 → 무시
    _sig(conn, "000660", "ma_cross", "BUY", 1000, "2026-06-01 10:00:00")  # 진입
    _sig(conn, "000660", "ma_cross", "BUY", 1100, "2026-06-01 10:30:00")  # 보유중 → 무시
    _sig(conn, "000660", "ma_cross", "SELL", 1100, "2026-06-01 11:00:00")  # 청산: (1100-1000)/1000=+10%
    _sig(conn, "000660", "ma_cross", "BUY", 2000, "2026-06-01 12:00:00")  # 미청산 보유

    r = perf.compute_strategy_performance(conn, mode="paper")["rows"][0]
    assert r["trades"] == 1
    assert r["sum_return"] == 10.0
    assert r["open_position"] == 1


def test_ON_OFF_전략_모두_집계(tmp_path):
    conn = _db(tmp_path)
    _sig(conn, "005930", "rsi_ma", "BUY", 1000, "2026-06-01 10:00:00", observe=0)
    _sig(conn, "005930", "rsi_ma", "SELL", 1100, "2026-06-01 11:00:00", observe=0)
    _sig(conn, "005930", "ma_cross", "BUY", 1000, "2026-06-01 10:00:00", observe=1)
    _sig(conn, "005930", "ma_cross", "SELL", 1200, "2026-06-01 11:00:00", observe=1)

    rows = perf.compute_strategy_performance(conn, mode="paper")["rows"]
    keys = {(r["symbol"], r["strategy"]) for r in rows}
    assert keys == {("005930", "rsi_ma"), ("005930", "ma_cross")}


def test_모드_분리(tmp_path):
    conn = _db(tmp_path)
    _sig(conn, "005930", "rsi_ma", "BUY", 1000, "2026-06-01 10:00:00", mode="paper")
    _sig(conn, "005930", "rsi_ma", "SELL", 1100, "2026-06-01 11:00:00", mode="paper")
    _sig(conn, "005930", "rsi_ma", "BUY", 1000, "2026-06-01 10:00:00", mode="live")
    _sig(conn, "005930", "rsi_ma", "SELL", 2000, "2026-06-01 11:00:00", mode="live")

    paper = perf.compute_strategy_performance(conn, mode="paper")["rows"]
    assert len(paper) == 1
    assert paper[0]["sum_return"] == 10.0  # paper만


def test_신호없으면_빈배열(tmp_path):
    conn = _db(tmp_path)
    assert perf.compute_strategy_performance(conn, mode="paper")["rows"] == []


def test_엔드포인트_응답형식(tmp_path):
    conn = _db(tmp_path)
    _sig(conn, "005930", "rsi_ma", "BUY", 1000, "2026-06-01 10:00:00")
    _sig(conn, "005930", "rsi_ma", "SELL", 1100, "2026-06-01 11:00:00")

    app.dependency_overrides[get_db] = lambda: conn
    try:
        client = TestClient(app)
        res = client.get("/api/strategy-performance?mode=paper")
        assert res.status_code == 200
        body = res.json()
        assert "data" in body and "rows" in body["data"]
        assert body["data"]["rows"][0]["strategy"] == "rsi_ma"
    finally:
        app.dependency_overrides.clear()


def test_잘못된_모드_400(tmp_path):
    conn = _db(tmp_path)
    app.dependency_overrides[get_db] = lambda: conn
    try:
        client = TestClient(app)
        res = client.get("/api/strategy-performance?mode=bad")
        assert res.status_code == 400
    finally:
        app.dependency_overrides.clear()
