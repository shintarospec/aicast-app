# AIcast Room さくらVPS運用ガイド

## 🚀 初回セットアップ

### 1. Google Cloud認証設定
```bash
# gcloudツールのインストール（必要に応じて）
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# 認証設定
gcloud auth application-default login --no-launch-browser
gcloud config set project aicast-472807
gcloud auth application-default set-quota-project aicast-472807
```

### 2. 依存関係のインストール
```bash
cd aicast-app
pip3 install -r requirements.txt
```

### 3. 認証確認
```bash
python3 -c "
import vertexai
vertexai.init(project='aicast-472807', location='asia-northeast1')
print('✅ 認証成功')
"
```

## 🎯 アプリケーション起動

### 開発・テスト環境
```bash
cd aicast-app
python3 run.py
```

### 本番環境（バックグラウンド実行）
```bash
cd aicast-app

# Screen session使用
screen -S aicast
python3 run.py
# Ctrl+A, D でデタッチ

# または nohup使用
nohup python3 run.py > app.log 2>&1 &
```

## 🔧 運用コマンド

### アプリケーション状態確認
```bash
# プロセス確認
ps aux | grep streamlit

# ポート確認
netstat -tulpn | grep 8501

# ログ確認（nohup使用時）
tail -f app.log
```

### Screen session管理
```bash
# セッション一覧
screen -ls

# セッション復帰
screen -r aicast

# セッション強制終了
screen -S aicast -X quit
```

### アプリケーション停止
```bash
# Screen session内で Ctrl+C

# または、プロセスID確認して終了
ps aux | grep streamlit
kill <PID>
```

## 🔄 アップデート手順

### コード更新
```bash
cd aicast-app
git pull
```

### アプリケーション再起動
```bash
# 現在のプロセスを停止
screen -S aicast -X quit

# 新しいセッションで起動
screen -S aicast
python3 run.py
# Ctrl+A, D でデタッチ
```

## 🌐 アクセス

- **ローカル開発**: http://localhost:8501
- **本番環境**: http://YOUR_SERVER_IP:8501

## 🚨 トラブルシューティング

### 認証エラー
```bash
# 認証状態確認
gcloud auth list
gcloud auth application-default print-access-token

# 再認証
gcloud auth application-default login --no-launch-browser
```

### ポート衝突
```bash
# 使用中のポート確認
sudo netstat -tulpn | grep 8501

# プロセス終了
sudo kill <PID>
```

### 依存関係エラー
```bash
# 依存関係再インストール
pip3 install -r requirements.txt --upgrade
```

## 📊 モニタリング

### システムリソース
```bash
# CPU・メモリ使用量
top
htop

# ディスク使用量
df -h
```

### アプリケーションログ
```bash
# リアルタイムログ
tail -f app.log

# エラーログ検索
grep -i error app.log
```