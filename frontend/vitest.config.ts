import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

// テスト専用の設定。vite 8 と vitest 同梱 vite の型競合を避けるため
// vite.config.ts とは分離し、vue-tsc の型チェック対象からも外している。
export default defineConfig({
	plugins: [vue()],
	test: {
		// コンポーネントテストのため DOM 環境を使う
		environment: 'jsdom',
		globals: false,
	},
})
