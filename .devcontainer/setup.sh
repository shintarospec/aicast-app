#!/bin/bash
set -e

echo "🔧 AIcast Room 開発環境セットアップ開始..."

# 1. Python依存関係インストール
echo "📦 依存関係をインストール中..."
pip3 install --user -r requirements.txt

# 2. 認証ディレクトリ作成
mkdir -p credentials

# 3. GitHub Codespaces Secrets から認証情報を復元
if [ -n "$SERVICE_ACCOUNT_KEY" ]; then
    echo "🔐 サービスアカウントキーを復元中..."
    echo "$SERVICE_ACCOUNT_KEY" > credentials/service-account-key.json
    export GOOGLE_APPLICATION_CREDENTIALS="$PWD/credentials/service-account-key.json"
    echo "✅ サービスアカウントキー復元完了"
else
    echo "⚠️  SERVICE_ACCOUNT_KEY が見つかりません"
    echo "   GitHub Settings → Codespaces Secrets に登録してください"
fi

if [ -n "$GOOGLE_DRIVE_CREDENTIALS" ]; then
    echo "🔐 Google Drive認証情報を復元中..."
    echo "$GOOGLE_DRIVE_CREDENTIALS" > credentials/google_drive_credentials.json
    echo "✅ Google Drive認証情報復元完了"
else
    echo "⚠️  GOOGLE_DRIVE_CREDENTIALS が見つかりません（オプション）"
fi

if [ -n "$GCP_PROJECT" ]; then
    echo "✅ GCP_PROJECT: $GCP_PROJECT"
else
    echo "⚠️  GCP_PROJECT が見つかりません"
fi

echo ""
echo "✅ セットアップ完了！"
echo ""
echo "📝 次のステップ:"
echo "  1. python3 test_vertex_vps.py で認証をテスト"
echo "  2. python3 run.py でアプリを起動"
echo ""
