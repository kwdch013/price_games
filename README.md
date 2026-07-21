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
- メタデータ源: Steam Store API(無料・キー不要)
- 実行環境: Docker

## 開発
```bash
cp .env.example .env        # DATABASE_URL を設定（共有 Postgres の price_games ロール）
docker compose up           # API 起動(http://localhost:8010）
docker compose run --rm api pytest   # テスト
```

- API のホストポートは **8010**(8000 は既存の別アプリが使用中のため)
- DB は共有 Postgres の `price_games` データベース/ロールを使用(接続は `database_default` ネットワーク経由)

## ステータス
現在 Issue #1(プロジェクト基盤)を構築中。
