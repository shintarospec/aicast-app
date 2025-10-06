# AIcast スケジュール投稿システム - 健全性チェックリスト

## 🔍 日次健全性チェック

### 1. システム動作確認
```bash
# スケジュール投稿チェッカーの実行
python3 local_schedule_checker.py
```

**期待される正常出力:**
```
🕐 現在時刻(JST): 2025-XX-XX XX:XX:XX  ← JST時刻表示
✅ cronサービス動作中                   ← cron正常動作
📭 実行対象のスケジュール投稿はありません   ← または投稿実行ログ
```

### 2. タイムゾーン整合性チェック
```bash
# 現在のタイムゾーン確認
date
timedatectl  # systemd環境の場合
```

### 3. データベース時刻確認
```bash
# スケジュール投稿の時刻確認
sqlite3 casting_office.db "SELECT id, scheduled_at, sent_status FROM posts WHERE scheduled_at IS NOT NULL AND sent_status = 'scheduled' ORDER BY scheduled_at LIMIT 5;"
```

## 🚨 アラート条件

### 即座対応が必要
- [ ] スケジュール投稿が3時間以上遅延
- [ ] cronサービス停止
- [ ] JST以外の時刻表示

### 監視が必要  
- [ ] UTC時刻での比較実行
- [ ] Cloud Functionエラー率上昇
- [ ] Google Sheets時刻表示異常

## 🛠️ トラブルシューティング

### タイムゾーン問題
```bash
# 1. pytzライブラリ確認
python3 -c "import pytz; print(pytz.timezone('Asia/Tokyo'))"

# 2. システム時刻確認  
date
echo "JST: $(TZ='Asia/Tokyo' date)"
echo "UTC: $(TZ='UTC' date)"

# 3. スケジュール投稿ログ確認
tail -n 50 app.log | grep -i "schedule\|時刻"
```

### データベース問題
```bash
# スケジュール投稿データ確認
sqlite3 casting_office.db "
SELECT 
    id, 
    cast_id,
    scheduled_at,
    sent_status,
    datetime('now', 'localtime') as current_jst
FROM posts 
WHERE scheduled_at IS NOT NULL 
AND sent_status = 'scheduled'
ORDER BY scheduled_at;
"
```

## 📋 定期メンテナンス（週次）

### 1. ログローテーション
```bash
# アプリケーションログのローテーション
cp app.log app.log.$(date +%Y%m%d)
echo "" > app.log
```

### 2. データベース最適化
```bash
# SQLiteデータベースの最適化
sqlite3 casting_office.db "VACUUM;"
sqlite3 casting_office.db "ANALYZE;"
```

### 3. 古いログ削除
```bash
# 30日以上古いログファイルを削除
find . -name "app.log.*" -mtime +30 -delete
```

## 📊 パフォーマンス監視

### 重要指標
- スケジュール投稿の実行精度（±5分以内）
- Cloud Function呼び出し成功率（95%以上）
- データベースレスポンス時間（1秒以内）

### 監視コマンド
```bash
# スケジュール投稿実行統計
sqlite3 casting_office.db "
SELECT 
    COUNT(*) as total_scheduled,
    COUNT(CASE WHEN sent_status = 'sent' THEN 1 END) as completed,
    COUNT(CASE WHEN sent_status = 'scheduled' THEN 1 END) as pending
FROM posts 
WHERE scheduled_at IS NOT NULL;
"
```

## 🔄 復旧手順

### タイムゾーン問題発生時
1. `TIMEZONE_RESOLUTION_LOG.md` を参照
2. JST時刻処理の確認
3. `local_schedule_checker.py` の時刻比較ロジック検証
4. 必要に応じてサービス再起動

### 緊急時の手動投稿
```bash
# 手動でスケジュール投稿を実行
python3 -c "
import sqlite3
from datetime import datetime
import pytz

JST = pytz.timezone('Asia/Tokyo')
current_jst = datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
print(f'Current JST: {current_jst}')

# 対象投稿の手動実行（投稿ID指定）
# python3 local_schedule_checker.py --post-id [ID]
"
```

---

**最終更新**: 2025年10月3日
**更新者**: システム管理者
**バージョン**: 1.0