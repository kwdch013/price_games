<script setup lang="ts">
// バックエンド疎通状態を表示する最小コンポーネント
import { onMounted, ref } from 'vue'
import { fetchHealth } from '../api/client'

// 'loading' | 'ok' | 'error'
const state = ref<'loading' | 'ok' | 'error'>('loading')

async function check(): Promise<void> {
	state.value = 'loading'
	try {
		const res = await fetchHealth()
		state.value = res.status === 'ok' ? 'ok' : 'error'
	} catch {
		state.value = 'error'
	}
}

onMounted(check)
</script>

<template>
	<p class="health" :data-state="state">
		<span v-if="state === 'loading'">バックエンド確認中…</span>
		<span v-else-if="state === 'ok'">バックエンド疎通 OK</span>
		<span v-else>バックエンドに接続できません</span>
	</p>
</template>

<style scoped>
.health[data-state='ok'] {
	color: #2e7d32;
}
.health[data-state='error'] {
	color: #c62828;
}
</style>
