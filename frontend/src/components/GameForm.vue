<script setup lang="ts">
// ゲーム登録フォーム。登録に成功したら created イベントで新規ゲームを親へ通知する。
// タイトル入力から Steam を検索し、候補選択で発売日/現在価格/画像/steam_appid を自動反映する。
import { onBeforeUnmount, reactive, ref, watch } from 'vue'
import {
	createGame,
	fetchSteamApp,
	MEDIA,
	searchSteam,
	type Game,
	type Medium,
	type SteamSearchItem,
} from '../api/client'

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

// Steam サジェスト関連の状態
const suggestions = ref<SteamSearchItem[]>([])
const searching = ref(false)
// 選択で得た発売日・画像はプレビュー表示のみ（Game モデルに列が無いため永続化しない）
const releaseDate = ref<string | null>(null)
const headerImage = ref<string | null>(null)

const SEARCH_DELAY_MS = 300
const MIN_QUERY_LEN = 2
let debounceTimer: ReturnType<typeof setTimeout> | undefined
// 候補選択でタイトルを書き換える際、再検索を走らせないためのフラグ
let suppressSearch = false
// 手入力のたびに進める世代番号。非同期の検索・詳細取得は、await 後にこの値が
// 進んでいれば「古い結果」とみなして破棄し、新しい入力状態を上書きしないようにする。
let inputGen = 0

// タイトル入力の変化を監視し、デバウンスして Steam を検索する
watch(
	() => form.title,
	(title) => {
		if (suppressSearch) {
			suppressSearch = false
			return
		}
		// 手入力で世代を進め、前回の Steam 紐付けは無効化する（古い appid の送信を防ぐ）
		inputGen += 1
		form.steam_appid = null
		releaseDate.value = null
		headerImage.value = null
		clearTimeout(debounceTimer)
		const q = title.trim()
		if (q.length < MIN_QUERY_LEN) {
			suggestions.value = []
			return
		}
		const gen = inputGen
		debounceTimer = setTimeout(() => void runSearch(q, gen), SEARCH_DELAY_MS)
	},
)

async function runSearch(q: string, gen: number): Promise<void> {
	searching.value = true
	try {
		const items = await searchSteam(q)
		if (gen !== inputGen) {
			return // 手入力が進んでいる：古いレスポンスなので破棄
		}
		suggestions.value = items
	} catch {
		if (gen === inputGen) {
			suggestions.value = []
		}
	} finally {
		searching.value = false
	}
}

// 候補を選択：詳細を取得してタイトル・現在価格・steam_appid を自動反映する
async function onSelect(item: SteamSearchItem): Promise<void> {
	const gen = inputGen
	suggestions.value = []
	try {
		const detail = await fetchSteamApp(item.appid)
		if (gen !== inputGen) {
			return // 取得中に手入力された：古い詳細で上書きしない
		}
		suppressSearch = true
		form.title = detail.name
		form.steam_appid = detail.appid
		if (detail.current_price !== null) {
			form.current_price = detail.current_price
		}
		releaseDate.value = detail.release_date
		headerImage.value = detail.header_image
	} catch {
		if (gen === inputGen) {
			error.value = 'Steam 詳細の取得に失敗しました'
		}
	}
}

onBeforeUnmount(() => clearTimeout(debounceTimer))

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
		suppressSearch = true
		Object.assign(form, initial())
		suggestions.value = []
		releaseDate.value = null
		headerImage.value = null
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
		<label class="title-field">
			タイトル
			<input v-model="form.title" type="text" placeholder="例: エルデンリング" autocomplete="off" />
			<span v-if="searching" class="hint">検索中…</span>
			<ul v-if="suggestions.length" class="suggest-list">
				<li
					v-for="item in suggestions"
					:key="item.appid"
					class="suggest-item"
					@click="onSelect(item)"
				>
					<img v-if="item.tiny_image" :src="item.tiny_image" alt="" class="suggest-thumb" />
					<span class="suggest-name">{{ item.name }}</span>
				</li>
			</ul>
		</label>
		<div v-if="form.steam_appid" class="steam-preview">
			<img v-if="headerImage" :src="headerImage" alt="" class="preview-image" />
			<p class="preview-meta">
				Steam 連携済み（appid: {{ form.steam_appid }}）<br />
				<span v-if="releaseDate">発売日: {{ releaseDate }}</span>
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
.title-field {
	position: relative;
}
.hint {
	font-size: 0.75rem;
	color: #888;
}
.suggest-list {
	list-style: none;
	margin: 0.2rem 0 0;
	padding: 0;
	border: 1px solid #ccc;
	border-radius: 6px;
	max-height: 14rem;
	overflow-y: auto;
	background: #fff;
}
.suggest-item {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	padding: 0.3rem 0.5rem;
	cursor: pointer;
}
.suggest-item:hover {
	background: #f0f0f0;
}
.suggest-thumb {
	width: 60px;
	height: auto;
	border-radius: 3px;
}
.suggest-name {
	font-size: 0.85rem;
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
