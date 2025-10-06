#!/bin/bash
# GCP X投稿システム デプロイスクリプト

echo "🚀 ミニマムGCP自動投稿システム デプロイ開始"

# プロジェクト設定
PROJECT_ID="aicast-472807"
REGION="asia-northeast1"
FUNCTION_NAME="x-poster"

# プロジェクト設定確認
echo "📋 プロジェクト設定: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# 現在の認証情報確認
echo "🔐 認証情報確認中..."
gcloud auth list --filter=status:ACTIVE --format="value(account)"

# 必要なAPIを有効化
echo "📡 Google Cloud APIs有効化中..."
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable cloudbuild.googleapis.com

echo "✅ APIs有効化完了"

# cloud_functionsディレクトリに移動
cd "$(dirname "$0")/../cloud_functions"

echo "📂 現在のディレクトリ: $(pwd)"
echo "📁 ファイル確認:"
ls -la

# Cloud Functions デプロイ
echo "☁️ Cloud Functions デプロイ中..."
echo "   Function名: $FUNCTION_NAME"
echo "   リージョン: $REGION"
echo "   Python: 3.11"

gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=x_poster \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars="GCP_PROJECT=$PROJECT_ID" \
    --memory=512Mi \
    --timeout=540s \
    --max-instances=10

# デプロイ結果確認
if [ $? -eq 0 ]; then
    echo "✅ デプロイ完了!"
    
    # Function URL取得
    FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME --region=$REGION --format="value(serviceConfig.uri)")
    
    echo ""
    echo "🎉 セットアップ完了!"
    echo "📍 Function URL: $FUNCTION_URL"
    echo ""
    echo "🔧 次のステップ:"
    echo "1. Secret Managerにアカウント別APIキーを設定"
    echo "   ./setup/setup-secret.sh [アカウントID]"
    echo ""
    echo "2. テスト投稿実行"
    echo "   curl -X POST '$FUNCTION_URL' \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"account_id\":\"test\",\"text\":\"Hello from Cloud Functions!\"}'"
    echo ""
    echo "3. AIcast RoomにFunction URLを設定"
    echo "   CLOUD_FUNCTIONS_URL = '$FUNCTION_URL'"
    
else
    echo "❌ デプロイ失敗"
    exit 1
fi