# AIcast Room デプロイ最適化プラン

## 現状分析
- さくらVPS: 1,000円/月
- 想定ボリューム: 100アカウント、5万投稿/月
- 運用者: 2名

## 推奨: さくらVPS継続 + 最適化

### 1. パフォーマンス最適化
```bash
# メモリ使用量監視
pip install psutil
python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"

# SQLiteの最適化
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
```

### 2. 運用効率化設定

#### systemdサービス化
```ini
# /etc/systemd/system/aicast.service
[Unit]
Description=AIcast Room Application
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/aicast-app
Environment=PATH=/path/to/your/venv/bin
ExecStart=/path/to/your/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### ログローテーション
```bash
# /etc/logrotate.d/aicast
/path/to/aicast-app/app.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    create 644 your_user your_group
}
```

### 3. 監視・アラート設定

#### リソース監視スクリプト
```python
# monitor.py
import psutil
import sqlite3
import requests
from datetime import datetime

def check_system():
    # CPU, Memory, Disk使用量チェック
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    
    # DB接続チェック
    try:
        conn = sqlite3.connect('casting_office.db', timeout=5)
        conn.close()
        db_status = "OK"
    except:
        db_status = "ERROR"
    
    status = {
        'timestamp': datetime.now(),
        'cpu': cpu,
        'memory': memory,
        'disk': disk,
        'database': db_status
    }
    
    # アラート条件
    if cpu > 80 or memory > 80 or disk > 80 or db_status == "ERROR":
        send_alert(status)
    
    return status

def send_alert(status):
    # Slack/Discord webhook通知
    pass
```

### 4. バックアップ戦略
```bash
# 日次バックアップスクリプト
#!/bin/bash
DATE=$(date +%Y%m%d)
tar -czf /backup/aicast_backup_$DATE.tar.gz \
    /path/to/aicast-app/casting_office.db \
    /path/to/aicast-app/credentials/

# 古いバックアップ削除（30日保持）
find /backup -name "aicast_backup_*.tar.gz" -mtime +30 -delete
```

## スケーリング時の移行プラン

### 段階的移行戦略
1. **現状 → 10万投稿/月**: さくらVPS上位プラン
2. **10万 → 50万投稿/月**: Google Cloud Run移行検討
3. **50万投稿/月以上**: マイクロサービス化

### 移行判断指標
- CPU使用率が常時70%超
- メモリ使用率が常時80%超
- レスポンス時間が2秒超
- ダウンタイムが月1時間超

## コスト比較（月間5万投稿ベース）

| 選択肢 | 月額コスト | 管理工数 | スケーラビリティ |
|--------|-----------|----------|------------------|
| さくらVPS | 1,000円 | 中 | 手動 |
| Streamlit Cloud | 3,000円 | 低 | 自動（制限あり） |
| Google Cloud Run | 3,000-5,000円 | 低 | 自動 |

## 結論
現在のボリュームなら **さくらVPS継続** がコスト効率最高。
10万投稿/月を超えた段階でクラウド移行を検討。