"""주문 상태 조회/포지션 계산/감사 로그 테스트."""

from __future__ import annotations

import sqlite3

from app.db.database import connect, init_db
from app.services import audit_service, order_service


def _db(tmp_path) -> sqlite3.Connection:
    path = str(tmp_path / "test.db")
    init_db(path)
    return connect(path)


def test_주문_상태_갱신(tmp_path):
    conn = _db(tmp_path)
    order = order_service.save_order(
        conn, "005930", "BUY", 3, 70000, "paper", status="requested", kis_order_no="A1"
    )
    assert order["status"] == "requested"
    assert order["filled_qty"] == 0
    assert order_service.update_status(conn, order["id"], "filled") is True
    rows = order_service.list_orders(conn)
    assert rows[0]["status"] == "filled"
    assert rows[0]["filled_qty"] == 3


def test_포지션_계산(tmp_path):
    conn = _db(tmp_path)
    order_service.save_order(conn, "005930", "BUY", 10, 70000, "paper", status="filled")
    order_service.save_order(conn, "005930", "SELL", 4, 71000, "paper", status="filled")
    order_service.save_order(conn, "000660", "BUY", 5, 120000, "paper", status="requested")
    order_service.save_order(conn, "000660", "BUY", 99, 120000, "paper", status="rejected")

    positions = {p["symbol"]: p["qty"] for p in order_service.compute_positions(conn)}
    assert positions["005930"] == 6  # 10 매수 - 4 매도
    assert "000660" not in positions  # 요청 주문은 포지션에 반영되지 않음


def test_감사로그_조회(tmp_path):
    conn = _db(tmp_path)
    audit_service.log(conn, "BOT", "봇 시작")
    audit_service.log(conn, "ORDER", "주문 진행")
    logs = audit_service.list_logs(conn)
    assert len(logs) == 2
    assert logs[0]["category"] == "ORDER"


def test_감사로그_모드별_분리(tmp_path):
    conn = _db(tmp_path)
    audit_service.log(conn, "BOT", "모의 봇 시작", "paper")
    audit_service.log(conn, "MODE", "실전 봇 시작", "live")
    paper = audit_service.list_logs(conn, mode="paper")
    live = audit_service.list_logs(conn, mode="live")
    assert [g["message"] for g in paper] == ["모의 봇 시작"]
    assert [g["message"] for g in live] == ["실전 봇 시작"]
    assert paper[0]["mode"] == "paper"
    # mode 미지정이면 전체
    assert len(audit_service.list_logs(conn)) == 2
