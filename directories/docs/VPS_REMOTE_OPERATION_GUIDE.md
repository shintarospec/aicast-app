# VPS リモート操作設定ガイド

CodespacesからさくらVPSを操作するための設定手順です。

## 1. SSH公開鍵認証の設定

### CodespacesでSSHキーペア生成
```bash
# SSHキー生成（存在しない場合）
ssh-keygen -t rsa -b 4096 -C "your-email@example.com"

# 公開鍵をクリップボードにコピー
cat ~/.ssh/id_rsa.pub
```

### VPS側での設定
```bash
# VPSにSSHログイン
ssh ubuntu@YOUR_VPS_IP

# authorized_keysに公開鍵を追加
mkdir -p ~/.ssh
echo "YOUR_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

## 2. SSH設定ファイルの作成

Codespaces側で `~/.ssh/config` を設定：
```bash
cat >> ~/.ssh/config << 'EOF'
Host sakura-vps
    HostName YOUR_VPS_IP_ADDRESS
    User ubuntu
    Port 22
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
EOF
```

## 3. VPSデプロイヘルパーの設定

```bash
# 実行権限付与
chmod +x vps-deploy-helper.sh

# VPS IPアドレスを設定
nano vps-deploy-helper.sh
# VPS_HOST="your-sakura-vps-ip" を実際のIPに変更
```

## 4. VS Code タスクの使用方法

`Ctrl+Shift+P` → `Tasks: Run Task` から以下のタスクを実行：

### 🌐 VPS: コードプル & 再起動
- 最新コードをVPSにプル
- AIcast Roomアプリを再起動
- コード変更時に使用

### 🔄 VPS: コードプル (再起動なし)  
- コードプルのみ実行
- アプリは稼働継続
- 軽微な変更時に使用

### 📊 VPS: ステータス確認
- アプリの稼働状況確認
- 最新ログの表示
- 定期監視に使用

### 🚀 VPS: アプリ再起動
- アプリのみ再起動
- コード変更なしの再起動時

## 5. コマンドライン操作

```bash
# デプロイヘルパー使用例
./vps-deploy-helper.sh deploy   # コードプル & 再起動
./vps-deploy-helper.sh status   # ステータス確認
./vps-deploy-helper.sh logs     # ログ監視
```

## 6. 使用シナリオ

### 日常的な開発フロー
1. Codespacesでコード編集
2. `git commit` & `git push`
3. VSCode Task: **🌐 VPS: コードプル & 再起動**
4. VSCode Task: **📊 VPS: ステータス確認** で動作確認

### 緊急時の対応
1. VSCode Task: **📊 VPS: ステータス確認** で状況把握
2. VSCode Task: **🚀 VPS: アプリ再起動** で復旧
3. `./vps-deploy-helper.sh logs` でログ監視

### トラブルシューティング
```bash
# SSH接続確認
./vps-deploy-helper.sh check

# 手動SSH接続
ssh sakura-vps

# VPS側での直接操作
cd /home/ubuntu/aicast-app
screen -r aicast  # 既存セッションに接続
```

## セキュリティ注意事項

- SSH公開鍵認証を必ず使用
- VPS IPアドレスをコード内にハードコードしない
- 定期的にSSHキーのローテーション
- Codespacesは一時的環境のため、キーのバックアップを推奨