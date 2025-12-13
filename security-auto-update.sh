#!/bin/bash
# AIcast Room - 自動セキュリティアップデートスクリプト
# 作成日: 2025年12月13日
# 実行頻度: 毎日 AM 3:00（システム負荷が低い時間帯）

set -e

LOG_FILE="/home/ubuntu/aicast-app/security-logs/auto-update-$(date +%Y%m%d).log"
mkdir -p "/home/ubuntu/aicast-app/security-logs"

echo "========================================" > "$LOG_FILE"
echo "自動セキュリティアップデート" >> "$LOG_FILE"
echo "実行日時: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# パッケージリスト更新
echo "📦 パッケージリスト更新中..." >> "$LOG_FILE"
sudo apt update -qq >> "$LOG_FILE" 2>&1

# アップデート可能なパッケージ数を確認
UPGRADABLE=$(apt list --upgradable 2>/dev/null | grep -v "Listing" | wc -l)
echo "アップデート可能: $UPGRADABLE パッケージ" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

if [ "$UPGRADABLE" -gt 0 ]; then
    echo "🔧 セキュリティアップデート適用中..." >> "$LOG_FILE"
    
    # セキュリティアップデートのみ自動適用
    # （unattended-upgradesが既に設定されているが、手動でも実行）
    sudo unattended-upgrade -d >> "$LOG_FILE" 2>&1
    
    echo "✅ セキュリティアップデート完了" >> "$LOG_FILE"
else
    echo "✅ アップデートの必要なし" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "完了時刻: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 古いログ削除（7日以上前）
find /home/ubuntu/aicast-app/security-logs -name "auto-update-*.log" -mtime +7 -delete 2>/dev/null || true

exit 0
