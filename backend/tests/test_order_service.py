"""주문 저장/조회/포지션 + 감사 로그 테스트."""

from __future__ import annotations

import sqlite3

from app.db.database import connect, init_db
from app.services import audit_service, order_service


def _db(tmp_path) -> sqlite3.Connection:
    path = str(tmp_path / "test.db")
    init_db(path)
    return connect(path)


def test_주문_저장_조회_상태갱신(tmp_path):
    conn = _db(tmp_path)
    order = order_service.save_order(
        conn, "005930", "BUY", 3, 70000, "paper", status="requested", kis_order_no="A1"
    )
    assert order["status"] == "requested"
    assert order_service.update_status(conn, order["id"], "filled") is True
    rows = order_service.list_orders(conn)
    assert rows[0]["status"] == "filled"


def test_포지션_계산(tmp_path):
    conn = _db(tmp_path)
    order_service.save_order(conn, "005930", "BUY", 10, 70000, "paper", status="filled")
    order_service.save_order(conn, "005930", "SELL", 4, 71000, "paper", status="filled")
    order_service.save_order(conn, "000660", "BUY", 5, 120000, "paper", status="requested")
    order_service.save_order(conn, "000660", "BUY", 99, 120000, "paper", status="rejected")

    positions = {p["symbol"]: p["qty"] for p in order_service.compute_positions(conn)}
    assert positions["005930"] == 6  # 10 매수 - 4 매도
    assert positions["000660"] == 5  # 거부분 제외


def test_감사로그_저장_조회(tmp_path):
    conn = _db(tmp_path)
    audit_service.log(conn, "BOT", "봇 시작")
    audit_service.log(conn, "ORDER", "주문 집행")
    logs = audit_service.list_logs(conn)
    assert len(logs) == 2
    assert logs[0]["category"] == "ORDER"  # 최신순
