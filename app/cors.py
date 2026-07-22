"""CORS 許可オリジンの構築

開発サーバーは LAN 内の別マシンのブラウザからも開かれるため、オリジンは
`http://localhost:5173` に固定できず `http://<サーバーの LAN IP>:5173` にもなる。
そこでプライベート IP レンジ・localhost・`*.local` を正規表現で許可し、
それ以外を許可したい場合のみ環境変数 `CORS_ORIGINS`（カンマ区切り）で明示する。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

# IPv4 の 1 オクテット（0-255）。`10.999.999.999` のような無効値を許可しないため範囲を限定する
_OCTET = r"(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
# ポート番号（1-65535）
_PORT = r"(6553[0-5]|655[0-2]\d|65[0-4]\d\d|6[0-4]\d{3}|[1-5]\d{4}|[1-9]\d{0,3})"

# ローカルネットワークからのオリジン。fullmatch 前提のため、
# `http://192.168.0.100.evil.com` のような前方一致での回避は成立しない。
LOCAL_NETWORK_ORIGIN_REGEX = (
	r"https?://("
	r"localhost"
	rf"|127\.{_OCTET}\.{_OCTET}\.{_OCTET}"
	rf"|10\.{_OCTET}\.{_OCTET}\.{_OCTET}"
	rf"|172\.(1[6-9]|2\d|3[01])\.{_OCTET}\.{_OCTET}"
	rf"|192\.168\.{_OCTET}\.{_OCTET}"
	r"|[A-Za-z0-9-]+\.local"
	rf")(:{_PORT})?"
)


def parse_origins(raw: str | None) -> list[str]:
	"""カンマ区切りの `CORS_ORIGINS` を一覧へ変換する（空要素は無視）"""
	if not raw:
		return []
	return [part.strip() for part in raw.split(",") if part.strip()]


def cors_options(env: Mapping[str, str] | None = None) -> dict[str, Any]:
	"""`CORSMiddleware` へ渡す引数を組み立てる"""
	source = os.environ if env is None else env
	return {
		"allow_origins": parse_origins(source.get("CORS_ORIGINS")),
		"allow_origin_regex": LOCAL_NETWORK_ORIGIN_REGEX,
		"allow_methods": ["*"],
		"allow_headers": ["*"],
	}
