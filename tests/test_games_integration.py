"""実 DB（PostgreSQL）への結合テスト

実際に DB へ接続できるとき（CI の postgres サービス / コンテナ経由）のみ実行し、
接続できない環境（DB 未起動・認証不可など）では自動スキップする。
テストデータは登録→検証→削除まで行い、共有 DB を汚さない。
"""

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session

from app.db import engine, init_db
from app.models import Game

pytestmark = pytest.mark.integration

# スキームだけでなく実接続を試み、繋がらなければスキップする
try:
	with engine.connect():
		pass
except SQLAlchemyError as exc:  # 接続不可・認証失敗など
	pytest.skip(f"DB へ接続できないためスキップ: {exc}", allow_module_level=True)


def test_登録と取得のラウンドトリップ() -> None:
	init_db()  # テーブルが無ければ作成
	with Session(engine) as session:
		game = Game(title="結合テスト用", medium="PC(Steam)", purchase_price=1000)
		session.add(game)
		session.commit()
		session.refresh(game)
		game_id = game.id
	try:
		with Session(engine) as session:
			fetched = session.get(Game, game_id)
			assert fetched is not None
			assert fetched.title == "結合テスト用"
			assert fetched.created_at is not None
	finally:
		# 後始末（共有 DB を汚さない）
		with Session(engine) as session:
			obj = session.get(Game, game_id)
			if obj is not None:
				session.delete(obj)
				session.commit()


def test_不正な進行度は直挿入でもDB制約で弾かれる() -> None:
	init_db()
	with Session(engine) as session:
		# progress=999 は CheckConstraint 違反
		session.add(Game(title="不正データ", medium="PC(Steam)", purchase_price=1000, progress=999))
		with pytest.raises(IntegrityError):
			session.commit()
		session.rollback()
