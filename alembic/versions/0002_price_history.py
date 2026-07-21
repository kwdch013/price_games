"""price_history テーブルを追加する

app.models.PriceHistory に対応する。game.id への FK（ON DELETE CASCADE）、
price >= 0 の CHECK 制約、game_id へのインデックスを持つ。

Revision ID: 0002_price_history
Revises: 0001_baseline
Create Date: 2026-07-21
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# リビジョン識別子
revision: str = "0002_price_history"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	op.create_table(
		"price_history",
		sa.Column("id", sa.Integer(), nullable=False),
		sa.Column("game_id", sa.Integer(), nullable=False),
		sa.Column("price", sa.Integer(), nullable=False),
		sa.Column("captured_at", sa.DateTime(), nullable=False),
		sa.CheckConstraint("price >= 0", name="ck_price_history_price_nonneg"),
		sa.ForeignKeyConstraint(
			["game_id"], ["game.id"], name="fk_price_history_game_id", ondelete="CASCADE"
		),
		sa.PrimaryKeyConstraint("id"),
	)
	op.create_index("ix_price_history_game_id", "price_history", ["game_id"])


def downgrade() -> None:
	op.drop_index("ix_price_history_game_id", table_name="price_history")
	op.drop_table("price_history")
