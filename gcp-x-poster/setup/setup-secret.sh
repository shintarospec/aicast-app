#!/bin/bash
# Secret Manager設定スクリプト

PROJECT_ID="aicast-472807"

echo "🔐 Secret Manager セットアップ"

# 使用方法表示
if [ $# -eq 0 ]; then
    echo "使用方法: $0 [アカウントID]"
    echo "例: $0 test_account"
    echo ""
    echo "このスクリプトはX APIキーをSecret Managerに安全に保存します"
    echo "実行前に以下の情報を準備してください:"
    echo "- Consumer Key"
    echo "- Consumer Secret" 
    echo "- Access Token"
    echo "- Access Token Secret"
    exit 1
fi

ACCOUNT_ID=$1

echo "アカウント設定: $ACCOUNT_ID"
echo ""

# APIキー入力
echo "🔑 X APIキーを入力してください:"
echo -n "Consumer Key: "
read -r CONSUMER_KEY

echo -n "Consumer Secret: "
read -s CONSUMER_SECRET
echo ""

echo -n "Access Token: "
read -r ACCESS_TOKEN

echo -n "Access Token Secret: "
read -s ACCESS_TOKEN_SECRET
echo ""

# JSON作成
TEMP_FILE="/tmp/api-keys-${ACCOUNT_ID}.json"
cat > "$TEMP_FILE" << EOF
{
  "consumer_key": "$CONSUMER_KEY",
  "consumer_secret": "$CONSUMER_SECRET",
  "access_token": "$ACCESS_TOKEN",
  "access_token_secret": "$ACCESS_TOKEN_SECRET"
}
EOF

echo ""
echo "📝 APIキー設定をSecret Managerに保存中..."

# Secret作成または更新
SECRET_NAME="x-api-${ACCOUNT_ID}"

# 既存シークレットの確認
if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "🔄 既存シークレットを更新します: $SECRET_NAME"
    gcloud secrets versions add "$SECRET_NAME" \
        --data-file="$TEMP_FILE" \
        --project="$PROJECT_ID"
else
    echo "🆕 新しいシークレットを作成します: $SECRET_NAME"
    gcloud secrets create "$SECRET_NAME" \
        --data-file="$TEMP_FILE" \
        --project="$PROJECT_ID"
fi

# 一時ファイル削除
rm -f "$TEMP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Secret設定完了: $SECRET_NAME"
    echo ""
    echo "🧪 テスト方法:"
    echo "curl -X POST 'https://asia-northeast1-aicast-472807.cloudfunctions.net/x-poster' \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{\"account_id\":\"$ACCOUNT_ID\",\"text\":\"Hello from Cloud Functions!\"}'"
else
    echo "❌ Secret設定失敗"
    exit 1
fi