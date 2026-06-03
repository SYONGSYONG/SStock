"""거래 모드(paper/live)별 도메인·TR_ID 전환 테스트."""

from __future__ import annotations

from app.config import Settings
from app.kis.constants import resolve_tr_id, resolve_ws_tr_id


def _settings(mode: str) -> Settings:
    return Settings(
        _env_file=None,
        trading_mode=mode,
        kis_paper_app_key="dummy_key",
        kis_paper_app_secret="dummy_secret",
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
    # KisCredentials.masked_app_key()는 앞4·뒤4만 남기고 시크릿은 노출하지 않는다.
    s = Settings(
        _env_file=None,
        kis_paper_app_key="ABCD1234EFGH5678",
        kis_paper_app_secret="topsecret",
    )
    masked = s.kis_for("paper").masked_app_key()
    assert masked == "ABCD…5678"
    assert "topsecret" not in masked


def _dual_settings() -> Settings:
    return Settings(
        _env_file=None,
        kis_min_call_interval_sec=None,  # conftest의 0 강제를 끄고 모드별 기본값 검증
        kis_paper_app_key="paperkey",
        kis_paper_app_secret="papersecret",
        kis_paper_account_no="11111111",
        kis_live_app_key="livekey",
        kis_live_app_secret="livesecret",
        kis_live_account_no="63376776",
    )


def test_kis_for_모드별_자격증명_분리():
    s = _dual_settings()
    paper = s.kis_for("paper")
    live = s.kis_for("live")

    assert paper.app_key == "paperkey" and paper.account_no == "11111111"
    assert live.app_key == "livekey" and live.account_no == "63376776"
    # 도메인·호출간격도 모드별
    assert "29443" in paper.rest_base and "29443" not in live.rest_base
    assert paper.call_interval == 0.45 and live.call_interval == 0.06
    assert paper.is_complete and live.is_complete


def test_미설정_모드는_자격증명_불완전():
    # 모드별 자격증명이 비면 해당 모드는 KIS 호출 불가(완전 분리, 폴백 없음).
    s = Settings(
        _env_file=None,
        kis_paper_app_key="paperkey",
        kis_paper_app_secret="papersecret",
        kis_paper_account_no="11111111",
    )
    # paper만 설정 → paper는 가능, live는 불가
    assert s.has_kis_credentials("paper") is True
    assert s.has_kis_credentials("live") is False
    assert s.kis_for("live").app_key == ""
