"""ゲーム CRUD / 集計 API の単体テスト（インメモリ SQLite）"""

from fastapi.testclient import TestClient


def _sample(**overrides: object) -> dict[str, object]:
	base: dict[str, object] = {
		"title": "テストゲーム",
		"medium": "PC(Steam)",
		"purchase_price": 6000,
		"current_price": 4000,
		"progress": 0,
	}
	base.update(overrides)
	return base


def test_登録すると損失付きで返る(client: TestClient) -> None:
	res = client.post("/games", json=_sample(progress=50))
	assert res.status_code == 201
	body = res.json()
	assert body["id"] > 0
	assert body["pile_loss"] == 3000  # 6000 × (1 - 0.5)
	assert body["price_diff_loss"] == 2000  # 6000 - 4000


def test_現在価格未設定なら価格差損失はNull(client: TestClient) -> None:
	res = client.post("/games", json=_sample(current_price=None))
	assert res.status_code == 201
	assert res.json()["price_diff_loss"] is None


def test_一覧と個別取得(client: TestClient) -> None:
	created = client.post("/games", json=_sample()).json()
	assert len(client.get("/games").json()) == 1
	got = client.get(f"/games/{created['id']}")
	assert got.status_code == 200
	assert got.json()["title"] == "テストゲーム"


def test_集計は各損失の合計を返す(client: TestClient) -> None:
	client.post("/games", json=_sample(purchase_price=6000, current_price=4000, progress=50))
	client.post("/games", json=_sample(purchase_price=5000, current_price=None, progress=0))
	summary = client.get("/games/summary").json()
	assert summary["count"] == 2
	assert summary["total_pile_loss"] == 3000 + 5000
	assert summary["total_price_diff_loss"] == 2000  # 2件目は None なので加算されない
	assert summary["total_loss"] == 3000 + 5000 + 2000


def test_進行度を更新すると積みゲー損失が再計算される(client: TestClient) -> None:
	created = client.post("/games", json=_sample(purchase_price=6000, progress=0)).json()
	res = client.patch(f"/games/{created['id']}", json={"progress": 100})
	assert res.status_code == 200
	assert res.json()["pile_loss"] == 0


def test_削除すると404になる(client: TestClient) -> None:
	created = client.post("/games", json=_sample()).json()
	assert client.delete(f"/games/{created['id']}").status_code == 204
	assert client.get(f"/games/{created['id']}").status_code == 404


def test_不正な進行度は422(client: TestClient) -> None:
	assert client.post("/games", json=_sample(progress=101)).status_code == 422


def test_不正な媒体は422(client: TestClient) -> None:
	assert client.post("/games", json=_sample(medium="スマホ")).status_code == 422


def test_タイトル空は422(client: TestClient) -> None:
	assert client.post("/games", json=_sample(title="")).status_code == 422
