"""시장 국면 분류기(classify_regime) 테스트 — 오토모드 1단계."""

from __future__ import annotations

from app.strategies.regime import (
    REGIME_RANGE,
    REGIME_STRONG_DOWN,
    REGIME_STRONG_UP,
    REGIME_VERY_STRONG_DOWN,
    REGIME_VERY_STRONG_UP,
    classify_regime,
    regime_label,
)

# 봉=틱(bar_ticks=1)으로 두고 봉 종가열을 직접 제어한다.
P1 = {"regime_bar_ticks": 1}


def test_완만한_상승추세는_강한상승(tmp_path=None):
    closes = [1000.0 + i for i in range(60)]  # 봉당 +1, 최근20봉 범위 19틱 < 30
    assert classify_regime(closes, P1) == REGIME_STRONG_UP


def test_변동성_큰_급상승은_아주강한상승():
    closes = [1000.0 + 3 * i for i in range(60)]  # 범위 57틱 >= 30
    assert classify_regime(closes, P1) == REGIME_VERY_STRONG_UP


def test_완만한_하락추세는_강한하강():
    closes = [1200.0 - i for i in range(60)]
    assert classify_regime(closes, P1) == REGIME_STRONG_DOWN


def test_변동성_큰_급락은_아주강한하강():
    closes = [1200.0 - 3 * i for i in range(60)]
    assert classify_regime(closes, P1) == REGIME_VERY_STRONG_DOWN


def test_횡보는_횡보노이즈():
    closes = [1000.0 + (i % 2) for i in range(60)]  # 1000/1001 교대 → 추세 0
    assert classify_regime(closes, P1) == REGIME_RANGE


def test_확정봉_부족하면_None():
    closes = [1000.0 + i for i in range(30)]  # ma40+lookback5+1=46 미만
    assert classify_regime(closes, P1) is None


def test_기본_틱봉50_경로로도_상승_분류():
    # 원시 틱 2500개(50봉) 상승 → 틱봉 집계 경로로도 상승 국면
    closes = [1000.0 + i for i in range(2500)]
    assert classify_regime(closes) in (REGIME_STRONG_UP, REGIME_VERY_STRONG_UP)


def test_빈_히스토리는_None():
    assert classify_regime([], P1) is None


def test_국면_라벨():
    assert regime_label(REGIME_RANGE) == "횡보/노이즈"
    assert regime_label(REGIME_STRONG_UP) == "강한상승"
    assert regime_label(None) == ""
