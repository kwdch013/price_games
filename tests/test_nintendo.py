"""Nintendo eShop 連携の単体テスト

- 正規化（純関数）: 検索結果の絞り込み・サムネイル URL の組み立て・セール価格の採用
- HTTP 呼び出し: httpx.MockTransport で Nintendo を差し替え、変換まで通す
- ルーター: TestClient から /nintendo/* を叩き、失敗時のハンドリングも検証する
外部（実 Nintendo）へは接続しない。
"""

import asyncio
from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.nintendo import get_client
from app.services import nintendo

# ---- サンプルレスポンス（実 Nintendo の構造を模したもの） ---------------------

# search.nintendo.jp: 価格は float、iurl は CDN ハッシュか URL のどちらか
_SEARCH_RAW = {
	"result": {
		"total": 5,
		"items": [
			{
				"title": "スプラトゥーン3",
				"nsuid": "70010000046394",
				"hard": "1_HAC",
				"sform_n": "パッケージ版／ダウンロード版",
				"iurl": "be6eb6c8e642eb104ab329de6fb840c0",
				"price": 6500.0,
				"dprice": 6500.0,
				"current_price": 6500.0,
				"sale_flg": "0",
			},
			{
				"title": "スプラトゥーン レイダース",
				"nsuid": "70010000122823",
				"hard": "05_BEE",
				"sform_n": "パッケージ版／ダウンロード版",
				# iurl が URL 形式で来ることもある
				"iurl": "https://example.com/raiders.png",
				"price": 6480.0,
				"current_price": 6480.0,
				"sale_flg": "0",
			},
			{
				# ダウンロード版が無い（未発売など）: nsuid が null
				"title": "ゼルダの伝説 時のオカリナ",
				"nsuid": None,
				"hard": "1_HAC",
				"iurl": None,
				"current_price": None,
			},
			# 対象外の機種（積みゲー管理の対象は Switch 系のみ）
			{"title": "amiibo リンク", "nsuid": "70050000000001", "hard": "9_amiibo"},
			{"title": "3DS のソフト", "nsuid": "50010000000002", "hard": "2_CTR"},
		],
	}
}

# api.ec.nintendo.com: セール中のみ discount_price が入る
_PRICE_SALE_RAW = {
	"personalized": False,
	"country": "JP",
	"prices": [
		{
			"title_id": 70070000037189,
			"sales_status": "onsale",
			"regular_price": {"amount": "2,358円", "currency": "JPY", "raw_value": "2358"},
			"discount_price": {
				"amount": "471円",
				"currency": "JPY",
				"raw_value": "471",
				"start_datetime": "2026-07-17T15:00:00Z",
				"end_datetime": "2026-07-31T14:59:59Z",
			},
		}
	],
}

_PRICE_REGULAR_RAW = {
	"personalized": False,
	"country": "JP",
	"prices": [
		{
			"title_id": 70010000046394,
			"sales_status": "onsale",
			"regular_price": {"amount": "6,500円", "currency": "JPY", "raw_value": "6500"},
		}
	],
}

_PRICE_NOT_FOUND_RAW = {
	"personalized": False,
	"country": "JP",
	"prices": [{"title_id": 70010000000001, "sales_status": "not_found"}],
}


# ---- 正規化（純関数） --------------------------------------------------------


def test_サムネイルはハッシュならCDNのURLへ変換する() -> None:
	url = nintendo.build_thumbnail("be6eb6c8e642eb104ab329de6fb840c0")
	assert url == "https://img-eshop.cdn.nintendo.net/i/be6eb6c8e642eb104ab329de6fb840c0.jpg"


def test_サムネイルがURL形式ならそのまま使う() -> None:
	assert nintendo.build_thumbnail("https://example.com/x.png") == "https://example.com/x.png"


def test_サムネイルが無ければNone() -> None:
	assert nintendo.build_thumbnail(None) is None
	assert nintendo.build_thumbnail("") is None


def test_検索候補はSwitch系のみに絞る() -> None:
	items = nintendo.normalize_search(_SEARCH_RAW)
	# amiibo（9_amiibo）と 3DS（2_CTR）は除外される
	assert [i.title for i in items] == [
		"スプラトゥーン3",
		"スプラトゥーン レイダース",
		"ゼルダの伝説 時のオカリナ",
	]


def test_検索候補を正規化する() -> None:
	items = nintendo.normalize_search(_SEARCH_RAW)
	assert items[0].nsuid == "70010000046394"
	assert items[0].hardware == "Nintendo Switch"
	assert items[0].price == 6500  # float から int へ
	assert items[0].thumbnail is not None
	# Switch 2 の機種名も解決する
	assert items[1].hardware == "Nintendo Switch 2"


