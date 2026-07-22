"""実サービス結合テスト用の疎通確認ヘルパー。"""

import httpx
import pytest


def skip_if_unreachable(url: str, params: dict[str, object], service_name: str) -> None:
	"""上流へ疎通確認し、到達不能ならモジュールごとスキップする。

	捕捉するのは接続そのものが成立しない `ConnectError` / `ConnectTimeout` だけに絞る。
	`ReadTimeout`・`RemoteProtocolError`・`ProxyError` などは接続が成立した後の異常であり、
	上流の劣化・仕様変更として結合テストが検出すべき回帰のため、スキップせず失敗させる。
	4xx/5xx も同じ理由で `raise_for_status()` を呼ばず素通りさせる。
	"""
	try:
		with httpx.Client(timeout=10.0) as client:
			client.get(url, params=params)
	except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
		pytest.skip(
			f"{service_name} へ接続できないためスキップ: {exc}",
			allow_module_level=True,
		)
