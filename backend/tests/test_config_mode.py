"""거래 모드(paper/live)별 도메인·TR_ID 전환 테스트."""

from __future__ import annotations

from app.config import Settings
from app.kis.constants import resolve_tr_id, resolve_ws_tr_id


def _settings(mode: str) -> Settings:
    return Settings(
        _env_file=None,
        trading_mode=mode,
        kis_app_key="dummy_key",
        kis_app_secret="dummy_secret",
    )


def test_paper_mode_domains_사용():
    s = _settings("paper")
    assert "29443" in s.rest_base
    assert s.ws_base.endswith("31000")
    assert s.is_live is False


def test_live_mode_domains_사용():
    s = _settings("live")
    assert "9443" in s.rest_base and "29443" not in s.rest_base
    assert s.ws_base.endswith("21000")
    assert s.is_live is True


def test_resolve_tr_id_매수_모드별():
    assert resolve_tr_id("order_cash_buy", "paper") == "VTTC0012U"
    assert resolve_tr_id("order_cash_buy", "live") == "TTTC0012U"


def test_resolve_tr_id_잔고조회_모드별():
    assert resolve_tr_id("inquire_balance", "paper") == "VTTC8434R"
    assert resolve_tr_id("inquire_balance", "live") == "TTTC8434R"


def test_resolve_ws_tr_id_체결통보_모드별():
    assert resolve_ws_tr_id("realtime_execution", "paper") == "H0STCNI9"
    assert resolve_ws_tr_id("realtime_execution", "live") == "H0STCNI0"


def test_app_key_마스킹():
    s = _settings("paper")
    masked = s.masked_app_key()
    assert "dummy_secret" not in masked
    assert s.kis_app_key not in masked or len(s.kis_app_key) <= 8
