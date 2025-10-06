# 🚨 Development Rules - Mission-Critical Functions (MCF) Protection

## 🎖️ Mission-Critical Functions (MCF) - Absolute Protection

### Currently Stable MCF Components
1. **Scheduled Post Function** - 2025-10-04 MCF Stable Operation Confirmed
2. **Retweet Scheduling Function** - 2025-10-04 MCF Stable Operation Confirmed  
3. **UI Send Function** - 2025-10-04 MCF Stable Operation Confirmed

**These MCF components are the foundation of production operations. Any errors or regressions in MCF are absolutely forbidden!**

## 📋 必須守るべきルール

### 1. 既存機能への影響禁止
**絶対に既存の成功している機能に影響を与えてはいけません！**

- 既存のURL・エンドポイントを変更しない
- 既存のデータベーススキーマを変更しない  
- 既存の環境変数を削除・変更しない
- 既存のcron設定を上書きしない
- 既存の関数の引数・戻り値を変更しない

### 2. 必須作業フロー

#### 新機能追加前
1. `CODE_REVIEW_CHECKLIST.md` を必ず確認
2. 既存機能テストを実行: `python3 test_existing_functions.py`
3. 影響範囲を明確に設計

#### 新機能実装中
1. `config.py` で設定を一元管理
2. 新機能は独立したファイル・モジュールで実装
3. ハードコードされたURL・設定は禁止

#### 新機能追加後
1. 既存機能テスト実行: `python3 test_existing_functions.py`
2. UI送信機能テスト
3. 自動スケジューラーテスト
4. 全機能の統合テスト

### 3. 設定管理ルール

```python
# ❌ 禁止: ハードコード
CLOUD_FUNCTION_URL = "https://example.com/api"

# ✅ 推奨: config.py使用
from config import Config
url = Config.get_cloud_functions_url()
```

### 4. テスト投稿ルール

**絶対に「テストです」などの明示的なテスト文言を使用しない！**
**テストアカウントは「shinrepoto」のみを使用する！**

```python
# ❌ 禁止: 明示的なテスト文言
test_text = "テスト投稿です"
test_text = "Test post"

# ❌ 禁止: ハードコードされたアカウント
account_id = "shinrepoto"  # ハードコード禁止

# ✅ 推奨: config.pyからの取得
from config import Config
test_text = Config.get_test_post()  # 🔧, ⚡, 🚀 など
test_account = Config.get_test_account_id()  # shinrepoto

# テスト投稿の安全性チェック
if Config.is_safe_test_content(text) and Config.is_test_account(account_id):
    # 安全なテスト投稿実行
    pass
else:
    # 危険なテスト設定
    pass
```

### 5. ファイル構成ルール

- **新機能**: 独立したファイルで実装
- **共通設定**: `config.py` で管理
- **テスト**: `test_existing_functions.py` で既存機能保護

## 🧪 テストコマンド（生命線機能保護）

```bash
# 🚨 必須: 生命線機能保護テスト
python3 test_existing_functions.py

# 🚨 必須: 生命線機能監視
python3 monitor_critical_functions.py

# 設定確認
python3 -c "from config import Config; print(Config.get_cloud_functions_url())"

# 生命線機能設定検証
python3 -c "from config import Config; errors = Config.validate_critical_settings(); print('✅ 設定正常' if not errors else f'❌ {errors}')"

# スケジューラー単体テスト
python3 local_schedule_checker.py
python3 local_retweet_scheduler.py
```

## 🖥️ GUI中心テスト方針

**基本的にテストはStreamlit GUIで行うことを推奨します。**

### GUI優先テストの利点
- **実際のユーザー操作環境** でのテスト
- **総合的な機能確認** が可能
- **UI/UX の同時検証**
- **直感的な操作フロー** でのテスト

### 推奨テスト手順
1. **Streamlit アプリ起動**: `python3 run.py`
2. **ブラウザアクセス**: `http://0.0.0.0:8502`
3. **各機能をGUIで操作テスト**:
   - ダッシュボード表示確認
   - キャスト管理（XAPI情報フォーム含む）
   - 投稿管理（Draft→Approved→Scheduled）
   - スケジュール投稿設定
   - リツイート予約機能

### コマンドラインテストの使用場面
- **緊急時のトラブルシューティング**
- **開発中のデバッグ**
- **CI/CD自動テスト**
- **システム統合テスト**

```bash
# 緊急時のみ: 既存機能保護テスト
python3 test_existing_functions.py

# 開発時のみ: 単体テスト

## 📝 コミット前チェックリスト

- [ ] `CODE_REVIEW_CHECKLIST.md` を確認済み
- [ ] `python3 test_existing_functions.py` が成功
- [ ] ハードコードされた設定がない
- [ ] 新機能が独立実装されている
- [ ] 既存機能に影響がない

## ⚠️ トラブル時の対応

### 既存機能が動かない場合
1. `python3 test_existing_functions.py` で問題を特定
2. `git log --oneline -10` で最近の変更を確認
3. 必要に応じて直前のコミットに戻す
4. 原因を特定して修正

### URL・設定関連の問題
1. `config.py` の設定を確認
2. 全ファイルでハードコードがないか確認
3. Cloud Functions URLが正しいか確認

## 🎯 成功の定義

- 新機能が正常動作する
- 既存機能が変わらず動作する
- すべてのテストが成功する
- 設定が一元管理されている

**このルールを守ることで、安定した本番環境を維持できます！**