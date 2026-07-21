// SummaryPanel の単体テスト
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import SummaryPanel from './SummaryPanel.vue'

describe('SummaryPanel', () => {
	it('各損失の合計を整形表示する', () => {
		const wrapper = mount(SummaryPanel, {
			props: {
				summary: {
					count: 2,
					total_pile_loss: 8000,
					total_price_diff_loss: 2000,
					total_loss: 10000,
				},
			},
		})
		const text = wrapper.text()
		expect(text).toContain('¥10,000')
		expect(text).toContain('¥8,000')
		expect(text).toContain('¥2,000')
		expect(text).toContain('2 件')
	})
})
