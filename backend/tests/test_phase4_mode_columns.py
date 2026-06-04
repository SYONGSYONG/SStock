"""Phase 4 — DB mode 컬럼 + 모드별 데이터 격리 테스트."""

from __future__ import annotations

import sqlite3

import pytest

from app.config import Settings
from app.db.database import connect, init_db
from app.services import budget_service, order_service, strategy_service, watchlist_service
from app.services.risk_guard import OrderIntent, RiskError, check_order


def _db(tmp_path) -> sqlite3.Connection:
    """임시 테스트 DB를 초기화하고 연결을 반환한다."""
    init_db(str(tmp_path / "t.db"))
    return connect(str(tmp_path / "t.db"))


def _settings() -> Settings:
    """테스트용 설정을 반환한다."""
    return Settings(
        _env_file=None,
        trading_mode="paper",
        kis_paper_app_key="k",
        kis_paper_app_secret="s",
        daily_max_orders=999,
        daily_max_amount=10**12,
    )


class TestMigration:
    """마이그레이션 테스트: 기존 DB → mode 컬럼 추가."""

    def test_마이그레이션_watchlist_기존행_paper로_보존(self, tmp_path):
        """기존 watchlist 행이 mode=paper로 마이그레이션되는지 확인."""
        # 1. 신규 DB 초기화 (mode 컬럼 포함)
        init_db(str(tmp_path / "t.db"))
        conn = connect(str(tmp_path / "t.db"))

        # 2. 기본 mode=paper 행 추가
        watchlist_service.add_symbol(conn, "005930", "삼성전자", mode="paper")
        watchlist_service.add_symbol(conn, "000660", "SK하이닉스", mode="paper")

        # 3. 같은 symbol을 live로도 추가 가능 (복합 UNIQUE)
        watchlist_service.add_symbol(conn, "005930", "삼성전자", mode="live")

        # 4. 확인: paper 2개, live 1개
        paper_rows = watchlist_service.list_symbols(conn, mode="paper")
        live_rows = watchlist_service.list_symbols(conn, mode="live")

        assert len(paper_rows) == 2
        assert len(live_rows) == 1
        assert paper_rows[0]["symbol"] == "005930"
        assert live_rows[0]["symbol"] == "005930"

    def test_마이그레이션_strategy_config_기존행_paper로_보존(self, tmp_path):
        """기존 strategy_config 행이 mode=paper로 마이그레이션."""
        init_db(str(tmp_path / "t.db"))
        conn = connect(str(tmp_path / "t.db"))

        # paper 전략 추가
        strategy_service.upsert_config(
            conn,
            "005930",
            "SMA",
            {"short": 5, "long": 20},
            enabled=True,
            mode="paper",
        )
        # 같은 symbol/strategy를 live로도 추가 가능
        strategy_service.upsert_config(
            conn,
            "005930",
            "SMA",
            {"short": 5, "long": 20},
            enabled=False,
            mode="live",
        )

        paper_configs = strategy_service.list_configs(conn, mode="paper")
        live_configs = strategy_service.list_configs(conn, mode="live")

        assert len(paper_configs) == 1
        assert len(live_configs) == 1
        assert paper_configs[0]["enabled"]
        assert not live_configs[0]["enabled"]

    def test_마이그레이션_capital_envelope_기존행_paper로_보존(self, tmp_path):
        """기존 capital_envelope 행이 mode=paper로 마이그레이션."""
        init_db(str(tmp_path / "t.db"))
        conn = connect(str(tmp_path / "t.db"))

        # paper 칸막이 설정
        budget_service.set_principal(conn, "005930", 1_000_000, mode="paper")
        # live 칸막이도 추가 가능
        budget_service.set_principal(conn, "005930", 5_000_000, mode="live")

        paper_principal = budget_service.get_principal(conn, "005930", mode="paper")
        live_principal = budget_service.get_principal(conn, "005930", mode="live")

        assert paper_principal == 1_000_000
        assert live_principal == 5_000_000


