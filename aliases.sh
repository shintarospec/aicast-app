# AIcast Room クイックコマンド用エイリアス・関数
# このファイルを ~/.bashrc や ~/.zshrc に追加してください

# Streamlit再起動関数
aicast_restart() {
    echo "🔄 Streamlit再起動を実行します..."
    /workspaces/aicast-app/restart-streamlit.sh
}

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
alias restart="aicast_restart"
alias 再起動="aicast_restart"
alias deploy="aicast_deploy"
alias 本番="aicast_deploy"

# 使用例:
# restart         # Streamlit再起動
# 再起動          # Streamlit再起動（日本語）
# deploy "Google Sheets機能修正"
# 本番 "キャスト管理機能追加"
# deploy          # デフォルトメッセージで実行