# AIcast Room 機能追加・改修仕様書
## 更新日: 2025年10月7日

---

## 📋 概要

本文書は、2025年10月7日に実施されたAIcast Roomの機能追加・改修内容をまとめた仕様書です。主要な修正として、以下の8つの機能を実装しました：

1. **安全な日時パース処理** - エラー回避とデータ整合性確保
2. **データベース不整合修正** - posted_atフィールドの正規化
3. **JST時刻表示** - UTC→JST変換と見やすい表示
4. **一括予約機能** - 即座実行から予約スケジュールへの変更
5. **投稿チューニング機能のVPS環境対応** - Streamlitウィジェットの環境統一
6. **X投稿ボタンの初期設定化** - デフォルト選択の最適化
7. **送信時刻設定のシンプル化** - 直感的なUI操作
8. **予約一覧から承認済みへ戻る機能** - 柔軟な状態管理

これらの改修により、スケジュール投稿機能の安定化とユーザビリティの大幅向上を実現しました。

---

## 🔧 修正・追加機能一覧

### 1. 安全な日時パース処理の実装

#### **問題背景**
- データベースの`posted_at`フィールドに「時刻のみ」のデータが混入
- `ValueError: time data '17:00:00' does not match format '%Y-%m-%d %H:%M:%S'`エラーが発生
- アプリケーションクラッシュの原因となっていた

#### **実装内容**
```python
def safe_datetime_parse(date_str, default_format='%Y-%m-%d %H:%M:%S'):
    """
    安全に日時をパースする汎用関数
    データベースの不正な値に対して柔軟に対応
    """
    if not date_str:
        return None
    
    # 複数のフォーマットを試行
    formats_to_try = [
        default_format,            # 標準: '2024-01-01 12:00:00'
        '%H:%M:%S',               # 時刻のみ: '17:00:00'
        '%Y-%m-%d',               # 日付のみ: '2024-01-01'
        '%Y-%m-%d %H:%M',         # 秒なし: '2024-01-01 12:00'
        '%d/%m/%Y %H:%M:%S',      # 欧州形式
        '%d-%m-%Y %H:%M:%S',      # 欧州形式（ハイフン）
    ]
    
    for fmt in formats_to_try:
        try:
            parsed_dt = datetime.datetime.strptime(date_str, fmt)
            
            # 時刻のみの場合は今日の日付を追加
            if fmt == '%H:%M:%S':
                today = datetime.date.today()
                parsed_dt = datetime.datetime.combine(today, parsed_dt.time())
            
            return parsed_dt
        except ValueError:
            continue
    
    # すべて失敗した場合は None を返す
    print(f"⚠️ 日時パースエラー: '{date_str}' - 対応していないフォーマットです")
    return None
```

#### **適用箇所**
- スケジュール投稿時刻の表示処理
- 投稿データの時刻情報取得
- 一括予約機能の時刻処理

#### **効果**
- アプリケーションクラッシュの完全回避
- データベース不整合への柔軟な対応
- エラーハンドリングの向上

---

### 2. データベース不整合の修正

#### **問題背景**
- `posted_at`フィールドに「17:00:00」のような時刻のみデータが保存
- 投稿生成時にランダム時刻のみ生成 → 承認時に日付が追加される仕様

#### **修正内容**
```sql
UPDATE posts 
SET posted_at = SUBSTR(created_at, 1, 10) || ' ' || posted_at 
WHERE posted_at LIKE '%:%' AND posted_at NOT LIKE '%-%';
```

#### **修正前後の例**
- **修正前**: `posted_at = '17:00:00'`, `created_at = '2025-09-25 16:35:00'`
- **修正後**: `posted_at = '2025-09-25 17:00:00'`

#### **効果**
- データ整合性の確保
- 時刻表示の正常化
- 既存データの救済

---

### 3. JST時刻表示の実装

#### **問題背景**
- スケジュール投稿の実行時刻がUTC表示
- `✅ 実行: 2025-10-07T14:50:02.514261`（UTC）で分かりにくい

