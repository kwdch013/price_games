"""Nintendo eShop 価格取得 API（検索・現在価格）"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.schemas import NintendoPrice, NintendoSearchItem
from app.services import nintendo

router = APIRouter(prefix="/nintendo", tags=["nintendo"])


async def get_client() -> AsyncIterator[httpx.AsyncClient]:
	"""Nintendo 問い合わせ用の HTTP クライアント（テストで差し替え可能にするため DI）"""
	async with httpx.AsyncClient(timeout=10.0) as client:
		yield client


@router.get("/search", response_model=list[NintendoSearchItem])
async def search(
	q: str = Query(min_length=1, description="検索するタイトル文字列"),
	client: httpx.AsyncClient = Depends(get_client),
) -> list[NintendoSearchItem]:
	"""タイトルから Switch 系の候補を検索する"""
	try:
		return await nintendo.search_games(q, client)
	# 上流の障害・タイムアウトに加え、HTTP 200 で返る想定外の応答も 502 にする
	except (httpx.HTTPError, nintendo.UpstreamResponseError) as exc:
		raise HTTPException(
			status_code=status.HTTP_502_BAD_GATEWAY, detail="Nintendo へ接続できません"
		) from exc


@router.get("/price/{nsuid}", response_model=NintendoPrice)
async def price(
	# nsuid は数字のみ。誤ったパスをそのまま上流へ投げないよう入口で弾く
	nsuid: str = Path(pattern=r"^\d+$", description="eShop の商品 ID"),
	client: httpx.AsyncClient = Depends(get_client),
) -> NintendoPrice:
	"""nsuid から現在価格（セール中はセール価格）を取得する"""
	try:
		found = await nintendo.get_price(nsuid, client)
	except (httpx.HTTPError, nintendo.UpstreamResponseError) as exc:
		raise HTTPException(
			status_code=status.HTTP_502_BAD_GATEWAY, detail="Nintendo へ接続できません"
		) from exc
	if found is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品が見つかりません")
	return found
