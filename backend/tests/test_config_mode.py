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


def test_paper_레거시_단일세트로_폴백():
    # 모드별 paper 값이 없으면 기존 kis_app_* 를 paper로 사용한다.
    s = Settings(
        _env_file=None,
        kis_app_key="legacy",
        kis_app_secret="legacysecret",
        kis_account_no="00000000",
    )
    paper = s.kis_for("paper")
    assert paper.app_key == "legacy" and paper.account_no == "00000000"
    # live는 폴백하지 않는다(모의 키로 실전 도메인 호출 방지)
    assert s.kis_for("live").app_key == ""
    assert s.has_kis_credentials("paper") is True
    assert s.has_kis_credentials("live") is False
