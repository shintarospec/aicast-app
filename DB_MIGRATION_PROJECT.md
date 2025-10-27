# 📊 DBマイグレーションプロジェクト状態記録

**最終更新日**: 2025年10月27日 02:37 JST  
**プロジェクト**: 新プロンプト構造への完全移行  
**現在のステータス**: ✅ ローカル完了 / ⏸️ 本番適用保留

---

## 📋 プロジェクト概要

新プロンプト構造（NEW_PROMPT_STRUCTURE.md）に基づき、4つの新テーブルを追加するDBマイグレーション。

### 対象テーブル
1. `account_mission` - アカウント運営指針（5セクション）
2. `persona_detailed` - 詳細ペルソナ（9項目）
3. `sample_profiles` - サンプルプロフィール
4. `sample_posts` - サンプル投稿（カテゴリ管理）

---

## ✅ 完了済みタスク

### 1. ローカルDBバックアップ作成 ✅
- **実行日時**: 2025-10-27 02:37 JST
- **バックアップファイル**:
  - `db_backups/casting_office_20251027_023741.db` (バイナリコピー)
  - `db_backups/casting_office_20251027_023741.sql` (SQLダンプ)
- **保存場所**: `/workspaces/aicast-app/db_backups/`
- **Gitコミット**: ✅ コミット済み (b6d3931f)

### 2. マイグレーションSQL作成 ✅
- **ファイル**: `migrations/20251026_add_prompt_tables.sql`
- **内容**: 
  ```sql
  CREATE TABLE IF NOT EXISTS account_mission (...)
  CREATE TABLE IF NOT EXISTS persona_detailed (...)
  CREATE TABLE IF NOT EXISTS sample_profiles (...)
  CREATE TABLE IF NOT EXISTS sample_posts (...)
  ```
- **仕様準拠**: NEW_PROMPT_STRUCTURE.md に完全準拠
- **Gitコミット**: ✅ コミット済み (b6d3931f)

### 3. マイグレーション手順書作成 ✅
- **ファイル**: `migrations/README.md`
- **内容**: 本番適用手順の簡易ガイド

### 4. Gitコミット ✅
- **コミットハッシュ**: b6d3931f
- **ブランチ**: clean-production
- **コミットメッセージ**: 
  ```
  chore(db): add local DB backup and migration SQL for new prompt tables 
  (account_mission, persona_detailed, sample_profiles, sample_posts)
  ```
- **含まれるファイル**:
  - migrations/20251026_add_prompt_tables.sql
  - migrations/README.md
  - db_backups/ (複数のバックアップファイル)

---

## ⏸️ 保留中タスク

### 1. 本番DBバックアップ取得 🔴 未実施
- **目的**: 本番環境（VPS）のDBを事前バックアップ
- **推奨コマンド**:
  ```bash
  ssh ubuntu@153.126.194.114 'cd /home/ubuntu/aicast-app && \
  cp casting_office.db db_backups/casting_office_before_migration_$(date +%Y%m%d_%H%M%S).db && \
  sqlite3 casting_office.db .dump > db_backups/dump_before_migration_$(date +%Y%m%d_%H%M%S).sql'
  ```

### 2. 本番DBへマイグレーションSQL適用 🔴 未実施
- **目的**: 本番DBに4つの新テーブルを追加
- **推奨コマンド**:
  ```bash
  ssh ubuntu@153.126.194.114 'cd /home/ubuntu/aicast-app && \
  sqlite3 casting_office.db < migrations/20251026_add_prompt_tables.sql'
  ```
- **注意**: 
  - CREATE TABLE IF NOT EXISTS を使用しているため安全
  - 既存データには影響なし

### 3. 本番アプリケーション再起動 🔴 未実施
- **目的**: 新しいDB構造を認識させる
- **推奨コマンド**:
  ```bash
  ssh ubuntu@153.126.194.114 'cd /home/ubuntu/aicast-app && \
  screen -S aicast -X quit; sleep 3 && \
  screen -dmS aicast bash -c "source .venv/bin/activate && python3 run.py"'
  ```

### 4. 本番動作確認 🔴 未実施
- **確認項目**:
  - [ ] キャスト管理 → 運営指針タブが正常動作
  - [ ] 詳細ペルソナの入力・保存
  - [ ] サンプル投稿の追加・表示
  - [ ] CSV一括インポート/エクスポート
  - [ ] build_full_prompt() による投稿生成

---

## 🔍 現在のローカルDB状態

### テーブル確認コマンド実行結果
```bash
sqlite3 casting_office.db "SELECT name FROM sqlite_master WHERE type='table';"
```

**確認済みテーブル**:
- ✅ `account_mission` (存在)
- ✅ `persona_detailed` (存在)
- ✅ `sample_profiles` (存在)
- ✅ `sample_posts` (存在)
- その他: casts, posts, retweet_schedules, cast_x_credentials など

**結論**: ローカルDBは既に新構造に対応済み

---

## 📦 バックアップファイル一覧

