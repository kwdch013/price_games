<script setup lang="ts">
// 登録済みゲームの一覧。各ゲームの損失を表示し、削除イベントを親へ通知する。
import { formatYen, type Game } from '../api/client'

defineProps<{ games: Game[] }>()
const emit = defineEmits<{ delete: [id: number] }>()
</script>

<template>
	<div class="game-list">
		<h2>登録済み（{{ games.length }} 件）</h2>
		<p v-if="games.length === 0" class="empty">まだ登録がありません。</p>
		<table v-else>
			<thead>
				<tr>
					<th>タイトル</th>
					<th>媒体</th>
					<th>購入</th>
					<th>現在</th>
					<th>進行</th>
					<th>積みゲー損失</th>
					<th>価格差損失</th>
					<th></th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="g in games" :key="g.id">
					<td>{{ g.title }}</td>
					<td>{{ g.medium }}</td>
					<td>{{ formatYen(g.purchase_price) }}</td>
					<td>{{ formatYen(g.current_price) }}</td>
					<td>{{ g.progress }}%</td>
					<td class="loss">{{ formatYen(g.pile_loss) }}</td>
					<td class="loss">{{ formatYen(g.price_diff_loss) }}</td>
					<td>
						<button type="button" @click="emit('delete', g.id)">削除</button>
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<style scoped>
.game-list table {
	width: 100%;
	border-collapse: collapse;
	font-size: 0.9rem;
}
.game-list th,
.game-list td {
	border-bottom: 1px solid #eee;
	padding: 0.4rem 0.5rem;
	text-align: left;
}
.loss {
	color: #c62828;
	font-variant-numeric: tabular-nums;
}
.empty {
	color: #777;
}
</style>