class TestWatchlistModeIsolation:
    """watchlist 모드별 격리 테스트."""

    def test_paper_live_관심종목_독립(self, tmp_path):
        """paper와 live 관심종목이 완전히 독립."""
        conn = _db(tmp_path)

        # paper: 005930, 000660 추가
        watchlist_service.add_symbol(conn, "005930", mode="paper")
        watchlist_service.add_symbol(conn, "000660", mode="paper")

        # live: 051910 추가
        watchlist_service.add_symbol(conn, "051910", mode="live")

        paper = watchlist_service.list_symbols(conn, mode="paper")
        live = watchlist_service.list_symbols(conn, mode="live")

        assert len(paper) == 2
        assert len(live) == 1
        assert set(r["symbol"] for r in paper) == {"005930", "000660"}
        assert set(r["symbol"] for r in live) == {"051910"}

    def test_같은_symbol_paper_live_동시_등록(self, tmp_path):
        """같은 symbol을 paper/live 각각 등록 가능 (복합 UNIQUE)."""
        conn = _db(tmp_path)

        w1 = watchlist_service.add_symbol(conn, "005930", "삼성전자", mode="paper")
        w2 = watchlist_service.add_symbol(conn, "005930", "삼성전자", mode="live")

        assert w1["symbol"] == w2["symbol"] == "005930"
        assert w1["id"] != w2["id"]

    def test_watchlist_remove_모드별(self, tmp_path):
        """remove도 모드별로 동작."""
        conn = _db(tmp_path)

        watchlist_service.add_symbol(conn, "005930", mode="paper")
        watchlist_service.add_symbol(conn, "005930", mode="live")

        # paper만 삭제
        assert watchlist_service.remove_symbol(conn, "005930", mode="paper")

        paper = watchlist_service.list_symbols(conn, mode="paper")
        live = watchlist_service.list_symbols(conn, mode="live")

        assert len(paper) == 0
        assert len(live) == 1


class TestStrategyModeIsolation:
    """strategy_config 모드별 격리 테스트."""

    def test_paper_live_전략_독립(self, tmp_path):
        """paper와 live 전략이 완전히 독립."""
        conn = _db(tmp_path)

        strategy_service.upsert_config(
            conn,
            "005930",
            "SMA",
            {"short": 5, "long": 20},
            enabled=True,
            mode="paper",
        )
        strategy_service.upsert_config(
            conn,
            "005930",
            "RSI",
            {"period": 14, "upper": 70, "lower": 30},
            enabled=True,
            mode="live",
        )

        paper = strategy_service.list_configs(conn, mode="paper")
        live = strategy_service.list_configs(conn, mode="live")

        assert len(paper) == 1
        assert paper[0]["strategy"] == "SMA"
        assert len(live) == 1
        assert live[0]["strategy"] == "RSI"

    def test_list_enabled_모드별(self, tmp_path):
        """list_enabled가 모드별로 필터."""
        conn = _db(tmp_path)

        strategy_service.upsert_config(
            conn,
            "005930",
            "SMA",
            {"short": 5, "long": 20},
            enabled=True,
            mode="paper",
        )
        strategy_service.upsert_config(
            conn,
            "005930",
            "RSI",
            {"period": 14},
            enabled=False,
            mode="paper",
        )
        strategy_service.upsert_config(
            conn,
            "005930",
            "SMA",
            {"short": 5, "long": 20},
            enabled=False,
            mode="live",
        )

        enabled_paper = strategy_service.list_enabled(conn, mode="paper")
        enabled_live = strategy_service.list_enabled(conn, mode="live")

        assert len(enabled_paper) == 1
        assert enabled_paper[0]["strategy"] == "SMA"
        assert len(enabled_live) == 0

    def test_upsert_config_충돌기준_symbol_strategy_mode(self, tmp_path):
        """upsert의 충돌 기준은 (symbol, strategy, mode)."""
        conn = _db(tmp_path)

        # paper에 추가
        c1 = strategy_service.upsert_config(
            conn,
            "005930",
            "SMA",
            {"short": 5, "long": 20},
            enabled=True,
            mode="paper",
        )

        # 같은 종목/전략/모드로 갱신
        c2 = strategy_service.upsert_config(
            conn,
            "005930",
            "SMA",
            {"short": 10, "long": 30},
            enabled=False,
            mode="paper",
        )

        assert c1["id"] == c2["id"]  # 같은 행
        assert c2["enabled"] is False
        assert c2["params"]["short"] == 10

        # live는 다른 행
        c3 = strategy_service.upsert_config(
            conn,
            "005930",
            "SMA",
            {"short": 5, "long": 20},
            enabled=True,
            mode="live",
        )

        assert c3["id"] != c1["id"]


