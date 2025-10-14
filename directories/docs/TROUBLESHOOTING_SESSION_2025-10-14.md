# 🚨 トラブルシューティングセッション記録

**日時:** 2025年10月14日  
**概要:** Secret Manager自動同期機能実装・投稿承認日修正・ドキュメント整理

---

## 🎯 解決した主要問題

### 1. 新規アカウント投稿失敗問題（cute_angel_ten）
**症状:** 404 Secret not found エラーで投稿失敗  
**原因:** Secret Managerに新規アカウントのクレデンシャルが未登録  
**初期対応:** 手動でSecret Manager登録を試みるもフィールド名の不一致で失敗  
**根本原因発見:** 
- Secret Manager: `consumer_key`, `consumer_secret` (4フィールド)
- Database: `api_key`, `api_secret` (5フィールド)
- フィールド名の不一致により自動同期が不可能

**解決策:**
1. jonaikudasaiアカウントのSecret Managerを修正（version 3作成）
2. Secret Manager自動同期機能の実装

**結果:** ✅ 新規アカウント登録時に自動でSecret Manager同期

---

### 2. Secret Manager自動同期機能実装
**背景:** 手動登録では毎回ミスが発生するリスクが高い  
**要件:** 「これを自動化できないと意味がないです」（ユーザー要望）

**実装内容:**
```python
def sync_to_secret_manager(cast_name, credentials_dict):
    """
    キャストのX API認証情報をGoogle Cloud Secret Managerに同期
    
    Args:
        cast_name: キャスト名
        credentials_dict: 認証情報の辞書（5フィールド）
    
    Returns:
        tuple: (success: bool, message: str)
    """
    # Secret Manager SDKインポート（オプショナル）
    try:
        from google.cloud import secretmanager_v1 as secretmanager
    except ImportError:
        return False, "Secret Manager SDKがインストールされていません"
    
    # 認証情報の検証（5フィールド必須）
    required_fields = ['api_key', 'api_secret', 'bearer_token', 
                       'access_token', 'access_token_secret']
    
    # Secret Manager用にフィールド名変換
    secret_data = {
        "consumer_key": credentials_dict.get("api_key", ""),
        "consumer_secret": credentials_dict.get("api_secret", ""),
        # ... 残りのフィールド
    }
    
    # Secret作成または更新
    # - Secret自体が存在しない場合は自動作成
    # - version管理により履歴保持
```

**統合ポイント:**
- `save_cast_x_credentials()` 関数内で自動呼び出し
- `twitter_username` が存在する場合のみ同期実行
- エラー時もDB保存は継続（影響最小化）

**テスト結果:** ✅ 成功！Secret Manager自動同期確認

---

### 3. 投稿承認日の不具合修正
**症状:** `quick_approve()` 実行後、承認日が正しく設定されない  
**原因:** `posted_at` フィールドに時刻のみ設定され、日付が欠落  
**影響範囲:** 承認済み投稿の表示・管理に支障

**修正内容:**
```python
def quick_approve(post_id):
    # 修正前
    time_part = row['posted_at'] or datetime.datetime.now(JST).strftime('%H:%M:%S')
    posted_at = time_part  # ❌ 時刻のみ
    
    # 修正後
    approval_date_jst = datetime.datetime.now(JST).date()
    time_part = row['posted_at'] or datetime.datetime.now(JST).strftime('%H:%M:%S')
    posted_at = f"{approval_date_jst.strftime('%Y-%m-%d')} {time_part}"  # ✅ 日付+時刻
```

**結果:** ✅ 承認日が正しく「今日の日付 + 時刻」で設定される

---

### 4. UnboundLocalError（os module）
**症状:** システム設定ページで `UnboundLocalError: cannot access local variable 'os'` エラー  
**原因:** 関数内で `import os` を実行しているのに、ファイル先頭でも `import os`（グローバル）が存在  
**Python仕様:** 関数内でローカルimportすると、そのスコープ内でのみ有効になり、グローバルのosが見えなくなる

**修正内容:**
- app.py 4箇所の関数内 `import os` を削除
  - Line 3461 (関数内import)
  - Line 4472 (関数内import)
  - Line 4588 (関数内import)
  - Line 6884 (関数内import)
- グローバルimport（Line 14）のみを使用

**結果:** ✅ システム設定ページのエラー解消

---

### 5. ドキュメント構造整理
**症状:** `/docs` と `/directories/docs` の2つのフォルダが存在  
**問題点:** 
- ドキュメントが分散
- 古いファイルと新しいファイルが混在
- 管理が煩雑

**実施内容:**
1. `/docs` フォルダの全32ファイルを確認
2. 重要ファイル4つを `/directories/docs` に移動
   - DB_SYNC_AUTOMATION_LEVELS.md
   - DB_SYNC_STRATEGY.md
   - VPS_PRODUCTION_DEPLOYMENT_GUIDE.md
   - VPS_REMOTE_OPERATION_GUIDE.md
3. `/docs` フォルダを完全削除

**結果:** ✅ ドキュメントが `/directories/docs` に統一（38ファイル）

---

### 6. cloud_functions/x_poster/main.py の意図しない変更
**症状:** git statusでmain.pyに予期しない変更が検出  
**原因:** Secret Manager実装時の試行錯誤で変更が残った  
**変更内容:**
- `USE_SECRET_MANAGER` フラグ追加
- `get_credentials_from_env()` 関数追加

