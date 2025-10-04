#!/bin/bash
# Secret Manager用のアカウント設定スクリプト

PROJECT_ID="aicast-472807"

if [ $# -eq 0 ]; then
    echo "❌ 使用方法: $0 <account_id>"
    echo "例: $0 user_a"
    exit 1
fi

ACCOUNT_ID=$1
SECRET_NAME="x-api-${ACCOUNT_ID}"

echo "🔐 アカウント「$ACCOUNT_ID」のSecret Manager設定"

# APIキー入力
echo "📝 X APIキーを入力してください:"
read -p "Consumer Key: " CONSUMER_KEY
read -p "Consumer Secret: " CONSUMER_SECRET  
read -p "Access Token: " ACCESS_TOKEN
read -p "Access Token Secret: " ACCESS_TOKEN_SECRET

# JSON作成
cat > /tmp/api-keys-${ACCOUNT_ID}.json << EOF
{
  "consumer_key": "$CONSUMER_KEY",
  "consumer_secret": "$CONSUMER_SECRET", 
  "access_token": "$ACCESS_TOKEN",
  "access_token_secret": "$ACCESS_TOKEN_SECRET"
}
EOF

# Secret作成または更新
if gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "🔄 既存のSecretを更新中..."
    gcloud secrets versions add $SECRET_NAME \
        --data-file=/tmp/api-keys-${ACCOUNT_ID}.json \
        --project=$PROJECT_ID
else
    echo "✨ 新しいSecretを作成中..."
    gcloud secrets create $SECRET_NAME \
        --data-file=/tmp/api-keys-${ACCOUNT_ID}.json \
        --project=$PROJECT_ID
fi

# 一時ファイル削除
rm /tmp/api-keys-${ACCOUNT_ID}.json

echo "✅ Secret「$SECRET_NAME」設定完了!"
echo ""
echo "🧪 テスト投稿:"
echo "FUNCTION_URL=\$(gcloud functions describe x-poster --region=asia-northeast1 --format=\"value(serviceConfig.uri)\")"
echo "curl -X POST \$FUNCTION_URL \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"account_id\": \"$ACCOUNT_ID\", \"text\": \"テスト投稿 from Cloud Functions\"}'"