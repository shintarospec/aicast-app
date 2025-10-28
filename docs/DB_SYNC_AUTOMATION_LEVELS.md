# DB同期作業の分類・自動化レベル

## 🔄 自動化レベル分類

### Level 1: 完全自動化 ✅
**対象作業:**
- 定期バックアップ（6時間間隔）
- DB健全性チェック
- スキーマ差分確認
- マスタデータ差分確認

**VS Code タスク:**
- 🔍 DB: スキーマ差分確認
- 💾 DB: VPSバックアップ作成
- 🩺 DB: 健全性チェック

**自動実行設定:**
```bash
# VPS cron設定
0 */6 * * * /home/ubuntu/aicast-app/auto-backup.sh
0 9,18 * * * /home/ubuntu/aicast-app/db-health-check.sh
```

### Level 2: 半自動化（確認付き） ⚠️
**対象作業:**
- マスタデータ同期
- 新機能用テーブル追加
- インデックス追加

**特徴:**
- スクリプトで実行
- 事前確認プロンプト表示
- 自動バックアップ作成
- ロールバック準備

**VS Code タスク:**
- 📋 DB: マスタデータ差分確認
- 🔄 DB: マスタデータ同期

**手順例:**
```bash
# 1. 差分確認
./db-sync-manager.sh check-master global_advice

# 2. バックアップ作成（自動）
./db-sync-manager.sh backup-vps

# 3. 同期実行（確認付き）
./db-sync-manager.sh sync-master global_advice
```

### Level 3: 完全手動 🚨
**対象作業:**
- スキーマ破壊的変更
- 大量データ移行
- ユーザーデータ関連操作
- 緊急時復旧

**安全対策:**
- 複数バックアップ必須
- 段階的実行
- 動作確認テスト
- ロールバック計画書

**手順:**
1. 詳細な実行計画作成
2. 複数バックアップ作成
3. 本番アプリ一時停止
4. 手動実行・確認
5. 動作テスト
6. アプリ再開

## 🎯 今後のUI改善・投稿高度化での適用例

### UI改善シナリオ

#### 新カスタムフィールド追加
**分類:** Level 2（半自動化）
```bash
# 1. 開発環境で新フィールド追加
ALTER TABLE casts ADD COLUMN new_ui_field TEXT DEFAULT '';

# 2. 差分確認
./db-sync-manager.sh check-schema

# 3. 同期実行
./db-sync-manager.sh sync-schema
```

#### UI設定テーブル追加
**分類:** Level 2（半自動化）
```sql
CREATE TABLE ui_settings (
    id INTEGER PRIMARY KEY,
    setting_key TEXT UNIQUE,
    setting_value TEXT,
    user_id INTEGER
);
```

### 投稿高度化シナリオ

#### 新アドバイスカテゴリ追加
**分類:** Level 1（完全自動化）
```bash
# マスタデータ追加のみ
./db-sync-manager.sh sync-master global_advice
```

#### AI生成ロジック設定テーブル
**分類:** Level 2（半自動化）
```sql
CREATE TABLE ai_generation_settings (
    id INTEGER PRIMARY KEY,
    cast_id INTEGER,
    model_settings JSON,
    prompt_templates TEXT
);
```

#### コンテンツ品質スコアリング
**分類:** Level 2（半自動化）
```sql
ALTER TABLE posts ADD COLUMN quality_score REAL DEFAULT 0.0;
ALTER TABLE posts ADD COLUMN ai_confidence REAL DEFAULT 0.0;
```

## 🛡️ 安全性確保の具体例

### マスタデータ同期時の安全対策
```bash
# 1. 自動バックアップ
./db-sync-manager.sh backup-vps

# 2. 差分確認
./db-sync-manager.sh check-master situations

# 3. 確認プロンプト
echo "以下の変更を適用しますか？"
diff /tmp/local_situations.csv /tmp/vps_situations.csv

# 4. 同期実行
./db-sync-manager.sh sync-master situations

# 5. 健全性チェック
./db-sync-manager.sh integrity-check
```

### スキーマ変更時の安全対策
```bash
# 1. 複数バックアップ作成
cp casting_office.db casting_office_pre_schema.db
./db-sync-manager.sh backup-vps

# 2. テスト環境での検証
sqlite3 test_db.db < migration.sql

# 3. 本番適用
# 手動実行（Level 3）

# 4. ロールバック準備
# バックアップからの復旧手順確認
```

## 📊 モニタリング・アラート

### 自動監視項目
- DB サイズ増加監視
- バックアップ失敗アラート
- 健全性チェック異常検知
- ディスク使用量警告

### ログ管理
```bash
# バックアップログ
tail -f /home/ubuntu/aicast-app/db_backups/backup.log

# 同期ログ
tail -f /home/ubuntu/aicast-app/sync.log

# エラーログ
tail -f /home/ubuntu/aicast-app/db_error.log
```

これらの分類に従って、今後のUI改善・投稿高度化を安全に進めることができます。