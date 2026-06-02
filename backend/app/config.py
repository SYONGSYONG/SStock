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

    def masked_app_key(self) -> str:
        """로그 노출용 마스킹된 앱키."""
        key = self.kis_app_key
        if len(key) <= 8:
            return "****"
        return f"{key[:4]}…{key[-4:]}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
