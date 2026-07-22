<script setup lang="ts">
// タイトル入力とサジェスト。媒体に応じた提供元（Steam / Nintendo eShop）を検索し、
// 候補選択で得た詳細を select イベントで親へ渡す。
// 手入力で前回の紐付けが無効になった場合は select に null を渡す。
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { Medium } from '../api/client'
import {
	fetchSuggestDetail,
	searchTitles,
	suggestSourceFor,
	type SuggestDetail,
	type SuggestItem,
} from '../api/suggest'

const props = defineProps<{ title: string; medium: Medium }>()
const emit = defineEmits<{
	'update:title': [string]
	select: [SuggestDetail | null]
	error: [string]
}>()

const suggestions = ref<SuggestItem[]>([])
const searching = ref(false)

// 現在の媒体で価格を自動取得できるか（PS5 などは提供元が無い）
const canSuggest = computed(() => suggestSourceFor(props.medium) !== null)

const SEARCH_DELAY_MS = 300
const MIN_QUERY_LEN = 2
let debounceTimer: ReturnType<typeof setTimeout> | undefined
// 候補選択などこのコンポーネントから設定したタイトル。同じ値の再入力を手入力と
// 誤認しないよう、フラグではなく「設定した値」を覚えて比較する。
let appliedTitle: string | null = null
// 手入力・媒体変更のたびに進める世代番号。非同期の検索・詳細取得は、await 後に
// この値が進んでいれば「古い結果」とみなして破棄する。
let inputGen = 0

/** デバウンスして検索を予約する。クエリが短ければ候補を消すだけ */
function scheduleSearch(q: string, medium: Medium): void {
	clearTimeout(debounceTimer)
	if (suggestSourceFor(medium) === null || q.length < MIN_QUERY_LEN) {
		suggestions.value = []
		return
	}
	const gen = inputGen
	debounceTimer = setTimeout(() => void runSearch(q, medium, gen), SEARCH_DELAY_MS)
}

// タイトルの変化を監視し、デバウンスして検索する
watch(
	() => props.title,
	(title) => {
		if (appliedTitle !== null && title === appliedTitle) {
			appliedTitle = null
			return // 候補選択による書き換え：再検索しない
		}
		appliedTitle = null
		inputGen += 1
		emit('select', null) // 手入力：前回の紐付けを解除する
		scheduleSearch(title.trim(), props.medium)
	},
)

// 媒体の変化を監視する。提供元が変わるため前の媒体の候補・紐付けは捨てる
watch(
	() => props.medium,
	(medium) => {
		inputGen += 1
		suggestions.value = []
		emit('select', null)
		// タイトルが入力済みなら新しい提供元で検索し直す
		scheduleSearch(props.title.trim(), medium)
	},
)

async function runSearch(q: string, medium: Medium, gen: number): Promise<void> {
	searching.value = true
	try {
		const items = await searchTitles(medium, q)
		if (gen !== inputGen) {
			return // 入力・媒体が変わっている：古いレスポンスなので破棄
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

/** 検索を再実行させずにタイトルを書き換える */
function applyTitle(title: string): void {
	appliedTitle = title
	emit('update:title', title)
}

// 候補を選択：詳細を取得して親へ渡す
async function onSelect(item: SuggestItem): Promise<void> {
	const gen = inputGen
	const medium = props.medium
	suggestions.value = []
	if (!item.priceAvailable) {
		// ダウンロード版が無いなど価格を取得できない候補：タイトルだけ反映する
		applyTitle(item.title)
		emit('select', {
			title: item.title,
			currentPrice: null,
			steamAppid: null,
			releaseDate: null,
			image: item.image,
			note: item.note,
		})
		return
	}
	try {
		const detail = await fetchSuggestDetail(medium, item)
		if (gen !== inputGen || detail === null) {
			return // 取得中に手入力・媒体変更された：古い詳細で上書きしない
		}
		applyTitle(detail.title)
		emit('select', detail)
	} catch {
		if (gen === inputGen) {
			emit('error', '価格情報の取得に失敗しました')
		}
	}
}

function onInput(event: Event): void {
	emit('update:title', (event.target as HTMLInputElement).value)
}

onBeforeUnmount(() => clearTimeout(debounceTimer))
</script>

<template>
	<label class="title-field">
		タイトル
		<input
			:value="title"
			type="text"
			placeholder="例: エルデンリング"
			autocomplete="off"
			@input="onInput"
		/>
		<span v-if="searching" class="hint">検索中…</span>
		<span v-else-if="!canSuggest" class="hint">この媒体は価格の自動取得に対応していません</span>
		<ul v-if="suggestions.length" class="suggest-list">
			<li
				v-for="item in suggestions"
				:key="item.key"
				class="suggest-item"
				:class="{ 'is-unavailable': !item.priceAvailable }"
				@click="onSelect(item)"
			>
				<img v-if="item.image" :src="item.image" alt="" class="suggest-thumb" />
				<span class="suggest-name">
					{{ item.title }}
					<small v-if="item.note" class="suggest-note">{{ item.note }}</small>
				</span>
			</li>
		</ul>
	</label>
</template>

<style scoped>
.title-field {
	position: relative;
	display: grid;
	gap: 0.2rem;
	font-size: 0.9rem;
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
	display: grid;
	font-size: 0.85rem;
}
.suggest-note {
	color: #777;
	font-size: 0.75rem;
}
/* 価格を取得できない候補（ダウンロード版なし）は選べるが控えめに見せる */
.suggest-item.is-unavailable .suggest-name {
	color: #888;
}
</style>
