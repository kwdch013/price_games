"""実 Steam Store API への結合テスト

外部サービス（Steam）に依存し CI では不安定になりうるため、既定では実行しない。
`STEAM_INTEGRATION=1` を指定したときだけ実行する opt-in 方式とする
（ローカルや専用ジョブでの実接続検証を想定）。指定時でも、ネットワークに
到達できない場合だけモジュールごと自動スキップする。
"""

import asyncio
import os

import httpx
import pytest

from app.services import steam
from tests.upstream_probe import skip_if_unreachable

pytestmark = pytest.mark.integration

# 外部依存のため既定ではスキップ。opt-in のときだけ実接続を試みる。
if not os.getenv("STEAM_INTEGRATION"):
	pytest.skip(
		"STEAM_INTEGRATION 未設定のためスキップ（実 Steam 結合テストは opt-in）",
		allow_module_level=True,
	)

skip_if_unreachable(
	steam.SEARCH_URL,
	{"term": "portal", "l": "japanese", "cc": "jp"},
	"Steam",
)


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
