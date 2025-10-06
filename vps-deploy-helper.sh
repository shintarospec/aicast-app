#!/bin/bash

# VPSデプロイヘルパースクリプト
# Usage: ./vps-deploy-helper.sh [command]

VPS_HOST="153.126.194.114"  # さくらVPS IPアドレス
VPS_USER="ubuntu"
VPS_PATH="/home/ubuntu/aicast-app"

# SSH接続確認
check_ssh() {
    echo "🔍 VPS接続確認中..."
    if ssh -o ConnectTimeout=5 ${VPS_USER}@${VPS_HOST} 'echo "✅ SSH接続成功"'; then
        return 0
    else
        echo "❌ SSH接続失敗 - VPS_HOSTを確認してください"
        return 1
    fi
}

# コードプル & 再起動
deploy_with_restart() {
    echo "🌐 VPS: コードプル & アプリ再起動"
    ssh ${VPS_USER}@${VPS_HOST} "
        cd ${VPS_PATH} && 
        git pull origin clean-production && 
        screen -S aicast -X quit; 
        sleep 2 && 
        screen -dmS aicast bash -c 'source .venv/bin/activate && python3 run.py' && 
        echo '✅ デプロイ & 再起動完了'
    "
}

# コードプルのみ
deploy_only() {
    echo "🔄 VPS: コードプル (再起動なし)"
    ssh ${VPS_USER}@${VPS_HOST} "
        cd ${VPS_PATH} && 
        git pull origin clean-production && 
        echo '✅ プル完了 - アプリは継続稼働中'
    "
}

# ステータス確認
check_status() {
    echo "📊 VPS: ステータス確認"
    ssh ${VPS_USER}@${VPS_HOST} "
        echo '=== アプリ稼働状況 ===' && 
        ps aux | grep 'python3 run.py' | grep -v grep && 
        echo '' && 
        echo '=== 最新ログ (スケジュール投稿) ===' && 
        cd ${VPS_PATH} && tail -5 schedule.log && 
        echo '' && 
        echo '=== 最新ログ (リツイート予約) ===' && 
        tail -5 retweet.log
    "
}

# アプリ再起動
restart_app() {
    echo "🚀 VPS: アプリ再起動"
    ssh ${VPS_USER}@${VPS_HOST} "
        cd ${VPS_PATH} && 
        screen -S aicast -X quit; 
        sleep 3 && 
        screen -dmS aicast bash -c 'source .venv/bin/activate && python3 run.py' && 
        echo '✅ AIcast Room 再起動完了'
    "
}

# ログ監視
watch_logs() {
    echo "📋 VPS: リアルタイムログ監視 (Ctrl+C で終了)"
    ssh ${VPS_USER}@${VPS_HOST} "cd ${VPS_PATH} && tail -f schedule.log"
}

# メイン処理
case "$1" in
    "deploy")
        check_ssh && deploy_with_restart
        ;;
    "pull")
        check_ssh && deploy_only
        ;;
    "status")
        check_ssh && check_status
        ;;
    "restart")
        check_ssh && restart_app
        ;;
    "logs")
        check_ssh && watch_logs
        ;;
    "check")
        check_ssh
        ;;
    *)
        echo "🛠️  VPS デプロイヘルパー"
        echo ""
        echo "使用方法:"
        echo "  ./vps-deploy-helper.sh deploy   - コードプル & アプリ再起動"
        echo "  ./vps-deploy-helper.sh pull     - コードプルのみ"
        echo "  ./vps-deploy-helper.sh status   - ステータス確認"
        echo "  ./vps-deploy-helper.sh restart  - アプリ再起動"
        echo "  ./vps-deploy-helper.sh logs     - リアルタイムログ監視"
        echo "  ./vps-deploy-helper.sh check    - SSH接続確認"
        echo ""
        echo "📝 初回設定:"
        echo "1. VPS_HOSTを実際のIPアドレスに変更"
        echo "2. chmod +x vps-deploy-helper.sh"
        echo "3. SSH公開鍵認証を設定"
        ;;
esac