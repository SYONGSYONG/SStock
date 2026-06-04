"""기간별 매매손익 계산(로컬 DB 기반).

이 앱은 봇의 모든 주문을 `orders` 테이블에 기록하므로, 실현손익을 KIS API 없이
주문 이력에서 직접 계산한다(모의·실전 동일, KIS `TTTC8715R` 기간별매매손익현황조회와
같은 화면 구성). 평균원가법으로 매도마다 실현손익을 산출한다.

수수료·증권거래세는 봇이 체결가만 기록하므로 보유하지 않는다 → **추정치**로 반영한다
(KIS HTS의 실현손익도 수수료·세금을 가감한 값). 추정 상수는 명시적으로 둔다.

KIS API(실전, TTTC8715R) 연동 seam은 라우터에 둔다 — 현재는 로컬 계산을 사용한다.
"""

from __future__ import annotations

import sqlite3
from typing import Any

# 추정 상수(체결가만 기록하므로 실제 수수료/세금 미보유 → 보수적 추정).
ESTIMATED_FEE_RATE = 0.00015  # 거래 수수료 추정 0.015%(매수·매도 양방향)
ESTIMATED_TAX_RATE = 0.0015  # 증권거래세 추정 0.15%(매도분만, 2025년 기준 근사)


def _resolve_name(symbol: str) -> str:
    """종목명을 마스터에서 조회(없으면 빈 문자열)."""
    try:
        from app.stocks.master import get_name

        return get_name(symbol) or ""
    except Exception:  # noqa: BLE001 — 이름 조회 실패는 치명적이지 않다
        return ""


def _build_rows(conn: sqlite3.Connection, mode: str) -> list[dict[str, Any]]:
    """모든 체결을 시간순으로 처리해 매도마다 실현손익 행을 만든다(평균원가법).

    전체 이력을 순회해야 평균원가가 정확하므로, 날짜 필터는 행 생성 후 적용한다.
    """
    orders = conn.execute(
        "SELECT symbol, side, filled_qty, price, created_at FROM orders "
        "WHERE mode = ? AND status NOT IN ('rejected', 'cancelled') AND filled_qty > 0 "
        "ORDER BY id",
        (mode,),
    ).fetchall()

    # 종목별 보유수량/보유원가 러닝 상태
    holding: dict[str, dict[str, float]] = {}
    rows: list[dict[str, Any]] = []
    for o in orders:
        symbol = o["symbol"]
        qty = int(o["filled_qty"])
        price = float(o["price"] or 0)
        st = holding.setdefault(symbol, {"qty": 0.0, "cost": 0.0})

        if o["side"] == "BUY":
            st["qty"] += qty
            st["cost"] += qty * price
            continue

        # SELL: 보유분만큼만 실현(미보유 매도는 봇 정책상 발생하지 않지만 방어적으로 무시)
        if st["qty"] <= 0:
            continue
        avg = st["cost"] / st["qty"]
        sell_qty = min(qty, int(st["qty"]))
        buy_amount = avg * sell_qty
        sell_amount = price * sell_qty
        buy_fee = round(buy_amount * ESTIMATED_FEE_RATE)
        sell_fee = round(sell_amount * ESTIMATED_FEE_RATE)
        tax = round(sell_amount * ESTIMATED_TAX_RATE)
        fee = buy_fee + sell_fee
        realized = round(sell_amount - buy_amount - fee - tax)
        pnl_rate = (realized / buy_amount * 100) if buy_amount else 0.0

        rows.append(
            {
                "trade_date": str(o["created_at"])[:10],
                "symbol": symbol,
                "name": _resolve_name(symbol),
                "source": "bot",  # 로컬 계산은 봇 주문 이력 기반 → 전부 봇
                "sell_qty": sell_qty,
                "buy_unit_price": round(avg),
                "sell_unit_price": round(price),
                "buy_amount": round(buy_amount),
                "sell_amount": round(sell_amount),
                "buy_fee": buy_fee,
                "sell_fee": sell_fee,
                "fee": fee,
                "tax": tax,
                "realized_pnl": realized,
                "pnl_rate": round(pnl_rate, 2),
            }
        )

        st["qty"] -= sell_qty
        st["cost"] -= avg * sell_qty

    return rows


def bot_sell_dates(conn: sqlite3.Connection, mode: str) -> set[tuple[str, str]]:
    """봇이 매도 체결한 (종목코드, 매매일자) 집합. 봇/직접 분류용.

    봇 주문은 우리 DB(orders)에 기록되므로, KIS가 돌려준 계좌 전체 매매 중 이 집합에
    드는 (종목, 날짜)의 매도는 봇이 낸 것으로 본다(그 외는 직접 매매).
    """
    rows = conn.execute(
        "SELECT symbol, date(created_at) AS d FROM orders "
        "WHERE mode = ? AND side = 'SELL' AND status NOT IN ('rejected', 'cancelled') "
        "AND filled_qty > 0",
        (mode,),
    ).fetchall()
    return {(r["symbol"], r["d"]) for r in rows}


def annotate_source(conn: sqlite3.Connection, mode: str, rows: list[dict[str, Any]]) -> None:
    """KIS가 돌려준 행에 봇/직접 구분을 채운다(우리 orders와 (종목,날짜) 대조)."""
    bot_dates = bot_sell_dates(conn, mode)
    for r in rows:
        r["source"] = "bot" if (r.get("symbol"), r.get("trade_date")) in bot_dates else "manual"


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """매도/매수/합계 요약(KIS 화면 하단 구성). 로컬·KIS 경로 공용."""
    sell_amount = sum(r["sell_amount"] for r in rows)
    buy_amount = sum(r["buy_amount"] for r in rows)
    sell_fee = sum(r["sell_fee"] for r in rows)
    buy_fee = sum(r["buy_fee"] for r in rows)
    tax = sum(r["tax"] for r in rows)
    qty = sum(r["sell_qty"] for r in rows)
    realized = sum(r["realized_pnl"] for r in rows)

    return {
        "sell": {
            "qty": qty,
            "amount": sell_amount,
            "fee": sell_fee,
            "tax": tax,
            "settle": sell_amount - sell_fee - tax,
        },
        "buy": {
            "qty": qty,
            "amount": buy_amount,
            "fee": buy_fee,
            "tax": 0,
            "settle": buy_amount + buy_fee,
        },
        "realized_pnl_total": realized,
        "total_pnl_rate": round(realized / buy_amount * 100, 2) if buy_amount else 0.0,
    }


def compute_trade_pnl(
    conn: sqlite3.Connection,
    mode: str = "paper",
    start: str | None = None,
    end: str | None = None,
    symbol: str | None = None,
    sort: str = "desc",
) -> dict[str, Any]:
    """기간별 매매손익(행 + 요약)을 계산한다.

    start/end: 'YYYY-MM-DD'(KST, 매매일자 기준 포함). 미지정이면 전체 기간.
    symbol: 지정 시 해당 종목만. sort: 'desc'(역순, 최신 먼저) | 'asc'(정순).
    수수료·세금은 추정치이므로 estimated=True를 함께 반환한다.
    """
    rows = _build_rows(conn, mode)

    if symbol:
        rows = [r for r in rows if r["symbol"] == symbol]
    if start:
        rows = [r for r in rows if r["trade_date"] >= start]
    if end:
        rows = [r for r in rows if r["trade_date"] <= end]

    summary = summarize(rows)
    rows.sort(key=lambda r: r["trade_date"], reverse=(sort != "asc"))

    return {
        "rows": rows,
        "summary": summary,
        "source": "local",
        "estimated": True,
        "available": True,
        "period": {"start": start, "end": end},
    }
