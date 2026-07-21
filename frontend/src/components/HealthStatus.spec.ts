// HealthStatus コンポーネントの単体テスト
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import HealthStatus from './HealthStatus.vue'

afterEach(() => {
	vi.restoreAllMocks()
})

describe('HealthStatus', () => {
	it('疎通成功時は OK を表示する', async () => {
		// fetch をモックして status=ok を返す
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				json: () => Promise.resolve({ status: 'ok' }),
			}),
		)
		const wrapper = mount(HealthStatus)
		await flushPromises()
		expect(wrapper.text()).toContain('疎通 OK')
	})

	it('疎通失敗時はエラー表示する', async () => {
		vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('boom')))
		const wrapper = mount(HealthStatus)
		await flushPromises()
		expect(wrapper.text()).toContain('接続できません')
	})
})
