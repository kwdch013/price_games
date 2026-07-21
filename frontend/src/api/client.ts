// バックエンド API への薄いクライアント
// API のベース URL は環境変数で上書き可能（既定は開発時のホストポート 8010）
const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8010'

export interface HealthResponse {
	status: string
}

// ヘルスチェック。疎通確認に使う。
export async function fetchHealth(): Promise<HealthResponse> {
	const res = await fetch(`${API_BASE}/health`)
	if (!res.ok) {
		throw new Error(`health check failed: ${res.status}`)
	}
	return (await res.json()) as HealthResponse
}
