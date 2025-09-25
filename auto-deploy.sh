#!/bin/bash
# AIcast Room 完全自動デプロイ (新サーバー対応)

echo "🚀 AIcast Room 完全自動デプロイを開始します..."
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

# 2. 本番環境への自動デプロイ
echo "🔄 本番環境 (ubuntu@153.126.194.114) を更新中..."

# SSHパスワード認証での自動実行
# 注意: 実際の本番環境ではSSHキー認証を推奨
read -s -p "🔑 本番サーバーのパスワードを入力してください: " SERVER_PASSWORD
echo ""

# sshpassを使用した自動ログイン (利用可能な場合)
if command -v sshpass >/dev/null 2>&1; then
    echo "🤖 sshpass経由で自動デプロイ実行中..."
    sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no ubuntu@153.126.194.114 << 'EOF'
        echo "📁 aicast-appディレクトリに移動..."
        cd /home/ubuntu/aicast-app
        
        echo "📥 最新コードを取得中..."
        git pull origin main
        
        echo "🔄 既存プロセスの停止..."
        if screen -list | grep -q "aicast"; then
            screen -S aicast -X quit
            sleep 3
            echo "✅ 既存プロセスを停止しました"
        else
            echo "ℹ️  既存プロセスなし"
        fi
        
        echo "🚀 新プロセスを起動中..."
        screen -dmS aicast bash -c 'cd /home/ubuntu/aicast-app && python3 run.py'
        sleep 2
        
        echo "📊 プロセス状況:"
        screen -list
        
        echo "✅ 本番デプロイ完了！"
EOF
    echo ""
    echo "🎉 完全自動デプロイ成功！"
else
    echo "⚠️  sshpassが見つかりません。手動デプロイ手順を表示します:"
    echo ""
    echo "📋 本番環境で以下のコマンドを実行してください:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "ssh ubuntu@153.126.194.114"
    echo "cd /home/ubuntu/aicast-app"
    echo "git pull origin main"
    echo "screen -S aicast -X quit; sleep 2; screen -dmS aicast bash -c 'python3 run.py'"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

echo ""
echo "🌐 アプリURL: http://153.126.194.114:8502"
echo "🔗 GitHub Actions: https://github.com/shintarospec/aicast-app/actions"