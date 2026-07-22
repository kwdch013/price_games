"""DB モデル（SQLModel）"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, func
from sqlmodel import Field, SQLModel


def _now() -> datetime:
	"""登録日時のデフォルト（UTC）"""
	return datetime.now(timezone.utc)


class Game(SQLModel, table=True):
	"""購入したゲーム1件。金額は円（整数）で保持する。"""

	# API 層(Pydantic)に加え、直挿入経路でも不正値を弾くための DB 制約
	__table_args__ = (
		CheckConstraint("purchase_price >= 0", name="ck_game_purchase_price_nonneg"),
		CheckConstraint(
			"current_price IS NULL OR current_price >= 0",
			name="ck_game_current_price_nonneg",
		),
		CheckConstraint("progress BETWEEN 0 AND 100", name="ck_game_progress_range"),
	)

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
	created_at: datetime = Field(
		default_factory=_now,
		sa_column=Column(
			DateTime(timezone=True),
			nullable=False,
			server_default=func.now(),
		),
	)


class PriceHistory(SQLModel, table=True):
	"""ゲーム1件の価格推移。current_price のスナップショットを時系列で残す。"""

	__tablename__ = "price_history"

	# 直挿入経路でも負値を弾く DB 制約
	__table_args__ = (
		CheckConstraint("price >= 0", name="ck_price_history_price_nonneg"),
	)

	id: int | None = Field(default=None, primary_key=True)
	# 親 game 削除時は履歴も CASCADE で消す（DB 側で整合を保つ）
	game_id: int = Field(foreign_key="game.id", ondelete="CASCADE", index=True)
	price: int
	captured_at: datetime = Field(
		default_factory=_now,
		sa_column=Column(
			DateTime(timezone=True),
			nullable=False,
			server_default=func.now(),
		),
	)