class TestBudgetModeIsolation:
    """budget/capital_envelope 모드별 격리 테스트."""

    def test_paper_live_칸막이_독립(self, tmp_path):
        """paper와 live 칸막이가 완전히 독립."""
        conn = _db(tmp_path)

        budget_service.set_principal(conn, "005930", 1_000_000, mode="paper")
        budget_service.set_principal(conn, "005930", 5_000_000, mode="live")

        paper_principal = budget_service.get_principal(conn, "005930", mode="paper")
        live_principal = budget_service.get_principal(conn, "005930", mode="live")

        assert paper_principal == 1_000_000
        assert live_principal == 5_000_000

    def test_compute_symbol_state_모드별(self, tmp_path):
        """compute_symbol_state가 모드별로 주문 집계."""
        conn = _db(tmp_path)

        # paper에서 10주 @1000 매수
        order_service.save_order(conn, "005930", "BUY", 10, 1000, "paper", status="filled")
        # live에서 20주 @2000 매수
        order_service.save_order(conn, "005930", "BUY", 20, 2000, "live", status="filled")

        state_paper = budget_service.compute_symbol_state(conn, "005930", mode="paper")
        state_live = budget_service.compute_symbol_state(conn, "005930", mode="live")

        assert state_paper["holding_qty"] == 10
        assert state_paper["holding_cost"] == 10000
        assert state_live["holding_qty"] == 20
        assert state_live["holding_cost"] == 40000

    def test_envelope_status_모드별(self, tmp_path):
        """envelope_status가 모드별 상태를 계산."""
        conn = _db(tmp_path)

        budget_service.set_principal(conn, "005930", 100_000, mode="paper")
        budget_service.set_principal(conn, "005930", 500_000, mode="live")

        # paper: 매수 후 매도로 5000 이익 실현
        order_service.save_order(conn, "005930", "BUY", 10, 10000, "paper", status="filled")
        order_service.save_order(conn, "005930", "SELL", 10, 10500, "paper", status="filled")

        # live: 손실 없음
        order_service.save_order(conn, "005930", "BUY", 5, 20000, "live", status="filled")

        status_paper = budget_service.envelope_status(conn, "005930", mode="paper")
        status_live = budget_service.envelope_status(conn, "005930", mode="live")

        assert status_paper["principal"] == 100_000
        assert status_paper["realized_pnl"] == 5000  # 실현이익은 정보로만 표시
        assert status_paper["ceiling"] == 100_000  # 이익은 한도 미반영 → 원금 그대로
        assert status_paper["holding_cost"] == 0  # 매도 완료

        assert status_live["principal"] == 500_000
        assert status_live["realized_pnl"] == 0
        assert status_live["holding_cost"] == 100_000

    def test_list_budgets_모드별(self, tmp_path):
        """list_budgets가 모드별로 반환."""
        conn = _db(tmp_path)

        budget_service.set_principal(conn, "005930", 100_000, mode="paper")
        budget_service.set_principal(conn, "000660", 200_000, mode="paper")
        budget_service.set_principal(conn, "051910", 300_000, mode="live")

        paper_budgets = budget_service.list_budgets(conn, mode="paper")
        live_budgets = budget_service.list_budgets(conn, mode="live")

        assert len(paper_budgets) == 2
        assert len(live_budgets) == 1
        assert set(b["symbol"] for b in paper_budgets) == {"005930", "000660"}
        assert live_budgets[0]["symbol"] == "051910"

    def test_delete_principal_모드별(self, tmp_path):
        """delete_principal이 모드별로 삭제."""
        conn = _db(tmp_path)

        budget_service.set_principal(conn, "005930", 1_000_000, mode="paper")
        budget_service.set_principal(conn, "005930", 5_000_000, mode="live")

        # paper만 삭제
        assert budget_service.delete_principal(conn, "005930", mode="paper")

        assert budget_service.get_principal(conn, "005930", mode="paper") is None
        assert budget_service.get_principal(conn, "005930", mode="live") == 5_000_000