**判断:** この変更は今回のスコープ外（Cloud Functions側の変更は不要）

**対応:** git restoreで元に戻す

**結果:** ✅ main.pyを元の状態に復元

---

## 🔧 技術的実装詳細

### Secret Manager SDK追加
**requirements.txt:**
```
google-cloud-secret-manager
```

**インストール確認:**
```bash
pip3 install google-cloud-secret-manager
```

### フィールド名マッピング
| Database (5フィールド) | Secret Manager (5フィールド) |
|---|---|
| api_key | consumer_key |
| api_secret | consumer_secret |
| bearer_token | bearer_token |
| access_token | access_token |
| access_token_secret | access_token_secret |

### Secret Manager命名規則
```
x-api-{account_id}
```
例: `x-api-jonaikudasai`, `x-api-cute_angel_ten`

---

## 📊 変更ファイル一覧

### 変更ファイル
1. **app.py** - Secret Manager自動同期機能追加・quick_approve修正・import os削除
2. **requirements.txt** - google-cloud-secret-manager追加

### 削除ファイル
3. **/docs/** - 全32ファイル削除（重要4ファイルは移動）

### 移動ファイル
4. **DB_SYNC_AUTOMATION_LEVELS.md** → /directories/docs/
5. **DB_SYNC_STRATEGY.md** → /directories/docs/
6. **VPS_PRODUCTION_DEPLOYMENT_GUIDE.md** → /directories/docs/
7. **VPS_REMOTE_OPERATION_GUIDE.md** → /directories/docs/

### 復元ファイル
8. **cloud_functions/x_poster/main.py** - 元の状態に復元

---

## ✅ テスト結果

### Secret Manager自動同期テスト
```
✅ 新規アカウント登録時の自動同期成功
✅ Secret Manager version管理確認
✅ 既存Secretの更新確認
```

### 投稿承認日修正テスト
```
✅ quick_approve()実行後の承認日確認
✅ 日付+時刻の正しいフォーマット確認
```

### システム設定ページテスト
```
✅ UnboundLocalError解消確認
✅ 全機能正常動作確認
```

---

## 🛡️ 今回の学習と改善

### 1. 自動化の重要性
**学習:** 手動オペレーションは必ずミスが発生する  
**改善:** データベース↔Secret Manager の完全自動同期実装

### 2. フィールド名の統一性
**学習:** 外部システムとDB間でフィールド名が異なると保守性が低下  
**改善:** マッピング層を明示的に実装

### 3. Python スコープ管理
**学習:** 関数内importは予期しない動作を引き起こす  
**改善:** グローバルimportのみ使用する方針を徹底

### 4. Git操作の慎重性
**学習:** 開発中の試行錯誤がコミットに混入するリスク  
**改善:** git statusとgit diffで変更内容を必ず確認

### 5. ドキュメント管理の一元化
**学習:** 分散したドキュメントは管理が困難  
**改善:** `/directories/docs` に統一

---

## 📝 コミット情報

### コミットメッセージ
```
feat: Secret Manager自動同期機能追加 & 投稿承認日修正

- Secret Manager自動同期機能実装（sync_to_secret_manager関数）
- save_cast_x_credentials()に自動同期を統合
- quick_approve()の承認日設定を修正（日付+時刻）
- import os 重複削除（4箇所）
- /docs フォルダ削除・/directories/docs に統合
- requirements.txt に google-cloud-secret-manager 追加
- cloud_functions/x_poster/main.py を元に戻す
```

### 影響範囲
- **MCF機能:** X API投稿の信頼性向上（Secret Manager自動同期）
- **内部処理:** 投稿承認フローの安定性向上
- **開発環境:** ドキュメント構造の明確化
- **依存関係:** Secret Manager SDK追加

---

## 🔄 今後の展開

### 短期（今週中）
- [ ] 本番環境でのSecret Manager自動同期テスト
- [ ] 全キャストのSecret Manager同期状態確認
- [ ] 新規アカウント登録フローの完全テスト

### 中期（今月中）
- [ ] Secret Manager監視・アラート設定
- [ ] 認証情報の定期的な健全性チェック
- [ ] ドキュメントの更新（Secret Manager運用ガイド）

### 長期（来月以降）
- [ ] Secret Managerのバージョン管理戦略確立
- [ ] 複数環境（dev/staging/prod）対応
- [ ] 認証情報のローテーション自動化

---

## 📚 関連ドキュメント

- `DEVELOPMENT_PLANS.md` - 開発計画・進捗管理
- `DEVELOPMENT_RULES.md` - 開発ルール・コーディング規約
- `MCF_DEFINITION.md` - MCF（Mission Critical Functions）定義
- `DB_SYNC_AUTOMATION_LEVELS.md` - DB同期自動化レベル
- `DB_SYNC_STRATEGY.md` - DB同期戦略

---

## 💡 ユーザーフィードバック

### ポジティブ
- ✅ "成功しました！" - Secret Manager自動同期テスト
- ✅ "エラーが消えました！" - システム設定ページ修正

### 改善要望
- 🔄 "これを自動化できないと意味がないです" → 実装完了✅

---

*作成日: 2025年10月14日*  
*最終更新: 2025年10月14日*  
*重要度: 🔴 Critical*  
*関連Issue: Secret Manager認証エラー、投稿承認日不具合*
