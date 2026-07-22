"""実 Nintendo（search.nintendo.jp / api.ec.nintendo.com）への結合テスト

外部サービスに依存し CI では不安定になりうるため、既定では実行しない。
`NINTENDO_INTEGRATION=1` を指定したときだけ実行する opt-in 方式とする
（ローカルや専用ジョブでの実接続検証を想定）。指定時でも、上流へ接続できない
場合はモジュールごと自動スキップする。
"""

import asyncio
import os

import httpx
import pytest

from app.services import nintendo
from tests.upstream_probe import skip_if_unreachable

pytestmark = pytest.mark.integration

# 外部依存のため既定ではスキップ。opt-in のときだけ実接続を試みる。
if not os.getenv("NINTENDO_INTEGRATION"):
	pytest.skip(
		"NINTENDO_INTEGRATION 未設定のためスキップ（実 Nintendo 結合テストは opt-in）",
		allow_module_level=True,
	)

skip_if_unreachable(
	nintendo.SEARCH_URL,
	{"q": "スプラトゥーン", "opt_sshop": 1, "limit": 1},
	"Nintendo",
)


def test_実検索でSwitchの候補が返る() -> None:
	async def _run() -> list[object]:
		async with httpx.AsyncClient(timeout=10.0) as client:
			return await nintendo.search_games("スプラトゥーン", client)  # type: ignore[return-value]

	items = asyncio.run(_run())
	assert len(items) >= 1
	assert items[0].title  # type: ignore[attr-defined]
	# 機種は Switch 系のみに正規化されている
	assert all(i.hardware in nintendo.HARDWARE_NAMES.values() for i in items)  # type: ignore[attr-defined]


def test_実価格取得で現在価格が取れる() -> None:
	# スプラトゥーン3（販売が安定している nsuid）
	async def _run() -> object:
		async with httpx.AsyncClient(timeout=10.0) as client:
			return await nintendo.get_price("70010000046394", client)

	price = asyncio.run(_run())
	assert price is not None
	assert price.regular_price > 0  # type: ignore[attr-defined]
	# 現在価格は定価以下（セール中はセール価格が入る）
	assert 0 < price.current_price <= price.regular_price  # type: ignore[attr-defined]


def test_存在しないnsuidはNone() -> None:
	async def _run() -> object:
		async with httpx.AsyncClient(timeout=10.0) as client:
			return await nintendo.get_price("70010000000001", client)

	assert asyncio.run(_run()) is None
