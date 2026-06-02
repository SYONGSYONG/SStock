"""대시보드 브로드캐스트 허브 테스트."""

from __future__ import annotations

from app.realtime.hub import DashboardHub


class FakeClient:
    def __init__(self, fail: bool = False) -> None:
        self.messages: list[str] = []
        self.fail = fail

    async def send_text(self, data: str) -> None:
        if self.fail:
            raise RuntimeError("연결 끊김")
        self.messages.append(data)


async def test_등록_브로드캐스트():
    hub = DashboardHub()
    a, b = FakeClient(), FakeClient()
    await hub.register(a)
    await hub.register(b)

    await hub.broadcast({"type": "tick", "data": {"symbol": "005930", "price": 70000}})

    assert hub.client_count == 2
    assert '"symbol": "005930"' in a.messages[0]
    assert len(b.messages) == 1


async def test_끊긴_클라이언트_자동제거():
    hub = DashboardHub()
    good, bad = FakeClient(), FakeClient(fail=True)
    await hub.register(good)
    await hub.register(bad)

    await hub.broadcast({"type": "tick", "data": {}})

    # 실패한 클라이언트는 제거됨
    assert hub.client_count == 1
    assert len(good.messages) == 1


async def test_해지():
    hub = DashboardHub()
    c = FakeClient()
    await hub.register(c)
    await hub.unregister(c)
    assert hub.client_count == 0
