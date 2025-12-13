#!/bin/bash
# AIcast Room - HTTPS化自動セットアップスクリプト
# ドメイン: aicast.nemo.work
# 実行日: 2025年12月13日

set -e

DOMAIN="aicast.nemo.work"
EMAIL="info@oob.co.jp"  # Let's Encrypt通知用メールアドレス
STREAMLIT_PORT=8503

echo "========================================"
echo "AIcast Room HTTPS化セットアップ"
echo "ドメイン: $DOMAIN"
echo "========================================"
echo ""

# ====================================
# 1. Nginx + Certbot インストール
# ====================================
echo "📦 1. Nginx + Certbot インストール中..."
sudo apt update -qq
sudo apt install -y nginx certbot python3-certbot-nginx

echo "✅ Nginx + Certbot インストール完了"
echo ""

# ====================================
# 2. UFW ファイアウォール設定
# ====================================
echo "🔥 2. ファイアウォール設定更新中..."
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status numbered

echo "✅ ファイアウォール設定完了"
echo ""

# ====================================
# 3. Nginx リバースプロキシ設定
# ====================================
echo "⚙️  3. Nginx リバースプロキシ設定中..."

# 既存の default 設定を無効化
sudo rm -f /etc/nginx/sites-enabled/default

# AIcast Room 用設定ファイル作成
sudo tee /etc/nginx/sites-available/aicast > /dev/null << EOF
# AIcast Room - Nginx リバースプロキシ設定
# ドメイン: $DOMAIN
# 作成日: $(date '+%Y-%m-%d')

# HTTP → HTTPS リダイレクト（SSL証明書取得後に有効化）
# server {
#     listen 80;
#     listen [::]:80;
#     server_name $DOMAIN;
#     return 301 https://\$server_name\$request_uri;
# }

# HTTPS サーバー（SSL証明書取得後に有効化）
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    # アクセスログ
    access_log /var/log/nginx/aicast-access.log;
    error_log /var/log/nginx/aicast-error.log;

    # Streamlit へリバースプロキシ
    location / {
        proxy_pass http://localhost:$STREAMLIT_PORT;
        proxy_http_version 1.1;
        
        # WebSocket サポート（Streamlit必須）
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # ヘッダー転送
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # タイムアウト設定（Streamlit長時間接続対応）
        proxy_read_timeout 86400;
        proxy_connect_timeout 86400;
        proxy_send_timeout 86400;
    }
}
EOF

# シンボリックリンク作成
sudo ln -sf /etc/nginx/sites-available/aicast /etc/nginx/sites-enabled/

# Nginx 設定テスト
sudo nginx -t

# Nginx 再起動
sudo systemctl restart nginx

echo "✅ Nginx リバースプロキシ設定完了"
echo ""

# ====================================
# 4. Let's Encrypt SSL証明書取得
# ====================================
echo "🔐 4. Let's Encrypt SSL証明書取得中..."

sudo certbot --nginx \
    -d $DOMAIN \
    --non-interactive \
    --agree-tos \
    --email $EMAIL \
    --redirect

echo "✅ SSL証明書取得完了"
echo ""

# ====================================
# 5. Streamlit を localhost のみに制限
# ====================================
echo "🔒 5. Streamlit アクセス制限設定中..."

# Streamlit設定ディレクトリ作成
mkdir -p /home/ubuntu/.streamlit

# Streamlit設定ファイル作成
tee /home/ubuntu/.streamlit/config.toml > /dev/null << EOF
[server]
# localhost のみ接続許可（Nginx経由のみアクセス可能）
address = "127.0.0.1"
port = $STREAMLIT_PORT

# ブラウザ自動起動無効
headless = true

# WebSocket有効化
enableWebsocketCompression = true
enableXsrfProtection = true

[browser]
# ブラウザ自動起動無効
gatherUsageStats = false
EOF

# UFW で 8503 ポートを外部から閉じる（localhost のみ許可）
sudo ufw delete allow 8503/tcp 2>/dev/null || true
sudo ufw status numbered

echo "✅ Streamlit アクセス制限完了（localhost のみ）"
echo ""

# ====================================
# 6. SSL証明書自動更新設定
# ====================================
echo "🔄 6. SSL証明書自動更新設定中..."

# certbot タイマー確認
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
sudo systemctl status certbot.timer --no-pager | head -5

echo "✅ SSL証明書自動更新設定完了（1日2回チェック）"
echo ""

# ====================================
# 7. Streamlit 再起動
# ====================================
echo "🔄 7. Streamlit 再起動中..."

# 既存プロセス停止
pkill -f "streamlit run" || true
screen -S aicast -X quit 2>/dev/null || true
sleep 3

# 新しいプロセス起動
cd /home/ubuntu/aicast-app
screen -dmS aicast bash -c "source .venv/bin/activate && python3 run.py"
sleep 5

# プロセス確認
if ps aux | grep -v grep | grep -q "streamlit"; then
    echo "✅ Streamlit 再起動完了"
else
    echo "❌ Streamlit 再起動失敗"
fi
echo ""

# ====================================
# 8. 動作確認
# ====================================
echo "========================================"
echo "🎉 HTTPS化セットアップ完了！"
echo "========================================"
echo ""
echo "✅ 1. Nginx: 稼働中"
systemctl is-active nginx && echo "   Status: active" || echo "   Status: inactive"
echo ""
echo "✅ 2. SSL証明書:"
sudo certbot certificates | grep -A3 "Certificate Name: $DOMAIN" || echo "   証明書情報取得中..."
echo ""
echo "✅ 3. ファイアウォール:"
sudo ufw status | grep -E "(80|443|8503)"
echo ""
echo "✅ 4. Streamlit:"
ps aux | grep streamlit | grep -v grep | awk '{print "   PID: " $2 ", 稼働時間: " $10}'
echo ""
echo "========================================"
echo "📝 アクセスURL:"
echo "   HTTPS: https://$DOMAIN"
echo "   HTTP:  http://$DOMAIN （自動リダイレクト）"
echo "========================================"
echo ""
echo "⚠️  注意:"
echo "   - 8503ポートは外部アクセス不可（localhost のみ）"
echo "   - 必ず HTTPS でアクセスしてください"
echo "   - SSL証明書は90日ごとに自動更新されます"
echo ""
echo "🔍 動作確認:"
echo "   curl -I https://$DOMAIN"
echo ""

# 動作確認
echo "🧪 HTTPS接続テスト:"
curl -I https://$DOMAIN 2>&1 | head -5 || echo "接続テスト失敗（数分後に再試行してください）"

exit 0
