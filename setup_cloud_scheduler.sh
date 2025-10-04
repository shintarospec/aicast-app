#!/bin/bash

# Google Cloud Scheduler設定スクリプト
# スケジュール投稿を定期的にチェックして実行する

PROJECT_ID=${GCP_PROJECT:-"aicast-472807"}
REGION=${GCP_REGION:-"asia-northeast1"}
SCHEDULE_CHECKER_URL="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/schedule_checker"

echo "🔧 Google Cloud Schedulerを設定中..."
echo "プロジェクト: $PROJECT_ID"
echo "リージョン: $REGION"

# Cloud Schedulerジョブを作成（5分間隔でチェック）
gcloud scheduler jobs create http aicast-schedule-checker \
    --location=$REGION \
    --schedule="*/5 * * * *" \
    --uri=$SCHEDULE_CHECKER_URL \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{"check_type":"scheduled"}' \
    --description="AIcast Room スケジュール投稿チェッカー（5分間隔）" \
    --time-zone="Asia/Tokyo" \
    --project=$PROJECT_ID

if [ $? -eq 0 ]; then
    echo "✅ Cloud Schedulerジョブを作成しました"
    echo "📅 5分間隔でスケジュール投稿をチェックします"
    echo "🕐 タイムゾーン: Asia/Tokyo"
else
    echo "❌ Cloud Schedulerジョブの作成に失敗しました"
    echo "既存のジョブがある場合は、以下で更新してください："
    echo "gcloud scheduler jobs update http aicast-schedule-checker --location=$REGION --schedule='*/5 * * * *'"
fi

echo ""
echo "📊 作成されたスケジューラーの確認："
gcloud scheduler jobs list --location=$REGION --project=$PROJECT_ID

echo ""
echo "🔧 手動でスケジューラーをテストする場合："
echo "gcloud scheduler jobs run aicast-schedule-checker --location=$REGION --project=$PROJECT_ID"