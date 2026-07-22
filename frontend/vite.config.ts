import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// dev server が `/api` を転送する先。
// compose ではサービス名（http://api:8000）、ホストで直接 npm run dev する場合は
// VITE_PROXY_TARGET=http://localhost:8010 を指定する。
const PROXY_TARGET = process.env.VITE_PROXY_TARGET || 'http://localhost:8010'

// https://vite.dev/config/
export default defineConfig({
	plugins: [vue()],
	server: {
		// LAN 内の別マシンから開けるよう全インターフェースで待ち受ける
		host: true,
		// サーバーの IP / ホスト名は環境ごとに異なるため Host ヘッダ検査を無効化する（開発用途）
		allowedHosts: true,
		proxy: {
			// ブラウザからは同一オリジンに見せ、dev server が API へ中継する。
			// これでブラウザ側の localhost 依存と CORS の両方を回避できる。
			'/api': {
				target: PROXY_TARGET,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api/, ''),
			},
		},
	},
})
