"""Nintendo eShop 連携（検索・現在価格の取得と正規化）

いずれもキー不要の公開エンドポイントを httpx で叩き、アプリ内スキーマへ正規化する。

- 検索: `search.nintendo.jp` … タイトル文字列から nsuid（商品 ID）を引く
- 価格: `api.ec.nintendo.com` … nsuid から定価とセール価格を引く

検索結果にも価格（`current_price`）は含まれるが、セール反映の正確さは価格 API が正となるため、
候補選択時に価格 API で確定させる想定。HTTP 呼び出し（async）と変換（純関数）を分けている。
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import httpx

from app.schemas import NintendoPrice, NintendoSearchItem
from app.services.upstream import UpstreamResponseError, parse_json_object


SEARCH_URL = "https://search.nintendo.jp/nintendo_soft/search.json"
PRICE_URL = "https://api.ec.nintendo.com/v1/price"

# サムネイルがハッシュ値で返る場合の CDN ベース URL
IMAGE_BASE_URL = "https://img-eshop.cdn.nintendo.net/i/"

# 対象とする機種コード → 表示名。積みゲー管理の対象は Switch 系のみとし、
# 3DS・Wii U・amiibo・アクセサリは候補から除外する。
HARDWARE_NAMES = {
	"1_HAC": "Nintendo Switch",
	"05_BEE": "Nintendo Switch 2",
}

# 検索の取得件数（サジェスト用途のため多すぎても使わない）
SEARCH_LIMIT = 20


def build_thumbnail(iurl: str | None) -> str | None:
	"""`iurl` をサムネイル URL へ変換する。

	URL 形式ならそのまま、CDN のハッシュ値なら eShop の画像 URL を組み立てる。
	"""
	if not iurl:
		return None
	if iurl.startswith(("http://", "https://")):
		return iurl
	return f"{IMAGE_BASE_URL}{iurl}.jpg"


def parse_price_yen(value: object) -> int | None:
	"""価格（float・文字列）を円の整数へ変換する。

	円に小数は無いため、整数で表せない値・負数・非数値・無限大は
	黙って丸めず None（価格不明）として扱う。float を経由すると
	大きな値で丸めや OverflowError が起きるため Decimal を使う。
	"""
	# bool は int のサブクラスなので明示的に除外する
	if value is None or isinstance(value, bool):
		return None
	try:
		amount = Decimal(str(value))
	except InvalidOperation, ValueError:
		return None
	if not amount.is_finite() or amount < 0 or amount != amount.to_integral_value():
		return None
	return int(amount)


def normalize_search(raw: dict) -> list[NintendoSearchItem]:
	"""検索レスポンスを候補一覧へ変換する（Switch 系のみ）。

	上流の仕様変更で型が変わっても例外にせず「候補なし」として扱う。
	"""
	container = raw.get("result")
	items = container.get("items") if isinstance(container, dict) else None
	if not isinstance(items, list):
		return []
	result: list[NintendoSearchItem] = []
	for it in items:
		if not isinstance(it, dict):
			continue
		title = it.get("title")
		hardware = HARDWARE_NAMES.get(str(it.get("hard")))
		if not title or hardware is None:
			continue
		nsuid = it.get("nsuid")
		result.append(
			NintendoSearchItem(
				nsuid=str(nsuid) if nsuid else None,
				title=str(title),
				hardware=hardware,
				thumbnail=build_thumbnail(it.get("iurl")),
				price=parse_price_yen(it.get("current_price")),
			)
		)
	return result


def _raw_value(price: object) -> int | None:
	"""価格オブジェクトの `raw_value` を円の整数へ変換する"""
	if not isinstance(price, dict):
		return None
	return parse_price_yen(price.get("raw_value"))


def normalize_price(raw: dict, nsuid: str) -> NintendoPrice | None:
	"""価格レスポンスを正規化する。該当なし・販売情報なしは None。

	複数 ID をまとめて問い合わせできる API のため、応答から問い合わせた nsuid の
	エントリだけを取り出す（取り違え防止）。
	"""
	entries = raw.get("prices")
	if not isinstance(entries, list):
		return None
	entry = next(
		(e for e in entries if isinstance(e, dict) and str(e.get("title_id")) == str(nsuid)),
		None,
	)
	if entry is None or entry.get("sales_status") == "not_found":
		return None
	regular = _raw_value(entry.get("regular_price"))
	if regular is None:
		return None
	discount = entry.get("discount_price")
	discounted = _raw_value(discount)
	if discounted is None:
		return NintendoPrice(
			nsuid=str(nsuid), regular_price=regular, current_price=regular, on_sale=False
		)
	return NintendoPrice(
		nsuid=str(nsuid),
		regular_price=regular,
		current_price=discounted,
		on_sale=True,
		sale_end=discount.get("end_datetime") if isinstance(discount, dict) else None,
	)


async def search_games(term: str, client: httpx.AsyncClient) -> list[NintendoSearchItem]:
	"""タイトル文字列から検索候補を取得する"""
	resp = await client.get(
		SEARCH_URL,
		# opt_sshop=1 はストア掲載商品に絞るためのオプション
		params={"q": term, "opt_sshop": 1, "limit": SEARCH_LIMIT},
	)
	resp.raise_for_status()
	return normalize_search(parse_json_object(resp))


async def get_price(nsuid: str, client: httpx.AsyncClient) -> NintendoPrice | None:
	"""nsuid から現在価格を取得する。存在しなければ None。"""
	resp = await client.get(PRICE_URL, params={"country": "JP", "lang": "ja", "ids": nsuid})
	resp.raise_for_status()
	return normalize_price(parse_json_object(resp), nsuid)
