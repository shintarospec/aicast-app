#!/bin/bash
# 実際のX APIキー設定スクリプト

PROJECT_ID="aicast-472807"

echo "🔐 実際のX APIキー設定"
echo "注意: 実際のAPIキー情報を入力してください"

# アカウントIDの入力
read -p "アカウントID (例: main_account): " ACCOUNT_ID

if [ -z "$ACCOUNT_ID" ]; then
    echo "❌ アカウントIDが必要です"
    exit 1
fi

echo "📝 以下の情報を入力してください（X Developer Portalより）:"

# APIキー情報の入力
read -p "Consumer Key: " CONSUMER_KEY
read -p "Consumer Secret: " CONSUMER_SECRET  
read -p "Access Token: " ACCESS_TOKEN
read -s -p "Access Token Secret: " ACCESS_TOKEN_SECRET
echo

# JSONファイル作成
cat > /tmp/api-keys-${ACCOUNT_ID}.json << EOF
{
  "consumer_key": "$CONSUMER_KEY",
  "consumer_secret": "$CONSUMER_SECRET",
  "access_token": "$ACCESS_TOKEN",
  "access_token_secret": "$ACCESS_TOKEN_SECRET"
}
EOF

# Secret Manager作成
echo "☁️ Secret Manager設定中..."
gcloud secrets create x-api-${ACCOUNT_ID} \
    --data-file=/tmp/api-keys-${ACCOUNT_ID}.json \
    --project=$PROJECT_ID

# 一時ファイル削除
rm /tmp/api-keys-${ACCOUNT_ID}.json

if [ $? -eq 0 ]; then
    echo "✅ APIキー設定完了: x-api-${ACCOUNT_ID}"
    echo ""
    echo "🚀 テスト投稿コマンド:"
    echo "curl -X POST 'https://x-poster-pmwmx7vixa-an.a.run.app' \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{\"account_id\":\"${ACCOUNT_ID}\",\"text\":\"Hello from Cloud Functions! 🚀\"}'"
else
    echo "❌ APIキー設定に失敗しました"
fi