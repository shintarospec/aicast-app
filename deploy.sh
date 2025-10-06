#!/bin/bash
# AIcast Room 本番デプロイスクリプト

echo "🚀 AIcast Room 本番デプロイを開始します..."

# 1. ローカルの変更をコミット・プッシュ
echo "📝 変更をGitにコミット中..."
git add -A
if [ $# -eq 0 ]; then
    # 引数がない場合はデフォルトメッセージ
    COMMIT_MSG="本番デプロイ: $(date '+%Y-%m-%d %H:%M:%S')"
else
    # 引数がある場合はそれをコミットメッセージに使用
    COMMIT_MSG="$*"
fi

git commit -m "$COMMIT_MSG"
git push origin main

echo "✅ GitHubにプッシュ完了"

# 2. 本番環境にSSH接続してアップデート
echo "🔄 本番環境を更新中..."
ssh -o StrictHostKeyChecking=no shintaro@153.127.48.168 << 'EOF'
    cd /home/shintaro/aicast-app
    git pull origin main
    
    # Screenセッションの確認と再起動
    if screen -list | grep -q "aicast"; then
        echo "🔄 既存のAIcastプロセスを再起動中..."
        screen -S aicast -X quit
        sleep 2
    fi
    
    # 新しいScreenセッションでアプリを起動
    echo "🚀 AIcastを起動中..."
    screen -dmS aicast bash -c 'cd /home/shintaro/aicast-app && python3 run.py'
    
    echo "✅ 本番環境のデプロイ完了！"
    echo "📊 Screenセッション一覧:"
    screen -list
EOF

echo "🎉 本番デプロイが完了しました！"
echo "🌐 アプリURL: http://153.127.48.168:8501"