"""KIS OpenAPI 도메인 및 TR_ID 상수.

거래 모드(paper/live)에 따라 도메인과 TR_ID가 달라진다.
출처: Reference/API_DOC/ 명세.
"""

from __future__ import annotations

# 거래 모드별 도메인
DOMAINS: dict[str, dict[str, str]] = {
    "paper": {
        "rest": "https://openapivts.koreainvestment.com:29443",
        "ws": "ws://ops.koreainvestment.com:31000",
    },
    "live": {
        "rest": "https://openapi.koreainvestment.com:9443",
        "ws": "ws://ops.koreainvestment.com:21000",
    },
}

# 기능명 → 모드별 TR_ID
TR_IDS: dict[str, dict[str, str]] = {
    "order_cash_buy": {"live": "TTTC0012U", "paper": "VTTC0012U"},
    "order_cash_sell": {"live": "TTTC0011U", "paper": "VTTC0011U"},
    "order_rvsecncl": {"live": "TTTC0013U", "paper": "VTTC0013U"},
    "inquire_psbl_order": {"live": "TTTC8908R", "paper": "VTTC8908R"},
    "inquire_balance": {"live": "TTTC8434R", "paper": "VTTC8434R"},
    "inquire_daily_ccld": {"live": "TTTC0081R", "paper": "VTTC0081R"},
    # 기간별 매매손익 — 모의투자 미지원(V-접두 TR 없음) → live 전용.
    "inquire_period_trade_profit": {"live": "TTTC8715R"},  # 종목별(매매손익현황)
    "inquire_period_profit": {"live": "TTTC8708R"},  # 일별 합산(손익일별합산)
}

# 시세 조회 TR_ID — 시장 데이터는 모드와 무관하게 동일
QUOTE_TR_IDS: dict[str, str] = {
    "inquire_price": "FHKST01010100",  # 주식현재가 시세
    "inquire_asking_price": "FHKST01010200",  # 호가/예상체결
    "inquire_time_itemchartprice": "FHKST03010200",  # 당일 분봉(1분·30건)
    "inquire_time_dailychartprice": "FHKST03010230",  # 일별 분봉(1분·120건·과거 1년)
    "inquire_daily_itemchartprice": "FHKST03010100",  # 기간별 시세(일/주/월/년)
    "inquire_investor": "FHKST01010900",  # 주식현재가 투자자(개인/외국인/기관 순매수)
}

# 실시간(웹소켓) TR_ID — 체결통보만 모드별로 다름
WS_TR_IDS: dict[str, dict[str, str]] = {
    "realtime_price": {"live": "H0STCNT0", "paper": "H0STCNT0"},
    "realtime_orderbook": {"live": "H0STASP0", "paper": "H0STASP0"},
    "realtime_execution": {"live": "H0STCNI0", "paper": "H0STCNI9"},
}


def resolve_tr_id(name: str, mode: str) -> str:
    """기능명과 모드로 REST TR_ID를 반환한다."""
    try:
        return TR_IDS[name][mode]
    except KeyError as exc:
        raise KeyError(f"알 수 없는 TR_ID 기능명/모드: {name}/{mode}") from exc


def resolve_ws_tr_id(name: str, mode: str) -> str:
    """기능명과 모드로 웹소켓 TR_ID를 반환한다."""
    try:
        return WS_TR_IDS[name][mode]
    except KeyError as exc:
        raise KeyError(f"알 수 없는 웹소켓 TR_ID 기능명/모드: {name}/{mode}") from exc
