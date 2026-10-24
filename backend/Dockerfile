FROM python:3.12-slim

WORKDIR /app

#PostgreSQL接続用ライブラリなどのビルドに必要なパッケージ

RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

#FastAPIおよび関連ライブラリのインストール

RUN pip install --no-cache-dir fastapi uvicorn sqlmodel psycopg2-binary redis cryptography pydantic-settings

#コードがない状態でのCOPYエラーを防ぐための空ディレクトリ作成

RUN mkdir -p /app/app

#main.pyがあればFastAPIを起動、なければ待機状態にする起動コマンド

CMD ["sh", "-c", "if [ -f /app/app/main.py ]; then uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload; else echo 'Waiting for code...' && tail -f /dev/null; fi"]

