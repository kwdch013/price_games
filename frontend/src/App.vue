<script setup lang="ts">
// アプリのルート。現段階はタイトルとバックエンド疎通表示のみ（雛形）。
import HealthStatus from './components/HealthStatus.vue'
</script>

<template>
	<main class="app">
		<h1>積みゲー損失可視化</h1>
		<p class="lead">購入したゲームの損失を可視化して、積みを崩すモチベを上げるアプリ</p>
		<HealthStatus />
	</main>
</template>

<style scoped>
.app {
	max-width: 720px;
	margin: 2rem auto;
	padding: 0 1rem;
	font-family: system-ui, sans-serif;
}
.lead {
	color: #555;
}
</style>
