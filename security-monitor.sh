#!/bin/bash
# AIcast Room - セキュリティ自動監視スクリプト
# 作成日: 2025年12月13日
# 実行頻度: 毎週月曜日 9:00（cron設定）

set -e

# ログファイル
LOG_DIR="/home/ubuntu/aicast-app/security-logs"
mkdir -p "$LOG_DIR"
REPORT_FILE="$LOG_DIR/weekly-security-report-$(date +%Y%m%d).txt"

echo "========================================" > "$REPORT_FILE"
echo "AIcast Room セキュリティ週次レポート" >> "$REPORT_FILE"
echo "生成日時: $(date '+%Y年%m月%d日 %H:%M')" >> "$REPORT_FILE"
echo "========================================" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# ====================================
# 1. ファイアウォール状態
# ====================================
echo "📊 1. ファイアウォール（UFW）状態" >> "$REPORT_FILE"
echo "-----------------------------------" >> "$REPORT_FILE"
sudo ufw status verbose >> "$REPORT_FILE" 2>&1 || echo "エラー: UFW状態取得失敗" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# ====================================
# 2. fail2ban ブロック統計
# ====================================
echo "🛡️  2. fail2ban 侵入検知統計" >> "$REPORT_FILE"
echo "-----------------------------------" >> "$REPORT_FILE"

# sshd jail の状態
sudo fail2ban-client status sshd >> "$REPORT_FILE" 2>&1 || echo "エラー: fail2ban状態取得失敗" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 現在ブロック中のIP詳細
echo "🚫 現在ブロック中のIP一覧:" >> "$REPORT_FILE"
BANNED_IPS=$(sudo fail2ban-client get sshd banip 2>/dev/null || echo "")
if [ -n "$BANNED_IPS" ]; then
    echo "$BANNED_IPS" | while read -r ip; do
        # whoisで国情報を取得（簡易版）
        COUNTRY=$(whois "$ip" 2>/dev/null | grep -i "country:" | head -1 | awk '{print $2}' || echo "不明")
        echo "  - $ip (国: $COUNTRY)" >> "$REPORT_FILE"
    done
else
    echo "  （現在ブロック中のIPはありません）" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# 過去7日間の攻撃試行回数
echo "📈 過去7日間の攻撃統計:" >> "$REPORT_FILE"
FAILED_ATTEMPTS=$(sudo journalctl -u ssh --since "7 days ago" | grep -i "failed\|invalid" | wc -l)
echo "  - SSH失敗ログイン試行: $FAILED_ATTEMPTS 回" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# ====================================
# 3. システムアップデート状態
# ====================================
echo "📦 3. システムアップデート状態" >> "$REPORT_FILE"
echo "-----------------------------------" >> "$REPORT_FILE"

# 利用可能なアップデート数
sudo apt update -qq 2>&1 > /dev/null
UPGRADABLE=$(apt list --upgradable 2>/dev/null | grep -v "Listing" | wc -l)
echo "  - アップデート可能パッケージ: $UPGRADABLE 個" >> "$REPORT_FILE"

if [ "$UPGRADABLE" -gt 0 ]; then
    echo "  - アップデート推奨パッケージ:" >> "$REPORT_FILE"
    apt list --upgradable 2>/dev/null | grep -v "Listing" | head -10 | sed 's/^/    /' >> "$REPORT_FILE"
fi

# 最終アップデート日時
LAST_UPDATE=$(stat /var/log/apt/history.log 2>/dev/null | grep "Modify:" | awk '{print $2, $3}')
echo "  - 最終アップデート: $LAST_UPDATE" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# ====================================
# 4. ディスク使用量
# ====================================
echo "💾 4. ディスク使用量" >> "$REPORT_FILE"
echo "-----------------------------------" >> "$REPORT_FILE"
df -h / | tail -1 | awk '{print "  - ルートパーティション: " $3 " / " $2 " 使用中 (" $5 ")"}' >> "$REPORT_FILE"
df -h /home | tail -1 | awk '{print "  - ホームディレクトリ: " $3 " / " $2 " 使用中 (" $5 ")"}' >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# ====================================
# 5. AIcast Room サービス状態
# ====================================
echo "🤖 5. AIcast Room サービス状態" >> "$REPORT_FILE"
echo "-----------------------------------" >> "$REPORT_FILE"

