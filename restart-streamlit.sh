#!/bin/bash

# AIcast Room - Streamlit安全再起動スクリプト
# 成功パターンに基づいた確実な再起動手順

set -e  # エラーで停止

echo "🔄 Streamlit再起動を開始します..."
echo ""

# ステップ1: 既存プロセスの停止
echo "📍 ステップ1: 既存のStreamlitプロセスを停止"
pkill -f 'streamlit run' || echo "   ℹ️  既存プロセスなし（正常）"
sleep 2
echo "   ✅ プロセス停止完了"
echo ""

# ステップ2: ポート確認
echo "📍 ステップ2: ポート8503の確認"
if lsof -i:8503 > /dev/null 2>&1; then
    echo "   ⚠️  ポート8503がまだ使用中です。強制終了します..."
    lsof -ti:8503 | xargs kill -9 2>/dev/null || true
    sleep 2
    echo "   ✅ ポート解放完了"
else
    echo "   ✅ ポート8503は利用可能です"
fi
echo ""

# ステップ3: 構文チェック
echo "📍 ステップ3: app.pyの構文チェック"
if python3 -m py_compile app.py; then
    echo "   ✅ 構文チェック: OK"
else
    echo "   ❌ 構文エラーがあります。再起動を中止します。"
    exit 1
fi
echo ""

# ステップ4: Streamlit起動（バックグラウンド）
echo "📍 ステップ4: Streamlitをバックグラウンドで起動"
nohup ./start-with-service-account.sh > /tmp/streamlit-restart.log 2>&1 &
STREAMLIT_PID=$!
echo "   ℹ️  プロセスID: $STREAMLIT_PID"
echo "   ⏳ 起動を待機中..."
sleep 5
echo ""

# ステップ5: 起動確認
echo "📍 ステップ5: 起動確認"
if curl -s http://localhost:8503 > /dev/null; then
    echo "   ✅ Streamlitが正常に起動しました！"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎉 再起動完了！"
    echo ""
    echo "🔗 URL: http://localhost:8503"
    echo "📋 ログ: tail -f /tmp/streamlit-restart.log"
    echo "🔢 プロセスID: $STREAMLIT_PID"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo "   ❌ Streamlitの起動に失敗しました"
    echo ""
    echo "📋 ログを確認してください:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    tail -20 /tmp/streamlit-restart.log
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
fi
