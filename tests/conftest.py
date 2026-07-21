"""テスト共通のフィクスチャ

API の単体テストは、実 DB に依存しないようインメモリ SQLite に
`get_session` を差し替えた TestClient を提供する。
（lifespan を起動しないため、起動時の実 DB 初期化は走らない）
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
	# インメモリ SQLite を1コネクションで共有する
	engine = create_engine(
		"sqlite://",
		connect_args={"check_same_thread": False},
		poolclass=StaticPool,
	)
	SQLModel.metadata.create_all(engine)

	def _override() -> Iterator[Session]:
		with Session(engine) as session:
			yield session

	app.dependency_overrides[get_session] = _override
	test_client = TestClient(app)
	yield test_client
	app.dependency_overrides.clear()
