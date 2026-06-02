"""SQLite 데이터베이스 초기화.

WAL 모드 활성화 + 02-specs.md의 스키마 5개 테이블 생성.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol      TEXT NOT NULL UNIQUE,
  name        TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS strategy_config (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol      TEXT NOT NULL,
  strategy    TEXT NOT NULL,
  params      TEXT NOT NULL,
  enabled     INTEGER NOT NULL DEFAULT 0,
  max_qty     INTEGER,
  max_amount  INTEGER,
  UNIQUE(symbol, strategy)
);

CREATE TABLE IF NOT EXISTS signals (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol      TEXT NOT NULL,
  strategy    TEXT NOT NULL,
  side        TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
  price       REAL,
  reason      TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS orders (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  signal_id    INTEGER REFERENCES signals(id),
  symbol       TEXT NOT NULL,
  side         TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
  qty          INTEGER NOT NULL,
  price        REAL,
  mode         TEXT NOT NULL CHECK(mode IN ('paper','live')),
  kis_order_no TEXT,
  status       TEXT NOT NULL,
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  category    TEXT NOT NULL,
  message     TEXT NOT NULL,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_audit_category ON audit_logs(category);
"""


def init_db(database_path: str) -> None:
    """DB 파일과 테이블을 생성하고 WAL 모드를 활성화한다."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def connect(database_path: str) -> sqlite3.Connection:
    """행을 dict처럼 접근할 수 있는 SQLite 연결을 반환한다.

    check_same_thread=False: FastAPI는 sync 엔드포인트를 스레드풀에서 실행하며
    의존성 생성 스레드와 실행 스레드가 다를 수 있다. 요청마다 새 연결을 열고
    공유하지 않으므로 안전하다.
    """
    conn = sqlite3.connect(database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def get_db() -> Iterator[sqlite3.Connection]:
    """FastAPI 의존성: 요청 범위 DB 연결."""
    from app.config import get_settings

    conn = connect(get_settings().database_path)
    try:
        yield conn
    finally:
        conn.close()
