# AIcast Room 運用者向け完全マニュアル

**バージョン**: 2.0  
**最終更新**: 2025年11月16日  
**対象**: システム運用者・管理者

---

## 📋 目次

1. [システム概要](#システム概要)
2. [アクセス情報](#アクセス情報)
3. [日常運用タスク](#日常運用タスク)
4. [キャスト管理](#キャスト管理)
5. [投稿管理](#投稿管理)
6. [自動生成機能](#自動生成機能)
7. [トラブルシューティング](#トラブルシューティング)
8. [定期メンテナンス](#定期メンテナンス)
9. [緊急時対応](#緊急時対応)
10. [参考資料](#参考資料)

---

## システム概要

### AIcast Roomとは

AIcast Roomは、複数のキャラクター（キャスト）を管理し、それぞれの個性に基づいたSNS投稿を自動生成・予約投稿するシステムです。

**主要機能**:
- 🎭 **キャスト管理**: 複数のキャラクターペルソナを一元管理
- 🤖 **AI投稿生成**: Google Vertex AI（Gemini）による自然な投稿文生成
- ⏰ **自動生成**: 毎日決まった時刻に自動で投稿案を生成
- 📅 **スケジュール投稿**: 日時を指定して予約投稿
- 🔄 **リツイート管理**: 引用ツイートの自動生成・予約
- 📊 **投稿管理**: 下書き→承認→予約→送信のワークフロー

### システム構成

```
┌─────────────────────────────────────────────┐
│ Streamlit UI (Web アプリケーション)          │
│ http://153.126.194.114:8503                 │
└─────────────┬───────────────────────────────┘
              │
┌─────────────┴───────────────────────────────┐
│ さくらVPS (Ubuntu 24.04 LTS)                │
│ IP: 153.126.194.114                         │
│ メモリ: 2GB / ディスク: 50GB                │
├─────────────────────────────────────────────┤
│ - Python 3.x (.venv仮想環境)               │
│ - SQLite データベース (casting_office.db)  │
│ - cron (自動生成バッチ実行)                 │
│ - screen (Streamlit常駐化)                  │
└─────────────┬───────────────────────────────┘
              │
┌─────────────┴───────────────────────────────┐
│ 外部連携                                     │
├─────────────────────────────────────────────┤
│ - Google Vertex AI (Gemini) - 投稿生成     │
│ - X API (Twitter) - 投稿実行                │
│ - Google Sheets API - レガシー送信         │
└─────────────────────────────────────────────┘
```

---

## アクセス情報

### Webアプリケーション

| 項目 | 内容 |
|------|------|
| **URL** | http://153.126.194.114:8503 |
| **ブラウザ** | Chrome / Edge / Safari 推奨 |
| **認証** | なし（VPN経由推奨） |
| **推奨画面サイズ** | 1920x1080以上 |

### サーバー（VPS）

| 項目 | 内容 |
|------|------|
| **ホスト** | 153.126.194.114 |
| **ユーザー** | ubuntu |
| **SSH接続** | `ssh ubuntu@153.126.194.114` |
| **アプリパス** | `/home/ubuntu/aicast-app` |
| **仮想環境** | `/home/ubuntu/aicast-app/.venv` |

### データベース

| 項目 | 内容 |
|------|------|
| **ファイルパス** | `/home/ubuntu/aicast-app/casting_office.db` |
| **種類** | SQLite 3 |
| **アクセス** | `sqlite3 casting_office.db` |
| **バックアップ先** | Google Drive自動同期 |

---

## 日常運用タスク

### 毎日実施すべき作業

#### 1. 投稿案の確認・承認（所要時間: 10-15分）

**手順**:
1. Webアプリにアクセス
2. サイドバーでキャストを選択
3. 「📬 投稿管理」→「📝 投稿案（下書き）」タブを開く
4. 自動生成された投稿案を確認
5. 問題なければ「✅ 選択した投稿を一括承認」をクリック

**確認ポイント**:
- [ ] キャラクター設定との整合性
- [ ] 文章の自然さ
- [ ] 不適切な表現の有無
- [ ] 誤字脱字のチェック

#### 2. 予約投稿の設定（所要時間: 5-10分）

**手順**:
1. 「📬 投稿管理」→「✅ 承認済み」タブを開く
2. 送信日・送信時刻を設定（テーブル上で直接編集可能）
3. 「💾 時刻変更を保存」をクリック
4. 不要な投稿は「選択」列のチェックを外す
5. 「📅 選択した投稿を予約」をクリック

**推奨設定**:
- 投稿間隔: 最低4時間以上空ける
- 投稿時間帯: 7:00-23:00（深夜避ける）
- 1日あたり: 3-5投稿程度

#### 3. システム稼働確認（所要時間: 2-3分）

**確認項目**:
```bash
# SSH接続して以下を確認
ssh ubuntu@153.126.194.114

# 1. アプリが起動しているか
screen -ls
# → aicast セッションが存在すること

# 2. 自動生成バッチが動いているか
tail -20 auto_generation.log
# → エラーがないこと

# 3. ディスク容量
df -h
# → 使用率が80%未満であること
```

### 週次タスク

#### 月曜日: 週間スケジュール確認

**手順**:
1. 各キャストの予約投稿数を確認
2. 不足している場合は手動で投稿案を生成
3. 特別イベント（祝日・季節イベント）の投稿を追加

**確認クエリ**:
```sql
-- キャスト別の予約済み投稿数を確認
SELECT c.name, c.nickname, COUNT(p.id) as scheduled_count
FROM casts c
LEFT JOIN posts p ON c.id = p.cast_id 
WHERE p.sent_status = 'scheduled' AND p.posted_at >= date('now')
GROUP BY c.id, c.name, c.nickname
ORDER BY c.name;
```

#### 金曜日: ログ確認とクリーンアップ

**手順**:
```bash
# 1. ログファイルサイズ確認
ls -lh *.log

# 2. 古いログをアーカイブ（1ヶ月以上前）
find . -name "*.log" -mtime +30 -exec gzip {} \;

# 3. データベース最適化
sqlite3 casting_office.db "VACUUM;"
```

### 月次タスク

#### 月初: パフォーマンスレビュー

**確認項目**:
1. 総投稿数・エンゲージメント率
2. AIコスト（Vertex AI使用量）
3. エラー発生率
4. ディスク使用量推移

**レポート生成クエリ**:
```sql
-- 先月の投稿統計
SELECT 
    c.name,
    COUNT(p.id) as total_posts,
    COUNT(CASE WHEN p.status = 'sent' THEN 1 END) as sent_posts,
    COUNT(CASE WHEN p.status = 'rejected' THEN 1 END) as rejected_posts
FROM casts c
LEFT JOIN posts p ON c.id = p.cast_id
WHERE p.created_at >= date('now', 'start of month', '-1 month')
  AND p.created_at < date('now', 'start of month')
GROUP BY c.id, c.name;
```

---

## キャスト管理

### 新規キャストの追加

#### 方法1: CSV一括インポート（推奨）

**手順**:
1. CSVテンプレートをダウンロード
   - 「👤 キャスト管理」→「📥 CSV管理」→「インポート」タブ
   - フォーマット説明を確認
2. CSVファイルを作成
   - 必須項目: `name`（ユーザー名）
   - 推奨項目: `nickname`, `age`, `personality`, `occupation`
3. ファイルをアップロード
4. 「💾 インポート実行」をクリック

**CSVフォーマット例**:
```csv
name,nickname,age,personality,occupation,hobby
tanaka_ai,タナカアイ,25,明るく前向き,Webデザイナー,カフェ巡り
yamada_tech,ヤマダ,30,論理的,エンジニア,プログラミング
```

**自動設定される項目**:
- `auto_generation_settings`: 自動的に初期化される
  - `enabled=1`（自動生成有効）
  - `auto_approve=2`（完全自動: 生成→承認→予約）
  - `posts_per_day=3`（1日3件生成）
  - `generation_time=09:00`（午前9時に生成）

#### インポート後の確認

**確認クエリ**:
```sql
-- 最新キャストの設定確認
SELECT 
    c.id, c.name, c.nickname,
    ags.enabled, ags.auto_approve, ags.posts_per_day, ags.generation_time
FROM casts c
LEFT JOIN auto_generation_settings ags ON c.id = ags.cast_id
ORDER BY c.id DESC
LIMIT 5;
```

**期待される結果**:
```
104|new_cast|ニューキャスト|1|2|3|09:00
```

### キャスト情報の編集

**手順**:
1. 「👤 キャスト管理」→「✏️ 編集」タブ
2. サイドバーでキャストを選択
3. 各項目を編集:
   - **ペルソナ**: 基本情報・詳細ペルソナ・キャラクター設定
   - **運営指針**: mission, persona_design, content_strategy
   - **サンプルプロフィール**: X（Twitter）プロフィール文
   - **X API認証**: API Key, Access Token等
4. 「💾 保存」をクリック

**重要フィールド**:
- `name`: X（Twitter）のユーザー名（@なし）
- `nickname`: 表示名
- `personality`: 性格設定（投稿生成に影響）
- `occupation`: 職業（投稿トピックに影響）
- `first_person`: 一人称（「私」「僕」「俺」など）
- `speech_style`: 話し方の特徴

### キャストの削除

**手順**:
1. 「👤 キャスト管理」→「✏️ 編集」タブ
2. サイドバーで削除対象キャストを選択
3. ページ下部の「🗑️ 削除」ボタンをクリック
4. 確認ダイアログで「OK」

**注意**:
- 削除すると関連データも全て削除されます（投稿・予約・サンプル等）
- **復元不可能**なので、事前にエクスポートを推奨

### キャストのバックアップ

**手順**:
```bash
# SSH接続
ssh ubuntu@153.126.194.114
cd /home/ubuntu/aicast-app

# 特定キャストのデータをエクスポート
sqlite3 casting_office.db <<EOF
.mode csv
.output backup_cast_95_$(date +%Y%m%d).csv
SELECT * FROM casts WHERE id = 95;
.output stdout
EOF

# 関連データも含めてバックアップ
sqlite3 casting_office.db <<EOF
.output backup_full_cast_95_$(date +%Y%m%d).sql
.dump casts WHERE id = 95
.dump posts WHERE cast_id = 95
.dump auto_generation_settings WHERE cast_id = 95
.output stdout
EOF
```

---

## 投稿管理

### 投稿ワークフロー

```
┌──────────────┐
│ 下書き作成    │ ← 自動生成 or 手動作成
│ (draft)      │
└──────┬───────┘
       │
       ↓ 内容確認・編集
┌──────────────┐
│ 承認          │ ← 一括承認 or 個別承認
│ (approved)   │
└──────┬───────┘
       │
       ↓ 日時設定
┌──────────────┐
│ 予約          │ ← sent_status='scheduled'
│ (scheduled)  │
└──────┬───────┘
       │
       ↓ スケジュール実行（cronまたは手動）
┌──────────────┐
│ 送信完了      │
│ (sent)       │
└──────────────┘
```

### 下書きの管理

#### 手動での投稿案作成

**手順**:
1. 「📬 投稿管理」→「🎨 投稿案生成」タブ
2. サイドバーでキャストを選択
3. 生成方法を選択:
   - **シチュエーション選択**: プリセットから選ぶ
   - **カスタム指示**: 自由記述
4. 文字数制限を設定（デフォルト140文字）
5. 「✨ 投稿案を生成」をクリック

**シチュエーション例**:
- 朝の挨拶
- 日常の気づき
- 仕事の合間
- 趣味について
- 夜の振り返り

#### 下書きの編集

**手順**:
1. 「📬 投稿管理」→「📝 投稿案（下書き）」タブ
2. 編集したい投稿の「✏️ 編集」をクリック
3. テキストエリアで内容を修正
4. 「💾 保存」をクリック

**編集のポイント**:
- 文字数制限: X（Twitter）は280文字まで
- ハッシュタグ: 多用しすぎない（2-3個まで）
- メンション: スパム防止のため控えめに
- 絵文字: キャラクター性に合わせて

### 承認処理

#### 一括承認

**手順**:
1. 「📬 投稿管理」→「📝 投稿案（下書き）」タブ
2. 承認したい投稿にチェック
3. 「✅ 選択した投稿を一括承認」をクリック

**効率化のコツ**:
- キャスト別に確認すると効率的
- 1日分（3-5件）をまとめて承認
- NGワードチェック機能の活用

#### 個別承認

**手順**:
1. 投稿カードの「✅ 承認」ボタンをクリック

**使い分け**:
- 一括承認: 定常的な投稿
- 個別承認: 特別な投稿・慎重を要する投稿

### 予約投稿の設定

#### テーブル形式での一括設定（推奨）

**手順**:
1. 「📬 投稿管理」→「✅ 承認済み」タブ
2. テーブルで直接編集:
   - **送信日**: カレンダーから選択
   - **送信時刻**: プルダウンから選択（30分刻み）
3. 複数の投稿を一度に編集可能
4. 「💾 時刻変更を保存」をクリック
5. 不要な投稿は「選択」列のチェックを外す
6. 「📅 選択した投稿を予約」をクリック

**テーブルUI仕様**（2025年11月8日リニューアル）:
- インライン編集可能（DateColumn, TimeColumn）
- 選択状態は`st.session_state.approved_selections`で永続化
- 保存後も選択状態を維持
- 予約実行後は該当IDを自動削除
- 行追加・削除は不可（`num_rows="fixed"`）

**注意事項**:
- 過去の日時は設定不可
- 同一時刻への複数予約は避ける
- 予約後は「📅 予約一覧」タブで確認

#### 予約の確認

**手順**:
1. 「📬 投稿管理」→「📅 予約一覧」タブ
2. キャスト別・日時別に予約を確認

**確認項目**:
- [ ] 送信日時が正しいか
- [ ] 投稿内容に問題ないか
- [ ] 同じ時間帯に集中していないか

### 送信済み投稿の確認

**手順**:
1. 「📬 投稿管理」→「📨 送信済み」タブ
2. 送信履歴を確認
3. エラーがあれば「詳細」で確認

**エラー対応**:
- **X API認証エラー**: X API設定を確認
- **Rate Limit**: 送信間隔を空ける
- **重複投稿エラー**: 既に送信済みの可能性

---

## 自動生成機能

### 自動生成の仕組み

**実行タイミング**:
- cron: 5分間隔で`auto_generation_batch.py`を実行
- 各キャストの`generation_time`に達したら生成開始
- 1日1回のみ実行（`last_generated_at`で管理）

**処理フロー**:
```
┌─────────────────────────────────────┐
│ cron (*/5 * * * *)                  │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ ロックファイル確認                   │
│ (.auto_generation.lock)             │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 実行対象の設定を取得                 │
│ WHERE enabled = 1                   │
│   AND generation_time <= 現在時刻    │
│   AND 今日未実行                     │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 各キャストについて投稿案を生成       │
│ posts_per_day 件分                  │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ auto_approve 設定に応じて処理        │
│ 0: 下書きのみ                        │
│ 1: 承認まで                          │
│ 2: 予約まで（完全自動）              │
└─────────────────────────────────────┘
```

### 自動生成設定の確認・変更

**GUI操作**:
1. 「👤 キャスト管理」→「🤖 自動生成設定」タブ
2. サイドバーでキャストを選択
3. 設定を変更:
   - **有効/無効**: 自動生成のON/OFF
   - **生成時刻**: 毎日の生成時刻（HH:MM形式）
   - **1日の生成件数**: posts_per_day（推奨: 3-5件）
   - **自動承認レベル**: auto_approve（0/1/2）
4. 「💾 設定を保存」をクリック

**auto_approveの設定値**:

| 値 | 動作 | 用途 |
|----|------|------|
| `0` | 下書きのみ生成 | 全件手動確認したい場合 |
| `1` | 承認まで自動 | 予約は手動で行いたい場合 |
| `2` | **予約まで完全自動** | 完全自動化（推奨） |

**推奨設定**:
```
enabled: 1（有効）
auto_approve: 2（完全自動）
posts_per_day: 3
generation_time: 09:00
```

### 自動生成のデバッグ

**ログ確認**:
```bash
# SSH接続
ssh ubuntu@153.126.194.114
cd /home/ubuntu/aicast-app

# 最新の自動生成ログを確認
tail -50 auto_generation.log

# 特定キャストのログをフィルタ
grep "cast_id=95" auto_generation.log | tail -20

# エラーのみ抽出
grep -i "error\|failed\|exception" auto_generation.log | tail -20
```

**よくあるエラーと対処**:

| エラーメッセージ | 原因 | 対処法 |
|-----------------|------|--------|
| `Vertex AI authentication failed` | Google Cloud認証エラー | `gcloud auth application-default login` |
| `No such table: auto_generation_settings` | テーブル未作成 | DBマイグレーション実行 |
| `Lock file exists` | 前回の実行が残っている | `.auto_generation.lock`を削除 |
| `Memory error` | メモリ不足 | VPSを再起動 |

### 手動での生成バッチ実行

**テスト実行**:
```bash
# SSH接続
ssh ubuntu@153.126.194.114
cd /home/ubuntu/aicast-app

# 仮想環境をアクティベート
source .venv/bin/activate

# バッチを手動実行
python3 auto_generation_batch.py

# 実行結果を確認
tail -30 auto_generation.log
```

**特定キャストのみ生成**:
```python
# カスタムスクリプト作成
cat > manual_generate.py <<'EOF'
import sys
sys.path.append('/home/ubuntu/aicast-app')
from app import execute_query, generate_post_with_ai

cast_id = 95  # 対象キャストID
posts_count = 3  # 生成件数

for i in range(posts_count):
    content = generate_post_with_ai(cast_id, situation="日常の気づき")
    execute_query(
        "INSERT INTO posts (cast_id, content, status) VALUES (?, ?, ?)",
        (cast_id, content, 'draft')
    )
    print(f"投稿 {i+1}/{posts_count} 生成完了")
EOF

python3 manual_generate.py
```

---

## トラブルシューティング

### アプリが起動しない

**症状**:
- Webページにアクセスできない
- `Connection refused`エラー

**確認手順**:
```bash
# 1. SSH接続
ssh ubuntu@153.126.194.114

# 2. screenセッション確認
screen -ls
# → aicast セッションが存在しない場合は停止している

# 3. プロセス確認
ps aux | grep streamlit
# → プロセスが存在しない場合は停止している

# 4. ポート確認
netstat -tuln | grep 8501
# → 何も表示されない場合はStreamlitが起動していない
```

**対処法**:
```bash
# 方法1: screenセッションから再起動
screen -S aicast -X quit  # 既存セッション終了
sleep 2
screen -dmS aicast bash -c "cd /home/ubuntu/aicast-app && source .venv/bin/activate && python3 run.py"

# 方法2: 直接再起動（デバッグ用）
cd /home/ubuntu/aicast-app
source .venv/bin/activate
python3 run.py
# → エラーメッセージを確認

# 方法3: 再起動スクリプト使用
./restart-streamlit.sh
```

**ログ確認**:
```bash
# アプリログを確認
cd /home/ubuntu/aicast-app
screen -r aicast
# Ctrl+A → D でデタッチ（終了させない）

# エラーログを確認
tail -50 app.log
```

### 自動生成が動かない

**症状**:
- 設定時刻を過ぎても投稿案が生成されない
- ログに実行記録がない

**確認手順**:
```bash
# 1. cron稼働確認
sudo systemctl status cron
# → active (running) であること

# 2. cronログ確認
sudo grep CRON /var/log/syslog | tail -20

# 3. 自動生成ログ確認
cd /home/ubuntu/aicast-app
tail -50 auto_generation.log

# 4. ロックファイル確認
ls -la .auto_generation.lock
# → 存在する場合は削除
rm -f .auto_generation.lock
```

**設定確認**:
```sql
-- SSH経由でDB確認
ssh ubuntu@153.126.194.114
cd /home/ubuntu/aicast-app
sqlite3 casting_office.db

-- 自動生成設定を確認
SELECT 
    c.id, c.name, c.nickname,
    ags.enabled, ags.auto_approve, ags.posts_per_day,
    ags.generation_time, ags.last_generated_at
FROM casts c
LEFT JOIN auto_generation_settings ags ON c.id = ags.cast_id
WHERE ags.enabled = 1;

-- 期待: enabled=1, generation_time設定済み
```

**手動実行でテスト**:
```bash
cd /home/ubuntu/aicast-app
source .venv/bin/activate
python3 auto_generation_batch.py
tail -30 auto_generation.log
```

### 投稿が送信されない

**症状**:
- 予約した投稿が送信されない
- `sent_status`が`scheduled`のまま

**確認手順**:
```bash
# 1. スケジュール実行cronを確認
crontab -l | grep schedule

# 2. 予約投稿の確認
sqlite3 casting_office.db "SELECT id, cast_id, content, posted_at, sent_status FROM posts WHERE sent_status='scheduled' ORDER BY posted_at LIMIT 10;"

# 3. スケジューラーログ確認
tail -50 schedule.log
```

**X API認証の確認**:
```bash
# X API設定の確認
sqlite3 casting_office.db "SELECT cast_id, x_api_key IS NOT NULL as has_api_key, x_bearer_token IS NOT NULL as has_bearer FROM cast_x_credentials WHERE cast_id = 95;"

# 期待: has_api_key=1, has_bearer=1
```

**手動送信テスト**:
```python
# SSH接続してPythonシェル起動
cd /home/ubuntu/aicast-app
source .venv/bin/activate
python3

# Pythonシェルで実行
>>> from app import execute_query
>>> post = execute_query("SELECT * FROM posts WHERE id = 4100", fetch="one")
>>> print(post['content'])
# → 投稿内容が表示されることを確認
```

### データベースエラー

**症状**:
- `database is locked`エラー
- `no such table`エラー

**対処法**:
```bash
# 1. ロックファイル削除
cd /home/ubuntu/aicast-app
rm -f casting_office.db-journal

# 2. データベース整合性チェック
sqlite3 casting_office.db "PRAGMA integrity_check;"
# → ok が表示されること

# 3. テーブル一覧確認
sqlite3 casting_office.db ".tables"

# 4. 不足しているテーブルがあればマイグレーション実行
# （例: auto_generation_settingsテーブルがない場合）
sqlite3 casting_office.db < migrations/add_auto_generation_settings.sql
```

**バックアップからの復元**:
```bash
# Google Driveバックアップから復元
cd /home/ubuntu/aicast-app
cp casting_office.db casting_office.db.broken
# Google Driveから最新バックアップをダウンロード
# casting_office.db に上書き
```

### メモリ不足

**症状**:
- アプリの動作が遅い
- `MemoryError`発生
- スワップ使用率が高い

**確認**:
```bash
# メモリ使用状況
free -h
# → Availableが200MB以下の場合は危険

# プロセス別メモリ使用量
ps aux --sort=-%mem | head -10
```

**対処法**:
```bash
# 1. 不要なプロセス終了
sudo systemctl stop apache2  # 不要なサービスがあれば停止

# 2. Streamlit再起動
screen -S aicast -X quit
sleep 5
screen -dmS aicast bash -c "cd /home/ubuntu/aicast-app && source .venv/bin/activate && python3 run.py"

# 3. それでも解決しない場合はVPS再起動
sudo reboot
# → 再起動後、Streamlitを手動起動
```

### 認証エラー

#### Google Cloud認証エラー

**症状**:
```
google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials
```

**対処法**:
```bash
# サービスアカウントキーを確認
ls -la /home/ubuntu/aicast-app/credentials/service-account-key.json

# 環境変数を設定
export GOOGLE_APPLICATION_CREDENTIALS=/home/ubuntu/aicast-app/credentials/service-account-key.json

# 認証テスト
cd /home/ubuntu/aicast-app
source .venv/bin/activate
python3 test_vertex_vps.py
```

#### X API認証エラー

**症状**:
```
401 Unauthorized
403 Forbidden
```

**対処法**:
```bash
# X API設定を確認
cd /home/ubuntu/aicast-app
sqlite3 casting_office.db

SELECT cast_id, x_api_key, x_bearer_token 
FROM cast_x_credentials 
WHERE cast_id = 95;

-- トークンが空の場合は再設定が必要
-- GUIから「👤 キャスト管理」→「X API認証」で設定
```

---

## 定期メンテナンス

### 日次メンテナンス（自動化推奨）

**ログローテーション**:
```bash
# cron設定（毎日午前3時）
0 3 * * * cd /home/ubuntu/aicast-app && find . -name "*.log" -size +100M -exec gzip {} \;
```

**ディスク使用量確認**:
```bash
# cron設定（毎日午前4時）
0 4 * * * df -h | grep -v tmpfs > /home/ubuntu/disk_usage.log
```

### 週次メンテナンス

**データベース最適化**:
```bash
# 毎週日曜日午前2時
0 2 * * 0 cd /home/ubuntu/aicast-app && sqlite3 casting_office.db "VACUUM; ANALYZE;"
```

**古いデータのアーカイブ**:
```sql
-- 3ヶ月以上前の送信済み投稿を削除
DELETE FROM posts 
WHERE status = 'sent' 
  AND sent_at < datetime('now', '-3 months');

-- 削除前にバックアップ推奨
```

### 月次メンテナンス

**バックアップの確認**:
```bash
# Google Driveバックアップを確認
# 手動でダウンロードしてローカル保存推奨
```

**パフォーマンス分析**:
```sql
-- 月次レポート生成
SELECT 
    strftime('%Y-%m', created_at) as month,
    COUNT(*) as total_posts,
    COUNT(CASE WHEN status='sent' THEN 1 END) as sent,
    COUNT(CASE WHEN status='rejected' THEN 1 END) as rejected,
    ROUND(AVG(LENGTH(content)), 1) as avg_length
FROM posts
GROUP BY strftime('%Y-%m', created_at)
ORDER BY month DESC
LIMIT 12;
```

**セキュリティアップデート**:
```bash
# VPSのパッケージ更新
sudo apt update
sudo apt upgrade -y

# Python依存関係の更新（慎重に）
cd /home/ubuntu/aicast-app
source .venv/bin/activate
pip list --outdated
# 必要に応じて個別更新
```

---

## 緊急時対応

### システム全体停止

**対応手順**:
```bash
# 1. SSH接続
ssh ubuntu@153.126.194.114

# 2. 全プロセス確認
ps aux | grep python

# 3. Streamlit停止
screen -S aicast -X quit
pkill -f streamlit

# 4. cron停止（必要に応じて）
sudo systemctl stop cron

# 5. データベースバックアップ
cd /home/ubuntu/aicast-app
cp casting_office.db casting_office.db.emergency_$(date +%Y%m%d_%H%M%S)

# 6. 原因調査
tail -100 app.log
tail -100 auto_generation.log
```

### データ復旧

**バックアップからの復元**:
```bash
# 1. 現在のDBを退避
cd /home/ubuntu/aicast-app
mv casting_office.db casting_office.db.broken_$(date +%Y%m%d)

# 2. Google Driveから最新バックアップを取得
# （手動ダウンロードまたは gdrive コマンド使用）

# 3. DBを配置
# casting_office.db としてコピー

# 4. 整合性チェック
sqlite3 casting_office.db "PRAGMA integrity_check;"

# 5. アプリ再起動
screen -dmS aicast bash -c "cd /home/ubuntu/aicast-app && source .venv/bin/activate && python3 run.py"
```

### 不正投稿の削除

**手順**:
```bash
# 1. 該当投稿を特定
sqlite3 casting_office.db "SELECT id, content, status, sent_status FROM posts WHERE id = [投稿ID];"

# 2. ステータス確認
# sent_status='scheduled' → まだ送信されていない
# status='sent' → 既に送信済み

# 3. 予約削除（未送信の場合）
sqlite3 casting_office.db "UPDATE posts SET sent_status='cancelled' WHERE id = [投稿ID];"

# 4. 送信済みの場合
# → X（Twitter）で手動削除が必要
# → 投稿履歴からは削除しない（記録として残す）
```

### VPS障害時の対応

**一時的な代替手段**:
1. ローカル環境でアプリを起動
2. データベースをVPSから取得
3. ローカルで運用継続

**手順**:
```bash
# 1. ローカルでDBを取得
scp ubuntu@153.126.194.114:/home/ubuntu/aicast-app/casting_office.db ./

# 2. ローカルでアプリ起動
cd /path/to/local/aicast-app
source .venv/bin/activate
python3 run.py

# 3. ブラウザでアクセス
# http://localhost:8501
```

---

## 参考資料

### 主要ドキュメント

| ドキュメント | 用途 | パス |
|-------------|------|------|
| **機能更新履歴** | 改修・機能追加の詳細 | `FEATURE_UPDATES_2025_10_07.md` |
| **自動生成仕様** | 自動生成機能の詳細 | `AUTO_GENERATION_SPECIFICATION.md` |
| **Streamlit仕様** | UI・機能一覧 | `CURRENT_STREAMLIT_SPEC.md` |
| **VPS運用手順** | サーバー管理 | `docs/README_SAKURA_VPS.md` |
| **X API実装** | X投稿機能 | `docs/X_API_IMPLEMENTATION_GUIDE.md` |

### データベーススキーマ

**主要テーブル**:

#### casts
```sql
CREATE TABLE casts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,          -- ユーザー名
    nickname TEXT,                       -- 表示名
    age INTEGER,
    personality TEXT,                    -- 性格
    occupation TEXT,                     -- 職業
    first_person TEXT,                   -- 一人称
    speech_style TEXT,                   -- 話し方
    -- その他詳細フィールド
);
```

#### posts
```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cast_id INTEGER NOT NULL,
    content TEXT NOT NULL,               -- 投稿本文
    status TEXT DEFAULT 'draft',         -- draft/approved/rejected/sent
    sent_status TEXT DEFAULT 'not_sent', -- not_sent/scheduled/sent/failed
    posted_at DATETIME,                  -- 予定投稿時刻
    sent_at DATETIME,                    -- 実際の送信時刻
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cast_id) REFERENCES casts(id) ON DELETE CASCADE
);
```

#### auto_generation_settings
```sql
CREATE TABLE auto_generation_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cast_id INTEGER NOT NULL UNIQUE,
    enabled INTEGER DEFAULT 0,           -- 0=無効, 1=有効
    auto_approve INTEGER DEFAULT 0,      -- 0=下書きのみ, 1=承認まで, 2=予約まで
    posts_per_day INTEGER DEFAULT 3,    -- 1日の生成件数
    generation_time TEXT DEFAULT '09:00', -- 生成時刻
    last_generated_at DATETIME,          -- 最終生成日時
    FOREIGN KEY (cast_id) REFERENCES casts(id) ON DELETE CASCADE
);
```

### cronジョブ一覧

```bash
# 自動生成バッチ（5分間隔）
*/5 * * * * cd /home/ubuntu/aicast-app && /home/ubuntu/aicast-app/.venv/bin/python3 auto_generation_batch.py >> auto_generation.log 2>&1

# 予約投稿送信（1分間隔）※未実装の場合
* * * * * cd /home/ubuntu/aicast-app && /home/ubuntu/aicast-app/.venv/bin/python3 schedule_sender.py >> schedule.log 2>&1

# ログローテーション（毎日3時）
0 3 * * * cd /home/ubuntu/aicast-app && find . -name "*.log" -size +100M -exec gzip {} \;

# DB最適化（毎週日曜2時）
0 2 * * 0 cd /home/ubuntu/aicast-app && sqlite3 casting_office.db "VACUUM; ANALYZE;"
```

### 環境変数

```bash
# Google Cloud認証
export GOOGLE_APPLICATION_CREDENTIALS=/home/ubuntu/aicast-app/credentials/service-account-key.json

# GCPプロジェクトID
export GCP_PROJECT=your-project-id

# タイムゾーン
export TZ=Asia/Tokyo
```

### よくある質問（FAQ）

#### Q1: 新規キャストを追加したが自動生成されない

**A**: `auto_generation_settings`テーブルを確認してください。

```sql
SELECT * FROM auto_generation_settings WHERE cast_id = [新規キャストID];
```

- レコードが存在しない場合: 2025年11月16日以前にCSV以外で作成された可能性
- `enabled=0`の場合: GUIから有効化
- `auto_approve=0,1`の場合: `2`に変更推奨

**対処**:
```sql
-- レコードが存在しない場合
INSERT INTO auto_generation_settings (cast_id, enabled, auto_approve, posts_per_day, generation_time)
VALUES ([キャストID], 1, 2, 3, '09:00');

-- enabled=0の場合
UPDATE auto_generation_settings SET enabled = 1 WHERE cast_id = [キャストID];
```

#### Q2: 投稿が重複して生成される

**A**: `last_generated_at`が正しく更新されていない可能性があります。

```sql
-- 最終生成日時を確認
SELECT cast_id, generation_time, last_generated_at 
FROM auto_generation_settings 
WHERE cast_id = [キャストID];

-- 手動で更新
UPDATE auto_generation_settings 
SET last_generated_at = datetime('now') 
WHERE cast_id = [キャストID];
```

#### Q3: AIの生成内容がキャラクターに合わない

**A**: ペルソナ設定を見直してください。

**確認ポイント**:
1. `personality`: 性格が明確に記述されているか
2. `first_person`: 一人称が設定されているか
3. `speech_style`: 話し方の特徴が記述されているか
4. サンプル投稿: カテゴリ別に5件以上登録されているか

**改善手順**:
1. 「👤 キャスト管理」→「✏️ 編集」
2. 各項目を詳細に記述
3. サンプル投稿を追加（重要）
4. 試験的に手動生成して確認

#### Q4: メモリ不足エラーが頻発する

**A**: VPSのメモリは2GBです。以下を確認してください。

```bash
# メモリ使用状況
free -h

# 対処1: スワップ領域の追加
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 対処2: 不要なプロセス停止
sudo systemctl disable apache2  # 使用していない場合
```

#### Q5: 予約投稿が送信されない

**A**: スケジュール送信機能の実装状況を確認してください。

**確認**:
```bash
# cronジョブを確認
crontab -l | grep schedule

# 該当cronがない場合は手動送信が必要
```

**現在の仕様**:
- 自動送信機能は開発中の可能性
- GUIから「📬 投稿管理」→「📅 予約一覧」で手動送信が必要な場合あり

---

## 付録

### ディレクトリ構造

```
/home/ubuntu/aicast-app/
├── app.py                        # メインアプリケーション
├── run.py                        # 起動スクリプト
├── auto_generation_batch.py      # 自動生成バッチ
├── casting_office.db             # SQLiteデータベース
├── style.css                     # CSSスタイル
├── requirements.txt              # Python依存関係
├── .venv/                        # 仮想環境
├── credentials/                  # 認証情報
│   └── service-account-key.json
├── migrations/                   # DBマイグレーション
├── docs/                         # ドキュメント
├── *.log                         # ログファイル
└── .auto_generation.lock         # ロックファイル
```

### バージョン履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2025-11-16 | 2.0 | 運用者向けマニュアル初版作成 |
| 2025-11-16 | 2.0.1 | auto_generation_settings自動初期化対応 |

---

**本マニュアルの更新**:
- 機能追加・変更があった場合は速やかに更新してください
- 不明点は`FEATURE_UPDATES_2025_10_07.md`を参照
- 技術的詳細は各種技術ドキュメントを参照

**問い合わせ**:
- システム管理者: [連絡先を記載]
- 緊急時: [緊急連絡先を記載]

---

*このマニュアルは AIcast Room v2.0 に基づいています。*
