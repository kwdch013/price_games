"""0003 日時型移行の PostgreSQL 結合テスト（Issue #16）"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Connection
from sqlalchemy.exc import SQLAlchemyError

from alembic import command
from app.db import engine

pytestmark = pytest.mark.integration

try:
	with engine.connect():
		pass
except SQLAlchemyError as exc:
	pytest.skip(f"DB へ接続できないためスキップ: {exc}", allow_module_level=True)

if engine.dialect.name != "postgresql":
	pytest.skip("PostgreSQL 専用の結合テスト", allow_module_level=True)

_ROOT = Path(__file__).resolve().parent.parent
_COLUMNS = (("game", "created_at"), ("price_history", "captured_at"))


def _isolated_url(schema_name: str) -> URL:
	"""共有 DB の public を参照しない接続 URL を作る。"""
	return engine.url.update_query_dict(
		{"options": f"-csearch_path={schema_name} -ctimezone=Asia/Tokyo"}
	)


def _alembic_config(monkeypatch: pytest.MonkeyPatch, database_url: URL) -> Config:
	cfg = Config(str(_ROOT / "alembic.ini"))
	cfg.set_main_option("script_location", str(_ROOT / "alembic"))
	monkeypatch.setenv("DATABASE_URL", database_url.render_as_string(hide_password=False))
	return cfg


def _column_definitions(conn: Connection) -> dict[tuple[str, str], tuple[str, str | None]]:
	rows = conn.execute(
		text(
			"""
			SELECT table_name, column_name, data_type, column_default
			FROM information_schema.columns
			WHERE table_schema = current_schema()
				AND (table_name, column_name) IN (
					('game', 'created_at'),
					('price_history', 'captured_at')
				)
			"""
		)
	).all()
	return {
		(row.table_name, row.column_name): (row.data_type, row.column_default)
		for row in rows
	}


def test_0003をPostgreSQLで往復して日時を保持する(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	schema_name = f"mig_test_{uuid4().hex[:12]}"
	with engine.begin() as conn:
		conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))

	isolated_engine = create_engine(_isolated_url(schema_name))
	try:
		cfg = _alembic_config(monkeypatch, isolated_engine.url)
		command.upgrade(cfg, "0002_price_history")
		with isolated_engine.begin() as conn:
			assert conn.execute(text("SELECT current_schema()")).scalar_one() == schema_name
			assert conn.execute(text("SHOW TIME ZONE")).scalar_one() == "Asia/Tokyo"
			conn.execute(
				text(
					"""
					INSERT INTO game (
						id, title, medium, purchase_price, current_price,
						progress, note, steam_appid, created_at
					) VALUES (
						1, '既存ゲーム', 'PC(Steam)', 1000, NULL,
						0, '', NULL, '2026-01-02 03:04:05'
					)
					"""
				)
			)
			conn.execute(
				text(
					"""
					INSERT INTO price_history (id, game_id, price, captured_at)
					VALUES (1, 1, 900, '2026-02-03 04:05:06')
					"""
				)
			)

		command.upgrade(cfg, "head")
		with isolated_engine.begin() as conn:
			definitions = _column_definitions(conn)
			assert set(definitions) == set(_COLUMNS)
			for column in _COLUMNS:
				data_type, default = definitions[column]
				assert data_type == "timestamp with time zone"
				assert default is not None
				assert "CURRENT_TIMESTAMP" in default.upper()

			created_at = conn.execute(
				text("SELECT created_at FROM game WHERE id = 1")
			).scalar_one()
			captured_at = conn.execute(
				text("SELECT captured_at FROM price_history WHERE id = 1")
			).scalar_one()
			assert created_at == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
			assert captured_at == datetime(2026, 2, 3, 4, 5, 6, tzinfo=timezone.utc)

			default_game = conn.execute(
				text(
					"""
					INSERT INTO game (
						id, title, medium, purchase_price, current_price,
						progress, note, steam_appid
					) VALUES (2, '既定値', 'PC(Steam)', 500, NULL, 0, '', NULL)
					RETURNING created_at
					"""
				)
			).scalar_one()
			default_history = conn.execute(
				text(
					"""
					INSERT INTO price_history (id, game_id, price)
					VALUES (2, 2, 400)
					RETURNING captured_at
					"""
				)
			).scalar_one()
			assert default_game.tzinfo is not None
			assert default_history.tzinfo is not None

		command.downgrade(cfg, "0002_price_history")
		with isolated_engine.connect() as conn:
			definitions = _column_definitions(conn)
			assert set(definitions) == set(_COLUMNS)
			for column in _COLUMNS:
				assert definitions[column] == ("timestamp without time zone", None)
			assert conn.execute(
				text("SELECT created_at FROM game WHERE id = 1")
			).scalar_one() == datetime(2026, 1, 2, 3, 4, 5)
			assert conn.execute(
				text("SELECT captured_at FROM price_history WHERE id = 1")
			).scalar_one() == datetime(2026, 2, 3, 4, 5, 6)
	finally:
		isolated_engine.dispose()
		with engine.begin() as conn:
			conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
