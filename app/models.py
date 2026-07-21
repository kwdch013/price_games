"""DB モデル（SQLModel）"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _now() -> datetime:
	"""登録日時のデフォルト（UTC）"""
	return datetime.now(timezone.utc)


class Game(SQLModel, table=True):
	"""購入したゲーム1件。金額は円（整数）で保持する。"""

	id: int | None = Field(default=None, primary_key=True)
	title: str
	medium: str
	purchase_price: int
	# 現在価格は取得できるまで任意（手入力 or 後の Steam 連携で補完）
	current_price: int | None = Field(default=None)
	# 進行度 0〜100（%）
	progress: int = Field(default=0)
	note: str = Field(default="")
	# Steam 連携用（後の Issue で使用）
	steam_appid: int | None = Field(default=None)
	created_at: datetime = Field(default_factory=_now)
