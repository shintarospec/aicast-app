#!/bin/bash

# DB同期管理スクリプト
# Usage: ./db-sync-manager.sh [operation] [options]

VPS_HOST="153.126.194.114"
VPS_USER="ubuntu"
VPS_PATH="/home/ubuntu/aicast-app"
LOCAL_DB="casting_office.db"
BACKUP_DIR="db_backups"

# 色付きメッセージ
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# バックアップディレクトリ作成
create_backup_dir() {
    mkdir -p "$BACKUP_DIR"
    log_info "バックアップディレクトリ準備完了"
}

# VPS DB バックアップ
backup_vps_db() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="vps_backup_${timestamp}.db"
    
    log_info "VPS DBバックアップ作成中..."
    
    if ssh ${VPS_USER}@${VPS_HOST} "cd ${VPS_PATH} && sqlite3 ${LOCAL_DB} \".backup /tmp/${backup_name}\""; then
        scp ${VPS_USER}@${VPS_HOST}:/tmp/${backup_name} ${BACKUP_DIR}/
        ssh ${VPS_USER}@${VPS_HOST} "rm /tmp/${backup_name}"
        log_success "VPS DBバックアップ完了: ${BACKUP_DIR}/${backup_name}"
        echo "${backup_name}"
        return 0
    else
        log_error "VPS DBバックアップ失敗"
        return 1
    fi
}

# ローカル DB バックアップ
backup_local_db() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="local_backup_${timestamp}.db"
    
    if [ -f "$LOCAL_DB" ]; then
        cp "$LOCAL_DB" "${BACKUP_DIR}/${backup_name}"
        log_success "ローカルDBバックアップ完了: ${BACKUP_DIR}/${backup_name}"
        echo "${backup_name}"
        return 0
    else
        log_error "ローカルDBが見つかりません: $LOCAL_DB"
        return 1
    fi
}

# スキーマ差分確認
check_schema_diff() {
    log_info "スキーマ差分確認中..."
    
    # VPSからスキーマ取得
    ssh ${VPS_USER}@${VPS_HOST} "cd ${VPS_PATH} && sqlite3 ${LOCAL_DB} '.schema'" > /tmp/vps_schema.sql
    
    # ローカルスキーマ取得
    if [ -f "$LOCAL_DB" ]; then
        sqlite3 "$LOCAL_DB" ".schema" > /tmp/local_schema.sql
    else
        log_error "ローカルDBが見つかりません"
        return 1
    fi
    
    # 差分表示
    if diff /tmp/local_schema.sql /tmp/vps_schema.sql > /dev/null; then
        log_success "スキーマに差分はありません"
        return 0
    else
        log_warning "スキーマに差分があります:"
        diff /tmp/local_schema.sql /tmp/vps_schema.sql
        return 1
    fi
}

# マスタデータ差分確認
check_master_data_diff() {
    local table=$1
    
    if [ -z "$table" ]; then
        log_error "テーブル名を指定してください"
        return 1
    fi
    
    log_info "${table} テーブルの差分確認中..."
    
    # VPSからデータ取得
    ssh ${VPS_USER}@${VPS_HOST} "cd ${VPS_PATH} && sqlite3 ${LOCAL_DB} \"SELECT * FROM ${table} ORDER BY id;\"" > /tmp/vps_${table}.csv
    
    # ローカルデータ取得
    if [ -f "$LOCAL_DB" ]; then
        sqlite3 "$LOCAL_DB" "SELECT * FROM ${table} ORDER BY id;" > /tmp/local_${table}.csv
    else
        log_error "ローカルDBが見つかりません"
        return 1
    fi
    
    # 差分表示
    if diff /tmp/local_${table}.csv /tmp/vps_${table}.csv > /dev/null; then
        log_success "${table} に差分はありません"
        return 0
    else
        log_warning "${table} に差分があります:"
        diff /tmp/local_${table}.csv /tmp/vps_${table}.csv
        return 1
    fi
}

