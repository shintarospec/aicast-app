#!/bin/bash

# 本番環境用の起動スクリプト
echo "=== AIcast App Starting ==="

# 環境変数の設定
export STREAMLIT_SERVER_PORT=8501
export STREAMLIT_SERVER_ADDRESS=0.0.0.0

#!/bin/bash

# AIcast room アプリケーション起動スクリプト（本番環境用）

# Google Cloud認証設定
export GCP_PROJECT="aicast-472807"

# Application Default Credentials (ADC) の確認
ADC_FILE="$HOME/.config/gcloud/application_default_credentials.json"
if [ -f "$ADC_FILE" ]; then
    echo "✅ Google Cloud Application Default Credentials 確認完了"
    echo "📍 認証ファイル: $ADC_FILE"
elif [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "✅ Google Cloud Service Account Key 確認完了"
    echo "📍 認証ファイル: $GOOGLE_APPLICATION_CREDENTIALS"
else
    echo "❌ Error: Google Cloud認証が設定されていません"
    echo "💡 以下のいずれかの方法で認証を設定してください:"
    echo "   1. gcloud auth application-default login"
    echo "   2. export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json"
    exit 1
fi

echo "🚀 AIcast room アプリケーションを起動中..."

# Streamlitアプリケーションを起動
python3 -m streamlit run app.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true