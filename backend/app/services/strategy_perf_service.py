"""섀도우 성과 보드 — 신호 기반 가상 성과 계산(순수, 모드별).

이미 쌓인 매매신호(`signals`)만으로 각 `(종목, 전략)`의 **가상 성과**를 시뮬레이션한다.
실제 주문·전략 전환과 무관하며(위험 0), ON(`observe=0`)·OFF(`observe=1`) 신호를 모두 포함한다.

모델(완결 거래 = BUY→SELL 페어, 1단위 포지션):
- `flat → BUY` 진입, `보유중 → SELL` 청산 → 완결 거래 1건(수익률 = (청산가−진입가)/진입가×100).
- 보유 중 BUY는 무시(추가 진입 안 함), 미보유 SELL은 무시(공매도 안 함).
- 종목 가격대가 달라도 전략끼리 공정 비교가 되도록 **절대금액이 아닌 비율(%)**로 집계한다.
- 어떤 프리셋이었는지는 프론트가 현재 설정으로 추론한다(백엔드는 종목·전략 단위까지만).
"""

from __future__ import annotations

import sqlite3
from typing import Any


def _resolve_name(symbol: str) -> str:
    """종목명을 마스터에서 조회(없으면 빈 문자열)."""
    try:
        from app.stocks.master import get_name

        return get_name(symbol) or ""
    except Exception:  # noqa: BLE001 — 이름 조회 실패는 치명적이지 않다
        return ""


def simulate_signal_pnl(signals: list[dict[str, Any]]) -> dict[str, Any]:
    """시간순 신호 한 시퀀스(한 종목·한 전략)를 1단위 가상 포지션으로 시뮬레이션한다.

    signals: created_at(또는 id) 오름차순으로 정렬된 신호 dict 목록(side/price 포함).
    반환: trades/wins/win_rate/sum_return/avg_return/open_position.
    """
    entry: float | None = None  # 보유 중이면 진입가, 아니면 None
    returns: list[float] = []

    for s in signals:
        side = s.get("side")
        price = s.get("price")
        if price is None or float(price) <= 0:
            continue  # 가격 없는 신호는 가상 손익 계산 불가 → 제외
        price = float(price)

        if side == "BUY":
            if entry is None:  # flat → 진입(보유 중 BUY는 무시)
                entry = price
        elif side == "SELL":
            if entry is not None:  # 보유중 → 청산(미보유 SELL은 무시)
                returns.append((price - entry) / entry * 100.0)
                entry = None

    trades = len(returns)
    wins = sum(1 for r in returns if r > 0)
    sum_return = sum(returns)
    return {
        "trades": trades,
        "wins": wins,
        "win_rate": round(wins / trades * 100.0, 2) if trades else 0.0,
        "sum_return": round(sum_return, 2),
        "avg_return": round(sum_return / trades, 2) if trades else 0.0,
        "open_position": 1 if entry is not None else 0,
        # 미청산 진입가(프론트가 현재가와 결합해 미실현 % 계산). 청산 완료면 None.
        "open_entry": entry,
    }


def compute_strategy_performance(
    conn: sqlite3.Connection, mode: str = "paper", start: str | None = None
) -> dict[str, Any]:
    """모드별 (종목,전략) 가상 성과 보드를 계산한다.

    신호를 (종목,전략)별로 묶어 시간순 시뮬레이션하고, 완결 거래수·수익률을 집계한다.
    start('YYYY-MM-DD', KST) 지정 시 created_at >= start 신호만 사용한다(기간 필터 — 기간
    시작 전 진입분은 제외돼 그 기간에 발생한 거래만 평가). 미지정이면 전체 기간.
    행 정렬: 누적 수익률 내림차순(성과 좋은 전략이 위), 동률은 (종목,전략) 사전순.
    """
    if start:
        signals = conn.execute(
            "SELECT symbol, strategy, side, price, created_at FROM signals "
            "WHERE mode = ? AND created_at >= ? ORDER BY created_at, id",
            (mode, start),
        ).fetchall()
    else:
        signals = conn.execute(
            "SELECT symbol, strategy, side, price, created_at FROM signals "
            "WHERE mode = ? ORDER BY created_at, id",
            (mode,),
        ).fetchall()

    # (종목,전략)별 신호 시퀀스(이미 시간순)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for s in signals:
        groups.setdefault((s["symbol"], s["strategy"]), []).append(dict(s))

    rows: list[dict[str, Any]] = []
    for (symbol, strategy), seq in groups.items():
        stats = simulate_signal_pnl(seq)
        rows.append(
            {
                "symbol": symbol,
                "name": _resolve_name(symbol),
                "strategy": strategy,
                **stats,
            }
        )

    rows.sort(key=lambda r: (-r["sum_return"], r["symbol"], r["strategy"]))
    return {"rows": rows}