# スキーマ同期（マイグレーション）
sync_schema() {
    log_warning "スキーマ同期は慎重な作業です。本当に実行しますか? (y/N)"
    read -r confirmation
    
    if [[ ! "$confirmation" =~ ^[Yy]$ ]]; then
        log_info "スキーマ同期をキャンセルしました"
        return 1
    fi
    
    # バックアップ作成
    log_info "安全のため VPS DB バックアップを作成します..."
    if ! backup_vps_db > /dev/null; then
        log_error "バックアップ作成失敗 - 同期を中止します"
        return 1
    fi
    
    # スキーマファイル生成
    sqlite3 "$LOCAL_DB" ".schema" > /tmp/new_schema.sql
    
    # VPSに送信して適用
    log_info "VPS にスキーマを同期中..."
    scp /tmp/new_schema.sql ${VPS_USER}@${VPS_HOST}:/tmp/
    
    ssh ${VPS_USER}@${VPS_HOST} "
        cd ${VPS_PATH} && 
        cp ${LOCAL_DB} ${LOCAL_DB}.schema_backup &&
        sqlite3 ${LOCAL_DB}_new < /tmp/new_schema.sql &&
        mv ${LOCAL_DB} ${LOCAL_DB}.old &&
        mv ${LOCAL_DB}_new ${LOCAL_DB} &&
        echo 'スキーマ同期完了'
    "
    
    if [ $? -eq 0 ]; then
        log_success "スキーマ同期完了"
        return 0
    else
        log_error "スキーマ同期失敗"
        return 1
    fi
}

# マスタデータ同期
sync_master_data() {
    local table=$1
    
    if [ -z "$table" ]; then
        log_error "テーブル名を指定してください"
        return 1
    fi
    
    log_warning "${table} のマスタデータを同期しますか? (y/N)"
    read -r confirmation
    
    if [[ ! "$confirmation" =~ ^[Yy]$ ]]; then
        log_info "マスタデータ同期をキャンセルしました"
        return 1
    fi
    
    # データエクスポート
    sqlite3 "$LOCAL_DB" ".mode insert ${table}" ".output /tmp/${table}_data.sql" "SELECT * FROM ${table};" ".quit"
    
    # VPSに送信して適用
    log_info "VPS に ${table} データを同期中..."
    scp /tmp/${table}_data.sql ${VPS_USER}@${VPS_HOST}:/tmp/
    
    ssh ${VPS_USER}@${VPS_HOST} "
        cd ${VPS_PATH} && 
        sqlite3 ${LOCAL_DB} 'DELETE FROM ${table};' &&
        sqlite3 ${LOCAL_DB} < /tmp/${table}_data.sql &&
        echo '${table} データ同期完了'
    "
    
    if [ $? -eq 0 ]; then
        log_success "${table} データ同期完了"
        return 0
    else
        log_error "${table} データ同期失敗"
        return 1
    fi
}

# データベース健全性チェック
check_db_integrity() {
    log_info "VPS DBの健全性チェック中..."
    
    ssh ${VPS_USER}@${VPS_HOST} "
        cd ${VPS_PATH} && 
        sqlite3 ${LOCAL_DB} 'PRAGMA integrity_check;' &&
        sqlite3 ${LOCAL_DB} 'PRAGMA foreign_key_check;'
    "
    
    if [ $? -eq 0 ]; then
        log_success "DB健全性チェック完了"
        return 0
    else
        log_error "DB健全性チェックでエラーが検出されました"
        return 1
    fi
}

# ヘルプ表示
show_help() {
    echo "🔄 DB同期管理スクリプト"
    echo ""
    echo "使用方法:"
    echo "  ./db-sync-manager.sh [operation] [options]"
    echo ""
    echo "操作一覧:"
    echo "  backup-vps              VPS DBバックアップ作成"
    echo "  backup-local            ローカルDBバックアップ作成"
    echo "  check-schema            スキーマ差分確認"
    echo "  check-master [table]    マスタデータ差分確認"
    echo "  sync-schema             スキーマ同期（危険）"
    echo "  sync-master [table]     マスタデータ同期"
    echo "  integrity-check         DB健全性チェック"
    echo ""
    echo "例:"
    echo "  ./db-sync-manager.sh check-schema"
    echo "  ./db-sync-manager.sh check-master situations"
    echo "  ./db-sync-manager.sh sync-master global_advice"
    echo ""
    echo "⚠️  注意: sync- 系の操作は本番データに影響します"
}

# メイン処理
main() {
    create_backup_dir
    
    case "$1" in
        "backup-vps")
            backup_vps_db
            ;;
        "backup-local")
            backup_local_db
            ;;
        "check-schema")
            check_schema_diff
            ;;
        "check-master")
            check_master_data_diff "$2"
            ;;
        "sync-schema")
            sync_schema
            ;;
        "sync-master")
            sync_master_data "$2"
            ;;
        "integrity-check")
            check_db_integrity
            ;;
        *)
            show_help
            ;;
    esac
}

main "$@"