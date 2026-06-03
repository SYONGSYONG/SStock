"""테스트 공통 설정.

`TestClient(app)`가 lifespan을 실행할 때 KIS 토큰 프리워밍이 실서버로 네트워크
호출을 하지 않도록 끈다. 어떤 테스트보다 먼저(import 시점) 환경변수를 설정한다.
"""

from __future__ import annotations

import os

os.environ.setdefault("KIS_TOKEN_PREWARM", "0")
# 레이트리미터는 테스트에서 끈다(호출 간 지연으로 테스트가 느려지는 것 방지).
os.environ.setdefault("KIS_MIN_CALL_INTERVAL_SEC", "0")

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()
