# X (Twitter) API 投稿機能 実装ガイド

## 🎯 概要

AIcast Room にX (Twitter) API投稿機能を実装しました！既存のGoogle Sheets連携に加えて、X (Twitter) への直接投稿が可能になります。

## ✨ 新機能

### 📤 送信先選択機能
- **Google Sheets**: 既存のスプレッドシート連携
- **X (Twitter)**: X APIへの直接投稿  
- **両方に送信**: Google Sheets と X (Twitter) 同時送信

### 🎛️ 統合されたUI
- 個別送信: 承認済み投稿から選択して送信
- 一括送信: 複数投稿を一括で送信先指定
- リアルタイム状況表示: 送信成功・失敗の詳細ログ

## 🛠️ セットアップ手順

### 1. X Developer Portal でアプリ作成
```
1. https://developer.twitter.com にアクセス
2. 「Create Project」でプロジェクト作成
3. アプリケーション作成（Read and Write権限必要）
4. Keys and Tokens タブで以下を取得:
   - API Key (Consumer Key)
   - API Secret (Consumer Secret)
   - Bearer Token
   - Access Token
   - Access Token Secret
```

### 2. 認証ファイル作成
`credentials/x_api_credentials.json` を作成:

```json
{
    "api_key": "YOUR_API_KEY",
    "api_secret": "YOUR_API_SECRET",
    "bearer_token": "YOUR_BEARER_TOKEN", 
    "access_token": "YOUR_ACCESS_TOKEN",
    "access_token_secret": "YOUR_ACCESS_TOKEN_SECRET"
}
```

### 3. 接続テスト
```bash
python3 test_x_api.py
```

## 🚀 使用方法

### 個別投稿送信
1. **キャスト管理** → 任意のキャスト選択
2. **承認済み** タブを開く
3. 送信したい投稿で**送信先**を選択:
   - 📊 Google Sheets
   - 🐦 X (Twitter)  
   - 📊🐦 両方に送信
4. 「📤 送信」ボタンクリック

### 一括送信
1. 承認済み投稿で複数選択（チェックボックス）
2. **📤 一括送信** エキスパンダを開く
3. **一括送信先**を選択
4. 「📤 選択した投稿を一括送信」実行

### 設定管理
1. **設定** ページを開く
2. **🐦 X (Twitter) API設定** セクション
3. 「🔍 X API認証状況確認」で接続テスト
4. 連携アカウント情報の確認

## 📊 送信履歴管理

### 送信ログ
- `send_history` テーブルで全送信履歴を記録
- 送信先、時刻、成功/失敗、エラーメッセージを保存
- 送信済みタブで詳細確認可能

### 送信状態
- `sent_status`: 'sent' (送信済み)
- `destination`: 'x_api', 'google_sheets', 'both'
- エラー時の詳細ログ記録

## 🔧 技術仕様

### 使用ライブラリ
- `tweepy`: X API v2 クライアント
- 既存: `streamlit`, `gspread` など

### API制限対応
- Rate Limit 自動待機機能
- エラーハンドリング（認証、権限、文字数制限）
- 280文字制限チェック

### セキュリティ
- 認証情報はローカルファイルで管理
- `.gitignore` でクレデンシャル除外
- 権限チェック機能

## 💰 コスト影響

### X API料金（2024年現在）
- **Basic**: $100/月 (月間1万投稿)
- **Pro**: $5,000/月 (月間100万投稿)

月間5万投稿の場合:
- X API: $100-500/月 (プランによる)
- 既存Gemini: 約1,520円/月
- **総額**: 約16,000-80,000円/月

**推奨運用**: Google Sheets経由の既存システム活用で低コスト維持

## 🎯 運用戦略

### ハイブリッド運用
```
1. 通常投稿 → Google Sheets → 既存システム → X投稿 (低コスト)
2. 緊急投稿 → X API直接投稿 (高速)
3. 重要投稿 → 両方に送信 (冗長化)
```

### コスト最適化
- 緊急時のみX API直接投稿
- 通常運用はGoogle Sheets経由維持
- 投稿頻度に応じてプラン選択

## 🔄 既存システムとの連携

### スプレッドシート → X投稿システム
既存の外部システムと併用可能:
- AIcast Room → Google Sheets (メイン)
- 外部システム → Sheets読み込み → X投稿
- AIcast Room → X API (緊急時)

### データ同期
- 両方の送信履歴をDB記録
- 重複投稿防止機能
- 送信状況の一元管理

## 🚨 トラブルシューティング

### よくあるエラー
```
❌ 認証エラー → API Keys確認
❌ 権限エラー → Read and Write権限確認  
❌ 文字数エラー → 280文字以内に調整
❌ Rate Limit → 時間をおいて再実行
```

### デバッグ方法
```bash
# 接続テスト
python3 test_x_api.py

# ログ確認
tail -f app.log
```

## 🎉 導入効果

### 運用効率向上
- 送信先統一UI で操作簡略化
- 一括送信による作業時間短縮
- リアルタイム状況確認

### 柔軟性向上  
- 送信先選択の自由度
- 緊急時の直接投稿対応
- ハイブリッド運用選択

### スケーラビリティ
- 月間5万 → 10万投稿対応
- API制限内での最適化
- 既存システムとの併用

## 📝 今後の拡張予定

- スケジュール投稿機能
- 画像投稿対応
- リプライ・リツイート機能
- X Analytics連携
- マルチアカウント対応

---

🎯 **結論**: 既存のGoogle Sheets連携を活かしつつ、X API直接投稿機能で柔軟性を大幅向上！ハイブリッド運用で効率とコストを両立できます。