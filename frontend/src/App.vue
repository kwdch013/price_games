<script setup lang="ts">
// アプリのルート。ゲーム登録→一覧→損失集計を束ねる。
import { onMounted, ref } from 'vue'
import {
	deleteGame,
	fetchSummary,
	listGames,
	type Game,
	type Summary,
} from './api/client'
import GameForm from './components/GameForm.vue'
import GameList from './components/GameList.vue'
import HealthStatus from './components/HealthStatus.vue'
import SummaryPanel from './components/SummaryPanel.vue'

const games = ref<Game[]>([])
const summary = ref<Summary | null>(null)
const loadError = ref('')

async function reload(): Promise<void> {
	loadError.value = ''
	try {
		// 一覧と集計は両方そろってから反映し、片方だけ古くならないようにする
		const [nextGames, nextSummary] = await Promise.all([listGames(), fetchSummary()])
		games.value = nextGames
		summary.value = nextSummary
	} catch {
		loadError.value = 'データの取得に失敗しました'
	}
}

async function onDelete(id: number): Promise<void> {
	try {
		await deleteGame(id)
		await reload()
	} catch {
		loadError.value = '削除に失敗しました'
	}
}

function onCreated(): void {
	// 登録後は一覧と集計を最新化する
	void reload()
}

onMounted(reload)
</script>

<template>
	<main class="app">
		<header>
			<h1>積みゲー損失可視化</h1>
			<HealthStatus />
		</header>

		<SummaryPanel v-if="summary" :summary="summary" />
		<p v-if="loadError" class="error">{{ loadError }}</p>

		<div class="layout">
			<GameForm @created="onCreated" />
			<GameList :games="games" @delete="onDelete" />
		</div>
	</main>
</template>

<style scoped>
.app {
	max-width: 960px;
	margin: 2rem auto;
	padding: 0 1rem;
	font-family: system-ui, sans-serif;
}
.layout {
	display: grid;
	grid-template-columns: 320px 1fr;
	gap: 1.5rem;
	align-items: start;
}
.error {
	color: #c62828;
}
@media (max-width: 720px) {
	.layout {
		grid-template-columns: 1fr;
	}
}
</style>
