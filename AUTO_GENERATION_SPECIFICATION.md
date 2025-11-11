# 投稿案自動生成機能 仕様書

## 📋 概要

**作成日**: 2025年11月11日  
**バージョン**: 1.0  
**機能**: 設定した時刻に自動的にキャスト別の投稿案を生成し、下書きとして保存

---

## 🎯 機能の目的

- キャスト別に毎日決まった時刻に投稿案を自動生成
- 手動での投稿案作成の負担を軽減
- 継続的なコンテンツ供給を実現

---

## ⚙️ システム構成

### 実行環境

| 項目 | 内容 |
|------|------|
| **サーバー** | さくらVPS（153.126.194.114） |
| **メモリ** | 2GB（安定稼働に必須） |
| **OS** | Ubuntu 24.04 LTS |
| **タイムゾーン** | JST（日本標準時） |
| **Python** | 3.x（仮想環境: `.venv`） |

### 実行スクリプト

| ファイル | 役割 |
|----------|------|
| `auto_generation_batch.py` | 自動生成バッチ処理のメインスクリプト |
| `app.py` | データベース操作関数（`execute_query`）を提供 |
| `.auto_generation_last_run` | 最終実行日を記録（YYYY-MM-DD形式） |
| `.auto_generation.lock` | 重複実行防止用ロックファイル |

### データベーステーブル

#### `auto_generation_settings`
```sql
CREATE TABLE auto_generation_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cast_id INTEGER NOT NULL UNIQUE,
    enabled INTEGER DEFAULT 0,           -- 有効/無効フラグ（0/1）
    generation_time TEXT,                -- 生成時刻（HH:MM形式、例: "15:00"）
    posts_per_day INTEGER DEFAULT 10,   -- 1日の生成件数（通常3件）
    last_generated_at DATETIME,          -- 最終生成日時
    total_generated INTEGER DEFAULT 0,   -- 累計生成数
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cast_id) REFERENCES casts(id) ON DELETE CASCADE
);
```

---

## 🔄 動作フロー

### 1. cron実行（5分間隔）

```bash
# cronによる定期実行（5分ごと）
*/5 * * * * cd /home/ubuntu/aicast-app && \
    /home/ubuntu/aicast-app/.venv/bin/python3 auto_generation_batch.py \
    >> auto_generation.log 2>&1
```

### 2. 実行判定ロジック

```
┌─────────────────────────────────────┐
│ cronが5分ごとに実行                  │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ ロックファイル確認                   │
│ (.auto_generation.lock)             │
│ - 既に実行中？ → スキップ            │
│ - 空き？ → ロック取得して続行        │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 現在時刻取得（JST）                  │
│ 例: 2025-11-11 15:03:00             │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 実行対象の設定を取得                 │
│ WHERE enabled = 1                   │
│   AND generation_time <= '15:03'    │
│   AND (last_generated_at IS NULL    │
│        OR DATE(last_generated_at)   │
│           < DATE('2025-11-11'))     │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 各キャストについて投稿案を生成       │
│ - サンプル投稿をランダム選択         │
│ - Gemini 2.5 Flashで生成            │
│ - 140文字以内に調整                 │
│ - DBに下書きとして保存              │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 最終実行日を記録                     │
│ .auto_generation_last_run           │
│ → 2025-11-11                        │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ ロック解放                           │
└─────────────────────────────────────┘
```

### 3. 1日1回実行の制御

**重複防止メカニズム**:
1. **ファイルベースフラグ**: `.auto_generation_last_run`に実行日（YYYY-MM-DD）を記録
2. **DB条件**: `last_generated_at`が今日でない場合のみ実行
3. **時刻条件**: `generation_time <= 現在時刻`の設定のみ対象

**例**:
- 設定時刻: `15:00`
- 初回実行: `15:00`の直後（例: 15:00, 15:05, 15:10のいずれか）
- 以降: その日は何度cronが動いてもスキップ
- 翌日: 再び15:00以降に1回実行

---

## 🤖 AI生成仕様

### 使用モデル

- **モデル名**: `gemini-2.5-flash`
- **プロバイダー**: Google Cloud Vertex AI
- **リージョン**: `us-central1`
- **認証**: サービスアカウントキー

### プロンプト構成

```python
prompt = f"""
あなたは「{cast_name}（{nickname}）」として投稿します。

以下のサンプル投稿を参考に、同じトーン・テーマ・文体で新しい投稿を1つ生成してください。

【サンプル投稿】
{sample_posts}

【重要な制約】
- 140文字以内
- サンプルと同じ口調・キャラクター性を保つ
- 絵文字の使用頻度もサンプルに合わせる
- 自然で魅力的な内容

投稿文のみを出力してください（説明不要）。
"""
```

### 生成パラメータ

| パラメータ | 値 | 説明 |
|-----------|---|------|
| `temperature` | 0.9 | 創造性（高め） |
| `max_output_tokens` | 200 | 最大トークン数 |
| `top_p` | 0.95 | 多様性 |

### 生成処理

