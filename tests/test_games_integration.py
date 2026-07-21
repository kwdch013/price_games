"""実 DB（PostgreSQL）への結合テスト

DATABASE_URL が postgresql を指すとき（CI の postgres サービス / コンテナ経由）のみ実行し、
それ以外（ローカルの SQLite フォールバック等）では自動スキップする。
テストデータは登録→検証→削除まで行い、共有 DB を汚さない。
"""

import pytest
from sqlmodel import Session

from app.db import DATABASE_URL, engine, init_db
from app.models import Game

pytestmark = pytest.mark.integration

# 実 Postgres に繋がらない環境ではスキップ
if not DATABASE_URL.startswith("postgresql"):
	pytest.skip("PostgreSQL 未接続のためスキップ", allow_module_level=True)


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
