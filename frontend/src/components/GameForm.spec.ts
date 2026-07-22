// GameForm の単体テスト（api クライアントをモック）
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type {
	Game,
	NintendoPrice,
	NintendoSearchItem,
	SteamAppDetail,
	SteamSearchItem,
} from '../api/client'
import GameForm from './GameForm.vue'

// API 呼び出しをモックし、MEDIA など定数は実物を使う
const {
	createGameMock,
	searchSteamMock,
	fetchSteamAppMock,
	searchNintendoMock,
	fetchNintendoPriceMock,
} = vi.hoisted(() => ({
	createGameMock: vi.fn(),
	searchSteamMock: vi.fn(),
	fetchSteamAppMock: vi.fn(),
	searchNintendoMock: vi.fn(),
	fetchNintendoPriceMock: vi.fn(),
}))
vi.mock('../api/client', async (importOriginal) => {
	const actual = await importOriginal<typeof import('../api/client')>()
	return {
		...actual,
		createGame: createGameMock,
		searchSteam: searchSteamMock,
		fetchSteamApp: fetchSteamAppMock,
		searchNintendo: searchNintendoMock,
		fetchNintendoPrice: fetchNintendoPriceMock,
	}
})

afterEach(() => {
	vi.clearAllMocks()
	vi.useRealTimers()
})

// 解決タイミングを手動制御できる Promise（非同期競合の検証用）
function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void } {
	let resolve!: (value: T) => void
	const promise = new Promise<T>((r) => {
		resolve = r
	})
	return { promise, resolve }
}

