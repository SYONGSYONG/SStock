"""SQLite 데이터베이스 초기화.

WAL 모드 활성화 + 02-specs.md의 스키마 5개 테이블 생성.

시각 컬럼(created_at)은 KST(한국시간)로 저장한다. SQLite `datetime('now')`는
UTC를 반환하므로 `'+9 hours'`를 더해 KST 벽시계로 기록한다. 프론트는 이 문자열을
가공 없이 잘라 표시하고, risk_guard의 일일 집계도 같은 KST 기준 `date('now','+9 hours')`를
쓰므로 표시·집계 모두 한국시간으로 일치한다.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

_KST = timezone(timedelta(hours=9))


def kst_now_str() -> str:
    """현재 시각을 KST 벽시계 문자열("YYYY-MM-DD HH:MM:SS")로 반환한다.

    SQLite datetime('now')와 동일한 포맷(공백 구분)이지만 UTC가 아닌 KST다.
    삽입 시 이 값을 명시적으로 넣어, 기존 테이블에 박혀 있는 UTC DEFAULT에
    의존하지 않고 created_at을 한국시간으로 기록한다.
    """
    return datetime.now(_KST).strftime("%Y-%m-%d %H:%M:%S")

SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol      TEXT NOT NULL,
  name        TEXT,
  mode        TEXT NOT NULL DEFAULT 'paper' CHECK(mode IN ('paper','live')),
  created_at  TEXT NOT NULL DEFAULT (datetime('now', '+9 hours')),
  UNIQUE(symbol, mode)
);

CREATE TABLE IF NOT EXISTS strategy_config (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol      TEXT NOT NULL,
  strategy    TEXT NOT NULL,
  params      TEXT NOT NULL,
  enabled     INTEGER NOT NULL DEFAULT 0,
  max_qty     INTEGER,
  max_amount  INTEGER,
  mode        TEXT NOT NULL DEFAULT 'paper' CHECK(mode IN ('paper','live')),
  UNIQUE(symbol, strategy, mode)
);

CREATE TABLE IF NOT EXISTS signals (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol      TEXT NOT NULL,
  strategy    TEXT NOT NULL,
  side        TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
  price       REAL,
  reason      TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now', '+9 hours'))
);

CREATE TABLE IF NOT EXISTS orders (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  signal_id    INTEGER REFERENCES signals(id),
  symbol       TEXT NOT NULL,
  side         TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
  qty          INTEGER NOT NULL,
  filled_qty   INTEGER NOT NULL DEFAULT 0,
  remaining_qty INTEGER NOT NULL DEFAULT 0,
  price        REAL,
  mode         TEXT NOT NULL CHECK(mode IN ('paper','live')),
  kis_order_no TEXT,
  status       TEXT NOT NULL,
  created_at   TEXT NOT NULL DEFAULT (datetime('now', '+9 hours'))
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  category    TEXT NOT NULL,
  message     TEXT NOT NULL,
  created_at  TEXT NOT NULL DEFAULT (datetime('now', '+9 hours'))
);

CREATE TABLE IF NOT EXISTS capital_envelope (
  symbol     TEXT NOT NULL,
  principal  INTEGER NOT NULL,
  mode       TEXT NOT NULL DEFAULT 'paper' CHECK(mode IN ('paper','live')),
  PRIMARY KEY(symbol, mode)
);

CREATE TABLE IF NOT EXISTS risk_limit (
  mode        TEXT NOT NULL PRIMARY KEY CHECK(mode IN ('paper','live')),
  max_orders  INTEGER NOT NULL,
  max_amount  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_audit_category ON audit_logs(category);
"""


