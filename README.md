# price_games — 積みゲー損失可視化アプリ

購入したものの未プレイで放置している「積みゲー」の損失を可視化し、プレイのモチベを上げる個人用 Web アプリ。

## 概要

購入したゲームの **タイトル・購入価格・媒体** を登録し、Steam の現在価格や進行度と比較して
「どれだけ損しているか」を可視化する。あわせて発売日などのメタデータ自動取得、
ポジティブレビューのまとめ、PC 向けおすすめ Mod を表示する。

### 損失の定義(両方を並記)
- **積みゲー損失** = `購入価格 × (1 − 進行度/100)` … 未プレイ分の「もったいない額」
- **価格差損失** = `max(購入価格 − 現在価格, 0)` … 高値掴み分

## 技術スタック
- バックエンド: FastAPI (Python 3.14)
- データベース: 共有 PostgreSQL(サーバー上の `postgres_db` を他アプリと使い回す)
- フロントエンド: Vue 3 (Vite / TypeScript)
- メタデータ源: Steam Store API / Nintendo eShop(いずれも無料・キー不要)
- 実行環境: Docker

### 価格取得の対応状況
| 媒体 | 検索 | 現在価格 | 取得元 |
| --- | --- | --- | --- |
| PC(Steam) | ○ | ○ | Steam Store API |
| Nintendo Switch / Switch 2 | ○ | ○(セール価格を含む) | `search.nintendo.jp` + `api.ec.nintendo.com` |
| PS5 / PS4 / Xbox | — | — | 公開 API が無く未対応 |

いずれもダウンロード版の価格。Nintendo は 3DS・Wii U・amiibo などを候補から除外している。

登録フォームでは、選択中の**媒体に応じてタイトルサジェストの提供元が切り替わる**。
候補を選ぶと現在価格(Nintendo はセール中ならセール価格)が自動入力される。
ダウンロード版が無い候補は、価格を取得できない旨を候補に表示する。

## 開発
```bash
cp .env.example .env        # DATABASE_URL を設定（共有 Postgres の price_games ロール）
docker compose up           # API 起動(http://localhost:8010）
docker compose run --rm api pytest   # テスト
```

外部サービスへ実接続する結合テストは opt-in。実行する場合は環境変数を指定する。

```bash
docker compose run --rm -e STEAM_INTEGRATION=1 api pytest tests/test_steam_integration.py
docker compose run --rm -e NINTENDO_INTEGRATION=1 api pytest tests/test_nintendo_integration.py
```

- API のホストポートは **8010**(8000 は既存の別アプリが使用中のため)
- フロント(Vite dev server)のホストポートは **5173**
- DB は共有 Postgres の `price_games` データベース/ロールを使用(接続は `database_default` ネットワーク経由)

### 別マシン(LAN)からアクセスする
`http://<サーバーの IP>:5173` を開けばそのまま動く。設定変更は不要。

- フロントは API を **同一オリジンの `/api`** で叩き、Vite dev server が `VITE_PROXY_TARGET`(既定 `http://api:8000`)へ中継する。
  ブラウザ視点の `localhost` に依存しないため、どのマシンから開いても到達できる
- CORS はプライベート IP レンジ(10/172.16-31/192.168)・`localhost`・`*.local` を既定で許可する。
  公開ドメインなど別のオリジンを許可したい場合のみ、環境変数 `CORS_ORIGINS`(カンマ区切り)を指定する
- ホストで直接 `npm run dev` する場合は `VITE_PROXY_TARGET=http://localhost:8010` を指定する
- IP アドレス・`localhost` でのアクセスは Vite が既定で許可する。独自ホスト名(例 `myserver.local`)で開く場合のみ
  `VITE_ALLOWED_HOSTS`(カンマ区切り)に列挙する。DNS rebinding 対策のため Host 検査自体は無効化しない

### DB マイグレーション(Alembic)
スキーマ変更は Alembic で管理する。接続先は環境変数 `DATABASE_URL` から読む(`alembic.ini` にパスワードは書かない)。

```bash
# 最新スキーマへ適用（コンテナ内で実行）
docker compose run --rm api alembic upgrade head
# 既にテーブルが存在する DB を初回だけベースラインへ整合（再作成しない）
docker compose run --rm api alembic stamp head
# モデル変更から新リビジョンを自動生成
docker compose run --rm api alembic revision --autogenerate -m "変更内容"
```

#### リビジョン
- `0001_baseline` — 既存 `game` テーブル(PK・CHECK 制約含む)。既存の共有 DB は当初 `alembic stamp head` で整合済み(stamp はテーブル/データを再作成せずリビジョンのみ記録する)
- `0002_price_history` — 価格推移を残す `price_history` テーブル(FK `game.id` の `ON DELETE CASCADE`、`price >= 0` の CHECK、`game_id` の index)

補足:
- `DATABASE_URL` にパスワードを URL エンコードして含める場合、`%` は `env.py` 側で `%%` にエスケープして扱う(`.env` に書く値自体は通常表記でよい)
- 当面は起動時 `init_db()`(create_all)と Alembic を併存させる。両者は制約名が異なりうるため、正となるスキーマは Alembic のリビジョンとする

## ステータス
現在 Issue #1(プロジェクト基盤)を構築中。