1. **サンプル投稿取得**: キャストIDに紐づくサンプル投稿をランダムに5件取得
2. **AI生成**: Geminiモデルに送信
3. **文字数チェック**: 140文字を超える場合は再生成（最大3回試行）
4. **DB保存**: `posts`テーブルに`status='draft'`で保存

---

## 🔒 安定性・信頼性の設計

### 1. 重複実行防止（ロックファイル機構）

```python
import fcntl

lock_file = open('.auto_generation.lock', 'w')
try:
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    # バッチ処理実行
except IOError:
    print("⏭️ 別のバッチ処理が実行中です。スキップします。")
    sys.exit(0)
finally:
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    lock_file.close()
```

**効果**:
- cronが5分間隔で実行されても、同時に複数プロセスが動作しない
- メモリ消費を抑制

### 2. Vertex AI初期化の最適化

```python
# グローバル変数で1回のみ初期化
_vertex_ai_initialized = False
_gemini_model = None

def init_vertex_ai():
    global _vertex_ai_initialized, _gemini_model
    
    if _vertex_ai_initialized:
        return _gemini_model  # 既に初期化済み
    
    # 初回のみ実行
    vertexai.init(project=project_id, location="us-central1", credentials=credentials)
    _gemini_model = GenerativeModel("gemini-2.5-flash")
    _vertex_ai_initialized = True
    return _gemini_model
```

**効果**:
- メモリ使用量を削減（毎回初期化しない）
- 処理速度の向上

### 3. メモリ要件

| 環境 | メモリ | 結果 |
|------|--------|------|
| **1GB** | ❌ 不足 | Streamlit（258MB）+ 自動生成（300MB）で限界に達し、頻繁にクラッシュ |
| **2GB** | ✅ 安定 | 使用率42%、余裕1.3GB以上で安定稼働 |

**推奨**: 最低2GB以上のメモリ

---

## 📊 実行ログ

### ログファイル

- **パス**: `/home/ubuntu/aicast-app/auto_generation.log`
- **形式**: 標準出力とエラー出力の両方を記録
- **ローテーション**: 手動（必要に応じて実施）

### ログ例（成功時）

```
============================================================
🚀 投稿案自動生成バッチ実行開始
   実行時刻（JST）: 2025-11-11 15:00:32
============================================================
🕐 現在時刻（JST）: 2025-11-11 15:00:32
🔍 検索する生成時刻: 15:00 以前（今日未実行）
✅ 実行対象: 3件
   - Hiranonorico (平野のリコ) - 設定時刻: 15:00
   - ami_dreamx (AMIちゃん) - 設定時刻: 15:00
   - cute_angel_ten (きゃわてん) - 設定時刻: 15:00

============================================================
🤖 自動生成開始: Hiranonorico（平野のリコ）
   生成件数: 3件
============================================================

📝 投稿案 1/3 を生成中...
✅ 投稿案 1 生成完了: 今日のランチは久しぶりのパスタ🍝...
📝 投稿案 2/3 を生成中...
✅ 投稿案 2 生成完了: 最近ハマってる韓ドラがやばい😭...
📝 投稿案 3/3 を生成中...
✅ 投稿案 3 生成完了: 週末のお出かけどこ行こうかな〜🤔...

============================================================
📊 生成結果: Hiranonorico（平野のリコ）
   成功: 3件
   失敗: 0件
   ステータス: success
============================================================

============================================================
🎉 投稿案自動生成バッチ実行完了
   総成功: 9件
   総失敗: 0件
============================================================
```

### エラーパターンと対処

| エラー | 原因 | 対処法 |
|--------|------|--------|
| `❌ サンプル投稿が見つかりません` | キャストにサンプル投稿が0件 | アプリの「キャスト管理」でサンプル投稿を追加 |
| `❌ Vertex AI初期化エラー` | 認証情報が正しくない | 環境変数`GOOGLE_APPLICATION_CREDENTIALS`を確認 |
| `⏭️ 別のバッチ処理が実行中` | 前回の処理がまだ終わっていない | 正常な挙動（自動的にスキップ） |

---

## 🛠️ 運用・管理

### アプリ内での設定方法

1. **「投稿生成」タブ** → **「自動生成設定」セクション**に移動
2. キャスト一覧から設定を変更したいキャストを選択
3. **設定項目**:
   - **有効/無効**: チェックボックスで切り替え
   - **生成時刻（JST）**: `HH:MM`形式で入力（例: `15:00`）
   - **日次生成数**: 通常は`3`件を推奨
4. **「💾 設定を保存」**ボタンをクリック

### cron設定の確認・変更

```bash
# 現在のcron設定を確認
ssh ubuntu@153.126.194.114 'crontab -l'

# cron設定を編集
ssh ubuntu@153.126.194.114 'crontab -e'
```

