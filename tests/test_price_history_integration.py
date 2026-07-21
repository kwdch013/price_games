"""price_history の結合テスト（実 PostgreSQL・Issue #14）

FK の ON DELETE CASCADE と price の CHECK 制約は DB 依存のため、
実接続できる環境（CI の postgres / コンテナ経由）でのみ検証する。
接続できない環境では自動スキップし、テストデータは後始末する。
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Game, PriceHistory

pytestmark = pytest.mark.integration

# 実接続を試み、繋がらなければスキップする
try:
	with engine.connect():
		pass
except SQLAlchemyError as exc:
	pytest.skip(f"DB へ接続できないためスキップ: {exc}", allow_module_level=True)


def test_game削除で価格履歴もCASCADE削除される() -> None:
	init_db()  # テーブルが無ければ作成
	with Session(engine) as session:
		game = Game(title="CASCADE検証", medium="PC(Steam)", purchase_price=2000)
		session.add(game)
		session.commit()
		session.refresh(game)
		game_id = game.id
		session.add(PriceHistory(game_id=game_id, price=2000))  # type: ignore[arg-type]
		session.add(PriceHistory(game_id=game_id, price=1500))  # type: ignore[arg-type]
		session.commit()

	try:
		# 親 game を削除すると子 price_history も消える
		with Session(engine) as session:
			session.delete(session.get(Game, game_id))
			session.commit()
		with Session(engine) as session:
			remaining = session.exec(
				select(PriceHistory).where(PriceHistory.game_id == game_id)
			).all()
			assert remaining == []
	finally:
		# 念のため後始末（親が残っていた場合）
		with Session(engine) as session:
			obj = session.get(Game, game_id)
			if obj is not None:
				session.delete(obj)
				session.commit()


def test_負の価格はCHECK制約で弾かれる() -> None:
	init_db()
	with Session(engine) as session:
		game = Game(title="CHECK検証", medium="PC(Steam)", purchase_price=1000)
		session.add(game)
		session.commit()
		session.refresh(game)
		game_id = game.id
	try:
		with Session(engine) as session:
			session.add(PriceHistory(game_id=game_id, price=-1))  # type: ignore[arg-type]
			with pytest.raises(IntegrityError):
				session.commit()
			session.rollback()
	finally:
		with Session(engine) as session:
			obj = session.get(Game, game_id)
			if obj is not None:
				session.delete(obj)
				session.commit()