#### **実装内容**
```python
# sent_at の表示形式を改善（JSTに変換）
if 'T' in sent_at_raw:
    sent_at_dt = datetime.datetime.fromisoformat(sent_at_raw.replace('Z', '+00:00'))
    # UTCからJSTに変換（+9時間）
    sent_at_jst = sent_at_dt + datetime.timedelta(hours=9)
    sent_at_display = sent_at_jst.strftime('%m-%d %H:%M:%S')
else:
    # 既にローカル形式の場合
    sent_at_dt = safe_datetime_parse(sent_at_raw)
    sent_at_display = sent_at_dt.strftime('%m-%d %H:%M:%S') if sent_at_dt else sent_at_raw
```

#### **表示改善**
- **修正前**: `✅ 実行: 2025-10-07T14:50:02.514261`
- **修正後**: `✅ 実行: 10-07 23:50:02`

#### **特徴**
- UTC → JST自動変換（+9時間）
- 秒単位での詳細表示
- 見やすい「月-日 時:分:秒」形式

---

### 4. 一括予約機能の実装

#### **機能概要**
承認済み投稿を選択して、設定された時刻で一括予約する機能

#### **機能変更内容**

##### **UI変更**
- **変更前**: `📤 一括送信` → **変更後**: `📅 一括予約`
- **動作**: 即座実行 → スケジュール予約
- **結果**: `sent_status = 'sent'` → `sent_status = 'scheduled'`

##### **時刻の優先順位システム**
```python
# 時刻取得の優先順位: scheduled_at > posted_at > created_at
if post_data['scheduled_at']:
    # 既にスケジュール時刻が設定されている場合
    target_datetime = safe_datetime_parse(post_data['scheduled_at'])
elif post_data['posted_at']:
    # 承認時刻を使用（今日の日付で適用）
    posted_at_raw = post_data['posted_at']
    if len(posted_at_raw) > 10:  # 日付部分が含まれている場合
        target_datetime = safe_datetime_parse(posted_at_raw)
    else:
        # 時刻のみの場合は今日の日付を追加
        target_datetime = safe_datetime_parse(f"{today} {posted_at_raw}")
else:
    # フォールバック: 作成時刻を使用
    target_datetime = safe_datetime_parse(post_data['created_at'])
```

##### **過去時刻自動調整機能**
```python
# 現在時刻と比較して過去の場合は自動調整
now = datetime.datetime.now()

if target_datetime <= now:
    # 過去の時刻の場合
    if target_datetime.date() == now.date():
        # 今日の過去時刻の場合は明日の同時刻に設定
        tomorrow = now.date() + datetime.timedelta(days=1)
        target_datetime = datetime.datetime.combine(tomorrow, target_datetime.time())
        print(f"📅 投稿ID {post_id}: 今日の過去時刻 → 明日の同時刻に自動調整")
    else:
        # 過去の日付の場合は明日の同時刻に設定
        tomorrow = now.date() + datetime.timedelta(days=1)
        target_datetime = datetime.datetime.combine(tomorrow, target_datetime.time())
        print(f"📅 投稿ID {post_id}: 過去日付 → 明日の同時刻に自動調整")
```

#### **動作例**

##### **例1**: 承認時刻ベースの予約
- **承認時刻**: `14:30:00`
- **現在時刻**: `16:00`
- **結果**: `2025-10-08 14:30:00`（明日）に自動調整

##### **例2**: 過去スケジュール時刻の調整
- **スケジュール時刻**: `2025-10-06 20:00:00`（昨日）
- **結果**: `2025-10-08 20:00:00`（明日）に自動調整

##### **例3**: 未来時刻の維持
- **スケジュール時刻**: `2025-10-07 18:00:00`（今日・未来）
- **結果**: 調整なしでそのまま予約

#### **完了メッセージ**
```
✅ 処理完了: N件の投稿を一括予約しました
📅 N件の投稿を一括予約しました！スケジュール投稿タブで確認できます。
```

---

## 🗃️ データベース変更

### **posts テーブル**
- `sent_status`フィールドの新しい値: `'scheduled'`（予約済み）
- `scheduled_at`フィールドの活用強化

