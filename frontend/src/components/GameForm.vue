<script setup lang="ts">
// ゲーム登録フォーム。登録に成功したら created イベントで新規ゲームを親へ通知する。
// タイトル入力とサジェストは TitleSuggest に委ね、ここでは選択結果を
// 発売日/現在価格/画像/steam_appid へ反映する。
import { reactive, ref } from 'vue'
import { createGame, MEDIA, type Game, type Medium } from '../api/client'
import type { SuggestDetail } from '../api/suggest'
import TitleSuggest from './TitleSuggest.vue'

const emit = defineEmits<{ created: [game: Game] }>()

interface FormState {
	title: string
	medium: Medium
	purchase_price: number | null
	current_price: number | null
	progress: number
	note: string
	steam_appid: number | null
}

function initial(): FormState {
	return {
		title: '',
		medium: 'PC(Steam)',
		purchase_price: null,
		current_price: null,
		progress: 0,
		note: '',
		steam_appid: null,
	}
}

const form = reactive<FormState>(initial())
const error = ref('')
const submitting = ref(false)

// 候補選択で得た発売日・画像・補足はプレビュー表示のみ
// （Game モデルに列が無いため永続化しない）
const releaseDate = ref<string | null>(null)
const headerImage = ref<string | null>(null)
const selectedNote = ref<string | null>(null)

// 保留中の検索・詳細取得を送信後に無効化するため子を参照する
const titleSuggest = ref<InstanceType<typeof TitleSuggest> | null>(null)

// 候補選択で自動入力した現在価格。紐付けが外れたときに
// 「自動入力のまま手を加えていない値」だけを消すために覚えておく。
let autoFilledPrice: number | null = null

/** 自動入力された現在価格を捨てる。利用者が編集した値はそのまま残す */
function clearAutoFilledPrice(): void {
	if (autoFilledPrice !== null && form.current_price === autoFilledPrice) {
		form.current_price = null
	}
	autoFilledPrice = null
}

/** サジェストの選択結果を反映する。手入力で紐付けが外れた場合は null が渡る */
function onSuggestSelect(detail: SuggestDetail | null): void {
	if (detail === null) {
		// 媒体変更・手入力で紐付けが外れた：前の提供元の価格を引き継がない
		clearAutoFilledPrice()
		form.steam_appid = null
		releaseDate.value = null
		headerImage.value = null
		selectedNote.value = null
		return
	}
	form.steam_appid = detail.steamAppid
	if (detail.currentPrice === null) {
		// 価格を取得できない候補：前の候補の価格を残さない
		clearAutoFilledPrice()
	} else {
		form.current_price = detail.currentPrice
		autoFilledPrice = detail.currentPrice
	}
	releaseDate.value = detail.releaseDate
	headerImage.value = detail.image
	selectedNote.value = detail.note
}

// v-model.number は空欄時に '' を返し得るため、数値 or null に正規化する
function toNumberOrNull(value: unknown): number | null {
	if (value === null || value === undefined || value === '') {
		return null
	}
	const n = Number(value)
	return Number.isFinite(n) ? n : null
}

async function submit(): Promise<void> {
	if (submitting.value) {
		return // 送信中の多重送信を防ぐ（Enter 連打・プログラム的 submit 対策）
	}
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
			steam_appid: form.steam_appid,
		})
		emit('created', game)
		Object.assign(form, initial())
		// 保留中の検索・詳細取得を無効化してから状態を捨てる
		titleSuggest.value?.reset()
		autoFilledPrice = null
		onSuggestSelect(null)
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
		<TitleSuggest
			ref="titleSuggest"
			:title="form.title"
			:medium="form.medium"
			@update:title="form.title = $event"
			@select="onSuggestSelect"
			@error="error = $event"
		/>
		<div v-if="form.steam_appid || selectedNote || releaseDate" class="steam-preview">
			<img v-if="headerImage" :src="headerImage" alt="" class="preview-image" />
			<p class="preview-meta">
				<span v-if="form.steam_appid">Steam 連携済み（appid: {{ form.steam_appid }}）<br /></span>
				<span v-if="releaseDate">発売日: {{ releaseDate }}<br /></span>
				<span v-if="selectedNote">{{ selectedNote }}</span>
			</p>
		</div>
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
.steam-preview {
	display: flex;
	gap: 0.5rem;
	align-items: center;
	font-size: 0.8rem;
	color: #555;
}
.preview-image {
	width: 120px;
	height: auto;
	border-radius: 4px;
}
.preview-meta {
	margin: 0;
}
.error {
	color: #c62828;
	margin: 0;
}
</style>
