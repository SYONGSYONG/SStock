"""KIS 응답의 문자열 숫자 안전 변환 유틸."""

from __future__ import annotations

from typing import Any


def to_int(value: Any) -> int | None:
    try:
        text = str(value).strip()
        return int(float(text)) if text else None
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> float | None:
    try:
        text = str(value).strip()
        return float(text) if text else None
    except (TypeError, ValueError):
        return None
