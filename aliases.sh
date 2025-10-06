# AIcast Room クイックデプロイ用エイリアス・関数
# このファイルを ~/.bashrc や ~/.zshrc に追加してください

# クイックデプロイ関数
aicast_deploy() {
    if [ $# -eq 0 ]; then
        echo "🚀 AIcast本番デプロイ開始..."
        ./deploy.sh "本番アップデート: $(date '+%Y-%m-%d %H:%M:%S')"
    else
        echo "🚀 AIcast本番デプロイ開始: $*"
        ./deploy.sh "$*"
    fi
}

# エイリアス
alias deploy="aicast_deploy"
alias 本番="aicast_deploy"

# 使用例:
# deploy "Google Sheets機能修正"
# 本番 "キャスト管理機能追加"
# deploy  # デフォルトメッセージで実行