function makeDetail(overrides: Partial<SteamAppDetail> = {}): SteamAppDetail {
	return {
		appid: 1245620,
		name: 'ELDEN RING',
		release_date: '2022年2月25日',
		current_price: 5000,
		header_image: null,
		short_description: null,
		genres: [],
		...overrides,
	}
}

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

	it('タイトル入力後デバウンスを経て searchSteam を呼び候補を表示する', async () => {
		vi.useFakeTimers()
		const items: SteamSearchItem[] = [
			{ appid: 1245620, name: 'ELDEN RING', tiny_image: null, price: 8800 },
		]
		searchSteamMock.mockResolvedValue(items)

		const wrapper = mount(GameForm)
		await wrapper.find('input[type="text"]').setValue('elden')
		// デバウンス経過前は未呼び出し
		expect(searchSteamMock).not.toHaveBeenCalled()
		await vi.advanceTimersByTimeAsync(400)

		expect(searchSteamMock).toHaveBeenCalledWith('elden')
		expect(wrapper.text()).toContain('ELDEN RING')
	})

	it('候補を選ぶと詳細を取得し現在価格・steam_appid を自動反映して送信する', async () => {
		const items: SteamSearchItem[] = [
			{ appid: 1245620, name: 'ELDEN RING', tiny_image: null, price: 8800 },
		]
		const detail: SteamAppDetail = {
			appid: 1245620,
			name: 'ELDEN RING',
			release_date: '2022年2月25日',
			current_price: 5000,
			header_image: 'https://example.com/h.jpg',
			short_description: '死は運命',
			genres: ['アクション'],
		}
		searchSteamMock.mockResolvedValue(items)
		fetchSteamAppMock.mockResolvedValue(detail)
		createGameMock.mockResolvedValue({} as Game)

		// フェイクタイマー下で描画した要素にはクリックリスナが付かないため実タイマーで待つ
		const wrapper = mount(GameForm)
		await wrapper.find('input[type="text"]').setValue('elden')
		await new Promise((resolve) => setTimeout(resolve, 350))
		await flushPromises()

		// 候補（li）をクリックして選択
		await wrapper.find('.suggest-item').trigger('click')
		await flushPromises()

		expect(fetchSteamAppMock).toHaveBeenCalledWith(1245620)
		// タイトル・現在価格が自動入力される
		const titleInput = wrapper.find('input[type="text"]').element as HTMLInputElement
		expect(titleInput.value).toBe('ELDEN RING')

		// 購入価格を入れて送信
		const numbers = wrapper.findAll('input[type="number"]')
		await numbers[0].setValue(8800)
		await wrapper.find('form').trigger('submit')
		await flushPromises()

		expect(createGameMock.mock.calls[0][0]).toMatchObject({
			title: 'ELDEN RING',
			current_price: 5000,
			steam_appid: 1245620,
		})
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

	it('詳細取得中に手入力すると古い詳細で上書きしない', async () => {
		searchSteamMock.mockResolvedValue([
			{ appid: 1245620, name: 'ELDEN RING', tiny_image: null, price: 8800 },
		] satisfies SteamSearchItem[])
		const d = deferred<SteamAppDetail>()
		fetchSteamAppMock.mockReturnValue(d.promise)

		const wrapper = mount(GameForm)
		await wrapper.find('input[type="text"]').setValue('elden')
		await new Promise((resolve) => setTimeout(resolve, 350))
		await flushPromises()

		// 候補を選択（詳細取得は保留のまま）
		await wrapper.find('.suggest-item').trigger('click')
		expect(fetchSteamAppMock).toHaveBeenCalledWith(1245620)

		// 取得完了前にユーザーがタイトルを手修正 → 世代が進む
		await wrapper.find('input[type="text"]').setValue('自分で決めたタイトル')

		// 遅れて詳細が返っても反映されない
		d.resolve(makeDetail())
		await flushPromises()

		const titleInput = wrapper.find('input[type="text"]').element as HTMLInputElement
		expect(titleInput.value).toBe('自分で決めたタイトル')

		// 手入力済みなので steam_appid は付かない（購入価格のみ入れて送信）
		await wrapper.findAll('input[type="number"]')[0].setValue(3000)
		createGameMock.mockResolvedValue({} as Game)
		await wrapper.find('form').trigger('submit')
		await flushPromises()
		expect(createGameMock.mock.calls[0][0].steam_appid).toBeNull()
	})

	it('古い検索レスポンスは新しい入力の候補を上書きしない', async () => {
		vi.useFakeTimers()
		const a = deferred<SteamSearchItem[]>()
		const b = deferred<SteamSearchItem[]>()
		searchSteamMock.mockReturnValueOnce(a.promise).mockReturnValueOnce(b.promise)

		const wrapper = mount(GameForm)
		await wrapper.find('input[type="text"]').setValue('ab')
		await vi.advanceTimersByTimeAsync(350) // 1回目の検索が発火し a を待つ
		await wrapper.find('input[type="text"]').setValue('abc')
		await vi.advanceTimersByTimeAsync(350) // 2回目の検索が発火し b を待つ

		// 新しい検索(b)を先に、古い検索(a)を後に解決する
		b.resolve([{ appid: 2, name: 'NEW-B', tiny_image: null, price: null }])
		await flushPromises()
		a.resolve([{ appid: 1, name: 'OLD-A', tiny_image: null, price: null }])
		await flushPromises()

		expect(wrapper.text()).toContain('NEW-B')
		expect(wrapper.text()).not.toContain('OLD-A')
	})

	it('媒体が Nintendo Switch なら Nintendo を検索する', async () => {
		vi.useFakeTimers()
		searchNintendoMock.mockResolvedValue([
			{
				nsuid: '70010000046394',
				title: 'スプラトゥーン3',
				hardware: 'Nintendo Switch',
				thumbnail: null,
				price: 6500,
			},
		] satisfies NintendoSearchItem[])

		const wrapper = mount(GameForm)
		await wrapper.find('select').setValue('Nintendo Switch')
		await wrapper.find('input[type="text"]').setValue('スプラ')
		await vi.advanceTimersByTimeAsync(400)

		expect(searchNintendoMock).toHaveBeenCalledWith('スプラ')
		expect(searchSteamMock).not.toHaveBeenCalled()
		// 機種名と価格が候補の補足に出る
		expect(wrapper.text()).toContain('スプラトゥーン3')
		expect(wrapper.text()).toContain('Nintendo Switch')
	})

	it('媒体を切り替えると前の媒体の候補は残らない', async () => {
		vi.useFakeTimers()
		searchSteamMock.mockResolvedValue([
			{ appid: 1245620, name: 'ELDEN RING', tiny_image: null, price: 8800 },
		] satisfies SteamSearchItem[])
		// 切り替え後の再検索は空にして、候補が消えることだけを見る
		searchNintendoMock.mockResolvedValue([])

		const wrapper = mount(GameForm)
		await wrapper.find('input[type="text"]').setValue('elden')
		await vi.advanceTimersByTimeAsync(400)
		expect(wrapper.text()).toContain('ELDEN RING')

		await wrapper.find('select').setValue('Nintendo Switch')
		await vi.advanceTimersByTimeAsync(400)

		expect(wrapper.text()).not.toContain('ELDEN RING')
	})

	it('Nintendo の候補を選ぶとセール価格を現在価格へ自動入力する', async () => {
		searchNintendoMock.mockResolvedValue([
			{
				nsuid: '70070000037189',
				title: 'セール中のゲーム',
				hardware: 'Nintendo Switch',
				thumbnail: null,
				price: 471,
			},
		] satisfies NintendoSearchItem[])
		fetchNintendoPriceMock.mockResolvedValue({
			nsuid: '70070000037189',
			regular_price: 2358,
			current_price: 471,
			on_sale: true,
			sale_end: '2026-07-31T14:59:59Z',
		} satisfies NintendoPrice)
		createGameMock.mockResolvedValue({} as Game)

		// クリックリスナを付けるため実タイマーで待つ
		const wrapper = mount(GameForm)
		await wrapper.find('select').setValue('Nintendo Switch')
		await wrapper.find('input[type="text"]').setValue('セール')
		await new Promise((resolve) => setTimeout(resolve, 350))
		await flushPromises()

		await wrapper.find('.suggest-item').trigger('click')
		await flushPromises()

		expect(fetchNintendoPriceMock).toHaveBeenCalledWith('70070000037189')
		// セール中である旨と定価が分かる
		expect(wrapper.text()).toContain('セール中')

		await wrapper.findAll('input[type="number"]')[0].setValue(6000)
		await wrapper.find('form').trigger('submit')
		await flushPromises()

		expect(createGameMock.mock.calls[0][0]).toMatchObject({
			title: 'セール中のゲーム',
			medium: 'Nintendo Switch',
			current_price: 471,
			steam_appid: null,
		})
	})

	it('ダウンロード版が無い候補は価格を取りに行かずタイトルだけ入る', async () => {
		searchNintendoMock.mockResolvedValue([
			{
				nsuid: null,
				title: 'ゼルダの伝説 時のオカリナ',
				hardware: 'Nintendo Switch',
				thumbnail: null,
				price: null,
			},
		] satisfies NintendoSearchItem[])

		const wrapper = mount(GameForm)
		await wrapper.find('select').setValue('Nintendo Switch')
		await wrapper.find('input[type="text"]').setValue('ゼルダ')
		await new Promise((resolve) => setTimeout(resolve, 350))
		await flushPromises()

		expect(wrapper.text()).toContain('価格を取得できません')

		await wrapper.find('.suggest-item').trigger('click')
		await flushPromises()

		expect(fetchNintendoPriceMock).not.toHaveBeenCalled()
		const titleInput = wrapper.find('input[type="text"]').element as HTMLInputElement
		expect(titleInput.value).toBe('ゼルダの伝説 時のオカリナ')
	})

	it('価格取得に対応しない媒体では検索しない', async () => {
		vi.useFakeTimers()

		const wrapper = mount(GameForm)
		await wrapper.find('select').setValue('PS5')
		await wrapper.find('input[type="text"]').setValue('ゴッド')
		await vi.advanceTimersByTimeAsync(400)

		expect(searchSteamMock).not.toHaveBeenCalled()
		expect(searchNintendoMock).not.toHaveBeenCalled()
		// 自動取得に対応していないことが分かる
		expect(wrapper.text()).toContain('自動取得')
	})

	it('詳細取得中に登録が成功したら遅れて届いた詳細でフォームが復活しない', async () => {
		searchSteamMock.mockResolvedValue([
			{ appid: 1245620, name: 'ELDEN RING', tiny_image: null, price: 8800 },
		] satisfies SteamSearchItem[])
		const d = deferred<SteamAppDetail>()
		fetchSteamAppMock.mockReturnValue(d.promise)
		const c = deferred<Game>()
		createGameMock.mockReturnValue(c.promise)

		const wrapper = mount(GameForm)
		await wrapper.find('input[type="text"]').setValue('elden')
		await new Promise((resolve) => setTimeout(resolve, 350))
		await flushPromises()

		// 候補を選択（詳細取得は保留のまま）
		await wrapper.find('.suggest-item').trigger('click')

		// 詳細を待たずに送信（登録も保留）
		await wrapper.findAll('input[type="number"]')[0].setValue(3000)
		await wrapper.find('form').trigger('submit')

		// 登録成功によるリセットの直後、watch が走る前に詳細が解決する競合を作る
		c.resolve({} as Game)
		d.resolve(makeDetail())
		await flushPromises()

		const titleInput = wrapper.find('input[type="text"]').element as HTMLInputElement
		expect(titleInput.value).toBe('')
		const priceInput = wrapper.findAll('input[type="number"]')[1].element as HTMLInputElement
		expect(priceInput.value).toBe('')
	})

	it('媒体を切り替えると自動入力された現在価格はクリアされる', async () => {
		searchSteamMock.mockResolvedValue([
			{ appid: 1245620, name: 'ELDEN RING', tiny_image: null, price: 8800 },
		] satisfies SteamSearchItem[])
		fetchSteamAppMock.mockResolvedValue(makeDetail({ current_price: 5000 }))
		searchNintendoMock.mockResolvedValue([])
		createGameMock.mockResolvedValue({} as Game)

		const wrapper = mount(GameForm)
		await wrapper.find('input[type="text"]').setValue('elden')
		await new Promise((resolve) => setTimeout(resolve, 350))
		await flushPromises()
		await wrapper.find('.suggest-item').trigger('click')
		await flushPromises()

		// Steam の価格が自動入力された状態から媒体を切り替える
		await wrapper.find('select').setValue('Nintendo Switch')
		await flushPromises()

		await wrapper.findAll('input[type="number"]')[0].setValue(3000)
		await wrapper.find('form').trigger('submit')
		await flushPromises()

		// 前の媒体の価格を引き継がない
		expect(createGameMock.mock.calls[0][0].current_price).toBeNull()
	})

	it('手入力した現在価格は媒体を切り替えても残る', async () => {
		searchNintendoMock.mockResolvedValue([])
		createGameMock.mockResolvedValue({} as Game)

		const wrapper = mount(GameForm)
		await wrapper.find('input[type="text"]').setValue('DQ')
		const numbers = wrapper.findAll('input[type="number"]')
		await numbers[0].setValue(5000)
		await numbers[1].setValue(4200) // 現在価格を手入力
		await wrapper.find('select').setValue('Nintendo Switch')
		await flushPromises()

		await wrapper.find('form').trigger('submit')
		await flushPromises()

		expect(createGameMock.mock.calls[0][0].current_price).toBe(4200)
	})

	it('古い検索が終わっても新しい検索中は検索中の表示が消えない', async () => {
		vi.useFakeTimers()
		const a = deferred<SteamSearchItem[]>()
		const b = deferred<SteamSearchItem[]>()
		searchSteamMock.mockReturnValueOnce(a.promise).mockReturnValueOnce(b.promise)

		const wrapper = mount(GameForm)
		await wrapper.find('input[type="text"]').setValue('ab')
		await vi.advanceTimersByTimeAsync(350)
		await wrapper.find('input[type="text"]').setValue('abc')
		await vi.advanceTimersByTimeAsync(350)

		// 古い検索だけが解決：新しい検索は継続中なので表示は消えない
		a.resolve([])
		await flushPromises()
		expect(wrapper.text()).toContain('検索中')

		b.resolve([])
		await flushPromises()
		expect(wrapper.text()).not.toContain('検索中')
	})

	it('送信中はもう一度 submit しても多重送信しない', async () => {
		searchSteamMock.mockResolvedValue([])
		const c = deferred<Game>()
		createGameMock.mockReturnValue(c.promise)

		const wrapper = mount(GameForm)
		await wrapper.find('input[type="text"]').setValue('DQ')
		await wrapper.findAll('input[type="number"]')[0].setValue(5000)

		// 1回目で送信開始（createGame は保留）、続けて2回目を試みる
		await wrapper.find('form').trigger('submit')
		await wrapper.find('form').trigger('submit')

		expect(createGameMock).toHaveBeenCalledOnce()

		c.resolve({} as Game)
		await flushPromises()
	})
})
