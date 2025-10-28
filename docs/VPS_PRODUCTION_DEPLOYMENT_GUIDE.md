# VPS本番環境デプロイメントガイド

## 📋 概要

AIcast Roomの本番環境デプロイメント時に必要な、Gitプッシュでは反映されない設定項目の完全ガイド。

---

## 🚀 デプロイメント手順

### Phase 1: 基本環境セットアップ

#### 1. リポジトリクローン
```bash
cd /home/ubuntu
git clone https://github.com/shintarospec/aicast-app.git
cd aicast-app
git checkout clean-production
```

#### 2. Python仮想環境構築
```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

#### 3. システムパッケージインストール
```bash
sudo apt update
sudo apt install sqlite3 -y
```

### Phase 2: アプリケーション設定

#### 4. Secrets設定
```bash
# .streamlitディレクトリ作成（存在しない場合）
mkdir -p .streamlit

# secrets.tomlファイル作成
cat > .streamlit/secrets.toml << 'EOF'
# AIcast Room - VPS本番環境用Secrets設定

[auth]
# パスワード認証
password_hash = "41e749030cd3aa529105b76146d59a5ea807146d5c8a8b3b10bd9d61e9db0cbd"  # aicast2025

[development]
# 本番環境設定
debug_mode = false
local_testing = false
EOF
```

#### 5. Google Cloud認証設定
```bash
# Application Default Credentials設定
gcloud auth application-default login --no-launch-browser
```

### Phase 3: 自動化設定（重要）

#### 6. cronジョブ設定 ⚠️ **必須設定**
```bash
# cronジョブエディタを開く
crontab -e

# エディタ選択で「1」（nano）を選択
# 以下の2行を追加：

# スケジュール投稿（AI生成投稿の自動投稿）- 1分間隔
* * * * * cd /home/ubuntu/aicast-app && /home/ubuntu/aicast-app/.venv/bin/python3 local_schedule_checker.py >> schedule.log 2>&1

# リツイート予約（リツイート・引用ツイート自動実行）- 5分間隔  
*/5 * * * * cd /home/ubuntu/aicast-app && /home/ubuntu/aicast-app/.venv/bin/python3 local_retweet_scheduler.py >> retweet.log 2>&1

# 保存して終了：Ctrl+O → Enter → Ctrl+X
```

**⚠️ 重要**: 両方のcronジョブを設定してください。片方だけでは対応する機能が動作しません。

#### 7. cronサービス確認・起動
```bash
# cronサービス状態確認
sudo service cron status

# 停止している場合は起動
sudo service cron start

# 自動起動設定
sudo systemctl enable cron
```

### Phase 4: アプリケーション起動

#### 8. アプリケーション起動テスト
```bash
# 単発起動テスト
python3 run.py

# 問題なければ Ctrl+C で停止
```

#### 9. Screen セッションでバックグラウンド実行
```bash
# Screenセッション作成
screen -S aicast

# アプリケーション起動
python3 run.py

# デタッチ（Ctrl+A, D）
# 再接続: screen -r aicast
```

---

## ⚠️ Gitプッシュで反映されない設定項目

### システム固有設定（各環境で個別設定必要）

#### 1. cronジョブ設定 ⭐ **最重要**
- **設定場所**: `crontab -e`
- **内容**: スケジュール投稿の自動実行（5分間隔）
- **理由**: サーバー固有のプロセス管理のため

#### 2. systemdサービス設定
- **設定場所**: `/etc/systemd/system/`
- **内容**: アプリケーションの自動起動設定
- **理由**: OS固有のサービス管理のため

#### 3. ファイアウォール設定
- **設定場所**: `ufw` または `iptables`
- **内容**: ポート8502の開放設定
- **理由**: セキュリティポリシーはサーバー固有のため

#### 4. SSL証明書
- **設定場所**: Let's Encrypt等
- **内容**: HTTPS化設定
- **理由**: ドメイン・サーバー固有のため

#### 5. 環境変数
- **設定場所**: `/etc/environment` または `~/.bashrc`
- **内容**: 実際のAPI キー等の機密情報
- **理由**: セキュリティ上Gitにコミットできないため

---

## ⚡ 重要：2つの独立した自動化システム

AIcast Roomには**2つの独立した自動化システム**があり、それぞれ個別のcronジョブ設定が必要です：

### 📅 システム1：スケジュール投稿
- **機能**: AI生成投稿の時間指定自動投稿
- **ファイル**: `local_schedule_checker.py`
- **データベース**: `posts`テーブルの`scheduled_at`カラム
- **cronジョブ**: `* * * * *` (1分間隔推奨)
- **ログファイル**: `schedule.log`

### 🔄 システム2：リツイート予約
- **機能**: 既存ツイートのリツイート・引用ツイート予約
- **ファイル**: `local_retweet_scheduler.py`  
- **データベース**: `retweet_schedules`テーブル
- **cronジョブ**: `*/5 * * * *` (5分間隔推奨)
- **ログファイル**: `retweet.log`

### ⚠️ 設定上の注意点
1. **両方のcronジョブが必要**: 片方だけでは対応する機能が動作しません
2. **独立したログファイル**: 問題の切り分けが容易
3. **異なる実行間隔**: スケジュール投稿はより頻繁にチェック

---

## 🔍 動作確認手順

### 1. 基本機能確認
```bash
# アプリケーションアクセス
curl http://localhost:8502

# または
wget -q --spider http://localhost:8502 && echo "OK" || echo "NG"
```

### 2. スケジュール投稿機能確認
```bash
# cronジョブ設定確認
crontab -l

