FROM node:20-slim

WORKDIR /app

# NASの共有フォルダの影響を受けない「ビルド領域」に package.json だけをコピー
COPY package.json ./

# ここでインストールを済ませる！（Synologyのエラーを完全に回避）
RUN npm install

EXPOSE 5173

# 起動コマンド
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
