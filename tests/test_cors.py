"""CORS 許可オリジンの単体テスト

別サーバー（LAN 内の別マシン）のブラウザからアクセスされる場合、オリジンは
`http://<サーバーの LAN IP>:5173` になる。これが許可されることを保証する。
"""

import re

from fastapi.testclient import TestClient

from app.cors import LOCAL_NETWORK_ORIGIN_REGEX, cors_options, parse_origins
from app.main import app

client = TestClient(app)


class TestParseOrigins:
	"""CORS_ORIGINS（カンマ区切り）の解釈"""

	def test_none_is_empty(self) -> None:
		assert parse_origins(None) == []

	def test_splits_and_strips(self) -> None:
		raw = "https://a.example.com, https://b.example.com"
		assert parse_origins(raw) == ["https://a.example.com", "https://b.example.com"]

	def test_ignores_empty_elements(self) -> None:
		assert parse_origins(" , https://a.example.com ,, ") == ["https://a.example.com"]


class TestLocalNetworkRegex:
	"""ローカルネットワーク判定の正規表現"""

	def test_allows_local_origins(self) -> None:
		allowed = [
			"http://localhost:5173",
			"http://127.0.0.1:5173",
			"http://192.168.0.100:5173",
			"http://10.0.0.1:5173",
			"http://172.16.0.5:5173",
			"http://172.31.255.254:8010",
			"http://mypc.local:5173",
			"http://192.168.0.100",  # ポート省略（80 番）
		]
		for origin in allowed:
			assert re.fullmatch(LOCAL_NETWORK_ORIGIN_REGEX, origin), origin

	def test_rejects_public_origins(self) -> None:
		rejected = [
			"https://evil.example.com",
			"http://192.168.0.100.evil.com",  # 前方一致での回避を防ぐ
			"http://172.32.0.1:5173",  # プライベート範囲外
			"http://11.0.0.1:5173",
			"http://localhost.evil.com",
		]
		for origin in rejected:
			assert not re.fullmatch(LOCAL_NETWORK_ORIGIN_REGEX, origin), origin


class TestCorsOptions:
	"""CORSMiddleware へ渡す引数の組み立て"""

	def test_default_has_regex_and_no_explicit_origin(self) -> None:
		opts = cors_options({})
		assert opts["allow_origin_regex"] == LOCAL_NETWORK_ORIGIN_REGEX
		assert opts["allow_origins"] == []

	def test_env_origins_are_added(self) -> None:
		opts = cors_options({"CORS_ORIGINS": "https://games.example.com"})
		assert opts["allow_origins"] == ["https://games.example.com"]


class TestPreflight:
	"""実アプリでのプリフライト応答"""

	def test_allows_lan_origin(self) -> None:
		"""LAN の別マシンから開いたフロントのオリジンを許可する"""
		res = client.options(
			"/games",
			headers={
				"Origin": "http://192.168.0.100:5173",
				"Access-Control-Request-Method": "GET",
			},
		)
		assert res.status_code == 200
		assert res.headers["access-control-allow-origin"] == "http://192.168.0.100:5173"

	def test_allows_localhost_origin(self) -> None:
		"""従来どおりローカル開発（localhost:5173）も許可する"""
		res = client.options(
			"/games",
			headers={
				"Origin": "http://localhost:5173",
				"Access-Control-Request-Method": "GET",
			},
		)
		assert res.status_code == 200
		assert res.headers["access-control-allow-origin"] == "http://localhost:5173"

	def test_rejects_unknown_origin(self) -> None:
		"""外部サイトからの呼び出しは許可しない"""
		res = client.options(
			"/games",
			headers={
				"Origin": "https://evil.example.com",
				"Access-Control-Request-Method": "GET",
			},
		)
		assert "access-control-allow-origin" not in res.headers
