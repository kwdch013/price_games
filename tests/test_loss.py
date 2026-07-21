"""損失計算（純関数）の単体テスト"""

import pytest

from app.services.loss import pile_loss, price_diff_loss


class TestPileLoss:
	"""積みゲー損失 = 購入価格 × (1 − 進行度/100)"""

	def test_未着手は全額が損失(self) -> None:
		assert pile_loss(5000, 0) == 5000

	def test_クリア済みは損失ゼロ(self) -> None:
		assert pile_loss(5000, 100) == 0

	def test_半分進行は半額(self) -> None:
		assert pile_loss(6000, 50) == 3000

	def test_端数は四捨五入して整数円(self) -> None:
		# 5000 × 0.67 = 3350
		assert pile_loss(5000, 33) == 3350

	def test_進行度が範囲外なら例外(self) -> None:
		with pytest.raises(ValueError):
			pile_loss(5000, 101)
		with pytest.raises(ValueError):
			pile_loss(5000, -1)

	def test_購入価格が負なら例外(self) -> None:
		with pytest.raises(ValueError):
			pile_loss(-1, 0)


class TestPriceDiffLoss:
	"""価格差損失 = max(購入価格 − 現在価格, 0)"""

	def test_値下がりした分が損失(self) -> None:
		assert price_diff_loss(6000, 4000) == 2000

	def test_現在価格が高ければ損失ゼロ(self) -> None:
		assert price_diff_loss(3000, 5000) == 0

	def test_現在価格が未設定なら計算不能でNone(self) -> None:
		assert price_diff_loss(5000, None) is None

	def test_価格が負なら例外(self) -> None:
		with pytest.raises(ValueError):
			price_diff_loss(5000, -1)