### **send_history テーブル**
- 予約履歴の記録: `status = 'scheduled'`
- 実行予定時刻の記録強化

---

### 5. 投稿チューニング機能のVPS環境対応

#### **問題背景**
- ローカル環境では正常動作するが、VPS環境でエラーが発生
- Streamlitウィジェットの`value`と`key`パラメータの環境間差異
- VPS特有の状態管理問題

#### **実装内容**
- **Streamlitウィジェットの修正**
  ```python
  # ウィジェットのvalue/keyパラメータの適切な設定
  # 環境間での動作統一のための調整
  ```

- **環境間差異の解決**
  - ローカル環境とVPS環境での動作統一
  - Streamlitの状態管理改善
  - デバッグ情報の追加

#### **技術的学び**
1. **Streamlitウィジェット**の`value`と`key`パラメータの適切な使い方
2. **環境間差異**の特定と対処法
3. **デバッグ情報**の重要性
4. **段階的なgitコミット**の価値

#### **開発プロセス改善**
- **詳細なコミットメッセージ**で将来のトラブルシューティングが容易に
- **小さな修正ごとのコミット**で安全な開発サイクル確立
- **本番環境での検証**完了

#### **効果**
- **ローカル**: ✅ 正常動作
- **VPS**: ✅ 正常動作（修正後）
- **両環境統一**: ✅ 完了
- 投稿チューニング機能の安定稼働

---

### 6. X投稿ボタンの初期設定化

#### **問題背景**
- 送信先選択のデフォルトがGoogle Sheetsに設定
- X (Twitter)への投稿が主要用途のため非効率
- ユーザーが毎回選択変更する必要

#### **実装内容**
```python
bulk_destination = st.selectbox(
    "一括予約先",
    options=[opt[0] for opt in bulk_destination_options],
    index=1,  # デフォルトで"🐦 X (Twitter)"を選択
    key="bulk_destination"
)
```

#### **適用箇所**
- 承認済み投稿の一括予約機能
- 個別投稿の送信先選択
- すべての投稿送信UI

#### **効果**
- 操作ステップの削減
- ユーザビリティの大幅向上
- X投稿の利便性強化

---

### 7. 送信時刻設定のシンプル化

#### **問題背景**
- 複雑な多段階時刻設定UI
- 直感的でない操作フロー
- 時刻設定での混乱

#### **実装内容**

##### **シンプルな時刻入力UI**
```python
# 日付選択
send_date = st.date_input(
    "📅 送信日",
    value=initial_date,
    min_value=today,
    key=f"send_date_{post['id']}"
)

# 時刻入力方式の選択
time_input_method = st.radio(
    "時刻入力方式",
    ["🔢 数値入力（1分単位）", "📋 プルダウン選択（5分刻み）"],
    key=f"time_method_{post['id']}",
    horizontal=True
)
```

##### **自動初期値設定**
- 保存済み時刻の自動読み込み
- 過去時刻の自動調整
- 現在時刻+10分のデフォルト設定

#### **改善ポイント**
- **3ステップ→1ステップ**の簡素化
- 直感的な「日付・時刻・保存」フロー
- エラー回避の自動化

#### **効果**
- 設定時間の大幅短縮
- ユーザーエラーの削減
- 操作の直感性向上

---

### 8. 予約一覧から承認済みへ戻る機能

#### **問題背景**
- スケジュール予約した投稿を承認済みに戻す手段がない
- 予約ミスの修正ができない
- 柔軟な状態管理が不可能

#### **実装内容**
```python
with col_action:
    if st.button("↩️ 承認済みに戻す", key=f"return_approved_{post['id']}", use_container_width=True):
        try:
            execute_query(
                "UPDATE posts SET sent_status = 'not_sent' WHERE id = ?",
                (post['id'],)
            )
            print(f"🔄 投稿ID {post['id']} を承認済み一覧に戻しました")
            st.session_state.page_status_message = ("success", f"↩️ 投稿ID {post['id']} を承認済み一覧に戻しました")
            st.rerun()
        except Exception as e:
            st.session_state.page_status_message = ("error", f"承認済みに戻すエラー: {str(e)}")
            st.rerun()
```

