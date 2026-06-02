"""관심종목 CRUD 서비스 테스트."""

from __future__ import annotations

import sqlite3

import pytest

from app.db.database import connect, init_db
from app.services.watchlist_service import add_symbol, list_symbols, remove_symbol


def _db(tmp_path) -> sqlite3.Connection:
    path = str(tmp_path / "test.db")
    init_db(path)
    return connect(path)


def test_종목_추가_후_목록조회(tmp_path):
    conn = _db(tmp_path)
    created = add_symbol(conn, "005930", "삼성전자")

    assert created["symbol"] == "005930"
    rows = list_symbols(conn)
    assert len(rows) == 1
    assert rows[0]["name"] == "삼성전자"


def test_중복_종목_추가시_에러(tmp_path):
    conn = _db(tmp_path)
    add_symbol(conn, "005930")
    with pytest.raises(sqlite3.IntegrityError):
        add_symbol(conn, "005930")


def test_종목_삭제(tmp_path):
    conn = _db(tmp_path)
    add_symbol(conn, "005930")

    assert remove_symbol(conn, "005930") is True
    assert remove_symbol(conn, "005930") is False
    assert list_symbols(conn) == []