### 2. 自動化システム機能確認
```bash
# cronジョブ設定確認
crontab -l

# スケジュール投稿システム手動テスト
cd /home/ubuntu/aicast-app
/home/ubuntu/aicast-app/.venv/bin/python3 local_schedule_checker.py

# リツイート予約システム手動テスト
/home/ubuntu/aicast-app/.venv/bin/python3 local_retweet_scheduler.py

# ログファイル確認
cat schedule.log | tail -10
cat retweet.log | tail -10
```

### 3. データベース確認
```bash
# スケジュール投稿データ確認
sqlite3 casting_office.db "SELECT id, cast_id, scheduled_at, sent_status FROM posts WHERE scheduled_at IS NOT NULL ORDER BY scheduled_at DESC LIMIT 5;"

# リツイート予約データ確認
sqlite3 casting_office.db "SELECT id, cast_id, tweet_id, scheduled_at, status FROM retweet_schedules WHERE status = 'scheduled' ORDER BY scheduled_at DESC LIMIT 5;"
```

### 4. Google Cloud認証確認
```bash
# 認証状態確認
gcloud auth list

# アクセストークン取得テスト
gcloud auth application-default print-access-token
```

---

## 🚨 トラブルシューティング

### cronジョブが動作しない
```bash
# cronサービス確認
sudo service cron status

# cronログ確認
sudo tail -f /var/log/cron.log

# 手動実行でエラー確認
cd /home/ubuntu/aicast-app && /home/ubuntu/aicast-app/.venv/bin/python3 local_schedule_checker.py
```

### アプリケーションアクセスできない
```bash
# プロセス確認
ps aux | grep streamlit

# ポート確認
netstat -tulpn | grep :8502

# ファイアウォール確認
sudo ufw status
```

### Google Cloud認証エラー
```bash
# 認証情報確認
ls -la ~/.config/gcloud/

# 再認証
gcloud auth application-default login --no-launch-browser
```

---

## 📊 監視・メンテナンス

### 日次確認項目
1. **アプリケーション稼働状況**
   ```bash
   curl -s http://localhost:8502 > /dev/null && echo "✅ App OK" || echo "❌ App Down"
   ```

2. **cronジョブ実行状況**
   ```bash
   tail -5 /home/ubuntu/aicast-app/schedule.log
   ```

3. **ディスク使用量**
   ```bash
   df -h
   du -sh /home/ubuntu/aicast-app/
   ```

### 週次メンテナンス
1. **ログローテーション**
   ```bash
   cd /home/ubuntu/aicast-app
   cp schedule.log schedule.log.$(date +%Y%m%d)
   > schedule.log
   ```

2. **システムアップデート**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

---

## 🔧 自動化スクリプト

### デプロイメント自動化スクリプト
```bash
#!/bin/bash
# deploy_vps.sh - VPS自動デプロイスクリプト

echo "🚀 AIcast Room VPS デプロイメント開始"

# 基本環境セットアップ
cd /home/ubuntu
if [ ! -d "aicast-app" ]; then
    git clone https://github.com/shintarospec/aicast-app.git
fi

cd aicast-app
git checkout clean-production
git pull origin clean-production

# Python環境セットアップ
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt

# システムパッケージ
sudo apt update
sudo apt install sqlite3 -y

# Secrets設定
mkdir -p .streamlit
if [ ! -f ".streamlit/secrets.toml" ]; then
    cat > .streamlit/secrets.toml << 'EOF'
[auth]
password_hash = "41e749030cd3aa529105b76146d59a5ea807146d5c8a8b3b10bd9d61e9db0cbd"

[development]
debug_mode = false
local_testing = false
EOF
fi

# cronジョブ確認
if ! crontab -l | grep -q "local_schedule_checker.py"; then
    echo "⚠️  cronジョブを手動で設定してください："
    echo "   crontab -e"
    echo "   */5 * * * * cd /home/ubuntu/aicast-app && /home/ubuntu/aicast-app/.venv/bin/python3 local_schedule_checker.py >> schedule.log 2>&1"
fi

echo "✅ デプロイメント完了"
echo "📍 次の手順:"
echo "   1. cronジョブ設定（上記参照）"
echo "   2. Google Cloud認証: gcloud auth application-default login --no-launch-browser"
echo "   3. アプリケーション起動: python3 run.py"
```

---

## 📚 関連ドキュメント

- [SCHEDULE_POSTING_DEVELOPMENT_HISTORY.md](./SCHEDULE_POSTING_DEVELOPMENT_HISTORY.md) - スケジュール投稿システム開発履歴
- [SYSTEM_HEALTH_CHECKLIST.md](./SYSTEM_HEALTH_CHECKLIST.md) - システム健全性チェックリスト
- [TIMEZONE_RESOLUTION_LOG.md](./TIMEZONE_RESOLUTION_LOG.md) - タイムゾーン問題解決ログ
- [README_SAKURA_VPS.md](../README_SAKURA_VPS.md) - Sakura VPS運用ガイド

---

## 📋 チェックリスト

### デプロイメント完了チェック
- [ ] リポジトリクローン完了
- [ ] Python仮想環境作成完了
- [ ] 依存関係インストール完了
- [ ] sqlite3インストール完了
- [ ] secrets.toml設定完了
- [ ] Google Cloud認証完了
- [ ] **cronジョブ設定完了** ⭐
- [ ] cronサービス起動確認完了
- [ ] アプリケーション起動確認完了
- [ ] スケジュール投稿動作確認完了

### 運用準備チェック
- [ ] Screenセッション設定完了
- [ ] 監視スクリプト配置完了
- [ ] ログローテーション設定完了
- [ ] バックアップ手順確認完了
- [ ] 緊急時連絡体制確認完了

---

*最終更新: 2025年10月6日*  
*作成者: GitHub Copilot*  
*レビュー: プロジェクトオーナー*