**デフォルト設定**:
```bash
# 環境変数
GOOGLE_APPLICATION_CREDENTIALS=/home/ubuntu/aicast-app/credentials/service-account-key.json
GCP_PROJECT=aicast-472807

# 投稿案自動生成（5分間隔）
*/5 * * * * cd /home/ubuntu/aicast-app && \
    /home/ubuntu/aicast-app/.venv/bin/python3 auto_generation_batch.py \
    >> auto_generation.log 2>&1
```

### ログ確認方法

```bash
# 最新50行を表示
ssh ubuntu@153.126.194.114 'tail -50 /home/ubuntu/aicast-app/auto_generation.log'

# リアルタイムで監視
ssh ubuntu@153.126.194.114 'tail -f /home/ubuntu/aicast-app/auto_generation.log'

# エラーのみ抽出
ssh ubuntu@153.126.194.114 'grep "❌" /home/ubuntu/aicast-app/auto_generation.log'
```

### 手動実行（テスト用）

```bash
ssh ubuntu@153.126.194.114 'cd /home/ubuntu/aicast-app && \
    export GOOGLE_APPLICATION_CREDENTIALS=/home/ubuntu/aicast-app/credentials/service-account-key.json && \
    export GCP_PROJECT=aicast-472807 && \
    /home/ubuntu/aicast-app/.venv/bin/python3 auto_generation_batch.py'
```

### トラブルシューティング

#### 1. 自動生成が実行されない

**確認項目**:
1. cronが動作しているか: `systemctl status cron`
2. 設定が有効化されているか: アプリの自動生成設定を確認
3. サンプル投稿が登録されているか: キャスト管理で確認
4. ログにエラーがないか: `auto_generation.log`を確認

#### 2. メモリ不足でクラッシュ

**症状**:
- アプリが頻繁に停止する
- ログに何も出力されない

**対処**:
1. メモリ使用量を確認: `free -h`
2. 2GB未満の場合は2GB以上に増設
3. 不要なプロセスを停止

#### 3. 認証エラー

**症状**:
```
❌ Vertex AI初期化エラー: 503 Getting metadata from plugin failed
```

**対処**:
```bash
# サービスアカウントキーの存在確認
ls -lh /home/ubuntu/aicast-app/credentials/service-account-key.json

# cronの環境変数を確認
crontab -l | grep GOOGLE_APPLICATION_CREDENTIALS
```

---

## 📈 パフォーマンス指標

### 生成速度

| モデル | 1投稿あたりの生成時間 |
|--------|---------------------|
| gemini-2.5-flash | 2〜3秒 |
| gemini-2.0-flash-exp | 1〜2秒（高速） |

### リソース使用量（2GB環境）

| 項目 | 使用量 | 割合 |
|------|--------|------|
| Streamlitアプリ | 338MB | 16.8% |
| 自動生成バッチ（実行中） | 311MB | 15.4% |
| **合計** | **約650MB** | **約32%** |
| **空き** | **約1.3GB** | **約68%** |

---

## 🔐 セキュリティ

### 認証情報の管理

1. **サービスアカウントキー**: `/home/ubuntu/aicast-app/credentials/service-account-key.json`
   - パーミッション: `600`（所有者のみ読み書き）
   - Gitには含めない（`.gitignore`に登録）

2. **環境変数**:
   - `GOOGLE_APPLICATION_CREDENTIALS`: サービスアカウントキーのパス
   - `GCP_PROJECT`: Google CloudプロジェクトID

### アクセス制限

- VPSへのSSHアクセスは公開鍵認証
- Streamlitアプリは認証システムで保護
- Vertex AI APIは特定のプロジェクトからのみアクセス可能

---

## 📝 変更履歴

| 日付 | バージョン | 変更内容 | コミットID |
|------|-----------|---------|-----------|
| 2025-11-11 | 1.0 | 初回リリース | 943db66a |
| 2025-11-11 | 1.0.1 | ロックファイル機構追加 | 603b6d70 |
| 2025-11-11 | 1.0.2 | Vertex AI初期化最適化 | 943db66a |

---

## 🎯 今後の拡張予定

### Phase 2（検討中）

- [ ] 生成時刻の複数設定（1日2回など）
- [ ] カテゴリ別の生成数設定
- [ ] 生成品質の自動評価
- [ ] 失敗時のリトライ機能
- [ ] Slack/メール通知機能

### Phase 3（将来構想）

- [ ] 曜日別の生成設定
- [ ] トレンドを考慮した投稿生成
- [ ] 自動承認機能（高品質投稿のみ）
- [ ] A/Bテストによるプロンプト最適化

---

## 📚 関連ドキュメント

- [FEATURE_UPDATES_2025_10_07.md](./FEATURE_UPDATES_2025_10_07.md) - 機能追加・改修履歴
- [README_SAKURA_VPS.md](./README_SAKURA_VPS.md) - VPS運用ガイド
- [copilot-instructions.md](./.github/copilot-instructions.md) - Copilot開発ガイドライン
- [auto_generation_batch.py](./auto_generation_batch.py) - バッチ処理スクリプト

---

**最終更新**: 2025年11月11日  
**文書バージョン**: 1.0  
**管理者**: AIcast Room 開発チーム
