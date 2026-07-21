"""Alembic マイグレーションの検証

まっさらな DB に `upgrade head` を適用してテーブルが作られること、
およびベースラインが現行モデルと一致（autogenerate 差分ゼロ）であることを確認する。
一時 SQLite ファイル DB を用いるため実 DB 接続は不要（単体テストとして常時実行）。
"""

from __future__ import annotations

import os
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from sqlmodel import SQLModel

import app.models  # noqa: F401  # SQLModel.metadata へモデルを登録する副作用のため
from alembic import command

# リポジトリルート（alembic.ini がある場所）
_ROOT = Path(__file__).resolve().parent.parent


def _alembic_config(database_url: str) -> Config:
	"""一時 DB を対象にした Alembic 設定を作る。env.py は DATABASE_URL を読む。"""
	cfg = Config(str(_ROOT / "alembic.ini"))
	cfg.set_main_option("script_location", str(_ROOT / "alembic"))
	os.environ["DATABASE_URL"] = database_url
	return cfg


def test_upgrade_headでgameテーブルが作成される(tmp_path: Path) -> None:
	url = f"sqlite:///{tmp_path / 'up.db'}"
	command.upgrade(_alembic_config(url), "head")

	engine = create_engine(url)
	inspector = inspect(engine)
	assert "game" in inspector.get_table_names()
	cols = {c["name"] for c in inspector.get_columns("game")}
	expected = {
		"id",
		"title",
		"medium",
		"purchase_price",
		"current_price",
		"progress",
		"note",
		"steam_appid",
		"created_at",
	}
	assert expected <= cols


def test_ベースラインが現行モデルと一致する(tmp_path: Path) -> None:
	# upgrade 後のスキーマとモデル定義に差分が無い＝ベースラインが最新モデルと一致
	url = f"sqlite:///{tmp_path / 'drift.db'}"
	command.upgrade(_alembic_config(url), "head")

	engine = create_engine(url)
	with engine.connect() as conn:
		ctx = MigrationContext.configure(conn)
		diff = compare_metadata(ctx, SQLModel.metadata)
	assert diff == [], f"モデルとマイグレーションに差分がある: {diff}"