def _ensure_order_columns(conn: sqlite3.Connection) -> None:
    """기존 DB에 체결 추적 컬럼이 없으면 추가하고 기본값을 맞춘다."""
    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(orders)").fetchall()
    }
    if "filled_qty" not in columns:
        conn.execute("ALTER TABLE orders ADD COLUMN filled_qty INTEGER NOT NULL DEFAULT 0")
    if "remaining_qty" not in columns:
        conn.execute(
            "ALTER TABLE orders ADD COLUMN remaining_qty INTEGER NOT NULL DEFAULT 0"
        )

    conn.execute(
        """
        UPDATE orders
           SET filled_qty = CASE
                                WHEN status = 'filled' THEN qty
                                ELSE COALESCE(filled_qty, 0)
                             END,
               remaining_qty = CASE
                                  WHEN status = 'filled' THEN 0
                                  WHEN status IN ('rejected', 'cancelled') THEN 0
                                  ELSE COALESCE(remaining_qty, qty)
                                END
        """
    )


def _ensure_mode_columns(conn: sqlite3.Connection) -> None:
    """기존 DB에 mode 컬럼이 없으면 추가한다.

    mode 컬럼은 UNIQUE/PK 변경을 동반하므로 테이블 재생성 방식으로 마이그레이션한다.
    기존 행은 'paper'로 설정한다(기존이 모의투자였으므로).
    """

    def has_mode(table: str) -> bool:
        """테이블에 mode 컬럼이 있는지 확인."""
        return any(
            r[1] == "mode"
            for r in conn.execute(f"PRAGMA table_info({table})").fetchall()
        )

    # watchlist: mode 컬럼 추가 + UNIQUE(symbol, mode)
    if not has_mode("watchlist"):
        conn.executescript("""
            CREATE TABLE watchlist_new (
              id          INTEGER PRIMARY KEY AUTOINCREMENT,
              symbol      TEXT NOT NULL,
              name        TEXT,
              mode        TEXT NOT NULL DEFAULT 'paper' CHECK(mode IN ('paper','live')),
              created_at  TEXT NOT NULL DEFAULT (datetime('now', '+9 hours')),
              UNIQUE(symbol, mode)
            );
            INSERT INTO watchlist_new (id, symbol, name, mode, created_at)
              SELECT id, symbol, name, 'paper', created_at FROM watchlist;
            DROP TABLE watchlist;
            ALTER TABLE watchlist_new RENAME TO watchlist;
        """)

    # strategy_config: mode 컬럼 추가 + UNIQUE(symbol, strategy, mode)
    if not has_mode("strategy_config"):
        conn.executescript("""
            CREATE TABLE strategy_config_new (
              id          INTEGER PRIMARY KEY AUTOINCREMENT,
              symbol      TEXT NOT NULL,
              strategy    TEXT NOT NULL,
              params      TEXT NOT NULL,
              enabled     INTEGER NOT NULL DEFAULT 0,
              max_qty     INTEGER,
              max_amount  INTEGER,
              mode        TEXT NOT NULL DEFAULT 'paper' CHECK(mode IN ('paper','live')),
              UNIQUE(symbol, strategy, mode)
            );
            INSERT INTO strategy_config_new (id, symbol, strategy, params, enabled, max_qty, max_amount, mode)
              SELECT id, symbol, strategy, params, enabled, max_qty, max_amount, 'paper' FROM strategy_config;
            DROP TABLE strategy_config;
            ALTER TABLE strategy_config_new RENAME TO strategy_config;
        """)

    # capital_envelope: mode 컬럼 추가 + PRIMARY KEY(symbol, mode)
    if not has_mode("capital_envelope"):
        conn.executescript("""
            CREATE TABLE capital_envelope_new (
              symbol     TEXT NOT NULL,
              principal  INTEGER NOT NULL,
              mode       TEXT NOT NULL DEFAULT 'paper' CHECK(mode IN ('paper','live')),
              PRIMARY KEY(symbol, mode)
            );
            INSERT INTO capital_envelope_new (symbol, principal, mode)
              SELECT symbol, principal, 'paper' FROM capital_envelope;
            DROP TABLE capital_envelope;
            ALTER TABLE capital_envelope_new RENAME TO capital_envelope;
        """)


def init_db(database_path: str) -> None:
    """DB 파일과 테이블을 생성하고 WAL 모드를 활성화한다."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.executescript(SCHEMA)
        _ensure_order_columns(conn)
        _ensure_mode_columns(conn)
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
