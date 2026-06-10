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

    # 계좌상품코드(2자리) — 모의/실전 공용.
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

    # 서버 호스트/포트는 저장소 루트 .env(BACKEND_HOST/BACKEND_PORT)로 이전 — 기동 스크립트가 읽는다.

    # 안전 가드 — risk_limit 테이블에 모드별 행이 없을 때 쓰는 기본값.
    # 대시보드에서 런타임에 변경하면 risk_limit에 저장되어 이 기본값보다 우선한다.
    daily_max_orders: int = 100
    daily_max_amount: int = 1_000_000
    # 하루 손실 한도(원, 0=비활성). 당일 실현손익이 -이 값 이하면 신규 매수 중단.
    daily_max_loss: int = 0

    # 시간 필터(전역) — 장 시작 직후/마감 직전 신규 진입 금지(분). 0이면 비활성.
    entry_block_after_open_min: int = 0
    entry_block_before_close_min: int = 0

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

        모의/실전은 각자 별도 키·시크릿·계좌(`kis_paper_*` / `kis_live_*`)를 쓴다.
        """
        if mode == "live":
            app_key = self.kis_live_app_key
            app_secret = self.kis_live_app_secret
            account_no = self.kis_live_account_no
        else:
            app_key = self.kis_paper_app_key
            app_secret = self.kis_paper_app_secret
            account_no = self.kis_paper_account_no
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
    def market_data_mode(self) -> TradingMode:
        """읽기 전용 시세 데이터(차트·추천 수급/시세) KIS 호출에 쓸 모드.

        시세/수급/차트는 모드 무관(동일 데이터)하므로, 더 높은 레이트리밋을 가진
        실전(≈16/s)을 쓰면 콜드 로드가 크게 빨라진다. 실전 자격증명이 완비됐을 때만
        live를 쓰고, 아니면 paper(≈2/s)로 폴백한다. 주문이 아니라 안전하다.
        """
        return "live" if self.has_kis_credentials("live") else "paper"


@lru_cache
def get_settings() -> Settings:
    return Settings()
