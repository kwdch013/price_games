"""DB 接続の下地（SQLModel エンジン / セッション）

共有 PostgreSQL（別アプリと同一インスタンスを使い回す）へ接続する。
接続情報は環境変数 DATABASE_URL で渡す（例: postgresql+psycopg://user:pass@host:5432/db）。
"""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

# 接続先は環境変数から取得する。未設定時はローカル開発向けのデフォルトを使う。
DATABASE_URL = os.environ.get(
	"DATABASE_URL",
	"postgresql+psycopg://price_games:price_games@localhost:5432/price_games",
)

# SQLite の場合のみ必要な接続引数（テスト等でのフォールバック用）
_connect_args = (
	{"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(
	DATABASE_URL,
	echo=False,
	# 切断済みコネクションを掴まないよう都度検査する
	pool_pre_ping=True,
	connect_args=_connect_args,
)


def init_db() -> None:
	"""テーブルを作成する（起動時に呼び出す）"""
	SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
	"""FastAPI の依存性注入で使うセッションジェネレータ"""
	with Session(engine) as session:
		yield session
