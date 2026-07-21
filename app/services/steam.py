"""Steam Store API 連携（検索・詳細取得と正規化）

Steam Store の公開 API（キー不要）を httpx で叩き、アプリ内スキーマへ正規化する。
HTTP 呼び出し（async）と、レスポンス変換（純関数）を分け、変換部を単体テストしやすくする。
"""

from __future__ import annotations

import httpx

from app.schemas import SteamAppDetail, SteamSearchItem

# cc=jp / l=japanese で日本語・日本円の結果を得る
SEARCH_URL = "https://store.steampowered.com/api/storesearch"
DETAIL_URL = "https://store.steampowered.com/api/appdetails"


def parse_price_jpy(price_overview: dict | None) -> int | None:
	"""price_overview.final を円へ換算する。

	Steam の価格は最小通貨単位×100（JPY も円×100）で返るため 100 で割る。
	価格情報が無い（無料・未取得）場合は None。
	"""
	if not price_overview:
		return None
	final = price_overview.get("final")
	if final is None:
		return None
	return int(final) // 100


def normalize_search(raw: dict) -> list[SteamSearchItem]:
	"""storesearch のレスポンスを検索候補の一覧へ変換する"""
	items = raw.get("items") or []
	result: list[SteamSearchItem] = []
	for it in items:
		appid = it.get("id")
		name = it.get("name")
		if appid is None or not name:
			continue
		result.append(
			SteamSearchItem(
				appid=int(appid),
				name=str(name),
				tiny_image=it.get("tiny_image"),
				price=parse_price_jpy(it.get("price")),
			)
		)
	return result


def normalize_detail(raw: dict, appid: int) -> SteamAppDetail | None:
	"""appdetails のレスポンスを詳細へ変換する。取得失敗（success=False）は None。"""
	entry = raw.get(str(appid))
	if not entry or not entry.get("success"):
		return None
	data = entry.get("data") or {}
	genres = [g.get("description") for g in (data.get("genres") or []) if g.get("description")]
	release = data.get("release_date") or {}
	return SteamAppDetail(
		appid=int(data.get("steam_appid", appid)),
		name=str(data.get("name", "")),
		release_date=release.get("date") or None,
		current_price=parse_price_jpy(data.get("price_overview")),
		header_image=data.get("header_image"),
		short_description=data.get("short_description"),
		genres=genres,
	)


async def search_games(term: str, client: httpx.AsyncClient) -> list[SteamSearchItem]:
	"""タイトル文字列から検索候補を取得する"""
	resp = await client.get(
		SEARCH_URL, params={"term": term, "l": "japanese", "cc": "jp"}
	)
	resp.raise_for_status()
	return normalize_search(resp.json())


async def get_app_detail(appid: int, client: httpx.AsyncClient) -> SteamAppDetail | None:
	"""appid からアプリ詳細を取得する。存在しなければ None。"""
	resp = await client.get(
		DETAIL_URL, params={"appids": appid, "cc": "jp", "l": "japanese"}
	)
	resp.raise_for_status()
	return normalize_detail(resp.json(), appid)
