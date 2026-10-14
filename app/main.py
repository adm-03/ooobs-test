import asyncio
import os

import httpx
from fastapi import FastAPI, HTTPException

from app.domain import SyncResult, sync

SOURCE_URL = os.getenv("ORDERS_URL", "https://test.ooobs.ru/api/orders")
CACHE_TTL = float(os.getenv("CACHE_TTL_SECONDS", "30"))


class Syncer:
    """Держит последний успешный снимок. Каждая синхронизация заменяет его целиком, а не дописывает."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._snapshot: SyncResult | None = None
        self._fetched_at = 0.0
        self._lock = asyncio.Lock()  # параллельные запросы не должны дёргать источник N раз

    async def get(self, *, force: bool = False) -> SyncResult:
        async with self._lock:
            fresh = self._snapshot and (asyncio.get_running_loop().time() - self._fetched_at) < CACHE_TTL
            if force or not fresh:
                await self._refresh()
            assert self._snapshot is not None
            return self._snapshot

    async def _refresh(self) -> None:
        try:
            resp = await self._client.get(SOURCE_URL)
            resp.raise_for_status()
            orders = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            if self._snapshot is None:  # отдать устаревшее лучше, чем 5xx, но на холодном старте отдавать нечего
                raise HTTPException(502, "orders source unavailable") from exc
            return
        self._snapshot = sync(orders)
        self._fetched_at = asyncio.get_running_loop().time()


app = FastAPI(title="Orders sync")


def get_syncer() -> Syncer:
    # Лениво, а не через lifespan: в serverless (Vercel) lifespan не гарантирован.
    if not hasattr(app.state, "syncer"):
        app.state.syncer = Syncer(httpx.AsyncClient(timeout=10))
    return app.state.syncer


@app.get("/", response_model=SyncResult)
@app.get("/api/clients", response_model=SyncResult)
async def clients() -> SyncResult:
    return await get_syncer().get()


@app.post("/api/sync", response_model=SyncResult)
async def run_sync() -> SyncResult:
    return await get_syncer().get(force=True)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