### db_backups/ ディレクトリ
```
db_backups/
├── casting_office_20251027_023741.db      # 最新ローカルバックアップ
├── casting_office_20251027_023741.sql     # 最新SQLダンプ
├── casting_office_20251026_before_production.db  # 本番適用前
└── vps_backup_20251011_065602.db          # 過去のVPSバックアップ
```

**注意**: これらのファイルはGitにコミット済みですが、本番DBは`.gitignore`で除外されています。

---

## 🚀 本番適用手順（実行前チェックリスト）

### 前提条件
- [ ] ローカルで全機能が正常動作していることを確認済み
- [ ] app.py のコミット（75d83a57, b6d3931f）が clean-production ブランチに存在
- [ ] VPSへのSSHアクセス可能

### 実行手順

#### ステップ1: 本番コードのプル
```bash
ssh ubuntu@153.126.194.114 'cd /home/ubuntu/aicast-app && \
git fetch origin && \
git checkout clean-production && \
git pull origin clean-production'
```

#### ステップ2: 本番DBバックアップ
```bash
ssh ubuntu@153.126.194.114 'cd /home/ubuntu/aicast-app && \
mkdir -p db_backups && \
cp casting_office.db db_backups/casting_office_before_migration_$(date +%Y%m%d_%H%M%S).db && \
sqlite3 casting_office.db .dump > db_backups/dump_before_migration_$(date +%Y%m%d_%H%M%S).sql && \
echo "✅ バックアップ完了"'
```

#### ステップ3: マイグレーションSQL適用
```bash
ssh ubuntu@153.126.194.114 'cd /home/ubuntu/aicast-app && \
sqlite3 casting_office.db < migrations/20251026_add_prompt_tables.sql && \
echo "✅ マイグレーション適用完了"'
```

#### ステップ4: テーブル存在確認
```bash
ssh ubuntu@153.126.194.114 'cd /home/ubuntu/aicast-app && \
sqlite3 casting_office.db "SELECT name FROM sqlite_master WHERE type=\"table\" AND name IN (\"account_mission\", \"persona_detailed\", \"sample_profiles\", \"sample_posts\");"'
```

#### ステップ5: アプリ再起動
```bash
ssh ubuntu@153.126.194.114 'cd /home/ubuntu/aicast-app && \
screen -S aicast -X quit; sleep 3 && \
screen -dmS aicast bash -c "source .venv/bin/activate && python3 run.py" && \
echo "✅ アプリ再起動完了"'
```

#### ステップ6: 動作確認
- ブラウザで本番URLにアクセス
- キャスト管理 → 各タブの動作確認
- 投稿生成テスト

---

## 🔧 ロールバック手順（問題発生時）

### データベースのロールバック
```bash
ssh ubuntu@153.126.194.114 'cd /home/ubuntu/aicast-app && \
cp db_backups/casting_office_before_migration_YYYYMMDD_HHMMSS.db casting_office.db && \
echo "✅ DBロールバック完了"'
```

### アプリケーションのロールバック
```bash
ssh ubuntu@153.126.194.114 'cd /home/ubuntu/aicast-app && \
git checkout <前のコミットハッシュ> && \
screen -S aicast -X quit; sleep 3 && \
screen -dmS aicast bash -c "source .venv/bin/activate && python3 run.py"'
```

---

## 📝 関連ドキュメント

- **プロンプト構造仕様**: `directories/docs/NEW_PROMPT_STRUCTURE.md`
- **マイグレーションSQL**: `migrations/20251026_add_prompt_tables.sql`
- **マイグレーション手順**: `migrations/README.md`
- **運用ガイド**: `README_SAKURA_VPS.md`
- **Copilot指示書**: `.github/copilot-instructions.md`

---

## 🎯 次回の再開時チェックポイント

### 確認事項
1. [ ] ローカルDBの最新バックアップ確認 (`db_backups/` の最新ファイル)
2. [ ] Gitブランチ状態確認 (`git log --oneline -5`)
3. [ ] 本番DBの状態確認（テーブル存在チェック）
4. [ ] 本番適用が必要か判断

### 再開コマンド例
```bash
# ローカルDB確認
sqlite3 casting_office.db "SELECT name FROM sqlite_master WHERE type='table';"

# 本番DB確認
ssh ubuntu@153.126.194.114 'cd /home/ubuntu/aicast-app && \
sqlite3 casting_office.db "SELECT name FROM sqlite_master WHERE type=\"table\";"'

# Gitステータス
git log --oneline -5
git status
```

---

## 💡 補足情報

### マイグレーションの安全性
- `CREATE TABLE IF NOT EXISTS` を使用しているため、既存テーブルがある場合はスキップされる
- 既存データへの影響は一切なし
- ロールバックは不要（追加のみ）

### 本番適用のタイミング
- ユーザートラフィックが少ない時間帯推奨
- 深夜または早朝の適用を推奨
- 所要時間: 5分以内（バックアップ含む）

---

**プロジェクトステータス**: ⏸️ 本番適用待機中

**次のアクション**: ユーザーが本番適用を指示するまで保留

---
