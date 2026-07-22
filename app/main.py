"""FastAPI エントリポイント"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.cors import cors_options
from app.db import init_db
from app.routers import games, nintendo, steam


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
	"""起動時に DB を初期化する"""
	init_db()
	yield


app = FastAPI(title="price_games", version="0.1.0", lifespan=lifespan)

# Vite dev server（別ポート）や LAN 内の別マシンからアクセスするため CORS を許可する
app.add_middleware(CORSMiddleware, **cors_options())

app.include_router(games.router)
app.include_router(steam.router)
app.include_router(nintendo.router)


@app.get("/health")
def health() -> dict[str, str]:
	"""ヘルスチェック。CI と死活監視で使用する"""
	return {"status": "ok"}
