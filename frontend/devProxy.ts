// dev server の `/api` プロキシ設定のうち、単体テストしたいロジックを切り出したもの。
// vite.config.ts 自体は型競合回避のため vitest の設定から分離しているため、ここに置く。

// Vite の proxy キーは `^` 始まりだと正規表現として URL（クエリ込み）に test される。
// 単なる前方一致にすると `/apiary` のような別パスまで転送してしまうため、
// `/api` の直後がパス区切り・クエリ・終端のときだけ対象にする。
export const API_PROXY_PATTERN = '^/api(/|\\?|$)'

/** `/api` プレフィックスを取り除き、バックエンド側のパスへ変換する */
export function rewriteApiPath(path: string): string {
	return path.replace(/^\/api(?=\/|\?|$)/, '')
}

/** カンマ区切りの `VITE_ALLOWED_HOSTS` をホスト名の一覧へ変換する */
export function parseAllowedHosts(raw: string | undefined): string[] {
	if (!raw) {
		return []
	}
	return raw
		.split(',')
		.map((host) => host.trim())
		.filter(Boolean)
}
