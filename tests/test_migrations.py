"""Alembic マイグレーションの検証

Issue #12 の受け入れ条件に対応する:
- まっさらな DB に `upgrade head` で game テーブル（PK・CHECK 制約含む）が作られる
- ベースラインが現行モデルと一致（autogenerate 差分ゼロ）
- 既存 DB を `stamp head` してもテーブル・データが破壊されない

一時 SQLite ファイル DB を用いるため実 DB 接続は不要（単体テストとして常時実行）。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlmodel import Session, SQLModel, select

import app.models  # noqa: F401  # SQLModel.metadata へモデルを登録する副作用のため
from alembic import command
from app.models import Game

# リポジトリルート（alembic.ini がある場所）
_ROOT = Path(__file__).resolve().parent.parent

# ベースラインが持つべき列と CHECK 制約（モデルと一致すること）
_EXPECTED_COLUMNS = {
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
_EXPECTED_CHECKS = {
	"ck_game_purchase_price_nonneg",
	"ck_game_current_price_nonneg",
	"ck_game_progress_range",
}


def _alembic_config(monkeypatch: pytest.MonkeyPatch, database_url: str) -> Config:
	"""一時 DB を対象にした Alembic 設定を作る。env.py は DATABASE_URL を読む。

	環境変数の変更は monkeypatch 経由にし、テスト終了時に自動復元させる
	（後続テストへ接続先が漏れないようにする）。
	"""
	cfg = Config(str(_ROOT / "alembic.ini"))
	cfg.set_main_option("script_location", str(_ROOT / "alembic"))
	monkeypatch.setenv("DATABASE_URL", database_url)
	return cfg


def test_upgrade_headでgameテーブルがPKとCHECK制約付きで作成される(
	tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
	url = f"sqlite:///{tmp_path / 'up.db'}"
	command.upgrade(_alembic_config(monkeypatch, url), "head")

	inspector = inspect(create_engine(url))
	assert "game" in inspector.get_table_names()

	# 列は過不足なく一致する（余分な列も検出する）
	cols = {c["name"] for c in inspector.get_columns("game")}
	assert cols == _EXPECTED_COLUMNS

	# 主キーは id 単一
	assert inspector.get_pk_constraint("game")["constrained_columns"] == ["id"]

	# 3 つの CHECK 制約が名前どおり存在する
	checks = {c["name"] for c in inspector.get_check_constraints("game")}
	assert _EXPECTED_CHECKS <= checks


def test_ベースラインが現行モデルと一致する(
	tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
	# upgrade 後のスキーマとモデル定義に差分が無い＝ベースラインが最新モデルと一致
	url = f"sqlite:///{tmp_path / 'drift.db'}"
	command.upgrade(_alembic_config(monkeypatch, url), "head")

	engine = create_engine(url)
	with engine.connect() as conn:
		ctx = MigrationContext.configure(conn)
		diff = compare_metadata(ctx, SQLModel.metadata)
	assert diff == [], f"モデルとマイグレーションに差分がある: {diff}"


def test_stampは既存テーブルとデータを破壊しない(
	tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
	# 既に game テーブルとデータが存在する DB を再現する
	url = f"sqlite:///{tmp_path / 'stamp.db'}"
	engine = create_engine(url)
	SQLModel.metadata.create_all(engine)
	with Session(engine) as session:
		session.add(Game(title="既存データ", medium="PC(Steam)", purchase_price=1000))
		session.commit()

	# stamp はテーブルを再作成せず、リビジョンだけを記録する
	cfg = _alembic_config(monkeypatch, url)
	command.stamp(cfg, "head")

	inspector = inspect(engine)
	assert "game" in inspector.get_table_names()

	# 既存データが残っている
	with Session(engine) as session:
		rows = session.exec(select(Game)).all()
		assert len(rows) == 1
		assert rows[0].title == "既存データ"

	# alembic_version に最新（head）リビジョンが記録される
	head = ScriptDirectory.from_config(cfg).get_current_head()
	with engine.connect() as conn:
		version = conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
	assert version == head
