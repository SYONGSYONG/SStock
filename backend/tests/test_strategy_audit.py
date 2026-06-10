"""전략 설정 변경 감사 로그(STRATEGY 카테고리) 테스트.

upsert_config / set_enabled 가 변경 이력을 audit_logs(STRATEGY)에 남기는지,
변경 주체(source: 수동/자동)를 기록해 사후에 자동·수동을 구분할 수 있는지 검증한다.
"""

from __future__ import annotations

import sqlite3

from app.db.database import connect, init_db
from app.services import audit_service, strategy_service


def _db(tmp_path) -> sqlite3.Connection:
    path = str(tmp_path / "test.db")
    init_db(path)
    return connect(path)


def _strategy_logs(conn: sqlite3.Connection) -> list[dict]:
    return [r for r in audit_service.list_logs(conn) if r["category"] == "STRATEGY"]


def test_신규_전략등록은_STRATEGY_감사로그를_남긴다(tmp_path):
    conn = _db(tmp_path)
    strategy_service.upsert_config(
        conn, "005930", "rsi_ma", {"ma_period": 50}, enabled=True
    )
    logs = _strategy_logs(conn)
    assert len(logs) == 1
    assert "005930" in logs[0]["message"]
    assert "등록" in logs[0]["message"]
    # 기본 변경 주체는 사용자(수동)
    assert "사용자" in logs[0]["message"]


def test_파라미터_변경은_before_after_diff를_기록한다(tmp_path):
    conn = _db(tmp_path)
    strategy_service.upsert_config(conn, "005930", "rsi_ma", {"ma_period": 50}, enabled=True)
    strategy_service.upsert_config(conn, "005930", "rsi_ma", {"ma_period": 80}, enabled=True)
    logs = _strategy_logs(conn)
    # 등록 1 + 변경 1
    assert len(logs) == 2
    change = logs[0]  # 최신순(DESC)
    assert "변경" in change["message"]
    assert "ma_period" in change["message"]
    assert "50" in change["message"] and "80" in change["message"]


def test_변경이_없으면_감사로그를_남기지_않는다(tmp_path):
    conn = _db(tmp_path)
    strategy_service.upsert_config(conn, "005930", "rsi_ma", {"ma_period": 50}, enabled=True)
    # 동일 값으로 다시 upsert → 변경 없음
    strategy_service.upsert_config(conn, "005930", "rsi_ma", {"ma_period": 50}, enabled=True)
    logs = _strategy_logs(conn)
    assert len(logs) == 1  # 등록 1건만


def test_enabled_토글은_ON_OFF를_감사로그로_남긴다(tmp_path):
    conn = _db(tmp_path)
    cfg = strategy_service.upsert_config(conn, "005930", "rsi_ma", {}, enabled=False)
    strategy_service.set_enabled(conn, cfg["id"], True)
    logs = _strategy_logs(conn)
    toggle = logs[0]
    assert "005930" in toggle["message"]
    assert "ON" in toggle["message"]


def test_source_파라미터로_자동변경을_구분기록한다(tmp_path):
    conn = _db(tmp_path)
    # 자동(오토모드)로 적용한 경우 source를 명시
    strategy_service.upsert_config(
        conn, "005930", "rsi_ma", {"ma_period": 50}, enabled=True, source="오토모드"
    )
    logs = _strategy_logs(conn)
    assert "오토모드" in logs[0]["message"]


def test_감사로그는_변경된_모드로_기록된다(tmp_path):
    conn = _db(tmp_path)
    strategy_service.upsert_config(
        conn, "005930", "rsi_ma", {"ma_period": 50}, enabled=True, mode="live"
    )
    logs = _strategy_logs(conn)
    assert logs[0]["mode"] == "live"
