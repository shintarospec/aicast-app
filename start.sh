#!/bin/bash

# 本番環境用の起動スクリプト
echo "=== AIcast App Starting ==="

# 環境変数の設定
export STREAMLIT_SERVER_PORT=8501
export STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Streamlitアプリケーションを起動
streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --browser.gatherUsageStats=false