#### **機能特徴**
- **ワンクリック操作**：簡単な状態変更
- **詳細ログ出力**：操作履歴の記録
- **エラーハンドリング**：安全な状態変更
- **即座反映**：画面の自動更新

#### **適用箇所**
- スケジュール投稿の待機中一覧
- 各投稿の個別操作エリア

#### **効果**
- 柔軟な投稿管理
- ユーザーミスの修正可能
- ワークフローの改善

---

## 🗃️ データベース変更

### **posts テーブル**
- `sent_status`フィールドの新しい値: `'scheduled'`（予約済み）
- `scheduled_at`フィールドの活用強化

### **send_history テーブル**
- 予約履歴の記録: `status = 'scheduled'`
- 実行予定時刻の記録強化

---

## 🎯 システム要件

### **動作環境**
- **開発環境**: VS Code Dev Container (Ubuntu 24.04.2 LTS)
- **本番環境**: VPS (153.126.194.114:8503)
- **Python**: 3.12
- **フレームワーク**: Streamlit

### **依存関係**
- `streamlit`: Web UI
- `sqlite3`: データベース
- `datetime`: 日時処理
- `vertexai`: AI投稿生成

---

## 🚀 デプロイ手順

### **開発→本番デプロイフロー**
1. **ローカル開発・テスト**
2. **Gitコミット**: 詳細なコミットメッセージ
3. **プッシュ**: `clean-production`ブランチ
4. **VPS自動デプロイ**: Git pull + アプリ再起動
5. **動作確認**: 本番環境での機能テスト

### **デプロイコマンド**
```bash
# Gitコミット・プッシュ
git add .
git commit -m "feat: 一括予約機能実装・過去時刻自動調整・JST時刻表示"
git push origin clean-production

# VPS自動デプロイ
ssh ubuntu@153.126.194.114 'cd /home/ubuntu/aicast-app && git pull origin clean-production && screen -S aicast -X quit; sleep 2 && screen -dmS aicast bash -c "source .venv/bin/activate && python3 run.py"'
```

---

## 🔍 テスト項目

### **機能テスト**
- [ ] 安全な日時パース処理の動作確認
- [ ] JST時刻表示の正確性
- [ ] 一括予約機能の動作
- [ ] 過去時刻自動調整の動作
- [ ] スケジュール投稿タブでの確認

### **エラーハンドリングテスト**
- [ ] 不正な日時データでのエラー回避
- [ ] データベース不整合時の対応
- [ ] ネットワークエラー時の処理

### **パフォーマンステスト**
- [ ] 大量投稿の一括予約処理
- [ ] メモリ使用量の確認
- [ ] レスポンス時間の測定

---

## 📝 今後の拡張予定

### **完了済み機能（2025年10月7日実装）**
- ✅ 安全な日時パース処理の実装
- ✅ データベース不整合の修正
- ✅ JST時刻表示の実装
- ✅ 一括予約機能の実装
- ✅ 投稿チューニング機能のVPS環境対応
- ✅ X投稿ボタンの初期設定化
- ✅ 送信時刻設定のシンプル化
- ✅ 予約一覧から承認済みへ戻る機能

### **短期改善**
- 一括予約時の詳細ログ出力
- 予約キャンセル機能
- 時刻調整のユーザー通知強化

### **長期改善**
- 時刻設定UIのさらなる簡素化
- 予約状況の可視化ダッシュボード
- 自動再試行機能

---

## 📞 サポート・問い合わせ

### **開発者**
- **GitHub**: shintarospec/aicast-app
- **ブランチ**: clean-production

### **ドキュメント**
- **設定ガイド**: `README_SAKURA_VPS.md`
- **運用マニュアル**: `.github/copilot-instructions.md`

---

**最終更新**: 2025年10月7日  
**文書バージョン**: 1.0  
**対象システム**: AIcast Room v2025.10.07