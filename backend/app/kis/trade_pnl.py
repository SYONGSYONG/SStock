"""KIS 기간별 매매손익 API(실전 전용).

- TTTC8715R `inquire-period-trade-profit` 기간별매매손익현황조회(종목별, 매도건별 행)
- TTTC8708R `inquire-period-profit` 기간별손익일별합산조회(일별 합산) — 참고용 seam

두 API 모두 **모의투자 미지원**(V-접두 TR 없음)이라 실전 모드에서만 동작한다. 모의 모드는
로컬 계산(`trade_pnl_service`)을 쓴다. 실현손익에는 실제 수수료·세금이 반영된다(estimated=False).

출력 필드는 KIS 명세(TTTC8715R output1)를 따른다. 일부 필드가 비어 오면 방어적으로
대체값(단가×수량 등)을 쓴다.
"""

from __future__ import annotations

from typing import Any

from app.config import Settings, get_settings
from app.kis.client import KisClient
from app.kis.constants import resolve_tr_id
from app.kis.numbers import to_float, to_int
from app.services.trade_pnl_service import summarize

_PERIOD_TRADE_PROFIT_PATH = "/uapi/domestic-stock/v1/trading/inquire-period-trade-profit"


def _ymd(date: str | None) -> str:
    """'YYYY-MM-DD' 또는 'YYYYMMDD' → 'YYYYMMDD'. None이면 빈 문자열."""
    if not date:
        return ""
    return date.replace("-", "")


def _to_dash(yyyymmdd: str) -> str:
    """'YYYYMMDD' → 'YYYY-MM-DD'(8자리 아니면 원본)."""
    s = str(yyyymmdd or "")
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 else s


def _map_row(row: dict[str, Any]) -> dict[str, Any]:
    """TTTC8715R output1 한 건 → 내부 행 형식(로컬 계산과 동일 키)."""
    sell_qty = to_int(row.get("sll_qty")) or 0
    buy_unit = to_int(row.get("pchs_unpr")) or 0
    sell_unit = to_int(row.get("sll_pric")) or 0
    buy_amount = to_int(row.get("buy_amt")) or buy_unit * sell_qty
    sell_amount = to_int(row.get("sll_amt")) or sell_unit * sell_qty
    fee = to_int(row.get("fee")) or 0
    tax = to_int(row.get("tl_tax")) or 0
    realized = to_int(row.get("rlzt_pfls"))
    if realized is None:
        realized = sell_amount - buy_amount - fee - tax
    rate = to_float(row.get("pfls_rt"))
    if rate is None:
        rate = (realized / buy_amount * 100) if buy_amount else 0.0
    return {
        "trade_date": _to_dash(row.get("trad_dt") or ""),
        "symbol": row.get("pdno") or "",
        "name": row.get("prdt_name") or "",
        "source": "manual",  # 기본값; 라우터에서 우리 orders와 대조해 봇/직접 보정
        "sell_qty": sell_qty,
        "buy_unit_price": buy_unit,
        "sell_unit_price": sell_unit,
        "buy_amount": buy_amount,
        "sell_amount": sell_amount,
        "buy_fee": 0,  # KIS는 행별 총수수료만 제공 → 매도측에 합산(요약 표기용)
        "sell_fee": fee,
        "fee": fee,
        "tax": tax,
        "realized_pnl": realized,
        "pnl_rate": round(rate, 2),
    }


async def get_period_trade_profit(
    settings: Settings | None = None,
    mode: str = "live",
    start: str | None = None,
    end: str | None = None,
    symbol: str | None = None,
    sort: str = "desc",
    kis_client: KisClient | None = None,
) -> dict[str, Any]:
    """기간별매매손익현황조회(TTTC8715R, 종목별). 실전 전용.

    rows/summary는 로컬 계산과 동일한 형식으로 반환한다(프론트 공용). 실제 수수료·세금이
    반영되므로 estimated=False.
    """
    settings = settings or get_settings()
    creds = settings.kis_for(mode)
    client = kis_client or KisClient(settings, mode=mode)
    tr_id = resolve_tr_id("inquire_period_trade_profit", mode)
    params = {
        "CANO": creds.account_no,
        "ACNT_PRDT_CD": creds.account_product,
        "INQR_STRT_DT": _ymd(start),
        "INQR_END_DT": _ymd(end),
        "SORT_DVSN": "00" if sort != "asc" else "01",  # 00 최근순 / 01 과거순
        "PDNO": symbol or "",
        "INQR_DVSN": "00",  # 00 전체(매수/매도)
        "CBLC_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }
    data = await client.get(_PERIOD_TRADE_PROFIT_PATH, tr_id, params)
    rows = [_map_row(r) for r in (data.get("output1") or [])]
    # 매도 건(수량>0)만 남긴다(매매손익은 매도 실현 기준)
    rows = [r for r in rows if r["sell_qty"] > 0]

    summary = summarize(rows)
    # 총실현손익/총수익률은 output2(tot_rlzt_pfls/tot_pftrt)가 있으면 그 값을 우선한다.
    out2 = data.get("output2") or {}
    if isinstance(out2, list):
        out2 = out2[0] if out2 else {}
    tot_realized = to_int(out2.get("tot_rlzt_pfls"))
    if tot_realized is not None:
        summary["realized_pnl_total"] = tot_realized
    tot_rate = to_float(out2.get("tot_pftrt"))
    if tot_rate is not None:
        summary["total_pnl_rate"] = round(tot_rate, 2)

    return {
        "rows": rows,
        "summary": summary,
        "source": "kis",
        "estimated": False,
        "available": True,
        "period": {"start": start, "end": end},
    }
