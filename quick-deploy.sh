#!/bin/bash
# AIcast Room 簡単デプロイスクリプト (手動プル方式)

echo "🚀 AIcast Room デプロイを開始します..."

# 1. ローカルの変更をコミット・プッシュ
echo "📝 変更をGitにコミット中..."
git add -A

if [ $# -eq 0 ]; then
    COMMIT_MSG="本番デプロイ: $(date '+%Y-%m-%d %H:%M:%S')"
else
    COMMIT_MSG="$*"
fi

git commit -m "$COMMIT_MSG"
git push origin main

echo "✅ GitHubにプッシュ完了"
echo ""
echo "📋 次に本番環境で以下のコマンドを実行してください:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "cd /home/shintaro/aicast-app"
echo "git pull origin main"
echo "screen -S aicast -X quit; sleep 2; screen -dmS aicast bash -c 'python3 run.py'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 アプリURL: http://153.127.48.168:8501"
echo "🎉 ローカル作業完了！"