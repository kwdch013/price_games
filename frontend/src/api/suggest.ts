// 媒体ごとのサジェスト提供元（Steam / Nintendo eShop）を吸収する層。
// フォーム側は媒体を意識せず「候補を検索する」「候補から詳細を取る」だけを扱えるようにする。
import {
	fetchNintendoPrice,
	fetchSteamApp,
	formatYen,
	searchNintendo,
	searchSteam,
	type Medium,
	type NintendoSearchItem,
	type SteamSearchItem,
} from './client'

export type SuggestSource = 'steam' | 'nintendo'

/** 媒体をまたいで共通に扱う候補 */
export interface SuggestItem {
	key: string
	title: string
	image: string | null
	note: string // 機種名・価格などの補足表示
	steamAppid: number | null
	nsuid: string | null
	priceAvailable: boolean // 選択時に現在価格を確定できるか
}

/** 候補選択で得られる自動入力用の情報 */
export interface SuggestDetail {
	title: string
	currentPrice: number | null
	steamAppid: number | null
	releaseDate: string | null
	image: string | null
	note: string | null // セール中である旨など
}

/** 媒体に対応する価格取得元。取得できない媒体は null */
export function suggestSourceFor(medium: Medium): SuggestSource | null {
	switch (medium) {
		case 'PC(Steam)':
		case 'PC(その他)':
			return 'steam'
		case 'Nintendo Switch':
			return 'nintendo'
		default:
			return null
	}
}

function fromSteam(item: SteamSearchItem): SuggestItem {
	return {
		key: `steam:${item.appid}`,
		title: item.name,
		image: item.tiny_image,
		note: item.price === null ? '' : formatYen(item.price),
		steamAppid: item.appid,
		nsuid: null,
		priceAvailable: true,
	}
}

function fromNintendo(item: NintendoSearchItem): SuggestItem {
	// ダウンロード版が無い候補も一覧には残し、価格を取れない旨を明示する
	const parts = [item.hardware, item.price === null ? null : formatYen(item.price)].filter(Boolean)
	return {
		// nsuid が無い候補もあるためタイトルで代替して一意にする
		key: `nintendo:${item.nsuid ?? item.title}`,
		title: item.title,
		image: item.thumbnail,
		note: item.nsuid
			? parts.join(' / ')
			: [...parts, 'ダウンロード版が無いため価格を取得できません'].join(' / '),
		steamAppid: null,
		nsuid: item.nsuid,
		priceAvailable: item.nsuid !== null,
	}
}

/** 媒体に応じて候補を検索する。価格取得に対応しない媒体では検索しない */
export async function searchTitles(medium: Medium, q: string): Promise<SuggestItem[]> {
	switch (suggestSourceFor(medium)) {
		case 'steam':
			return (await searchSteam(q)).map(fromSteam)
		case 'nintendo':
			return (await searchNintendo(q)).map(fromNintendo)
		default:
			return []
	}
}

/** 候補から自動入力用の詳細を取得する。価格を確定できない候補は null */
export async function fetchSuggestDetail(
	medium: Medium,
	item: SuggestItem,
): Promise<SuggestDetail | null> {
	if (!item.priceAvailable) {
		return null
	}
	if (suggestSourceFor(medium) === 'steam' && item.steamAppid !== null) {
		const detail = await fetchSteamApp(item.steamAppid)
		return {
			title: detail.name,
			currentPrice: detail.current_price,
			steamAppid: detail.appid,
			releaseDate: detail.release_date,
			image: detail.header_image,
			note: null,
		}
	}
	if (suggestSourceFor(medium) === 'nintendo' && item.nsuid !== null) {
		const price = await fetchNintendoPrice(item.nsuid)
		return {
			// eShop の価格 API はタイトルを返さないため、候補のタイトルをそのまま使う
			title: item.title,
			currentPrice: price.current_price,
			steamAppid: null,
			releaseDate: null,
			image: item.image,
			note: price.on_sale
				? `セール中（定価 ${formatYen(price.regular_price)}${formatSaleEnd(price.sale_end)}）`
				: null,
		}
	}
	return null
}

/** セール終了日時（UTC の ISO8601）を表示用の文字列にする */
function formatSaleEnd(saleEnd: string | null): string {
	if (!saleEnd) {
		return ''
	}
	const date = new Date(saleEnd)
	if (Number.isNaN(date.getTime())) {
		return ''
	}
	return ` / ${date.toLocaleDateString('ja-JP')}まで`
}
