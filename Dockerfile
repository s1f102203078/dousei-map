# Pythonの公式イメージを使用
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# 環境変数を設定（Pythonのバッファリングを無効化など）
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# ライブラリをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードをコンテナにコピー
COPY src/ .

# Cloud Run用: ポート8080を開ける
EXPOSE 8080

# コンテナ起動時のコマンド（開発時はdocker-composeで上書きされるので仮のもの）
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "config.wsgi:application"]