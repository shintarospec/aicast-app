# 🔐 AIcast Room セキュリティ対策ドキュメント

**最終更新**: 2025年12月13日  
**バージョン**: 1.0  
**運用環境**: さくらVPS (153.126.194.114:8503)

---

## 📋 目次

1. [セキュリティ概要](#セキュリティ概要)
2. [実施済み対策](#実施済み対策)
3. [推奨する追加対策](#推奨する追加対策)
4. [運用ガイドライン](#運用ガイドライン)
5. [インシデント対応](#インシデント対応)
6. [作業ログ](#作業ログ)

---

## セキュリティ概要

### リスク分析

| リスク項目 | 深刻度 | 現状 | 対策状況 |
|-----------|-------|------|---------|
| **不正ログイン** | 🟢 低 | パスワード認証済み | ✅ 実施済み |
| **データ漏洩** | 🟡 中 | SQLite平文保存 | ⚠️ 部分対応 |
| **サービス妨害（DDoS）** | 🟡 中 | ポート公開 | ⚠️ 未対応 |
| **SSH不正アクセス** | 🟡 中 | 鍵認証推奨 | ⚠️ 要確認 |
| **APIキー漏洩** | 🟢 低 | secrets.toml管理 | ✅ 実施済み |
| **OS脆弱性** | 🟢 低 | Ubuntu LTS自動更新 | ✅ 実施済み |

---

## 実施済み対策

### 1. ✅ Streamlitパスワード認証（2025年12月13日 実装確認）

**実装方法**:
- `auth_system.py`: クエリパラメータベース認証システム
- SHA256ハッシュ化パスワード
- セッショントークン有効期限: 8時間
- URLパラメータ + セッション状態の二重保存

**認証情報**:
```toml
# .streamlit/secrets.toml
[auth]
password_hash = "41e749030cd3aa529105b76146d59a5ea807146d5c8a8b3b10bd9d61e9db0cbd"  # aicast2025
```

**動作確認**:
```bash
# VPSで確認
ssh ubuntu@153.126.194.114
cd /home/ubuntu/aicast-app
cat .streamlit/secrets.toml | grep password_hash
```

**アクセスフロー**:
1. http://153.126.194.114:8503 にアクセス
2. パスワード入力画面表示
3. `aicast2025` を入力
4. 認証成功 → ダッシュボード表示

---

### 2. ✅ APIキー・認証情報の安全管理

**保護対象**:
- X API認証情報（API Key, API Secret, Bearer Token, Access Token, Access Secret）
- Google Cloud認証情報（サービスアカウントキー）
- Google Sheets API認証情報

**保存場所**:
```
/home/ubuntu/aicast-app/
├── .streamlit/secrets.toml       # Streamlit認証・設定
├── credentials/
│   └── service-account-key.json  # Google Cloud認証
└── casting_office.db             # X API認証（cast_x_credentials テーブル）
```

**アクセス制限**:
```bash
# ファイルパーミッション
chmod 600 .streamlit/secrets.toml
chmod 600 credentials/service-account-key.json
chmod 644 casting_office.db  # read/write ubuntu, read others
```

---

### 3. ✅ データベースアクセス制御

**構成**:
- SQLite 3 ローカルファイルDB
- 外部キー制約有効化: `PRAGMA foreign_keys = ON;`
- 接続管理: `execute_query()` 関数で統一

**バックアップ**:
- Google Drive自動同期（daily）
- ローカルバックアップ: `/home/ubuntu/aicast-app/backups/`

---

## 推奨する追加対策

### 優先度: 🔴 高（1週間以内）

#### 1. SSH鍵認証の強制化

**目的**: パスワード認証を無効化し、鍵認証のみ許可

**実装手順**:
```bash
# 1. SSH鍵ペアを生成（ローカル）
ssh-keygen -t ed25519 -C "aicast-admin@example.com"

# 2. 公開鍵をVPSに転送
ssh-copy-id -i ~/.ssh/id_ed25519.pub ubuntu@153.126.194.114

# 3. VPS側でSSH設定を変更（管理者権限必要）
sudo nano /etc/ssh/sshd_config
```

**設定内容**:
```ini
# /etc/ssh/sshd_config
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
AllowUsers ubuntu
```

**適用**:
```bash
sudo systemctl restart sshd
```

**影響**: SSH接続が鍵認証のみに限定される（自動処理には影響なし）

---

#### 2. ファイアウォール設定（UFW）

**目的**: 不要なポートを閉鎖し、必要最小限のアクセスのみ許可

**実装手順**:
```bash
# UFWインストール（既にインストール済み）
sudo apt install ufw

# デフォルトポリシー
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 必要なポート開放
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 8503/tcp   # Streamlit

# 有効化
sudo ufw enable
sudo ufw status verbose
```

**期待結果**:
```
Status: active
Logging: on (low)

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere
8503/tcp                   ALLOW IN    Anywhere
22/tcp (v6)                ALLOW IN    Anywhere (v6)
8503/tcp (v6)              ALLOW IN    Anywhere (v6)
```

**影響**: 8503以外のポートへの外部アクセスがブロックされる（自動処理には影響なし）

---

### 優先度: 🟡 中（1ヶ月以内）

#### 3. Nginx リバースプロキシ + SSL化

**目的**: HTTPS化とBasic認証の二重化

**実装概要**:
```bash
# Nginxインストール
sudo apt install nginx certbot python3-certbot-nginx

# SSL証明書取得（ドメイン必要）
sudo certbot --nginx -d aicast.yourdomain.com

# Nginx設定
sudo nano /etc/nginx/sites-available/aicast
```

**設定例**:
```nginx
server {
    listen 443 ssl http2;
    server_name aicast.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/aicast.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/aicast.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8503;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**影響**: アクセスURLが変更（http → https）、Streamlitは127.0.0.1のみリッスン

---

#### 4. VPN経由アクセス限定（Tailscale）

**目的**: インターネット公開を停止し、VPN経由のみアクセス可能に

**実装概要**:
```bash
# Tailscaleインストール
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Streamlitを127.0.0.1のみリッスン
# run.pyまたはapp.py起動オプション変更
streamlit run app.py --server.address=127.0.0.1
```

**影響**: 外部からの直接アクセス不可、Tailscale VPN接続必須

---

### 優先度: 🟢 低（必要に応じて）

#### 5. データベース暗号化（SQLCipher）

**目的**: SQLiteファイルの暗号化

**実装概要**:
```bash
pip install sqlcipher3

# コード修正
import sqlcipher3 as sqlite3
conn = sqlite3.connect('casting_office.db')
conn.execute("PRAGMA key='your-encryption-key'")
```

**影響**: 全てのDB接続コードを修正必要、パフォーマンス低下の可能性

---

## 運用ガイドライン

### 定期チェック項目（月次）

- [ ] OSアップデート確認: `sudo apt update && sudo apt upgrade`
- [ ] ログ確認: `tail -100 /home/ubuntu/aicast-app/app.log`
- [ ] ディスク使用量: `df -h`
- [ ] 不審なプロセス確認: `ps aux | grep -E 'python|streamlit'`
- [ ] SSHログイン試行確認: `sudo journalctl -u ssh | grep -i failed`

### パスワード管理

**現在のパスワード**: `aicast2025`

**変更手順**:
```python
# 新しいパスワードのハッシュ生成
import hashlib
new_password = "new_secure_password_2026"
hash_value = hashlib.sha256(new_password.encode()).hexdigest()
print(hash_value)
```

```toml
# .streamlit/secrets.toml更新
[auth]
password_hash = "生成されたハッシュ値"
```

```bash
# Streamlit再起動
screen -S aicast -X quit
screen -dmS aicast bash -c "cd /home/ubuntu/aicast-app && source .venv/bin/activate && python3 run.py"
```

### アクセスログ監視

```bash
# Streamlitアクセスログ
tail -f /home/ubuntu/aicast-app/app.log | grep -E 'password|auth|login'

# システムログ
sudo journalctl -f -u ssh
```

---

## インシデント対応

### 不正アクセスが疑われる場合

1. **即座にサーバー停止**
   ```bash
   ssh ubuntu@153.126.194.114
   screen -S aicast -X quit
   ```

2. **ログ確認**
   ```bash
   tail -200 app.log > /tmp/incident_$(date +%Y%m%d_%H%M%S).log
   sudo journalctl -u ssh --since "1 hour ago" > /tmp/ssh_$(date +%Y%m%d_%H%M%S).log
   ```

3. **パスワード変更**
   - Streamlit認証パスワード変更
   - SSH鍵の再生成
   - X API認証情報のローテーション

4. **再起動前の確認**
   - 不審なファイル: `find /home/ubuntu/aicast-app -mtime -1`
   - 不審なプロセス: `ps aux`
   - ネットワーク接続: `sudo netstat -tuln`

---

## 作業ログ

### 2025年12月13日

**実施内容**:
- ✅ セキュリティ対策の現状確認
- ✅ Streamlitパスワード認証の動作確認（既に実装済み）
- ✅ API認証情報の保存場所確認
- ✅ SECURITY.mdドキュメント作成
- ⏳ SSH鍵認証強制化（管理者権限必要のため保留）
- ⏳ UFWファイアウォール設定（管理者権限必要のため保留）

**判明事項**:
- 認証システム（`auth_system.py`）は2025年10月以前に実装済み
- パスワード: `aicast2025` (SHA256ハッシュ化)
- VPS環境ではsudo権限が制限されているため、一部設定変更は管理者に依頼必要

**次回アクション**:
1. VPS管理者に以下を依頼:
   - SSH鍵認証の強制化設定
   - UFWファイアウォール設定
2. ドメイン取得後、SSL化検討
3. Tailscale VPN導入の評価

**影響範囲**:
- ✅ 自動生成バッチ: 影響なし（独立プロセス）
- ✅ 予約投稿: 影響なし（cronジョブ）
- ✅ X API連携: 影響なし（外向き通信）
- ⚠️ UI管理画面: パスワード認証必要（既に実装済み）

---

## 参考資料

### 関連ドキュメント

- [運用者向けマニュアル](./OPERATOR_MANUAL.md)
- [Sakura VPS運用手順](./docs/README_SAKURA_VPS.md)
- [システム構成図](./OPERATOR_MANUAL.md#システム概要)

### 外部リンク

- [Streamlit Authentication](https://docs.streamlit.io/knowledge-base/deploy/authentication-without-sso)
- [Ubuntu Security Best Practices](https://ubuntu.com/server/docs/security-introduction)
- [Let's Encrypt SSL証明書](https://letsencrypt.org/)
- [Tailscale VPN](https://tailscale.com/)

---

**担当者**: システム管理者  
**レビュー**: 月次  
**承認**: プロジェクトオーナー
