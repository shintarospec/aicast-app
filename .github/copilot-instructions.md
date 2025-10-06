# Copilot Instructions for AIcast Room

## 概要

- **AIcast Room**は、Google Cloud Vertex AIとStreamlitを活用したキャスト管理・対話アプリです。
- メインファイル: `app.py`（Streamlit UI & DB操作）、`run.py`（起動・認証）、`test_vertex_vps.py`（Vertex AI認証テスト）。
- データベース: SQLite（`casting_office.db`）、キャスト情報は`PERSONA_FIELDS`で定義。

## アーキテクチャ

- **Streamlit**でWeb UIを構築（`app.py`）。
- **Vertex AI Gemini**モデルを利用（`vertexai.preview.generative_models`）。
- **Google Cloud認証**はADC（Application Default Credentials）推奨。`run.py`で自動チェック。
- **Google Sheets API**連携で投稿をスプレッドシートに送信可能。
- **DBアクセス**は`execute_query`関数でラップ、安全な接続・切断を徹底。

## 開発・運用ワークフロー

- **セットアップ**:  
  1. `gcloud auth application-default login --no-launch-browser`  
  2. `pip3 install -r requirements.txt`
  3. Google Sheets連携用: `credentials/service-account-key.json`を配置
- **起動**:  
  - 開発: `python3 run.py`  
  - 本番: `screen -S aicast && python3 run.py` または `nohup python3 run.py > app.log 2>&1 &`
- **認証テスト**:  
  - `python3 test_vertex_vps.py`でVertex AI認証・Geminiモデル接続を検証。
- **DBファイル**: `casting_office.db`は同ディレクトリに配置。スキーマは`PERSONA_FIELDS`参照。

## コーディング規約・パターン

- **環境変数**:  
  - `GCP_PROJECT`（Google CloudプロジェクトID）、`GOOGLE_APPLICATION_CREDENTIALS`（認証ファイルパス）を優先。
- **DB操作**:  
  - 必ず`execute_query`関数を利用。直接`sqlite3.connect`禁止。
- **投稿ワークフロー**:
  - `draft` → `approved` → `sent` の状態遷移
  - 送信先は拡張可能（現在：Google Sheets、将来：X API、外部サーバー）
- **UIカスタマイズ**:  
  - `style.css`でStreamlitコンポーネントのデザイン調整。
- **キャスト表示**:
  - 「name（nickname）」形式で統一表示
- **エラー処理**:  
  - 認証・依存関係エラーはREADME記載のコマンドで復旧。
- **ログ**:  
  - 本番は`app.log`に出力。`tail -f app.log`で監視。

## 依存関係・外部連携

- **Pythonパッケージ**:  
  - `streamlit`, `pandas`, `google-cloud-aiplatform`, `gspread`, `google-auth`（`requirements.txt`管理）
- **Google Cloud**:  
  - Vertex AI（Geminiモデル）、ADC認証必須
  - Google Sheets API（サービスアカウントキー必要）
- **ポート**:  
  - デフォルト`8501`。衝突時は`netstat`/`kill`で解決。

## 送信機能アーキテクチャ

- **送信先抽象化**: `send_to_google_sheets()`を参考に新しい送信先を追加可能
- **送信履歴**: `send_history`テーブルで送信ログを管理
- **状態管理**: `posts.sent_status`で送信状態を追跡
- **拡張予定**: X API送信、外部サーバー送信機能

## 参考ファイル

- `README_SAKURA_VPS.md`：運用・トラブルシューティング詳細
- `run.py`：起動・認証フロー
- `app.py`：主要ロジック・DB操作・送信機能
- `test_vertex_vps.py`：Vertex AI認証テスト