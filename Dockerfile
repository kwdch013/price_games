# 開発・テスト・実行を同一環境で行うためのコンテナ（Python 3.14）
FROM python:3.14-slim

# Python のログを即時出力・pyc 非生成
ENV PYTHONUNBUFFERED=1 \
	PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# プロジェクトをインストール可能にするためソースを先に配置する
COPY pyproject.toml ./
COPY app ./app
COPY tests ./tests

RUN pip install --no-cache-dir --upgrade pip && \
	pip install --no-cache-dir ".[dev]"

EXPOSE 8000

# 本番相当の起動。開発時の reload は compose 側で上書きする。
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
