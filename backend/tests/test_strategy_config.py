"""전략 설정 + 신호 저장 서비스 테스트."""

from __future__ import annotations

import sqlite3

from app.db.database import connect, init_db
from app.services import signal_service, strategy_service


def _db(tmp_path) -> sqlite3.Connection:
    path = str(tmp_path / "test.db")
    init_db(path)
    return connect(path)


def test_전략설정_upsert_및_조회(tmp_path):
    conn = _db(tmp_path)
    created = strategy_service.upsert_config(
        conn, "005930", "ma_cross", {"short": 5, "long": 20}, enabled=True
    )
    assert created["params"] == {"short": 5, "long": 20}
    assert created["enabled"] is True

    # 같은 (symbol, strategy)면 갱신
    updated = strategy_service.upsert_config(
        conn, "005930", "ma_cross", {"short": 10, "long": 60}, enabled=False
    )
    assert updated["id"] == created["id"]
    assert updated["params"] == {"short": 10, "long": 60}
    assert updated["enabled"] is False
    assert len(strategy_service.list_configs(conn)) == 1


def test_enabled_토글_및_삭제(tmp_path):
    conn = _db(tmp_path)
    cfg = strategy_service.upsert_config(conn, "005930", "rsi", {}, enabled=False)
    assert strategy_service.set_enabled(conn, cfg["id"], True) is True
    assert strategy_service.list_enabled(conn)[0]["id"] == cfg["id"]
    assert strategy_service.delete_config(conn, cfg["id"]) is True
    assert strategy_service.list_configs(conn) == []


def test_신호_저장_및_조회(tmp_path):
    conn = _db(tmp_path)
    signal_service.save_signal(conn, "005930", "ma_cross", "BUY", 70000.0, "골든크로스")
    signal_service.save_signal(conn, "000660", "rsi", "SELL", 120000.0, "RSI 과매수")
    rows = signal_service.list_signals(conn, limit=10)
    assert len(rows) == 2
    # 최신순(DESC)
    assert rows[0]["symbol"] == "000660"
    assert rows[1]["side"] == "BUY"
