<script setup lang="ts">
// ダッシュボード合計。積みゲー損失・価格差損失・総額を大きく表示する。
import { formatYen, type Summary } from '../api/client'

defineProps<{ summary: Summary }>()
</script>

<template>
	<div class="summary">
		<div class="card total">
			<span class="label">総損失</span>
			<span class="value">{{ formatYen(summary.total_loss) }}</span>
		</div>
		<div class="card">
			<span class="label">積みゲー損失</span>
			<span class="value">{{ formatYen(summary.total_pile_loss) }}</span>
		</div>
		<div class="card">
			<span class="label">価格差損失</span>
			<span class="value">{{ formatYen(summary.total_price_diff_loss) }}</span>
		</div>
		<div class="card">
			<span class="label">登録数</span>
			<span class="value">{{ summary.count }} 件</span>
		</div>
	</div>
</template>

<style scoped>
.summary {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
	gap: 0.75rem;
	margin: 1rem 0;
}
.card {
	display: grid;
	gap: 0.25rem;
	padding: 0.75rem 1rem;
	border-radius: 8px;
	background: #f5f5f5;
}
.card.total {
	background: #fdecea;
}
.label {
	font-size: 0.8rem;
	color: #666;
}
.value {
	font-size: 1.3rem;
	font-weight: 700;
	font-variant-numeric: tabular-nums;
}
</style>
