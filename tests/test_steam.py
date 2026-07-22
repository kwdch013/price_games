"""Steam 連携の単体テスト

- 正規化（純関数）: レスポンス変換・欠損値の扱い・価格の円換算
- HTTP 呼び出し: httpx.MockTransport で Steam を差し替え、変換まで通す
- ルーター: TestClient から /steam/* を叩き、失敗時のハンドリングも検証する
外部（実 Steam）へは接続しない。
"""

import asyncio
from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.steam import get_client
from app.services import steam

# ---- サンプルレスポンス（実 Steam の構造を模したもの） -------------------------

# storesearch: price.final は最小通貨単位×100（JPY なら円×100）で返る
_SEARCH_RAW = {
	"total": 2,
	"items": [
		{
			"id": 1245620,
			"name": "ELDEN RING",
			"tiny_image": "https://example.com/eldenring.jpg",
			"price": {"currency": "JPY", "initial": 924000, "final": 924000},
		},
		# 価格情報が無い候補（無料 or 未取得）も来うる
		{"id": 570, "name": "Dota 2", "tiny_image": "https://example.com/dota2.jpg"},
	],
}

# appdetails: {"<appid>": {"success": bool, "data": {...}}}
_DETAIL_RAW = {
	"1245620": {
		"success": True,
		"data": {
			"steam_appid": 1245620,
			"name": "ELDEN RING",
			"release_date": {"coming_soon": False, "date": "2022年2月25日"},
			"price_overview": {"currency": "JPY", "initial": 924000, "final": 831600},
			"header_image": "https://example.com/header.jpg",
			"short_description": "君よ、エルデンリングの王となれ。",
			"genres": [
				{"id": "1", "description": "アクション"},
				{"id": "25", "description": "アドベンチャー"},
			],
		},
	}
}


# ---- 正規化（純関数） --------------------------------------------------------


def test_価格は円へ換算される() -> None:
	assert steam.parse_price_jpy({"final": 924000}) == 9240


def test_価格情報が無ければNone() -> None:
	assert steam.parse_price_jpy(None) is None
	assert steam.parse_price_jpy({}) is None


def test_想定外の価格はNone() -> None:
	# JSON は Infinity/NaN を含みうる。int() の OverflowError で 500 に漏らさない
	assert steam.parse_price_jpy({"final": float("inf")}) is None
	assert steam.parse_price_jpy({"final": float("nan")}) is None
	# 負の価格は上流の異常なので価格不明として扱う
	assert steam.parse_price_jpy({"final": -100}) is None
	assert steam.parse_price_jpy({"final": "924000"}) == 9240
	assert steam.parse_price_jpy({"final": "不正"}) is None
	assert steam.parse_price_jpy({"final": [924000]}) is None
	assert steam.parse_price_jpy({"final": True}) is None
	assert steam.parse_price_jpy(["想定外"]) is None


def test_検索候補を正規化する() -> None:
	items = steam.normalize_search(_SEARCH_RAW)
	assert len(items) == 2
	assert items[0].appid == 1245620
	assert items[0].name == "ELDEN RING"
	assert items[0].price == 9240
	# 価格情報の無い候補は price=None
	assert items[1].appid == 570
	assert items[1].price is None


def test_検索結果が空でも壊れない() -> None:
	assert steam.normalize_search({"total": 0, "items": []}) == []
	assert steam.normalize_search({}) == []


def test_詳細を正規化する() -> None:
	detail = steam.normalize_detail(_DETAIL_RAW, 1245620)
	assert detail is not None
	assert detail.appid == 1245620
	assert detail.name == "ELDEN RING"
	assert detail.release_date == "2022年2月25日"
	assert detail.current_price == 8316  # 831600 // 100
	assert detail.header_image == "https://example.com/header.jpg"
	assert detail.genres == ["アクション", "アドベンチャー"]


def test_詳細取得失敗はNone() -> None:
	assert steam.normalize_detail({"999": {"success": False}}, 999) is None
	assert steam.normalize_detail({}, 1245620) is None


def test_価格未設定の詳細はcurrent_priceがNone() -> None:
	raw = {"570": {"success": True, "data": {"steam_appid": 570, "name": "Dota 2"}}}
	detail = steam.normalize_detail(raw, 570)
	assert detail is not None
	assert detail.current_price is None
	assert detail.genres == []


def test_想定外の形の応答でも壊れない() -> None:
	# 上流の仕様変更で型が変わっても例外にせず「該当なし」として扱う
	assert steam.normalize_search({"items": {"id": 1}}) == []
	assert steam.normalize_search({"items": ["文字列"]}) == []
	assert steam.normalize_search({"items": [{"id": "不正", "name": "ゲーム"}]}) == []
	assert steam.normalize_detail({"440": "文字列"}, 440) is None
	assert steam.normalize_detail({"440": {"success": True, "data": "文字列"}}, 440) is None

	raw = {
		"440": {
			"success": True,
			"data": {
				"steam_appid": 440,
				"name": "Team Fortress 2",
				"genres": {"description": "アクション"},
				"release_date": "文字列",
			},
		}
	}
	detail = steam.normalize_detail(raw, 440)
	assert detail is not None
	assert detail.genres == []
	assert detail.release_date is None


