"""애플리케이션 설정.

환경 변수(`.env`)에서 로드한다. 시크릿은 코드/로그/git에 노출하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.kis.constants import DOMAINS

TradingMode = Literal["paper", "live"]


@dataclass(frozen=True)
class KisCredentials:
    """특정 모드(paper/live)의 KIS 자격증명 + 도메인 + 호출 간격 묶음.

    모의/실전은 별도 앱키·시크릿·계좌·도메인이라, 동시 운용 시 모드별로 분리해 쓴다.
    """

    mode: TradingMode
    app_key: str
    app_secret: str
    account_no: str
    account_product: str
    rest_base: str
    ws_base: str
    call_interval: float

    @property
    def is_complete(self) -> bool:
        """실제 호출에 필요한 키·시크릿·계좌가 모두 채워졌는지."""
        return bool(self.app_key and self.app_secret and self.account_no)

    def masked_app_key(self) -> str:
        key = self.app_key
        return "****" if len(key) <= 8 else f"{key[:4]}…{key[-4:]}"


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
    # 단일 세트(레거시): 모드별 값이 없을 때 paper 폴백으로 쓴다.
    kis_app_key: str = ""
    kis_app_secret: str = ""
    kis_account_no: str = ""
    kis_account_product: str = "01"

    # 모드별 KIS 인증 (모의/실전 동시 운용). 시크릿 — git 커밋 금지.
    kis_paper_app_key: str = ""
    kis_paper_app_secret: str = ""
    kis_paper_account_no: str = ""
    kis_live_app_key: str = ""
    kis_live_app_secret: str = ""
    kis_live_account_no: str = ""

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

    # 분야별 추천 시세 데이터 소스 — kis(기본) | krx
    recommend_data_source: Literal["kis", "krx"] = "kis"

    # KRX 데이터 OpenAPI 키 (시크릿 — git 커밋 금지)
    krx_api_key: str = ""

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
        return self._call_interval_for(self.trading_mode)

    def _call_interval_for(self, mode: TradingMode) -> float:
        if self.kis_min_call_interval_sec is not None:
            return max(0.0, self.kis_min_call_interval_sec)
        return 0.06 if mode == "live" else 0.45

    def kis_for(self, mode: TradingMode) -> KisCredentials:
        """모드별 KIS 자격증명·도메인·호출간격을 묶어 반환한다.

        paper는 모드별 값이 없으면 레거시 단일 세트(`kis_app_*`)로 폴백한다.
        live는 폴백하지 않는다(모의 키로 실전 도메인 호출 방지).
        """
        if mode == "live":
            app_key = self.kis_live_app_key
            app_secret = self.kis_live_app_secret
            account_no = self.kis_live_account_no
        else:
            app_key = self.kis_paper_app_key or self.kis_app_key
            app_secret = self.kis_paper_app_secret or self.kis_app_secret
            account_no = self.kis_paper_account_no or self.kis_account_no
        return KisCredentials(
            mode=mode,
            app_key=app_key,
            app_secret=app_secret,
            account_no=account_no,
            account_product=self.kis_account_product,
            rest_base=DOMAINS[mode]["rest"],
            ws_base=DOMAINS[mode]["ws"],
            call_interval=self._call_interval_for(mode),
        )

    def has_kis_credentials(self, mode: TradingMode) -> bool:
        """해당 모드로 실제 KIS 호출이 가능한지(키·시크릿·계좌 존재)."""
        return self.kis_for(mode).is_complete

    @property
    def recommend_kis_mode(self) -> TradingMode:
        """추천(읽기 전용 시세·수급) KIS 호출에 쓸 모드.

        추천 데이터는 모드 무관(시세/수급은 동일)하므로, 더 높은 레이트리밋을 가진
        실전(≈16/s)을 쓰면 콜드 로드가 크게 빨라진다. 실전 자격증명이 완비됐을 때만
        live를 쓰고, 아니면 paper(≈2/s)로 폴백한다. 주문이 아니라 안전하다.
        """
        return "live" if self.has_kis_credentials("live") else "paper"

    def masked_app_key(self) -> str:
        """로그 노출용 마스킹된 앱키."""
        key = self.kis_app_key
        if len(key) <= 8:
            return "****"
        return f"{key[:4]}…{key[-4:]}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
