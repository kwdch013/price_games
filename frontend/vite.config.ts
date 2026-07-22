import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// nodenext 解決のため拡張子付きで import する（allowImportingTsExtensions 有効）
import { API_PROXY_PATTERN, parseAllowedHosts, rewriteApiPath } from './devProxy.ts'

// dev server が `/api` を転送する先。
// compose ではサービス名（http://api:8000）、ホストで直接 npm run dev する場合は
// VITE_PROXY_TARGET=http://localhost:8010 を指定する。
const PROXY_TARGET = process.env.VITE_PROXY_TARGET || 'http://localhost:8010'

// Vite は IP アドレス・localhost の Host を既定で許可するため、LAN の IP で開く分には設定不要。
// 独自ホスト名（例: myserver.local）で開く場合のみ VITE_ALLOWED_HOSTS に列挙する。
// DNS rebinding 対策として `true`（検証の全面無効化）は使わない。
const ALLOWED_HOSTS = parseAllowedHosts(process.env.VITE_ALLOWED_HOSTS)

// https://vite.dev/config/
export default defineConfig({
	plugins: [vue()],
	server: {
		// LAN 内の別マシンから開けるよう全インターフェースで待ち受ける
		host: true,
		...(ALLOWED_HOSTS.length > 0 ? { allowedHosts: ALLOWED_HOSTS } : {}),
		proxy: {
			// ブラウザからは同一オリジンに見せ、dev server が API へ中継する。
			// これでブラウザ側の localhost 依存と CORS の両方を回避できる。
			[API_PROXY_PATTERN]: {
				target: PROXY_TARGET,
				changeOrigin: true,
				rewrite: rewriteApiPath,
			},
		},
	},
})
