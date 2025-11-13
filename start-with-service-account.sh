#!/bin/bash
# AIcast Room を サービスアカウントキー認証で起動

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export GOOGLE_APPLICATION_CREDENTIALS="${SCRIPT_DIR}/credentials/service-account-key.json"
export GCP_PROJECT="aicast-472807"

echo "🔐 サービスアカウント認証を設定しました"
echo "📍 認証ファイル: $GOOGLE_APPLICATION_CREDENTIALS"

python3 run.py
