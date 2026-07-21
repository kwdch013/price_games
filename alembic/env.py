"""Alembic 実行環境の設定

接続先は環境変数 DATABASE_URL から取得する（alembic.ini にはパスワードを書かない）。
autogenerate を有効にするため、app.models を import して SQLModel のメタデータを
target_metadata に渡す。
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import app.models  # noqa: F401  # モデル登録の副作用のため import する

config = context.config

# DATABASE_URL を Alembic 設定へ反映する（未設定ならローカル開発向け既定）
_database_url = os.environ.get(
	"DATABASE_URL",
	"postgresql+psycopg://price_games:price_games@localhost:5432/price_games",
)
# set_main_option は ConfigParser の補間を通すため、パスワード等に含まれる
# `%`（URL エンコード時に出現）を `%%` にエスケープしてから渡す
config.set_main_option("sqlalchemy.url", _database_url.replace("%", "%%"))

if config.config_file_name is not None:
	fileConfig(config.config_file_name)

# autogenerate / 差分比較の対象となるメタデータ
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
	"""DB へ接続せず SQL を出力するモード"""
	url = config.get_main_option("sqlalchemy.url")
	context.configure(
		url=url,
		target_metadata=target_metadata,
		literal_binds=True,
		dialect_opts={"paramstyle": "named"},
		# SQLite でも列変更を扱えるよう batch モードを使う
		render_as_batch=True,
	)
	with context.begin_transaction():
		context.run_migrations()


def run_migrations_online() -> None:
	"""実 DB へ接続して適用するモード"""
	connectable = engine_from_config(
		config.get_section(config.config_ini_section, {}),
		prefix="sqlalchemy.",
		poolclass=pool.NullPool,
	)
	with connectable.connect() as connection:
		context.configure(
			connection=connection,
			target_metadata=target_metadata,
			render_as_batch=True,
		)
		with context.begin_transaction():
			context.run_migrations()


if context.is_offline_mode():
	run_migrations_offline()
else:
	run_migrations_online()
