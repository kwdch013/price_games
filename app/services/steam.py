"""Steam Store API 連携（検索・詳細取得と正規化）

Steam Store の公開 API（キー不要）を httpx で叩き、アプリ内スキーマへ正規化する。
HTTP 呼び出し（async）と、レスポンス変換（純関数）を分け、変換部を単体テストしやすくする。
"""

from __future__ import annotations

import httpx

from app.schemas import SteamAppDetail, SteamSearchItem
from app.services.upstream import parse_json_object

# cc=jp / l=japanese で日本語・日本円の結果を得る
SEARCH_URL = "https://store.steampowered.com/api/storesearch"
DETAIL_URL = "https://store.steampowered.com/api/appdetails"


def parse_price_jpy(price_overview: object) -> int | None:
	"""price_overview.final を円へ換算する。

	Steam の価格は最小通貨単位×100（JPY も円×100）で返るため 100 で割る。
	価格情報が無い（無料・未取得）場合は None。
	"""
	if not isinstance(price_overview, dict):
		return None
	final = price_overview.get("final")
	# bool は int のサブクラスなので明示的に除外する
	if final is None or isinstance(final, bool):
		return None
	try:
		# JSON は Infinity/NaN を含みうる。int() は OverflowError/ValueError を投げる
		value = int(final)
	except TypeError, ValueError, OverflowError:
		return None
	# 負の価格は上流の異常。黙って通さず価格不明として扱う
	if value < 0:
		return None
	return value // 100


def normalize_search(raw: dict) -> list[SteamSearchItem]:
	"""storesearch のレスポンスを検索候補の一覧へ変換する"""
	items = raw.get("items")
	if not isinstance(items, list):
		return []
	result: list[SteamSearchItem] = []
	for it in items:
		if not isinstance(it, dict):
			continue
		appid = it.get("id")
		name = it.get("name")
		if appid is None or not name:
			continue
		try:
			parsed_appid = int(appid)
		except TypeError, ValueError, OverflowError:
			continue
		tiny_image = it.get("tiny_image")
		result.append(
			SteamSearchItem(
				appid=parsed_appid,
				name=str(name),
				tiny_image=tiny_image if isinstance(tiny_image, str) else None,
				price=parse_price_jpy(it.get("price")),
			)
		)
	return result


def normalize_detail(raw: dict, appid: int) -> SteamAppDetail | None:
	"""appdetails のレスポンスを詳細へ変換する。取得失敗（success=False）は None。"""
	entry = raw.get(str(appid))
	# success は真偽値。文字列 "false" などの truthy な非 bool を成功と誤認しない
	if not isinstance(entry, dict) or entry.get("success") is not True:
		return None
	data = entry.get("data")
	if not isinstance(data, dict):
		return None
	raw_genres = data.get("genres")
	genres = []
	if isinstance(raw_genres, list):
		genres = [
			str(description)
			for genre in raw_genres
			if isinstance(genre, dict) and (description := genre.get("description"))
		]
	release = data.get("release_date")
	release_date = release.get("date") if isinstance(release, dict) else None
	raw_appid = data.get("steam_appid", appid)
	try:
		parsed_appid = int(raw_appid)
	except TypeError, ValueError, OverflowError:
		parsed_appid = appid
	header_image = data.get("header_image")
	short_description = data.get("short_description")
	return SteamAppDetail(
		appid=parsed_appid,
		name=str(data.get("name", "")),
		release_date=release_date if isinstance(release_date, str) else None,
		current_price=parse_price_jpy(data.get("price_overview")),
		header_image=header_image if isinstance(header_image, str) else None,
		short_description=short_description if isinstance(short_description, str) else None,
		genres=genres,
	)


async def search_games(term: str, client: httpx.AsyncClient) -> list[SteamSearchItem]:
	"""タイトル文字列から検索候補を取得する"""
	resp = await client.get(
		SEARCH_URL, params={"term": term, "l": "japanese", "cc": "jp"}
	)
	resp.raise_for_status()
	return normalize_search(parse_json_object(resp))


async def get_app_detail(appid: int, client: httpx.AsyncClient) -> SteamAppDetail | None:
	"""appid からアプリ詳細を取得する。存在しなければ None。"""
	resp = await client.get(
		DETAIL_URL, params={"appids": appid, "cc": "jp", "l": "japanese"}
	)
	resp.raise_for_status()
	return normalize_detail(parse_json_object(resp), appid)
