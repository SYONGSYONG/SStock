"""애플리케이션 설정.

환경 변수(`.env`)에서 로드한다. 시크릿은 코드/로그/git에 노출하지 않는다.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.kis.constants import DOMAINS

TradingMode = Literal["paper", "live"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"

    # 거래 모드 — 기본값 paper(모의투자). live는 명시적 전환만.
    trading_mode: TradingMode = "paper"

    # KIS 인증 (시크릿 — git 커밋 금지)
    kis_app_key: str = ""
    kis_app_secret: str = ""
    kis_account_no: str = ""
    kis_account_product: str = "01"

    # 기동 시 KIS 접근토큰 프리워밍(첫 시세/잔고 호출의 토큰 발급 왕복 제거).
    # 테스트는 conftest에서 끈다(실서버 KIS 호출 방지).
    kis_token_prewarm: bool = True

    # KIS 호출 사이 최소 간격(초) — 초당 거래건수 초과(EGW00201)를 사전 억제한다.
    # None이면 모드별 기본값(paper≈0.45→2건/초, live≈0.06→16건/초)을 쓴다.
    # 테스트는 conftest에서 0으로 끈다.
    kis_min_call_interval_sec: float | None = None

    # 서버
    host: str = "127.0.0.1"
    port: int = 8000

    # 안전 가드
    daily_max_orders: int = 20
    daily_max_amount: int = 1_000_000

    # 데이터베이스
    database_path: str = "./data/sstock.db"

    @property
    def rest_base(self) -> str:
        return DOMAINS[self.trading_mode]["rest"]

    @property
    def ws_base(self) -> str:
        return DOMAINS[self.trading_mode]["ws"]

    @property
    def is_live(self) -> bool:
        return self.trading_mode == "live"

    @property
    def kis_call_interval(self) -> float:
        """KIS 호출 간 최소 간격(초). 미설정 시 모드별 기본값."""
        if self.kis_min_call_interval_sec is not None:
            return max(0.0, self.kis_min_call_interval_sec)
        return 0.06 if self.trading_mode == "live" else 0.45

    def masked_app_key(self) -> str:
        """로그 노출용 마스킹된 앱키."""
        key = self.kis_app_key
        if len(key) <= 8:
            return "****"
        return f"{key[:4]}…{key[-4:]}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
