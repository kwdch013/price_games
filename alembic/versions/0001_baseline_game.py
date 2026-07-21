"""baseline: game テーブル（既存スキーマのベースライン）

現行の app.models.Game に対応する初期スキーマ。
既に game テーブルが存在する共有 DB では、適用せず `alembic stamp head` で
このリビジョンを「適用済み」として記録する。

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-21
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # AutoString（SQLModel の文字列型）を参照するため
from alembic import op

# リビジョン識別子
revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	op.create_table(
		"game",
		sa.Column("id", sa.Integer(), nullable=False),
		sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
		sa.Column("medium", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
		sa.Column("purchase_price", sa.Integer(), nullable=False),
		sa.Column("current_price", sa.Integer(), nullable=True),
		sa.Column("progress", sa.Integer(), nullable=False),
		sa.Column("note", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
		sa.Column("steam_appid", sa.Integer(), nullable=True),
		sa.Column("created_at", sa.DateTime(), nullable=False),
		# API 層に加え、直挿入経路でも不正値を弾くための DB 制約（モデルと一致）
		sa.CheckConstraint("purchase_price >= 0", name="ck_game_purchase_price_nonneg"),
		sa.CheckConstraint(
			"current_price IS NULL OR current_price >= 0",
			name="ck_game_current_price_nonneg",
		),
		sa.CheckConstraint("progress BETWEEN 0 AND 100", name="ck_game_progress_range"),
		sa.PrimaryKeyConstraint("id"),
	)


def downgrade() -> None:
	op.drop_table("game")
