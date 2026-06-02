"""종목 마스터(.mst)에서 KRX 테마 분류와 재무지표를 파싱한다.

`master.py`가 종목코드→한글명만 읽는 것과 달리, 이 모듈은 고정폭 트레일러를
필드별로 슬라이싱해 KRX 섹터 테마 플래그와 ROE·영업이익·시가총액을 추출한다.

오프셋 근거: KIS 공식 파서(Reference/SampleCode/open-trading-api-main/
stocks_info/kis_kospi_code_mst.py, kis_kosdaq_code_mst.py)의 field_specs.
개행을 유지한 채 `row[-trailer:]`로 잘라야 바이트 오프셋이 맞는다(실데이터 검증).
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.kis.numbers import to_float, to_int

# backend/app/stocks/sector.py → parents[3] = 저장소 루트
_ROOT = Path(__file__).resolve().parents[3]
_MASTER_DIR = _ROOT / "종목정보"

# 분야(KRX 섹터 테마): slug → 한글 라벨. 화면 표기 순서를 유지한다.
THEMES: dict[str, str] = {
    "semiconductor": "반도체",
    "bio": "바이오",
    "auto": "자동차",
    "bank": "은행",
    "energy_chem": "에너지화학",
    "steel": "철강",
    "media_telecom": "미디어통신",
    "construction": "건설",
    "securities": "증권",
    "shipbuilding": "선박",
    "insurance": "보험",
    "transport": "운송",
}

# KIS 공식 field_specs (part2 고정폭 너비 목록)
_KOSPI_SPECS: tuple[int, ...] = (
    2, 1, 4, 4, 4, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 9, 5, 5, 1, 1, 1, 2, 1, 1,
    1, 2, 2, 2, 3, 1, 3, 12, 12, 8, 15, 21, 2, 7, 1, 1, 1, 1, 1, 9,
    9, 9, 5, 9, 8, 9, 3, 1, 1, 1,
)
_KOSDAQ_SPECS: tuple[int, ...] = (
    2, 1, 4, 4, 4, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 9, 5, 5, 1, 1, 1, 2, 1, 1, 1, 2, 2, 2, 3,
    1, 3, 12, 12, 8, 15, 21, 2, 7, 1, 1, 1, 1, 9, 9, 9, 5, 9, 8, 9,
    3, 1, 1, 1,
)


@dataclass(frozen=True)
class _Layout:
    market: str
    path: Path
    specs: tuple[int, ...]
    theme_idx: dict[str, int]  # slug → part2 필드 인덱스
    grp: int  # 증권그룹구분코드 (ST=주권)
    halt: int  # 거래정지 여부
    mng: int  # 관리종목 여부
    pref: int  # 우선주 구분 코드 (0=보통주)
    sales: int
    op_profit: int
    roe: int
    base_date: int
    market_cap: int


_LAYOUTS: tuple[_Layout, ...] = (
    _Layout(
        market="KOSPI",
        path=_MASTER_DIR / "코스피" / "kospi_code.mst",
        specs=_KOSPI_SPECS,
        theme_idx={
            "auto": 15, "semiconductor": 16, "bio": 17, "bank": 18,
            "energy_chem": 20, "steel": 21, "media_telecom": 23, "construction": 24,
            "securities": 26, "shipbuilding": 27, "insurance": 28, "transport": 29,
        },
        grp=0, halt=34, mng=36, pref=54,
        sales=59, op_profit=60, roe=63, base_date=64, market_cap=65,
    ),
    _Layout(
        market="KOSDAQ",
        path=_MASTER_DIR / "코스닥" / "kosdaq_code.mst",
        specs=_KOSDAQ_SPECS,
        theme_idx={
            "auto": 10, "semiconductor": 11, "bio": 12, "bank": 13,
            "energy_chem": 15, "steel": 16, "media_telecom": 18, "construction": 19,
            "securities": 21, "shipbuilding": 22, "insurance": 23, "transport": 24,
        },
        grp=0, halt=29, mng=31, pref=49,
        sales=53, op_profit=54, roe=57, base_date=58, market_cap=59,
    ),
)


def _cut(part2: str, specs: tuple[int, ...]) -> list[str]:
    """고정폭 part2를 field_specs 너비대로 슬라이싱한다."""
    out: list[str] = []
    off = 0
    for w in specs:
        out.append(part2[off : off + w])
        off += w
    return out


def _parse(layout: _Layout) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not layout.path.exists():
        return rows
    # part2 길이 = field_specs 합. 개행을 제거해 마지막 줄(개행 없음)도 동일하게 처리.
    trailer = sum(layout.specs)
    with io.open(layout.path, "r", encoding="cp949", errors="replace") as f:
        for raw in f:
            row = raw.rstrip("\r\n")
            if len(row) <= trailer:
                continue
            head = row[0 : len(row) - trailer]
            code = head[0:9].rstrip()
            name = head[21:].strip()
            if not code or not name:
                continue
            v = _cut(row[-trailer:], layout.specs)
            themes = [
                slug for slug, idx in layout.theme_idx.items() if v[idx].strip() == "Y"
            ]
            grp = v[layout.grp].strip()
            pref = v[layout.pref].strip()
            halt = v[layout.halt].strip() == "Y"
            mng = v[layout.mng].strip() == "Y"
            # 추천 대상: 주권(ST) + 보통주(0) + 거래정지/관리종목 아님
            active = grp == "ST" and pref == "0" and not halt and not mng
            rows.append(
                {
                    "symbol": code,
                    "name": name,
                    "market": layout.market,
                    "themes": themes,
                    "roe": to_float(v[layout.roe]),
                    "op_profit": to_int(v[layout.op_profit]),
                    "sales": to_int(v[layout.sales]),
                    "market_cap": to_int(v[layout.market_cap]),
                    "base_date": v[layout.base_date].strip() or None,
                    "active": active,
                }
            )
    return rows


@lru_cache(maxsize=1)
def _load_all() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for layout in _LAYOUTS:
        rows.extend(_parse(layout))
    return rows


def list_themes() -> list[dict[str, Any]]:
    """테마 목록과 각 테마의 활성 종목 수를 반환한다(표기 순서 유지)."""
    rows = [r for r in _load_all() if r["active"]]
    return [
        {
            "slug": slug,
            "label": label,
            "count": sum(1 for r in rows if slug in r["themes"]),
        }
        for slug, label in THEMES.items()
    ]


def by_theme(slug: str) -> list[dict[str, Any]]:
    """해당 테마의 활성 종목을 시가총액 내림차순으로 반환한다."""
    if slug not in THEMES:
        return []
    rows = [r for r in _load_all() if r["active"] and slug in r["themes"]]
    rows.sort(key=lambda r: (-(r["market_cap"] or 0), r["symbol"]))
    return rows