def test_successがtruthyな非boolなら該当なし() -> None:
	# 文字列 "false" や 1 を成功と誤認すると、不正な応答から詳細を作ってしまう
	for success in ("false", 1, ["ok"]):
		raw = {"440": {"success": success, "data": {"steam_appid": 440, "name": "TF2"}}}
		assert steam.normalize_detail(raw, 440) is None


def test_appidが数値化できなくても壊れない() -> None:
	# int() が OverflowError を投げる値でも 500 に漏らさない
	assert steam.normalize_search({"items": [{"id": float("inf"), "name": "ゲーム"}]}) == []

	raw = {"440": {"success": True, "data": {"steam_appid": float("inf"), "name": "TF2"}}}
	detail = steam.normalize_detail(raw, 440)
	assert detail is not None
	# 上流の値が使えない場合は問い合わせた appid にフォールバックする
	assert detail.appid == 440


# ---- HTTP 呼び出し（MockTransport） ------------------------------------------


def _mock_client(handler: httpx.MockTransport) -> httpx.AsyncClient:
	return httpx.AsyncClient(transport=handler)


def test_search_gamesはStoreを叩いて正規化する() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		assert "storesearch" in request.url.path
		assert request.url.params.get("term") == "elden"
		return httpx.Response(200, json=_SEARCH_RAW)

	async def _run() -> list[object]:
		async with _mock_client(httpx.MockTransport(handler)) as client:
			return await steam.search_games("elden", client)  # type: ignore[return-value]

	items = asyncio.run(_run())
	assert [i.appid for i in items] == [1245620, 570]  # type: ignore[attr-defined]


def test_get_app_detailはappdetailsを叩いて正規化する() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		assert "appdetails" in request.url.path
		assert request.url.params.get("appids") == "1245620"
		return httpx.Response(200, json=_DETAIL_RAW)

	async def _run() -> object:
		async with _mock_client(httpx.MockTransport(handler)) as client:
			return await steam.get_app_detail(1245620, client)

	detail = asyncio.run(_run())
	assert detail is not None
	assert detail.name == "ELDEN RING"  # type: ignore[attr-defined]


# ---- ルーター（TestClient + 依存差し替え） -----------------------------------


def _override_with(handler: httpx.MockTransport) -> Iterator[TestClient]:
	async def _override() -> Iterator[httpx.AsyncClient]:
		async with httpx.AsyncClient(transport=handler) as client:
			yield client

	app.dependency_overrides[get_client] = _override
	yield TestClient(app)
	app.dependency_overrides.clear()


@pytest.fixture
def search_client() -> Iterator[TestClient]:
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(200, json=_SEARCH_RAW)

	yield from _override_with(httpx.MockTransport(handler))


@pytest.fixture
def detail_client() -> Iterator[TestClient]:
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(200, json=_DETAIL_RAW)

	yield from _override_with(httpx.MockTransport(handler))


def test_検索APIが候補一覧を返す(search_client: TestClient) -> None:
	res = search_client.get("/steam/search", params={"q": "elden"})
	assert res.status_code == 200
	body = res.json()
	assert body[0]["appid"] == 1245620
	assert body[0]["price"] == 9240


def test_検索クエリが空なら422(search_client: TestClient) -> None:
	assert search_client.get("/steam/search", params={"q": ""}).status_code == 422


def test_詳細APIが自動入力用の情報を返す(detail_client: TestClient) -> None:
	res = detail_client.get("/steam/apps/1245620")
	assert res.status_code == 200
	body = res.json()
	assert body["current_price"] == 8316
	assert body["release_date"] == "2022年2月25日"


def test_存在しないappidは404() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(200, json={"999": {"success": False}})

	gen = _override_with(httpx.MockTransport(handler))
	client = next(gen)
	assert client.get("/steam/apps/999").status_code == 404
	next(gen, None)  # teardown


def test_Steam側エラーは502() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(500, text="Steam down")

	gen = _override_with(httpx.MockTransport(handler))
	client = next(gen)
	assert client.get("/steam/search", params={"q": "x"}).status_code == 502
	next(gen, None)  # teardown


def test_JSONでない応答も502() -> None:
	# 上流がエラーページ（HTTP 200 + HTML）を返すことがあるため 500 にしない
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(200, text="<html>error</html>")

	gen = _override_with(httpx.MockTransport(handler))
	client = next(gen)
	assert client.get("/steam/search", params={"q": "x"}).status_code == 502
	assert client.get("/steam/apps/440").status_code == 502
	next(gen, None)  # teardown


def test_JSONだが想定外の形なら502() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(200, json=["想定外"])

	gen = _override_with(httpx.MockTransport(handler))
	client = next(gen)
	assert client.get("/steam/search", params={"q": "x"}).status_code == 502
	assert client.get("/steam/apps/440").status_code == 502
	next(gen, None)  # teardown
