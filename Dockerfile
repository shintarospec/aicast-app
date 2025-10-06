# ベースとなるPythonの環境を指定
FROM python:3.10-slim

# 作業ディレクトリを作成して移動
WORKDIR /app

# 必要なライブラリをインストール
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# アプリのコードをコピー
COPY . .

# Cloud Runが指定するポートでStreamlitを起動するコマンド
CMD echo "--- Starting Streamlit on PORT_ENV: $PORT ---" && streamlit run app.py --server.port=$PORT --server.headless=true
