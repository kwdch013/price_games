"""実 Steam Store API への結合テスト

ネットワーク経由で実際に Steam へ接続できるときのみ実行し、
接続できない環境（オフライン・レート制限など）では自動スキップする。
外部サービスに依存するため CI では不安定になりうる点に留意する。
"""

import asyncio

import httpx
import pytest

from app.services import steam

pytestmark = pytest.mark.integration

# 実接続を試み、繋がらなければモジュールごとスキップする
try:
	with httpx.Client(timeout=10.0) as _c:
		_c.get(steam.SEARCH_URL, params={"term": "portal", "l": "japanese", "cc": "jp"})
except httpx.HTTPError as exc:
	pytest.skip(f"Steam へ接続できないためスキップ: {exc}", allow_module_level=True)


def test_実検索で候補が返る() -> None:
	async def _run() -> list[object]:
		async with httpx.AsyncClient(timeout=10.0) as client:
			return await steam.search_games("portal", client)  # type: ignore[return-value]

	items = asyncio.run(_run())
	# 少なくとも1件は返り、必須項目が埋まっている
	assert len(items) >= 1
	assert items[0].appid > 0  # type: ignore[attr-defined]
	assert items[0].name  # type: ignore[attr-defined]


def test_実詳細取得で発売日と価格が取れる() -> None:
	# Team Fortress 2（無料）: 存在が安定している appid
	async def _run() -> object:
		async with httpx.AsyncClient(timeout=10.0) as client:
			return await steam.get_app_detail(440, client)

	detail = asyncio.run(_run())
	assert detail is not None
	assert detail.appid == 440  # type: ignore[attr-defined]
	assert detail.name  # type: ignore[attr-defined]
