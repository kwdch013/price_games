"""日時列を timezone-aware かつ DB 既定値付きにする

Revision ID: 0003_timestamp_tz_aware
Revises: 0002_price_history
Create Date: 2026-07-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_timestamp_tz_aware"
down_revision: str | None = "0002_price_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMP_COLUMNS = (
	("game", "created_at"),
	("price_history", "captured_at"),
)


def upgrade() -> None:
	for table_name, column_name in _TIMESTAMP_COLUMNS:
		if op.get_bind().dialect.name == "postgresql":
			op.alter_column(
				table_name,
				column_name,
				existing_type=sa.DateTime(),
				type_=sa.DateTime(timezone=True),
				server_default=sa.text("CURRENT_TIMESTAMP"),
				postgresql_using=f"{column_name} AT TIME ZONE 'UTC'",
			)
		else:
			# SQLite のテスト環境では ALTER COLUMN がないためテーブルを再構築する。
			with op.batch_alter_table(table_name) as batch_op:
				batch_op.alter_column(
					column_name,
					existing_type=sa.DateTime(),
					type_=sa.DateTime(timezone=True),
					server_default=sa.text("CURRENT_TIMESTAMP"),
				)


def downgrade() -> None:
	for table_name, column_name in reversed(_TIMESTAMP_COLUMNS):
		if op.get_bind().dialect.name == "postgresql":
			op.alter_column(
				table_name,
				column_name,
				existing_type=sa.DateTime(timezone=True),
				type_=sa.DateTime(),
				server_default=None,
				postgresql_using=f"{column_name} AT TIME ZONE 'UTC'",
			)
		else:
			with op.batch_alter_table(table_name) as batch_op:
				batch_op.alter_column(
					column_name,
					existing_type=sa.DateTime(timezone=True),
					type_=sa.DateTime(),
					server_default=None,
				)
