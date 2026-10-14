import httpx
import pytest

from app import main


@pytest.fixture
async def client(monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json=[{"id": 1, "name": "A", "phone": "89991234567", "email": "", "amount": 5, "created_at": "2026-10-01T00:00:00Z"}])

    main.app.state.syncer = main.Syncer(httpx.MockTransport(handler))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://t") as c:
        yield c, calls


async def test_repeated_sync_is_idempotent(client):
    c, calls = client
    first = (await c.post("/api/sync")).json()
    second = (await c.post("/api/sync")).json()
    assert first == second
    assert first["clients"] == [{"name": "A", "phone": "+79991234567", "email": "", "amount": 5}]
    assert (await c.get("/api/clients")).json() == first
    assert calls["n"] == 2  # GET взял из кэша
