// dev server の /api プロキシ設定の単体テスト
import { describe, expect, it } from 'vitest'

import { API_PROXY_PATTERN, parseAllowedHosts, rewriteApiPath } from './devProxy'

// Vite は proxy キーが `^` 始まりのとき、URL（クエリ込み）に対して正規表現を test する
function matches(url: string): boolean {
	return new RegExp(API_PROXY_PATTERN).test(url)
}

describe('API_PROXY_PATTERN', () => {
	it('/api 配下を転送対象にする', () => {
		expect(matches('/api/health')).toBe(true)
		expect(matches('/api/steam/search?q=elden')).toBe(true)
		expect(matches('/api')).toBe(true)
		expect(matches('/api?q=1')).toBe(true)
	})

	it('/api で始まる別パスは転送しない', () => {
		expect(matches('/apiary')).toBe(false)
		expect(matches('/apiary/list')).toBe(false)
		expect(matches('/assets/api.js')).toBe(false)
	})
})

describe('rewriteApiPath', () => {
	it('/api プレフィックスを取り除く', () => {
		expect(rewriteApiPath('/api/health')).toBe('/health')
		expect(rewriteApiPath('/api/steam/search?q=elden')).toBe('/steam/search?q=elden')
	})

	it('先頭以外の /api は書き換えない', () => {
		expect(rewriteApiPath('/games/api/health')).toBe('/games/api/health')
	})

	it('/api で始まる別パスは書き換えない', () => {
		expect(rewriteApiPath('/apiary')).toBe('/apiary')
	})
})

describe('parseAllowedHosts', () => {
	it('未設定は空配列（IP・localhost は Vite が既定で許可する）', () => {
		expect(parseAllowedHosts(undefined)).toEqual([])
		expect(parseAllowedHosts('')).toEqual([])
	})

	it('カンマ区切りを分解し空要素を捨てる', () => {
		expect(parseAllowedHosts(' myserver.local , ,example.test ')).toEqual([
			'myserver.local',
			'example.test',
		])
	})
})
