// バックエンド API への薄いクライアント
// API のベース URL は環境変数で上書き可能（既定は開発時のホストポート 8010）
const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8010'

export interface HealthResponse {
	status: string
}

// 媒体の選択肢（バックエンドの Enum 値と一致させる）
export const MEDIA = [
	'PC(Steam)',
	'PC(その他)',
	'PS5',
	'PS4',
	'Nintendo Switch',
	'Xbox',
	'その他',
] as const
export type Medium = (typeof MEDIA)[number]

export interface GameCreate {
	title: string
	medium: Medium
	purchase_price: number
	current_price: number | null
	progress: number
	note?: string
	steam_appid?: number | null
}

// Steam 検索候補（バックエンドの SteamSearchItem と一致）
export interface SteamSearchItem {
	appid: number
	name: string
	tiny_image: string | null
	price: number | null
}

// Steam アプリ詳細（バックエンドの SteamAppDetail と一致）
export interface SteamAppDetail {
	appid: number
	name: string
	release_date: string | null
	current_price: number | null
	header_image: string | null
	short_description: string | null
	genres: string[]
}

export interface Game {
	id: number
	title: string
	medium: string
	purchase_price: number
	current_price: number | null
	progress: number
	note: string
	steam_appid: number | null
	created_at: string
	pile_loss: number
	price_diff_loss: number | null
}

export interface Summary {
	count: number
	total_pile_loss: number
	total_price_diff_loss: number
	total_loss: number
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	const res = await fetch(`${API_BASE}${path}`, {
		headers: { 'Content-Type': 'application/json' },
		...init,
	})
	if (!res.ok) {
		throw new Error(`request failed: ${res.status}`)
	}
	// 204 No Content は本文なし
	if (res.status === 204) {
		return undefined as T
	}
	return (await res.json()) as T
}

// ヘルスチェック。疎通確認に使う。
export async function fetchHealth(): Promise<HealthResponse> {
	return request<HealthResponse>('/health')
}

export async function listGames(): Promise<Game[]> {
	return request<Game[]>('/games')
}

export async function createGame(payload: GameCreate): Promise<Game> {
	return request<Game>('/games', {
		method: 'POST',
		body: JSON.stringify(payload),
	})
}

export async function deleteGame(id: number): Promise<void> {
	await request<void>(`/games/${id}`, { method: 'DELETE' })
}

export async function fetchSummary(): Promise<Summary> {
	return request<Summary>('/games/summary')
}

// タイトル文字列から Steam 検索候補を取得する
export async function searchSteam(q: string): Promise<SteamSearchItem[]> {
	return request<SteamSearchItem[]>(`/steam/search?q=${encodeURIComponent(q)}`)
}

// appid から Steam アプリ詳細（発売日・現在価格・画像など）を取得する
export async function fetchSteamApp(appid: number): Promise<SteamAppDetail> {
	return request<SteamAppDetail>(`/steam/apps/${appid}`)
}

// 円表示のユーティリティ
export function formatYen(value: number | null): string {
	if (value === null) {
		return '—'
	}
	return `¥${value.toLocaleString('ja-JP')}`
}
