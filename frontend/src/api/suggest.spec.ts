// 媒体ごとのサジェスト提供元を吸収する層の単体テスト
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { NintendoPrice, NintendoSearchItem, SteamAppDetail, SteamSearchItem } from './client'
import { fetchSuggestDetail, searchTitles, suggestSourceFor } from './suggest'

const { searchSteamMock, fetchSteamAppMock, searchNintendoMock, fetchNintendoPriceMock } =
	vi.hoisted(() => ({
		searchSteamMock: vi.fn(),
		fetchSteamAppMock: vi.fn(),
		searchNintendoMock: vi.fn(),
		fetchNintendoPriceMock: vi.fn(),
	}))

vi.mock('./client', async (importOriginal) => {
	const actual = await importOriginal<typeof import('./client')>()
	return {
		...actual,
		searchSteam: searchSteamMock,
		fetchSteamApp: fetchSteamAppMock,
		searchNintendo: searchNintendoMock,
		fetchNintendoPrice: fetchNintendoPriceMock,
	}
})

afterEach(() => {
	vi.clearAllMocks()
})

describe('suggestSourceFor', () => {
	it('PC 系は Steam を使う', () => {
		expect(suggestSourceFor('PC(Steam)')).toBe('steam')
		expect(suggestSourceFor('PC(その他)')).toBe('steam')
	})

	it('Switch は Nintendo を使う', () => {
		expect(suggestSourceFor('Nintendo Switch')).toBe('nintendo')
	})

	it('価格を取得できない媒体は null', () => {
		expect(suggestSourceFor('PS5')).toBeNull()
		expect(suggestSourceFor('Xbox')).toBeNull()
		expect(suggestSourceFor('その他')).toBeNull()
	})
})

describe('searchTitles', () => {
	it('Steam 候補を共通形式へ変換する', async () => {
		const items: SteamSearchItem[] = [
			{ appid: 1245620, name: 'ELDEN RING', tiny_image: 'https://example.com/e.jpg', price: 8800 },
		]
		searchSteamMock.mockResolvedValue(items)

		const result = await searchTitles('PC(Steam)', 'elden')

		expect(searchSteamMock).toHaveBeenCalledWith('elden')
		expect(result).toEqual([
			{
				key: 'steam:1245620',
				title: 'ELDEN RING',
				image: 'https://example.com/e.jpg',
				note: '¥8,800',
				steamAppid: 1245620,
				nsuid: null,
				priceAvailable: true,
			},
		])
	})

	it('Nintendo 候補は機種名と価格を補足に出す', async () => {
		const items: NintendoSearchItem[] = [
			{
				nsuid: '70010000046394',
				title: 'スプラトゥーン3',
				hardware: 'Nintendo Switch',
				thumbnail: 'https://example.com/s.jpg',
				price: 6500,
			},
		]
		searchNintendoMock.mockResolvedValue(items)

		const result = await searchTitles('Nintendo Switch', 'スプラ')

		expect(searchNintendoMock).toHaveBeenCalledWith('スプラ')
		expect(result[0]).toMatchObject({
			key: 'nintendo:70010000046394',
			title: 'スプラトゥーン3',
			note: 'Nintendo Switch / ¥6,500',
			nsuid: '70010000046394',
			steamAppid: null,
			priceAvailable: true,
		})
	})

	it('ダウンロード版が無い Nintendo 候補は価格取得不可として示す', async () => {
		const items: NintendoSearchItem[] = [
			{
				nsuid: null,
				title: 'ゼルダの伝説 時のオカリナ',
				hardware: 'Nintendo Switch',
				thumbnail: null,
				price: null,
			},
		]
		searchNintendoMock.mockResolvedValue(items)

		const result = await searchTitles('Nintendo Switch', 'ゼルダ')

		expect(result[0].priceAvailable).toBe(false)
		expect(result[0].note).toContain('価格を取得できません')
		// key は nsuid が無くても一意になる
		expect(result[0].key).toBe('nintendo:ゼルダの伝説 時のオカリナ')
	})

	it('価格を取得できない媒体では検索せず空を返す', async () => {
		await expect(searchTitles('PS5', 'ゴッド')).resolves.toEqual([])
		expect(searchSteamMock).not.toHaveBeenCalled()
		expect(searchNintendoMock).not.toHaveBeenCalled()
	})
})

describe('fetchSuggestDetail', () => {
	const steamItem = {
		key: 'steam:1245620',
		title: 'ELDEN RING',
		image: null,
		note: '',
		steamAppid: 1245620,
		nsuid: null,
		priceAvailable: true,
	}

	it('Steam は詳細 API からタイトル・価格・発売日を取る', async () => {
		const detail: SteamAppDetail = {
			appid: 1245620,
			name: 'ELDEN RING',
			release_date: '2022年2月25日',
			current_price: 5000,
			header_image: 'https://example.com/h.jpg',
			short_description: null,
			genres: [],
		}
		fetchSteamAppMock.mockResolvedValue(detail)

		const result = await fetchSuggestDetail('PC(Steam)', steamItem)

		expect(fetchSteamAppMock).toHaveBeenCalledWith(1245620)
		expect(result).toEqual({
			title: 'ELDEN RING',
			currentPrice: 5000,
			steamAppid: 1245620,
			releaseDate: '2022年2月25日',
			image: 'https://example.com/h.jpg',
			note: null,
		})
	})

	const switchItem = {
		key: 'nintendo:70070000037189',
		title: 'セール中のゲーム',
		image: 'https://example.com/n.jpg',
		note: '',
		steamAppid: null,
		nsuid: '70070000037189',
		priceAvailable: true,
	}

	it('Nintendo は価格 API からセール価格を取り、セール中を補足に出す', async () => {
		const price: NintendoPrice = {
			nsuid: '70070000037189',
			regular_price: 2358,
			current_price: 471,
			on_sale: true,
			sale_end: '2026-07-31T14:59:59Z',
		}
		fetchNintendoPriceMock.mockResolvedValue(price)

		const result = await fetchSuggestDetail('Nintendo Switch', switchItem)

		expect(fetchNintendoPriceMock).toHaveBeenCalledWith('70070000037189')
		expect(result).toMatchObject({
			title: 'セール中のゲーム',
			currentPrice: 471,
			steamAppid: null,
			image: 'https://example.com/n.jpg',
		})
		// 定価とセール終了日が分かる補足を出す
		expect(result?.note).toContain('セール中')
		expect(result?.note).toContain('¥2,358')
	})

	it('Nintendo の通常価格ではセール表記を出さない', async () => {
		fetchNintendoPriceMock.mockResolvedValue({
			nsuid: '70010000046394',
			regular_price: 6500,
			current_price: 6500,
			on_sale: false,
			sale_end: null,
		} satisfies NintendoPrice)

		const result = await fetchSuggestDetail('Nintendo Switch', {
			...switchItem,
			nsuid: '70010000046394',
		})

		expect(result?.currentPrice).toBe(6500)
		expect(result?.note).toBeNull()
	})

	it('価格を取得できない候補は詳細を取りに行かない', async () => {
		const result = await fetchSuggestDetail('Nintendo Switch', {
			...switchItem,
			nsuid: null,
			priceAvailable: false,
		})

		expect(result).toBeNull()
		expect(fetchNintendoPriceMock).not.toHaveBeenCalled()
	})
})