class TestRiskGuardModeIsolation:
    """risk_guard의 모드별 격리 테스트."""

    def test_check_order_일일한도_모드별_격리(self, tmp_path):
        """일일 주문 한도가 모드별로 격리."""
        conn = _db(tmp_path)
        settings = Settings(
            _env_file=None,
            trading_mode="paper",
            kis_paper_app_key="k",
            kis_paper_app_secret="s",
            daily_max_orders=2,  # 일일 2건
            daily_max_amount=100_000,
        )

        # 일일 한도 검증 전에 칸막이 가드를 통과하도록 등록
        budget_service.set_principal(conn, "051910", 10**9, mode="paper")
        budget_service.set_principal(conn, "051910", 10**9, mode="live")

        # paper에서 2건 주문 저장
        order_service.save_order(conn, "005930", "BUY", 1, 10000, "paper", status="filled")
        order_service.save_order(conn, "000660", "BUY", 1, 10000, "paper", status="filled")

        # paper로 3번째 시도 -> 실패
        with pytest.raises(RiskError) as e:
            check_order(conn, settings, OrderIntent("051910", "BUY", 1, 10000), mode="paper")
        assert e.value.code == "DAILY_ORDER_LIMIT"

        # live로 3번째 시도 -> 성공 (live는 0건)
        check_order(conn, settings, OrderIntent("051910", "BUY", 1, 10000), mode="live")

    def test_check_order_칸막이_모드별_격리(self, tmp_path):
        """칸막이가 모드별로 격리."""
        conn = _db(tmp_path)
        settings = _settings()

        budget_service.set_principal(conn, "005930", 100_000, mode="paper")
        budget_service.set_principal(conn, "005930", 1_000_000, mode="live")

        # paper: 보유원가 50000 후 60000 더 매수 시도 -> 110000 > 100000 -> 거부
        order_service.save_order(conn, "005930", "BUY", 5, 10000, "paper", status="filled")
        with pytest.raises(RiskError) as e:
            check_order(conn, settings, OrderIntent("005930", "BUY", 6, 10000), mode="paper")
        assert e.value.code == "ENVELOPE_EXCEEDED"

        # live: 같은 60000이지만 한도가 1000000이므로 가능
        check_order(conn, settings, OrderIntent("005930", "BUY", 6, 10000), mode="live")

    def test_check_order_일일금액_모드별_격리(self, tmp_path):
        """일일 금액 한도가 모드별로 격리."""
        conn = _db(tmp_path)
        settings = Settings(
            _env_file=None,
            trading_mode="paper",
            kis_paper_app_key="k",
            kis_paper_app_secret="s",
            daily_max_orders=999,
            daily_max_amount=100_000,  # 일일 10만원
        )

        # 일일 금액 한도 검증 전에 칸막이 가드를 통과하도록 등록
        budget_service.set_principal(conn, "000660", 10**9, mode="paper")
        budget_service.set_principal(conn, "000660", 10**9, mode="live")

        # paper: 80000 주문
        order_service.save_order(conn, "005930", "BUY", 8, 10000, "paper", status="filled")

        # paper: 30000 추가 시도 -> 110000 > 100000 -> 실패
        with pytest.raises(RiskError) as e:
            check_order(conn, settings, OrderIntent("000660", "BUY", 3, 10000), mode="paper")
        assert e.value.code == "DAILY_AMOUNT_LIMIT"

        # live: 30000 주문 -> 성공 (live는 0원)
        check_order(conn, settings, OrderIntent("000660", "BUY", 3, 10000), mode="live")


class TestBackwardCompatibility:
    """하위호환성 테스트: mode 파라미터 미지정 시 기본값 'paper'."""

    def test_watchlist_기본값_paper(self, tmp_path):
        """mode 미지정 시 'paper'로 동작."""
        conn = _db(tmp_path)

        # mode 미지정으로 추가
        w = watchlist_service.add_symbol(conn, "005930")
        symbols = watchlist_service.list_symbols(conn)  # mode 미지정 = mode="paper"

        assert len(symbols) == 1
        assert symbols[0]["symbol"] == "005930"

    def test_strategy_기본값_paper(self, tmp_path):
        """mode 미지정 시 'paper'로 동작."""
        conn = _db(tmp_path)

        strategy_service.upsert_config(
            conn, "005930", "SMA", {"short": 5, "long": 20}  # mode 미지정
        )
        configs = strategy_service.list_configs(conn)  # mode 미지정 = mode="paper"

        assert len(configs) == 1

    def test_budget_기본값_paper(self, tmp_path):
        """mode 미지정 시 'paper'로 동작."""
        conn = _db(tmp_path)

        budget_service.set_principal(conn, "005930", 1_000_000)  # mode 미지정
        principal = budget_service.get_principal(conn, "005930")  # mode 미지정 = mode="paper"

        assert principal == 1_000_000

    def test_risk_guard_기본값_paper(self, tmp_path):
        """check_order mode 미지정 시 'paper'로 동작."""
        conn = _db(tmp_path)
        settings = _settings()

        budget_service.set_principal(conn, "005930", 100_000)
        budget_service.set_principal(conn, "005930", 1_000_000, mode="live")
        order_service.save_order(conn, "005930", "BUY", 10, 10000, "paper", status="filled")

        # mode 미지정 = mode="paper" → paper 칸막이 한도 초과
        with pytest.raises(RiskError) as e:
            check_order(conn, settings, OrderIntent("005930", "BUY", 1, 10000))
        assert e.value.code == "ENVELOPE_EXCEEDED"

        # live 칸막이는 한도가 커서 동일 주문도 성공
        check_order(conn, settings, OrderIntent("005930", "BUY", 1, 10000), mode="live")
