"""上流 HTTP API の応答検証に関する共通処理"""

from __future__ import annotations

import httpx


class UpstreamResponseError(Exception):
	"""上流の応答が想定外（JSON でない・型が違う）であることを表す"""


def parse_json_object(resp: httpx.Response) -> dict:
	"""応答を JSON オブジェクトとして読む。想定外なら専用例外を送出する"""
	try:
		data = resp.json()
	except ValueError as exc:
		# 上流は障害時にも HTTP 200 で HTML を返すことがある
		raise UpstreamResponseError("応答が JSON ではありません") from exc
	if not isinstance(data, dict):
		raise UpstreamResponseError("応答の形式が想定と異なります")
	return data
