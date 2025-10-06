# 🛡️ AIcast Room バックアップ戦略ガイド

**更新日:** 2025年10月5日  
**対象:** AIcast Room 完全版（6,377行）  
**重要度:** 🔴 CRITICAL

---

## 🎯 バックアップ対象の重要度分類

### 🔴 CRITICAL（絶対に失えないもの）
1. **app.py** - メインアプリケーション（6,377行）
2. **casting_office.db** - 全データベース
3. **credentials/** - 認証情報（Google・X API）
4. **docs/** - 整理済み25個のMDファイル
5. **local_schedule_checker.py** - スケジュール投稿システム
6. **local_retweet_scheduler.py** - リツイートシステム

### 🟡 IMPORTANT（重要な設定・ログ）
1. **run.py** - 起動・認証管理
2. **requirements.txt** - 依存関係
3. **style.css** - UIカスタマイズ
4. **app.log** - 運用ログ
5. **schedule.log / retweet.log** - 自動化ログ

### 🟢 BACKUP（バックアップ推奨）
1. **test_*.py** - テストスクリプト群
2. **deploy_*.sh** - デプロイスクリプト
3. **cloud_functions/** - Cloud Functions設定

---

## 🚀 推奨バックアップ方法

### 1. 📁 **Git版管理バックアップ（最重要）**

#### 即座に実行すべきコマンド
```bash
# 現在の完全版を確実に保存
git add .
git commit -m "✅ 完全版復旧完了 - 6377行app.py + 25MDファイル整理済み"
git push origin main

# 重要なタグ付け
git tag -a v1.0-complete -m "完全版復旧記念タグ"
git push origin v1.0-complete
```

#### 定期的なGitバックアップ
```bash
# 毎日の作業後
git add .
git commit -m "📅 $(date '+%Y-%m-%d') - 日次バックアップ"
git push origin main

# 週次重要タグ
git tag -a "weekly-$(date '+%Y%m%d')" -m "週次安全バックアップ"
git push origin "weekly-$(date '+%Y%m%d')"
```

### 2. 💾 **データベース専用バックアップ**

#### SQLiteダンプ作成
```bash
# 毎日実行推奨
sqlite3 casting_office.db ".backup casting_office_$(date '+%Y%m%d_%H%M').db"

# 週次圧縮バックアップ
tar -czf "db_backup_$(date '+%Y%m%d').tar.gz" casting_office.db *.log
```

#### データベース構造保存
```bash
# スキーマ情報のバックアップ
sqlite3 casting_office.db ".schema" > db_schema_$(date '+%Y%m%d').sql
sqlite3 casting_office.db ".dump" > db_full_dump_$(date '+%Y%m%d').sql
```

### 3. 🔐 **認証情報セキュアバックアップ**

#### 認証ファイル暗号化保存
```bash
# credentials フォルダの暗号化
tar -czf credentials_backup.tar.gz credentials/
gpg --symmetric --cipher-algo AES256 credentials_backup.tar.gz
rm credentials_backup.tar.gz  # 平文削除

# パスワード管理ツールに保存
# 1Password, Bitwarden, LastPass など
```

#### X API認証情報のDB抽出
```bash
# X API認証の緊急バックアップ
sqlite3 casting_office.db "SELECT * FROM cast_x_credentials;" > x_api_backup_$(date '+%Y%m%d').csv
```

### 4. ☁️ **クラウドバックアップ戦略**

#### Google Cloud Storage
```bash
# プロジェクト全体のクラウドバックアップ
gsutil -m cp -r . gs://aicast-backup-bucket/$(date '+%Y%m%d')/

# 重要ファイルのみ
gsutil cp app.py gs://aicast-backup-bucket/critical/app_$(date '+%Y%m%d').py
gsutil cp casting_office.db gs://aicast-backup-bucket/critical/db_$(date '+%Y%m%d').db
```

#### GitHub以外のGitリポジトリ
```bash
# GitLab・Bitbucketへのミラーリング
git remote add gitlab https://gitlab.com/username/aicast-mirror.git
git push gitlab main

git remote add bitbucket https://bitbucket.org/username/aicast-mirror.git
git push bitbucket main
```

### 5. 🏠 **ローカル物理バックアップ**

#### 外部ストレージへのバックアップ
```bash
# USB・外付けHDDへの完全コピー
rsync -avz --progress /workspaces/aicast-app/ /media/backup/aicast-$(date '+%Y%m%d')/

# 圧縮アーカイブ作成
tar -czf aicast_complete_backup_$(date '+%Y%m%d').tar.gz \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  .
```

---

## ⏰ バックアップスケジュール推奨

### 📅 **日次バックアップ（自動化推奨）**
```bash
#!/bin/bash
# daily_backup.sh
cd /workspaces/aicast-app
git add .
git commit -m "📅 自動日次バックアップ $(date '+%Y-%m-%d %H:%M')"
git push origin main

# データベースバックアップ
sqlite3 casting_office.db ".backup backup/daily/casting_office_$(date '+%Y%m%d').db"
```

### 📅 **週次バックアップ（手動実行）**
```bash
#!/bin/bash
# weekly_backup.sh
cd /workspaces/aicast-app

# 重要タグ作成
git tag -a "stable-$(date '+%Y%m%d')" -m "週次安定版"
git push origin "stable-$(date '+%Y%m%d')"

# 完全アーカイブ
tar -czf ../aicast_weekly_$(date '+%Y%m%d').tar.gz .

# クラウドアップロード
gsutil cp ../aicast_weekly_$(date '+%Y%m%d').tar.gz gs://aicast-backup-bucket/weekly/
```

### 📅 **月次バックアップ（完全版）**
```bash
#!/bin/bash
# monthly_backup.sh
cd /workspaces/aicast-app

# リリースタグ作成
git tag -a "release-$(date '+%Y%m')" -m "月次リリース版"
git push origin "release-$(date '+%Y%m')"

# 多重バックアップ
cp -r . ../aicast_monthly_$(date '+%Y%m%d')/
tar -czf ../aicast_monthly_$(date '+%Y%m%d').tar.gz .
```

---

## 🚨 緊急復旧手順

### Git履歴からの復旧
```bash
# コミット履歴確認
git log --oneline -10

# 特定コミットへの復旧
git reset --hard <commit-hash>

# ブランチ作成して安全に復旧
git checkout -b recovery-$(date '+%Y%m%d')
git reset --hard <known-good-commit>
```

### データベース復旧
```bash
# バックアップからの復元
cp backup/casting_office_YYYYMMDD.db casting_office.db

# SQLダンプからの復元
sqlite3 casting_office_new.db < db_full_dump_YYYYMMDD.sql
```

---

## 🔧 バックアップ自動化設定

### Cron設定例
```bash
# crontab -e で以下を追加

# 毎日午前2時にGitバックアップ
0 2 * * * cd /workspaces/aicast-app && git add . && git commit -m "自動日次 $(date)" && git push

# 毎日午前3時にDBバックアップ
0 3 * * * cd /workspaces/aicast-app && sqlite3 casting_office.db ".backup backup/casting_office_$(date +\%Y\%m\%d).db"

# 日曜日午前4時に週次バックアップ
0 4 * * 0 cd /workspaces/aicast-app && ./weekly_backup.sh
```

### GitHub Actions自動バックアップ
```yaml
# .github/workflows/backup.yml
name: Auto Backup
on:
  schedule:
    - cron: '0 2 * * *'  # 毎日午前2時
  workflow_dispatch:

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Create backup
        run: |
          tar -czf aicast-backup-$(date +%Y%m%d).tar.gz .
          # アーティファクトとして保存
      - uses: actions/upload-artifact@v3
        with:
          name: aicast-backup
          path: aicast-backup-*.tar.gz
```

---

## 📋 バックアップチェックリスト

### ✅ **即座に実行すべき項目**
- [ ] 現在の完全版をGitコミット・プッシュ
- [ ] 重要タグ（v1.0-complete）の作成
- [ ] データベースの手動バックアップ作成
- [ ] credentials フォルダの暗号化バックアップ

### ✅ **今週中に設定すべき項目**
- [ ] 日次自動Gitバックアップの設定
- [ ] データベース日次バックアップスクリプト作成
- [ ] 外部クラウドストレージの設定
- [ ] バックアップディレクトリの作成

### ✅ **今月中に構築すべき項目**
- [ ] GitHub Actions自動バックアップの設定
- [ ] 複数Gitリポジトリミラーリング
- [ ] 物理バックアップルーチンの確立
- [ ] 復旧手順書の完成

---

## 💡 おすすめの組み合わせ

### 🥇 **最強バックアップ組み合わせ**
1. **Git版管理** - 毎日の作業でコミット・プッシュ
2. **データベース日次バックアップ** - 自動化で毎日実行
3. **週次外部クラウド保存** - Google Cloud Storage等
4. **月次物理バックアップ** - 外付けストレージ
5. **認証情報暗号化保存** - パスワード管理ツール

この組み合わせで、**MCF DEATH GUARD**のような緊急事態にも完全対応できます！

---

*バックアップは保険です。今回のような緊急事態の経験を活かし、確実な保護体制を構築しましょう。*