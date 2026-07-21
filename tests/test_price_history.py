"""price_history テーブルの単体テスト（Issue #14）

一時 SQLite ファイル DB に対し、Alembic マイグレーションで price_history が
PK・FK・CHECK・index つきで作成されること、モデル経由の登録/取得ができることを確認する。
（FK の CASCADE / CHECK 制約の実効性は Postgres 依存のため結合テストで検証する）
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlmodel import Session, select

import app.models  # noqa: F401  # SQLModel.metadata へモデルを登録する副作用のため
from alembic import command
from app.models import Game, PriceHistory

_ROOT = Path(__file__).resolve().parent.parent


def _alembic_config(monkeypatch: pytest.MonkeyPatch, database_url: str) -> Config:
	cfg = Config(str(_ROOT / "alembic.ini"))
	cfg.set_main_option("script_location", str(_ROOT / "alembic"))
	monkeypatch.setenv("DATABASE_URL", database_url)
	return cfg


def test_upgrade_headでprice_historyが作成される(
	tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
	url = f"sqlite:///{tmp_path / 'ph.db'}"
	command.upgrade(_alembic_config(monkeypatch, url), "head")

	inspector = inspect(create_engine(url))
	assert "price_history" in inspector.get_table_names()

	cols = {c["name"] for c in inspector.get_columns("price_history")}
	assert cols == {"id", "game_id", "price", "captured_at"}

	# 主キーは id 単一
	assert inspector.get_pk_constraint("price_history")["constrained_columns"] == ["id"]

	# FK は game.id を CASCADE 参照
	fks = inspector.get_foreign_keys("price_history")
	assert len(fks) == 1
	assert fks[0]["referred_table"] == "game"
	assert fks[0]["constrained_columns"] == ["game_id"]
	assert fks[0]["referred_columns"] == ["id"]
	assert fks[0]["options"].get("ondelete") == "CASCADE"

	# price >= 0 の CHECK 制約
	checks = {c["name"] for c in inspector.get_check_constraints("price_history")}
	assert "ck_price_history_price_nonneg" in checks

	# game_id にインデックス
	indexed = {col for idx in inspector.get_indexes("price_history") for col in idx["column_names"]}
	assert "game_id" in indexed


def test_モデル経由で価格履歴を登録し時系列で取得できる(
	tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
	url = f"sqlite:///{tmp_path / 'ph_rt.db'}"
	command.upgrade(_alembic_config(monkeypatch, url), "head")
	engine = create_engine(url)

	with Session(engine) as session:
		game = Game(title="履歴テスト", medium="PC(Steam)", purchase_price=3000)
		session.add(game)
		session.commit()
		session.refresh(game)
		session.add(PriceHistory(game_id=game.id, price=3000))  # type: ignore[arg-type]
		session.add(PriceHistory(game_id=game.id, price=1980))  # type: ignore[arg-type]
		session.commit()
		game_id = game.id

	with Session(engine) as session:
		rows = session.exec(
			select(PriceHistory)
			.where(PriceHistory.game_id == game_id)
			.order_by(PriceHistory.captured_at)  # type: ignore[arg-type]
		).all()
		assert [r.price for r in rows] == [3000, 1980]
		assert all(r.captured_at is not None for r in rows)
