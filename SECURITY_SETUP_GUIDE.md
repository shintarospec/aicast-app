# 🚀 緊急セキュリティ強化 - 実行手順書

**作成日**: 2025年12月13日  
**所要時間**: 5分  
**影響**: 自動生成・予約投稿システムには影響なし

---

## ⚡ 今すぐ実行する手順

### ステップ1: VPSにログイン

```bash
ssh ubuntu@153.126.194.114
```

### ステップ2: セキュリティ強化スクリプトを実行

```bash
cd /home/ubuntu/aicast-app
sudo bash security-setup.sh
```

**パスワードを求められたら**、VPSのubuntuユーザーのパスワードを入力してください。

### ステップ3: 実行結果の確認

スクリプトが成功すると、以下のように表示されます：

```
========================================
✅ セキュリティ強化完了！
========================================

実施内容:
  ✅ ファイアウォール（UFW）設定完了
     - 許可ポート: 22 (SSH), 8503 (Streamlit)
     - その他のポート: すべて拒否

  ✅ fail2ban 侵入検知システム導入完了
     - SSH: 3回失敗で2時間ブロック
     - 自動起動: 有効

  ⚠️  SSH設定強化（要手動対応）
     - パスワード認証の無効化を推奨
     - 鍵認証への切り替えを推奨
```

---

## 📊 実施される対策

### 1. ファイアウォール（UFW）

**設定内容**:
- ✅ 受信：デフォルトで全拒否
- ✅ 送信：デフォルトで全許可
- ✅ 許可ポート：
  - 22/tcp（SSH）
  - 8503/tcp（Streamlit AIcast Room）

**効果**: 不要なポートへの攻撃をブロック

### 2. fail2ban（侵入検知システム）

**設定内容**:
- ✅ SSH総当たり攻撃の検知と自動ブロック
- ✅ 3回失敗 → 2時間アクセス禁止
- ✅ システム起動時に自動起動

**効果**: 総当たり攻撃（ブルートフォース）を防止

---

## ✅ 動作確認

### 1. ファイアウォール確認

```bash
sudo ufw status verbose
```

**期待される出力**:
```
Status: active
Logging: on (low)

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere                   # SSH
8503/tcp                   ALLOW IN    Anywhere                   # Streamlit AIcast Room
```

### 2. fail2ban確認

```bash
sudo fail2ban-client status sshd
```

**期待される出力**:
```
Status for the jail: sshd
|- Filter
|  |- Currently failed: 0
|  |- Total failed:     0
|  `- File list:        /var/log/auth.log
`- Actions
   |- Currently banned: 0
   |- Total banned:     0
   `- Banned IP list:
```

### 3. Streamlitアクセス確認

**ブラウザで確認**:
http://153.126.194.114:8503

✅ 正常にアクセスできること
✅ パスワード入力画面が表示されること

---

## 🔄 自動処理への影響確認

### cronジョブ確認

```bash
crontab -l | grep auto_generation
```

**期待される出力**:
```
*/5 * * * * cd /home/ubuntu/aicast-app && .venv/bin/python auto_generation_batch.py >> auto_generation.log 2>&1
```

### Streamlit稼働確認

```bash
ps aux | grep streamlit
```

**プロセスが動いていることを確認**

---

## ⚠️ トラブルシューティング

### Q1: スクリプト実行時にエラーが出る

**エラー例**: `Permission denied`

**対処法**:
```bash
chmod +x security-setup.sh
sudo bash security-setup.sh
```

### Q2: SSH接続が切れた

**原因**: ファイアウォール設定中に一時的に切断される可能性

**対処法**:
```bash
# 再接続するだけでOK
ssh ubuntu@153.126.194.114
```

### Q3: Streamlitにアクセスできない

**確認事項**:
```bash
# ポート8503が開いているか確認
sudo ufw status | grep 8503

# Streamlitが起動しているか確認
screen -ls
ps aux | grep streamlit
```

**対処法**:
```bash
# Streamlit再起動
screen -S aicast -X quit
screen -dmS aicast bash -c "cd /home/ubuntu/aicast-app && source .venv/bin/activate && python3 run.py"
```

### Q4: 自分のIPがブロックされた

**症状**: SSH接続できない

**対処法**:
- VPSのコンソール（さくらのコントロールパネル）からログイン
- 以下のコマンドでブロック解除:
```bash
sudo fail2ban-client set sshd unbanip YOUR_IP_ADDRESS
```

---

## 📅 今後の定期作業

### 毎週（月曜日）

```bash
# fail2banステータス確認
sudo fail2ban-client status sshd

# ブロックされたIPリスト確認
sudo fail2ban-client status sshd | grep "Banned IP list"
```

### 毎月（1日）

```bash
# セキュリティアップデート
sudo apt update
sudo apt upgrade -y

# ログ確認
sudo journalctl -u ssh --since "30 days ago" | grep -i "failed" | wc -l
```

---

## 🎯 次のステップ（任意）

### 優先度: 高

**SSH鍵認証への切り替え**

1. ローカルPCで鍵生成
   ```bash
   ssh-keygen -t ed25519 -C "aicast-admin"
   ```

2. 公開鍵をVPSに転送
   ```bash
   ssh-copy-id -i ~/.ssh/id_ed25519.pub ubuntu@153.126.194.114
   ```

3. 鍵認証でログインできることを確認
   ```bash
   ssh -i ~/.ssh/id_ed25519 ubuntu@153.126.194.114
   ```

4. パスワード認証を無効化
   ```bash
   sudo nano /etc/ssh/sshd_config
   # PasswordAuthentication no を追加
   sudo systemctl restart sshd
   ```

---

## 📞 サポート

問題が発生した場合:
1. [SECURITY.md](SECURITY.md) の「インシデント対応」セクションを参照
2. [VPS_RISK_ASSESSMENT_REPORT.md](VPS_RISK_ASSESSMENT_REPORT.md) でリスク内容を確認
3. 必要に応じてセキュリティ専門家に相談

---

**このスクリプトの実行で、VPSのセキュリティレベルが大幅に向上します！**
