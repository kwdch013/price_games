// GameForm の単体テスト（api クライアントをモック）
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Game } from '../api/client'
import GameForm from './GameForm.vue'

// createGame をモックし、MEDIA は実物を使う
const { createGameMock } = vi.hoisted(() => ({ createGameMock: vi.fn() }))
vi.mock('../api/client', async (importOriginal) => {
	const actual = await importOriginal<typeof import('../api/client')>()
	return { ...actual, createGame: createGameMock }
})

afterEach(() => {
	vi.clearAllMocks()
})

describe('GameForm', () => {
	it('必須未入力ならエラー表示し API を呼ばない', async () => {
		const wrapper = mount(GameForm)
		await wrapper.find('form').trigger('submit')
		expect(wrapper.text()).toContain('必須')
		expect(createGameMock).not.toHaveBeenCalled()
	})

	it('入力して送信すると createGame を呼び created を発火する', async () => {
		const created: Game = {
			id: 1,
			title: 'DQ',
			medium: 'PC(Steam)',
			purchase_price: 5000,
			current_price: null,
			progress: 0,
			note: '',
			steam_appid: null,
			created_at: '2026-07-21T00:00:00Z',
			pile_loss: 5000,
			price_diff_loss: null,
		}
		createGameMock.mockResolvedValue(created)

		const wrapper = mount(GameForm)
		await wrapper.find('input[type="text"]').setValue('DQ')
		await wrapper.find('input[type="number"]').setValue(5000)
		await wrapper.find('form').trigger('submit')
		await flushPromises()

		expect(createGameMock).toHaveBeenCalledOnce()
		expect(createGameMock.mock.calls[0][0]).toMatchObject({ title: 'DQ', purchase_price: 5000 })
		expect(wrapper.emitted('created')?.[0]).toEqual([created])
	})

	it('現在価格を空にすると null に正規化して送信する', async () => {
		createGameMock.mockResolvedValue({} as Game)
		const wrapper = mount(GameForm)
		await wrapper.find('input[type="text"]').setValue('DQ')
		const numbers = wrapper.findAll('input[type="number"]')
		await numbers[0].setValue(5000) // 購入価格
		await numbers[1].setValue('') // 現在価格を空に
		await wrapper.find('form').trigger('submit')
		await flushPromises()

		expect(createGameMock.mock.calls[0][0].current_price).toBeNull()
	})
})
