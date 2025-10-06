#!/bin/bash

# AIcast Room 便利スクリプト
# 使用方法: ./quick.sh [command]

case "$1" in
    "start" | "")
        echo "🚀 AIcast Room を起動中..."
        python3 run.py
        ;;
    "test")
        echo "🔍 Vertex AI 認証テスト中..."
        python3 test_vertex_vps.py
        ;;
    "auth")
        echo "🔐 Google Cloud 認証中..."
        gcloud auth application-default login --no-launch-browser
        ;;
    "install")
        echo "🛠️ 依存関係をインストール中..."
        pip3 install -r requirements.txt
        ;;
    "update")
        echo "🔄 システム更新中..."
        git pull
        pip3 install -r requirements.txt
        ;;
    "help")
        echo "AIcast Room 便利コマンド:"
        echo "  ./quick.sh start    - アプリ起動 (デフォルト)"
        echo "  ./quick.sh test     - Vertex AI認証テスト"
        echo "  ./quick.sh auth     - Google Cloud認証"
        echo "  ./quick.sh install  - 依存関係インストール"
        echo "  ./quick.sh update   - システム更新"
        echo "  ./quick.sh help     - このヘルプ"
        ;;
    *)
        echo "❌ 不明なコマンド: $1"
        echo "使用方法: ./quick.sh [start|test|auth|install|update|help]"
        exit 1
        ;;
esac