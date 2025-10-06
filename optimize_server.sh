#!/bin/bash
# AIcast Room サーバー最適化スクリプト
# さくらVPS向け運用効率化

echo "=== AIcast Room サーバー最適化開始 ==="

# 1. システム情報表示
echo "1. システム情報確認"
echo "CPU使用率: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)"
echo "メモリ使用率: $(free | grep Mem | awk '{printf("%.1f%%\n", $3/$2 * 100.0)}')"
echo "ディスク使用率: $(df -h / | awk 'NR==2{print $5}')"

# 2. Python環境チェック
echo -e "\n2. Python環境確認"
python3 --version
pip3 list | grep -E "(streamlit|google-cloud|pandas)"

# 3. プロセス確認
echo -e "\n3. AIcast関連プロセス確認"
ps aux | grep -E "(python.*app.py|python.*run.py)" | grep -v grep

# 4. ポート使用状況
echo -e "\n4. ポート8501使用状況"
netstat -tlnp | grep 8501 || echo "ポート8501は使用されていません"

# 5. ログファイルサイズ確認
echo -e "\n5. ログファイル確認"
if [ -f "app.log" ]; then
    echo "app.log サイズ: $(du -h app.log)"
    echo "最新のログ（最後の5行）:"
    tail -5 app.log
else
    echo "app.logが見つかりません"
fi

# 6. データベースファイル確認
echo -e "\n6. データベース確認"
if [ -f "casting_office.db" ]; then
    echo "DB ファイルサイズ: $(du -h casting_office.db)"
    echo "DB レコード数確認:"
    python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('casting_office.db')
    cursor = conn.cursor()
    
    # テーブル一覧とレコード数
    tables = ['posts', 'personas', 'send_history']
    for table in tables:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            print(f'{table}: {count} records')
        except:
            print(f'{table}: table not found')
    
    conn.close()
    print('DB接続: OK')
except Exception as e:
    print(f'DB接続エラー: {e}')
"
else
    echo "casting_office.dbが見つかりません"
fi

# 7. 認証ファイル確認
echo -e "\n7. 認証設定確認"
if [ -d "credentials" ]; then
    echo "credentialsフォルダ: 存在"
    ls -la credentials/
else
    echo "credentialsフォルダ: 存在しません"
fi

echo "GCP認証状況:"
gcloud auth list 2>/dev/null || echo "gcloud コマンドが見つかりません"

# 8. 必要な改善提案
echo -e "\n=== 改善提案 ==="

# メモリ使用率チェック
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.0f\n", $3/$2 * 100.0)}')
if [ "$MEMORY_USAGE" -gt 80 ]; then
    echo "⚠️  メモリ使用率が${MEMORY_USAGE}%です。最適化を検討してください。"
fi

# ログファイルサイズチェック
if [ -f "app.log" ]; then
    LOG_SIZE=$(du -k app.log | cut -f1)
    if [ "$LOG_SIZE" -gt 10240 ]; then  # 10MB以上
        echo "⚠️  ログファイルが大きくなっています（$(du -h app.log)）。ローテーションを設定してください。"
    fi
fi

echo -e "\n=== 最適化完了 ==="
echo "詳細な最適化設定は deployment_optimization.md を参照してください。"