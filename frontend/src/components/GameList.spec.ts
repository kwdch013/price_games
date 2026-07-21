// GameList の単体テスト
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { Game } from '../api/client'
import GameList from './GameList.vue'

function makeGame(overrides: Partial<Game> = {}): Game {
	return {
		id: 1,
		title: 'エルデンリング',
		medium: 'PC(Steam)',
		purchase_price: 9000,
		current_price: 6000,
		progress: 20,
		note: '',
		steam_appid: null,
		created_at: '2026-07-21T00:00:00Z',
		pile_loss: 7200,
		price_diff_loss: 3000,
		...overrides,
	}
}

describe('GameList', () => {
	it('損失を整形して表示する', () => {
		const wrapper = mount(GameList, { props: { games: [makeGame()] } })
		expect(wrapper.text()).toContain('¥7,200')
		expect(wrapper.text()).toContain('¥3,000')
	})

	it('現在価格が無ければ価格差損失はダッシュ表示', () => {
		const wrapper = mount(GameList, {
			props: { games: [makeGame({ current_price: null, price_diff_loss: null })] },
		})
		expect(wrapper.text()).toContain('—')
	})

	it('削除ボタンで delete イベントを id 付きで発火する', async () => {
		const wrapper = mount(GameList, { props: { games: [makeGame({ id: 42 })] } })
		await wrapper.find('button').trigger('click')
		expect(wrapper.emitted('delete')?.[0]).toEqual([42])
	})

	it('空なら未登録メッセージを出す', () => {
		const wrapper = mount(GameList, { props: { games: [] } })
		expect(wrapper.text()).toContain('まだ登録がありません')
	})
})
