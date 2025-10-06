# 🚨 トラブルシューティングセッション記録

**日時:** 2025年10月5日  
**概要:** システム復旧・予約投稿問題解決・ドキュメント整理

---

## 🎯 解決した主要問題

### 1. MCF DEATH GUARD無限ループ問題
**症状:** システム不安定、無限ループによる高負荷  
**原因:** MCF DEATH GUARDの過剰な保護機能  
**解決:** プロセス停止・無効化  
**結果:** システム安定化

### 2. app.py機能退行問題  
**症状:** ダッシュボード・XAPI機能の消失  
**原因:** Git操作により古いバージョンに戻った  
**解決:** `git reset --hard b9f06150` で完全版復旧  
**結果:** 6,376行の完全版app.py復活（元：2,511行）

### 3. 予約投稿システム問題
**症状:** 予約投稿が実行されない（リツイート予約は正常）  
**原因:** Secret Manager認証エラー  
**解決:** USE_SECRET_MANAGERフラグでSecret Manager無効化  
**結果:** 予約投稿機能完全復旧

---

## 🔧 技術的解決方法

### Secret Manager無効化処理
```python
# local_schedule_checker.py
USE_SECRET_MANAGER = False  # 開発環境向け設定

def get_account_id_for_cast(cast_name, db_path):
    # Secret Manager使用せず、データベース直接取得
    if USE_SECRET_MANAGER:
        # 将来の本番環境用（保持）
    else:
        # 現在の開発環境用
```

### Git復旧コマンド
```bash
# 失われたコミットの発見
git reflog --oneline -20

# 完全版への復旧
git reset --hard b9f06150
```

---

## 📊 復旧結果

### ✅ 復活した機能
- **📊 ダッシュボード** - 統計・分析機能
- **XAPI情報フォーム** - キャスト管理でのX API設定
- **予約投稿システム** - Secret Manager問題解決
- **25個のMDファイル** - 技術ドキュメント群復活

### 🔄 システム状況
- **アプリケーション:** 正常動作（ポート8502）
- **予約投稿:** 正常動作確認
- **リツイート予約:** 継続して正常動作
- **認証システム:** Google Cloud ADC正常

---

## 🛡️ 予防措置

### 1. ドキュメント保護
- すべてのMDファイルを`docs/`フォルダに統一
- 重要な技術資産として厳重管理
- Git履歴での変更追跡

### 2. テスト方針確立
- **基本：Streamlit GUI**での機能テスト
- **緊急時のみ：コマンドライン**テスト
- `DEVELOPMENT_RULES.md`に方針明記

### 3. セキュリティ拡張性保持
- Secret Managerコードを保持
- フラグによる機能切り替え
- 将来の本番環境対応準備

---

## 📚 参考ドキュメント

- `docs/SCHEDULE_POSTING_DEVELOPMENT_HISTORY.md` - 予約投稿開発履歴
- `docs/TIMEZONE_RESOLUTION_LOG.md` - タイムゾーン問題解決
- `docs/DEVELOPMENT_RULES.md` - 開発ルール・テスト方針
- `docs/SYSTEM_HEALTH_CHECKLIST.md` - システム健全性チェック

---

## 💡 今後の改善点

1. **定期的なシステムバックアップ**
2. **重要コミットのタグ付け**
3. **MCF機能の適切な設計**
4. **ドキュメント更新の自動化**

---

*作成日: 2025年10月5日*  
*最終更新: 2025年10月5日*  
*重要度: 🔴 Critical*