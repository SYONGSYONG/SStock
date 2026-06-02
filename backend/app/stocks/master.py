"""KIS 종목 마스터(.mst)에서 종목코드→한글명 매핑을 로드한다.

파일 위치: 저장소 루트의 `종목정보/`. CP949 인코딩, 고정폭 포맷.
포맷: 단축코드(9) + 표준코드(12) + 한글종목명 + 고정 트레일러(KOSPI 228 / KOSDAQ 222).
"""

from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

# backend/app/stocks/master.py → parents[3] = 저장소 루트
_ROOT = Path(__file__).resolve().parents[3]
_MASTER_DIR = _ROOT / "종목정보"

# (파일 경로, 트레일러 바이트 수)
_FILES: list[tuple[Path, int]] = [
    (_MASTER_DIR / "코스피" / "kospi_code.mst", 228),
    (_MASTER_DIR / "코스닥" / "kosdaq_code.mst", 222),
]


def _parse(path: Path, trailer: int) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    with io.open(path, "r", encoding="cp949", errors="replace") as f:
        for raw in f:
            row = raw.rstrip("\n")
            if len(row) <= trailer:
                continue
            head = row[0 : len(row) - trailer]
            code = head[0:9].rstrip()
            name = head[21:].strip()
            if code and name:
                result[code] = name
    return result


@lru_cache(maxsize=1)
def _load() -> dict[str, str]:
    merged: dict[str, str] = {}
    for path, trailer in _FILES:
        merged.update(_parse(path, trailer))
    return merged


def get_name(symbol: str) -> str | None:
    """종목코드(6자리)로 한글 종목명을 조회한다. 없으면 None."""
    return _load().get(symbol)


def search(query: str, limit: int = 20) -> list[dict[str, str]]:
    """종목명 또는 코드로 검색한다. [{symbol, name}, ...] 반환."""
    q = query.strip()
    if not q:
        return []
    data = _load()
    results: list[dict[str, str]] = []
    if q.isdigit():
        for code, name in data.items():
            if code.startswith(q):
                results.append({"symbol": code, "name": name})
    else:
        ql = q.lower()
        for code, name in data.items():
            if ql in name.lower():
                results.append({"symbol": code, "name": name})
    # 이름이 짧을수록(=쿼리에 가까울수록) 위로
    results.sort(key=lambda r: (len(r["name"]), r["symbol"]))
    return results[:limit]


def count() -> int:
    return len(_load())
