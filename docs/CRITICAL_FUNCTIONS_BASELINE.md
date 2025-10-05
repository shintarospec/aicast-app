# 🎖️ Mission-Critical Functions (MCF) - Stable Operation Baseline

## 📅 Record Information
- **Created**: 2025-10-04
- **Recorder**: System Administration
- **Status**: MCF Stable Operation Confirmed

## 🚀 Mission-Critical Functions (MCF) List

### 1. スケジュール投稿機能 ✅
- **ファイル**: `app.py`, `local_schedule_checker.py`
- **データベース**: `posts` テーブル
- **Cloud Functions URL**: `https://asia-northeast1-aicast-472807.cloudfunctions.net/x-poster`
- **cron設定**: `*/1 * * * * cd /workspaces/aicast-app && python3 local_schedule_checker.py >> schedule.log 2>&1`
- **動作確認**: ✅ 正常動作
- **最終テスト**: 2025-10-04 12:00 JST

### 2. リツイート予約機能 ✅
- **ファイル**: `app.py`, `local_retweet_scheduler.py`
- **データベース**: `retweet_schedules` テーブル
- **Cloud Functions URL**: `https://asia-northeast1-aicast-472807.cloudfunctions.net/x-poster`
- **cron設定**: `*/5 * * * * cd /workspaces/aicast-app && python3 local_retweet_scheduler.py >> retweet.log 2>&1`
- **動作確認**: ✅ 正常動作（Google Sheets設定は任意）
- **最終テスト**: 2025-10-04 12:00 JST

### 3. UI送信機能 ✅
- **ファイル**: `app.py` (send_to_x_api関数)
- **動作確認**: ✅ 管理画面から送信ボタンで正常動作
- **最終テスト**: 2025-10-04 12:00 JST

## 🔐 保護対象の設定

### 重要URL
```python
# 絶対に変更してはいけないURL（本番稼働中）
CLOUD_FUNCTIONS_URL = "https://asia-northeast1-aicast-472807.cloudfunctions.net/x-poster"
```

### テストアカウント設定
```python
# テスト専用アカウント（変更禁止）
TEST_ACCOUNT_ID = "shinrepoto"
```

### 重要cron設定
```bash
# 投稿スケジューラー（毎分実行）
*/1 * * * * cd /workspaces/aicast-app && python3 local_schedule_checker.py >> schedule.log 2>&1

# リツイートスケジューラー（5分毎実行）
*/5 * * * * cd /workspaces/aicast-app && python3 local_retweet_scheduler.py >> retweet.log 2>&1

# PATH設定（認証エラー防止）
PATH=/home/codespace/google-cloud-sdk/bin:/usr/local/bin:/usr/bin:/bin
```

### 重要データベーススキーマ
- `posts` テーブル: 投稿管理
- `retweet_schedules` テーブル: リツイート予約管理
- `casts` テーブル: キャスト管理

## ⚠️ 絶対禁止事項

### 1. URL変更の禁止
- Cloud Functions URLは本番稼働中のため変更禁止
- ハードコード禁止（config.pyで一元管理）

### 2. cron設定の変更禁止
- 既存のcron設定を削除・変更禁止
- 新しいスケジューラーは追加のみ可能

### 3. データベーススキーマ変更の禁止
- 既存テーブルの構造変更禁止
- 既存カラムの削除・変更禁止

### 4. 既存関数の変更禁止
- 既存の成功している関数の引数・戻り値変更禁止
- 新機能は新しい関数で実装

## 📊 品質保証テスト

### 毎回実行必須テスト
```bash
# 既存機能保護テスト
python3 test_existing_functions.py

# 構文チェック
python3 -c "import app; print('✅ 構文OK')"

# 設定確認
python3 -c "from config import Config; print(f'✅ URL: {Config.get_cloud_functions_url()}')"
```

### 手動確認項目
- [ ] UI送信ボタンが動作する
- [ ] スケジュール投稿が時刻通りに実行される
- [ ] リツイート予約が正常に作成できる
- [ ] エラーログに異常がない

## 🔄 復旧手順

### 問題発生時の対応
1. `python3 test_existing_functions.py` でエラー特定
2. `git log --oneline -10` で最近の変更確認
3. 必要に応じて直前のコミットに戻す
4. config.pyの設定確認
5. cron設定確認 (`crontab -l`)

### 緊急連絡先
- システム管理者
- 開発責任者

## 📝 変更履歴
- 2025-10-04: 初期ベースライン作成
- 安定稼働状態を記録
- 生命線機能の保護ルール確立

**この文書の内容は生命線機能の保護のため、変更時は慎重に検討すること**