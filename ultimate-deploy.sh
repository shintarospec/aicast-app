#!/bin/bash
# AIcast Room 究極デプロイスクリプト (Codespace完結版)

echo "🚀 AIcast Room 究極デプロイを開始します..."
echo ""

# 1. ローカルの変更をコミット・プッシュ
echo "📝 変更をGitにコミット & プッシュ中..."
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

# 2. GitHub Actions経由で本番デプロイを実行
echo "🤖 GitHub Actions経由で本番デプロイを実行中..."

# GitHub APIを使用してワークフローを手動実行
if command -v gh >/dev/null 2>&1; then
    echo "📡 GitHub CLI経由でワークフロー実行..."
    gh workflow run deploy.yml --field message="$COMMIT_MSG"
    echo "✅ GitHub Actionsワークフローを開始しました"
    echo "🔗 進捗確認: https://github.com/shintarospec/aicast-app/actions"
else
    echo "⚠️  GitHub CLI未インストール"
    echo "🔗 手動実行: https://github.com/shintarospec/aicast-app/actions/workflows/deploy.yml"
    echo "👆 上記URLで「Run workflow」ボタンをクリックしてください"
fi

echo ""
echo "📋 または本番環境で直接実行:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "cd /home/shintaro/aicast-app"
echo "git pull origin main"  
echo "screen -S aicast -X quit; sleep 2; screen -dmS aicast bash -c 'python3 run.py'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 アプリURL: http://153.127.48.168:8501"
echo "🎉 デプロイ完了！"