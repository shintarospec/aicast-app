# タイムゾーン問題解決ログ

## 📅 解決日時
- **解決日**: 2025年10月3日
- **解決時刻**: 12:26 JST
- **対応担当**: システム管理者

## 🚨 発生していた問題

### 初期症状
- **問題**: Hiranonorico の 09:35 スケジュール投稿が実行されない
- **影響範囲**: JST 昼間時間帯（09:00-15:00頃）のスケジュール投稿
- **原因**: JST/UTC タイムゾーン変換の不整合（9時間のオフセット問題）

### 具体的な事象
```
- 予定時刻: JST 09:35 (ユーザー設定)
- システム解釈: UTC 09:35 (間違った解釈)
- 実際の実行予定: JST 18:35 (9時間後)
→ 昼間の投稿が夜まで実行されない問題
```

## 🔍 調査・分析過程

### 1. 問題特定フェーズ
- **調査対象**: `local_schedule_checker.py` のタイムゾーン処理
- **発見事項**: UTC時刻とJST時刻の混在比較
- **影響投稿**: kurumibutterfly (ID: 128, 132), shinrepoto (ID: 118)

### 2. システム構造分析
```
投稿ライフサイクル:
1. 投稿生成 → ランダム時刻 (JST) → created_at
2. 投稿承認 → posted_at 設定
3. スケジュール → ユーザー設定 (JST) → scheduled_at  
4. 実行判定 → 時刻比較 → Cloud Function 送信
```

### 3. コード解析結果
- **app.py**: JST時刻で正しく保存・表示 ✅
- **local_schedule_checker.py**: 修正前は UTC/JST 混在 ❌
- **Cloud Function**: UTC時刻を内部生成 ✅

## ⚡ 実装した解決策

### タイムゾーン統一アプローチ
```python
# local_schedule_checker.py の修正点

# 修正前: UTC時刻との比較
current_time = datetime.now()  # UTC時刻

# 修正後: JST時刻同士の比較  
JST = pytz.timezone('Asia/Tokyo')
current_time_jst = datetime.now(JST)
current_time_local_str = current_time_jst.strftime('%Y-%m-%d %H:%M:%S')
```

### データベース時刻処理
```sql
-- スケジュール投稿クエリ
SELECT p.id, p.cast_id, p.content, p.scheduled_at, c.name as cast_name
FROM posts p
JOIN casts c ON p.cast_id = c.id
WHERE p.scheduled_at IS NOT NULL 
AND datetime(p.scheduled_at) <= datetime(?)  -- JST時刻同士で比較
AND p.sent_status = 'scheduled'
ORDER BY p.scheduled_at ASC
```

## 🎯 解決後のシステム設計

### 完全JST統一アーキテクチャ
1. **ユーザー入力**: JST時刻で入力
2. **データベース保存**: JST時刻で保存 (`scheduled_at`)
3. **時刻比較**: JST時刻同士で比較
4. **表示**: JST時刻で表示（Google Sheets含む）
5. **Cloud Function**: 時刻情報は送信せず、内部でUTC生成

### Cloud Function送信ペイロード
```json
{
    "action": "post",
    "account_id": "account_name",
    "text": "投稿内容"
}
```
**重要**: 時刻情報は送信しない → Cloud Function側でUTC時刻を自動生成

## ✅ 動作確認結果

### テスト実行ログ
```
🕐 スケジュール投稿チェッカー - ローカルテスト
現在時刻: 2025-10-03 03:26:17  (UTC時刻)
✅ cronサービス動作中

🕐 現在時刻(JST): 2025-10-03 12:26:17  (JST時刻 - 正常)
📭 実行対象のスケジュール投稿はありません
```

### 成功確認項目
- ✅ JST時刻での正確な現在時刻取得
- ✅ タイムゾーン変換なしのシンプルな比較
- ✅ cronサービス正常動作
- ✅ データベース接続・クエリ正常実行

## 🔧 技術仕様

### 使用ライブラリ
```python
import pytz  # タイムゾーン処理
JST = pytz.timezone('Asia/Tokyo')
```

### データベーススキーマ
```sql
posts テーブル:
- scheduled_at TEXT  -- JST時刻文字列 'YYYY-MM-DD HH:MM:SS'
- created_at TEXT    -- 投稿生成時刻 (JST)
- posted_at TEXT     -- 承認時刻
- sent_status TEXT   -- 'scheduled', 'sent', etc.
```

## 🚀 運用ガイドライン

### 正常動作の確認方法
```bash
# スケジュール投稿システムのテスト
python3 local_schedule_checker.py

# 期待される出力例:
# 🕐 現在時刻(JST): 2025-10-03 12:26:17
# ✅ cronサービス動作中
# 📭 実行対象のスケジュール投稿はありません
```

### トラブルシューティング
1. **タイムゾーン関連エラー**: `pytz` ライブラリの確認
2. **時刻比較エラー**: JST時刻同士の比較になっているか確認
3. **Cloud Function送信エラー**: 時刻情報を送信していないか確認

### 監視ポイント
- JST時刻での正確な時刻表示
- スケジュール投稿の予定通りの実行
- Google SheetsでのJST時刻表示維持

## 📋 ベストプラクティス

### 1. タイムゾーン処理の原則
- **入力・表示・保存**: 全てJST時刻で統一
- **比較処理**: 同一タイムゾーン同士で実行
- **外部API**: 必要時のみUTC変換

### 2. コードレビューチェックポイント
```python
# ❌ 避けるべきパターン
datetime.now()  # タイムゾーン不明

# ✅ 推奨パターン
datetime.now(JST)  # 明確なJST時刻
```

### 3. データベース設計指針
- 時刻フィールドは文字列として保存
- タイムゾーン情報を明示的に管理
- 比較クエリは同一タイムゾーンで実行

## 🎉 成功要因

1. **明確な要件定義**: 「JST表示維持、Cloud Function内部UTC処理」
2. **段階的アプローチ**: 問題特定 → 構造分析 → 解決策実装
3. **一貫性重視**: 全システムでJST時刻統一
4. **シンプル設計**: 複雑なタイムゾーン変換を避ける

## 📝 今後の保守・拡張時の注意点

### 新機能追加時
- タイムゾーン処理はJST統一を維持
- 外部API連携時のUTC変換ポイントを明確化
- 時刻比較ロジックの一貫性確保

### 障害対応時
- このログを参照してタイムゾーン関連の調査を実施
- JST/UTC混在が発生していないか確認
- Cloud Function側の時刻処理を検証

---

**📞 緊急時連絡**: このログをもとに技術サポートに連絡
**🔄 更新履歴**: 今後の修正・変更はこのログに追記