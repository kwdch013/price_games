<script setup lang="ts">
// ゲーム登録フォーム。登録に成功したら created イベントで新規ゲームを親へ通知する。
import { reactive, ref } from 'vue'
import { createGame, MEDIA, type Game, type Medium } from '../api/client'

const emit = defineEmits<{ created: [game: Game] }>()

interface FormState {
	title: string
	medium: Medium
	purchase_price: number | null
	current_price: number | null
	progress: number
	note: string
}

function initial(): FormState {
	return {
		title: '',
		medium: 'PC(Steam)',
		purchase_price: null,
		current_price: null,
		progress: 0,
		note: '',
	}
}

const form = reactive<FormState>(initial())
const error = ref('')
const submitting = ref(false)

// v-model.number は空欄時に '' を返し得るため、数値 or null に正規化する
function toNumberOrNull(value: unknown): number | null {
	if (value === null || value === undefined || value === '') {
		return null
	}
	const n = Number(value)
	return Number.isFinite(n) ? n : null
}

async function submit(): Promise<void> {
	error.value = ''
	const purchase = toNumberOrNull(form.purchase_price)
	const current = toNumberOrNull(form.current_price)
	if (!form.title.trim() || purchase === null || purchase < 0) {
		error.value = 'タイトルと購入価格（0以上）は必須です'
		return
	}
	if (current !== null && current < 0) {
		error.value = '現在価格は0以上で入力してください'
		return
	}
	submitting.value = true
	try {
		const game = await createGame({
			title: form.title.trim(),
			medium: form.medium,
			purchase_price: purchase,
			current_price: current,
			progress: form.progress,
			note: form.note,
		})
		emit('created', game)
		Object.assign(form, initial())
	} catch {
		error.value = '登録に失敗しました'
	} finally {
		submitting.value = false
	}
}
</script>

<template>
	<form class="game-form" @submit.prevent="submit">
		<h2>ゲームを登録</h2>
		<label>
			タイトル
			<input v-model="form.title" type="text" placeholder="例: エルデンリング" />
		</label>
		<label>
			媒体
			<select v-model="form.medium">
				<option v-for="m in MEDIA" :key="m" :value="m">{{ m }}</option>
			</select>
		</label>
		<label>
			購入価格（円）
			<input v-model.number="form.purchase_price" type="number" min="0" />
		</label>
		<label>
			現在価格（円・任意）
			<input v-model.number="form.current_price" type="number" min="0" />
		</label>
		<label>
			進行度: {{ form.progress }}%
			<input v-model.number="form.progress" type="range" min="0" max="100" />
		</label>
		<label>
			メモ（任意）
			<textarea v-model="form.note" rows="2"></textarea>
		</label>
		<p v-if="error" class="error">{{ error }}</p>
		<button type="submit" :disabled="submitting">登録</button>
	</form>
</template>

<style scoped>
.game-form {
	display: grid;
	gap: 0.5rem;
	padding: 1rem;
	border: 1px solid #ddd;
	border-radius: 8px;
}
.game-form label {
	display: grid;
	gap: 0.2rem;
	font-size: 0.9rem;
}
.error {
	color: #c62828;
	margin: 0;
}
</style>
