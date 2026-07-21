"""損失計算（純関数）

- 積みゲー損失: 未プレイ分の「もったいない額」
- 価格差損失: 高値掴み分（現在価格が分かる場合のみ）
金額は円（整数）で扱う。
"""

from __future__ import annotations


def pile_loss(purchase_price: int, progress: int) -> int:
	"""積みゲー損失 = 購入価格 × (1 − 進行度/100) を四捨五入した整数（円）"""
	if purchase_price < 0:
		raise ValueError("購入価格は 0 以上である必要があります")
	if not 0 <= progress <= 100:
		raise ValueError("進行度は 0〜100 の範囲である必要があります")
	return round(purchase_price * (1 - progress / 100))


def price_diff_loss(purchase_price: int, current_price: int | None) -> int | None:
	"""価格差損失 = max(購入価格 − 現在価格, 0)。現在価格が未設定なら None。"""
	if current_price is None:
		return None
	if purchase_price < 0 or current_price < 0:
		raise ValueError("価格は 0 以上である必要があります")
	return max(purchase_price - current_price, 0)
