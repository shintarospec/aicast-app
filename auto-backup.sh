#!/bin/bash

# 自動バックアップスクリプト
# VPS cron設定: 0 */6 * * * /home/ubuntu/aicast-app/auto-backup.sh

BACKUP_DIR="/home/ubuntu/aicast-app/db_backups"
DB_FILE="/home/ubuntu/aicast-app/casting_office.db"
MAX_BACKUPS=24  # 保持する最大バックアップ数（6時間×24 = 6日分）

# バックアップディレクトリ作成
mkdir -p "$BACKUP_DIR"

# タイムスタンプ付きバックアップファイル名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/auto_backup_${TIMESTAMP}.db"

# バックアップ実行
if sqlite3 "$DB_FILE" ".backup $BACKUP_FILE"; then
    echo "$(date): バックアップ成功 - $BACKUP_FILE" >> "${BACKUP_DIR}/backup.log"
    
    # 古いバックアップファイルを削除（最大保持数を超える場合）
    cd "$BACKUP_DIR"
    ls -t auto_backup_*.db | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm
    
    echo "$(date): 古いバックアップクリーンアップ完了" >> "${BACKUP_DIR}/backup.log"
else
    echo "$(date): バックアップ失敗" >> "${BACKUP_DIR}/backup.log"
    exit 1
fi

# ディスク使用量チェック
DISK_USAGE=$(df "$BACKUP_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "$(date): 警告 - ディスク使用量が80%を超えています ($DISK_USAGE%)" >> "${BACKUP_DIR}/backup.log"
fi