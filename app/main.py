"""FastAPI エントリポイント（Issue #1: 最小起動）"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
	"""起動時に DB を初期化する"""
	init_db()
	yield


app = FastAPI(title="price_games", version="0.1.0", lifespan=lifespan)

# 開発時は Vite dev server（別ポート）からアクセスするため CORS を許可する
app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:5173"],
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
	"""ヘルスチェック。CI と死活監視で使用する"""
	return {"status": "ok"}
