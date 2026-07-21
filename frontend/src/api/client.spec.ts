// API クライアントの単体テスト（fetch をモック）
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createGame, deleteGame, fetchSummary, formatYen } from './client'

afterEach(() => {
	vi.restoreAllMocks()
})

function mockFetch(res: Partial<Response>): void {
	vi.stubGlobal('fetch', vi.fn().mockResolvedValue(res))
}

describe('request（共通処理）', () => {
	it('非2xx は例外を投げる', async () => {
		mockFetch({ ok: false, status: 422 })
		await expect(fetchSummary()).rejects.toThrow('422')
	})

	it('204 は本文なしで解決する（deleteGame）', async () => {
		const f = vi.fn().mockResolvedValue({ ok: true, status: 204 })
		vi.stubGlobal('fetch', f)
		await expect(deleteGame(1)).resolves.toBeUndefined()
		// DELETE メソッドで呼ばれている
		expect(f.mock.calls[0][1]).toMatchObject({ method: 'DELETE' })
	})

	it('2xx は JSON を返す（createGame）', async () => {
		mockFetch({
			ok: true,
			status: 201,
			json: () => Promise.resolve({ id: 1, title: 'x' }),
		})
		const game = await createGame({
			title: 'x',
			medium: 'PC(Steam)',
			purchase_price: 1000,
			current_price: null,
			progress: 0,
		})
		expect(game.id).toBe(1)
	})
})

describe('formatYen', () => {
	it('数値は円記号と桁区切りで整形する', () => {
		expect(formatYen(12345)).toBe('¥12,345')
	})

	it('null はダッシュ', () => {
		expect(formatYen(null)).toBe('—')
	})
})
