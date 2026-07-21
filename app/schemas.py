"""API 入出力スキーマ（Pydantic）"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Medium(str, Enum):
	"""媒体の選択肢"""

	pc_steam = "PC(Steam)"
	pc_other = "PC(その他)"
	ps5 = "PS5"
	ps4 = "PS4"
	switch = "Nintendo Switch"
	xbox = "Xbox"
	other = "その他"


class GameCreate(BaseModel):
	"""登録リクエスト"""

	title: str = Field(min_length=1)
	medium: Medium
	purchase_price: int = Field(ge=0)
	current_price: int | None = Field(default=None, ge=0)
	progress: int = Field(default=0, ge=0, le=100)
	note: str = ""
	steam_appid: int | None = None


class GameUpdate(BaseModel):
	"""部分更新リクエスト（指定した項目のみ更新）"""

	title: str | None = Field(default=None, min_length=1)
	medium: Medium | None = None
	purchase_price: int | None = Field(default=None, ge=0)
	current_price: int | None = Field(default=None, ge=0)
	progress: int | None = Field(default=None, ge=0, le=100)
	note: str | None = None
	steam_appid: int | None = None


class GameRead(BaseModel):
	"""レスポンス（損失計算を含む）"""

	id: int
	title: str
	medium: str
	purchase_price: int
	current_price: int | None
	progress: int
	note: str
	steam_appid: int | None
	created_at: datetime
	# 計算値
	pile_loss: int
	price_diff_loss: int | None


class Summary(BaseModel):
	"""ダッシュボード集計"""

	count: int
	total_pile_loss: int
	total_price_diff_loss: int
	total_loss: int