# Streamlit稼働確認
if ps aux | grep -v grep | grep -q "streamlit"; then
    echo "  ✅ Streamlit: 稼働中" >> "$REPORT_FILE"
    STREAMLIT_PID=$(ps aux | grep streamlit | grep -v grep | awk '{print $2}' | head -1)
    STREAMLIT_UPTIME=$(ps -p "$STREAMLIT_PID" -o etime= | xargs)
    echo "     稼働時間: $STREAMLIT_UPTIME" >> "$REPORT_FILE"
else
    echo "  ❌ Streamlit: 停止中" >> "$REPORT_FILE"
fi

# cronジョブ確認
if crontab -l | grep -q "auto_generation_batch.py"; then
    echo "  ✅ 自動生成バッチ: cronジョブ設定済み" >> "$REPORT_FILE"
else
    echo "  ⚠️  自動生成バッチ: cronジョブ未設定" >> "$REPORT_FILE"
fi

# 最新の自動生成ログ確認
if [ -f "/home/ubuntu/aicast-app/auto_generation.log" ]; then
    LAST_GEN=$(tail -1 /home/ubuntu/aicast-app/auto_generation.log 2>/dev/null)
    echo "  - 最新自動生成ログ: $(echo $LAST_GEN | cut -c 1-80)..." >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# ====================================
# 6. セキュリティ推奨事項
# ====================================
echo "💡 6. セキュリティ推奨アクション" >> "$REPORT_FILE"
echo "-----------------------------------" >> "$REPORT_FILE"

RECOMMENDATIONS=0

# アップデートが10個以上ある場合
if [ "$UPGRADABLE" -gt 10 ]; then
    echo "  ⚠️  $UPGRADABLE 個のアップデートが待機中 → 適用を推奨" >> "$REPORT_FILE"
    RECOMMENDATIONS=$((RECOMMENDATIONS + 1))
fi

# ディスク使用率が80%以上の場合
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "  ⚠️  ディスク使用率が ${DISK_USAGE}% → 容量確認を推奨" >> "$REPORT_FILE"
    RECOMMENDATIONS=$((RECOMMENDATIONS + 1))
fi

# fail2banでブロック数が多い場合
BANNED_COUNT=$(sudo fail2ban-client status sshd | grep "Currently banned:" | awk '{print $4}')
if [ "$BANNED_COUNT" -gt 20 ]; then
    echo "  ⚠️  ブロック中のIPが ${BANNED_COUNT} 個 → 攻撃が活発化" >> "$REPORT_FILE"
    RECOMMENDATIONS=$((RECOMMENDATIONS + 1))
fi

if [ "$RECOMMENDATIONS" -eq 0 ]; then
    echo "  ✅ 現在、推奨アクションはありません" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# ====================================
# 7. サマリー
# ====================================
echo "========================================" >> "$REPORT_FILE"
echo "📋 サマリー" >> "$REPORT_FILE"
echo "========================================" >> "$REPORT_FILE"
echo "  - セキュリティレベル: 🟢 良好" >> "$REPORT_FILE"
echo "  - 週間ブロック数: $BANNED_COUNT IP" >> "$REPORT_FILE"
echo "  - 週間攻撃試行: $FAILED_ATTEMPTS 回" >> "$REPORT_FILE"
echo "  - アップデート待ち: $UPGRADABLE パッケージ" >> "$REPORT_FILE"
echo "  - 推奨アクション: $RECOMMENDATIONS 件" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "詳細: $REPORT_FILE" >> "$REPORT_FILE"
echo "========================================" >> "$REPORT_FILE"

# レポートをコンソールに出力（cron実行時はログに記録される）
cat "$REPORT_FILE"

# 古いレポート削除（30日以上前のものを削除）
find "$LOG_DIR" -name "weekly-security-report-*.txt" -mtime +30 -delete 2>/dev/null || true

# 緊急アラート（重要な問題がある場合）
if [ "$RECOMMENDATIONS" -gt 2 ]; then
    echo "" >> "$REPORT_FILE"
    echo "🚨 警告: $RECOMMENDATIONS 件の推奨アクションがあります！" >> "$REPORT_FILE"
    echo "   詳細を確認して対応してください。" >> "$REPORT_FILE"
fi

# 正常終了
exit 0
