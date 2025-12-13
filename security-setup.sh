#!/bin/bash
# AIcast Room - 緊急セキュリティ強化スクリプト
# 作成日: 2025年12月13日

set -e  # エラーで即座に停止

echo "========================================"
echo "AIcast Room セキュリティ強化スクリプト"
echo "========================================"
echo ""

# 管理者権限確認
if [ "$EUID" -ne 0 ]; then 
    echo "❌ このスクリプトはroot権限で実行してください"
    echo "実行方法: sudo bash security-setup.sh"
    exit 1
fi

echo "✅ 管理者権限を確認しました"
echo ""

# バックアップ作成
echo "📦 現在の設定をバックアップ中..."
BACKUP_DIR="/home/ubuntu/security-backup-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp /etc/ssh/sshd_config "$BACKUP_DIR/" 2>/dev/null || true
ufw status verbose > "$BACKUP_DIR/ufw-before.txt" 2>/dev/null || true
echo "✅ バックアップ完了: $BACKUP_DIR"
echo ""

# ====================================
# 1. ファイアウォール（UFW）設定
# ====================================
echo "🔥 [1/4] ファイアウォール（UFW）設定中..."

# UFWをリセット（既存設定をクリア）
ufw --force reset

# デフォルトポリシー
ufw default deny incoming
ufw default allow outgoing

# 必要なポートのみ開放
ufw allow 22/tcp comment 'SSH'
ufw allow 8503/tcp comment 'Streamlit AIcast Room'

# UFW有効化（強制実行）
ufw --force enable

echo "✅ ファイアウォール設定完了"
ufw status verbose
echo ""

# ====================================
# 2. fail2ban（侵入検知システム）導入
# ====================================
echo "🛡️  [2/4] fail2ban 侵入検知システム導入中..."

# fail2banインストール
if ! command -v fail2ban-client &> /dev/null; then
    echo "📥 fail2banをインストール中..."
    apt-get update -qq
    apt-get install -y fail2ban
else
    echo "✅ fail2banは既にインストール済み"
fi

# fail2ban設定ファイル作成
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
# 基本設定
bantime = 3600        # 1時間ブロック
findtime = 600        # 10分間で
maxretry = 5          # 5回失敗したらブロック
destemail = root@localhost
sendername = Fail2Ban

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 3          # SSH は3回失敗でブロック
bantime = 7200        # 2時間ブロック
EOF

# fail2ban起動
systemctl enable fail2ban
systemctl restart fail2ban

echo "✅ fail2ban設定完了"
fail2ban-client status
echo ""

# ====================================
# 3. SSH設定の強化確認
# ====================================
echo "🔐 [3/4] SSH設定確認中..."

# 現在のSSH設定を表示
echo "現在のSSH設定:"
grep -E "^PasswordAuthentication|^PubkeyAuthentication|^PermitRootLogin|^Port" /etc/ssh/sshd_config || echo "  デフォルト設定を使用中"

echo ""
echo "⚠️  推奨設定（手動で適用してください）:"
echo "  PasswordAuthentication no   # パスワード認証を無効化"
echo "  PubkeyAuthentication yes     # 鍵認証を有効化"
echo "  PermitRootLogin no           # root直接ログインを禁止"
echo ""
echo "📝 SSH設定変更手順:"
echo "  1. sudo nano /etc/ssh/sshd_config"
echo "  2. 上記の設定を追加"
echo "  3. sudo systemctl restart sshd"
echo ""

# ====================================
# 4. セキュリティ状態の確認
# ====================================
echo "🔍 [4/4] セキュリティ状態確認中..."
echo ""

echo "=== ファイアウォール状態 ==="
ufw status numbered
echo ""

echo "=== fail2ban状態 ==="
fail2ban-client status sshd
echo ""

echo "=== 開放ポート ==="
ss -tuln | grep LISTEN
echo ""

echo "=== 最近のSSH失敗ログイン（過去24時間） ==="
journalctl -u ssh --since "24 hours ago" | grep -i "failed\|invalid" | tail -10 || echo "  失敗ログインなし"
echo ""

# ====================================
# 完了レポート
# ====================================
echo "========================================"
echo "✅ セキュリティ強化完了！"
echo "========================================"
echo ""
echo "実施内容:"
echo "  ✅ ファイアウォール（UFW）設定完了"
echo "     - 許可ポート: 22 (SSH), 8503 (Streamlit)"
echo "     - その他のポート: すべて拒否"
echo ""
echo "  ✅ fail2ban 侵入検知システム導入完了"
echo "     - SSH: 3回失敗で2時間ブロック"
echo "     - 自動起動: 有効"
echo ""
echo "  ⚠️  SSH設定強化（要手動対応）"
echo "     - パスワード認証の無効化を推奨"
echo "     - 鍵認証への切り替えを推奨"
echo ""
echo "バックアップ保存先: $BACKUP_DIR"
echo ""
echo "次のステップ:"
echo "  1. SSH鍵認証の設定"
echo "  2. 定期的なログ監視（fail2ban-client status）"
echo "  3. 月次セキュリティアップデート（sudo apt update && sudo apt upgrade）"
echo ""
echo "========================================"
echo "詳細: /home/ubuntu/aicast-app/SECURITY.md"
echo "========================================"
