"""Steam メタデータ取得 API（検索・詳細）"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas import SteamAppDetail, SteamSearchItem
from app.services import steam

router = APIRouter(prefix="/steam", tags=["steam"])


async def get_client() -> AsyncIterator[httpx.AsyncClient]:
	"""Steam 問い合わせ用の HTTP クライアント（テストで差し替え可能にするため DI）"""
	async with httpx.AsyncClient(timeout=10.0) as client:
		yield client


@router.get("/search", response_model=list[SteamSearchItem])
async def search(
	q: str = Query(min_length=1, description="検索するタイトル文字列"),
	client: httpx.AsyncClient = Depends(get_client),
) -> list[SteamSearchItem]:
	"""タイトルから候補を検索する"""
	try:
		return await steam.search_games(q, client)
	except httpx.HTTPError as exc:  # 上流（Steam）の障害・タイムアウト
		raise HTTPException(
			status_code=status.HTTP_502_BAD_GATEWAY, detail="Steam へ接続できません"
		) from exc


@router.get("/apps/{appid}", response_model=SteamAppDetail)
async def app_detail(
	appid: int, client: httpx.AsyncClient = Depends(get_client)
) -> SteamAppDetail:
	"""appid から発売日・現在価格・画像などの詳細を取得する"""
	try:
		detail = await steam.get_app_detail(appid, client)
	except httpx.HTTPError as exc:
		raise HTTPException(
			status_code=status.HTTP_502_BAD_GATEWAY, detail="Steam へ接続できません"
		) from exc
	if detail is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND, detail="アプリが見つかりません"
		)
	return detail
