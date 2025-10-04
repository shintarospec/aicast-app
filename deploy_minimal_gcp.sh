#!/bin/bash

# ミニマムGCP自動投稿システム デプロイスクリプト

set -e

echo "🚀 ミニマムGCP自動投稿システム デプロイ開始"

# 環境変数設定
PROJECT_ID="aicast-472807"
REGION="asia-northeast1"
FUNCTION_NAME="x-poster"

echo "📋 設定確認:"
echo "  プロジェクトID: $PROJECT_ID"
echo "  リージョン: $REGION"
echo "  関数名: $FUNCTION_NAME"

# 1. プロジェクト設定
echo "🔧 GCPプロジェクト設定..."
gcloud config set project $PROJECT_ID

# 2. 必要なAPIを有効化
echo "🔌 必要なAPIを有効化..."
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# 3. Cloud Functions デプロイ
echo "☁️ Cloud Functions デプロイ..."
cd cloud_functions/x_poster

gcloud functions deploy $FUNCTION_NAME \
    --runtime python39 \
    --trigger-http \
    --allow-unauthenticated \
    --region $REGION \
    --memory 256MB \
    --timeout 60s \
    --set-env-vars GCP_PROJECT=$PROJECT_ID

# 4. デプロイ成功確認
echo "✅ デプロイ完了確認..."
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME --region=$REGION --format="value(httpsTrigger.url)")

echo ""
echo "🎉 デプロイ完了！"
echo "📍 Cloud Functions URL: $FUNCTION_URL"
echo ""
echo "🔗 次のステップ:"
echo "  1. Secret Managerに認証情報を設定"
echo "  2. AIcast RoomにCloud Functions URLを設定"
echo "  3. テスト投稿実行"
echo ""
echo "🔑 Secret Manager設定例:"
echo "  gcloud secrets create x-api-account-test"
echo "  echo '{\"consumer_key\":\"xxx\",\"consumer_secret\":\"xxx\",\"access_token\":\"xxx\",\"access_token_secret\":\"xxx\"}' | gcloud secrets versions add x-api-account-test --data-file=-"
echo ""
echo "📱 テスト用curl:"
echo "  curl -X POST $FUNCTION_URL \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"account_id\":\"account-test\",\"text\":\"Hello from Cloud Functions!\"}'"

cd ../..
echo "✨ セットアップ完了！"