def test_ダウンロード版が無い候補はnsuidと価格がNone() -> None:
	item = nintendo.normalize_search(_SEARCH_RAW)[2]
	assert item.nsuid is None
	assert item.price is None
	assert item.thumbnail is None


def test_検索結果が空でも壊れない() -> None:
	assert nintendo.normalize_search({"result": {"items": []}}) == []
	assert nintendo.normalize_search({}) == []


def test_セール中はセール価格を現在価格に採用する() -> None:
	price = nintendo.normalize_price(_PRICE_SALE_RAW, "70070000037189")
	assert price is not None
	assert price.regular_price == 2358
	assert price.current_price == 471
	assert price.on_sale is True
	assert price.sale_end == "2026-07-31T14:59:59Z"


def test_通常時は定価を現在価格に採用する() -> None:
	price = nintendo.normalize_price(_PRICE_REGULAR_RAW, "70010000046394")
	assert price is not None
	assert price.regular_price == 6500
	assert price.current_price == 6500
	assert price.on_sale is False
	assert price.sale_end is None


def test_存在しないnsuidはNone() -> None:
	assert nintendo.normalize_price(_PRICE_NOT_FOUND_RAW, "70010000000001") is None


def test_価格が空の応答はNone() -> None:
	assert nintendo.normalize_price({"prices": []}, "70010000046394") is None
	assert nintendo.normalize_price({}, "70010000046394") is None


def test_問い合わせたnsuid以外の価格は採用しない() -> None:
	# 別 ID の結果しか含まない応答を取り違えない
	assert nintendo.normalize_price(_PRICE_REGULAR_RAW, "70010000099999") is None


# ---- HTTP 呼び出し（MockTransport） ------------------------------------------


def _mock_client(handler: httpx.MockTransport) -> httpx.AsyncClient:
	return httpx.AsyncClient(transport=handler)


def test_search_gamesは検索APIを叩いて正規化する() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		assert "search.json" in request.url.path
		assert request.url.params.get("q") == "スプラトゥーン"
		return httpx.Response(200, json=_SEARCH_RAW)

	async def _run() -> list[object]:
		async with _mock_client(httpx.MockTransport(handler)) as client:
			return await nintendo.search_games("スプラトゥーン", client)  # type: ignore[return-value]

	items = asyncio.run(_run())
	assert len(items) == 3


def test_get_priceは価格APIを叩いて正規化する() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		assert "price" in request.url.path
		assert request.url.params.get("ids") == "70070000037189"
		assert request.url.params.get("country") == "JP"
		return httpx.Response(200, json=_PRICE_SALE_RAW)

	async def _run() -> object:
		async with _mock_client(httpx.MockTransport(handler)) as client:
			return await nintendo.get_price("70070000037189", client)

	price = asyncio.run(_run())
	assert price is not None
	assert price.current_price == 471  # type: ignore[attr-defined]


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
def price_client() -> Iterator[TestClient]:
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(200, json=_PRICE_SALE_RAW)

	yield from _override_with(httpx.MockTransport(handler))


def test_検索APIが候補一覧を返す(search_client: TestClient) -> None:
	res = search_client.get("/nintendo/search", params={"q": "スプラトゥーン"})
	assert res.status_code == 200
	body = res.json()
	assert body[0]["nsuid"] == "70010000046394"
	assert body[0]["hardware"] == "Nintendo Switch"
	assert body[0]["price"] == 6500


def test_検索クエリが空なら422(search_client: TestClient) -> None:
	assert search_client.get("/nintendo/search", params={"q": ""}).status_code == 422


def test_価格APIがセール価格を返す(price_client: TestClient) -> None:
	res = price_client.get("/nintendo/price/70070000037189")
	assert res.status_code == 200
	body = res.json()
	assert body["current_price"] == 471
	assert body["regular_price"] == 2358
	assert body["on_sale"] is True


def test_存在しないnsuidは404() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(200, json=_PRICE_NOT_FOUND_RAW)

	gen = _override_with(httpx.MockTransport(handler))
	client = next(gen)
	assert client.get("/nintendo/price/70010000000001").status_code == 404


def test_nsuidが数字以外なら422(price_client: TestClient) -> None:
	assert price_client.get("/nintendo/price/abc").status_code == 422


def test_上流障害は502() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		raise httpx.ConnectError("接続できません")

	gen = _override_with(httpx.MockTransport(handler))
	client = next(gen)
	assert client.get("/nintendo/search", params={"q": "x"}).status_code == 502
	assert client.get("/nintendo/price/70010000046394").status_code == 502
