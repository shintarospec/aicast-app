# Streamlit安全再起動スクリプト

成功パターンに基づいた確実なStreamlit再起動スクリプトです。

## 📝 作成背景

従来の再起動方法では失敗することが多かったため、成功した再起動フローを分析してスクリプト化しました。

## 🚀 使い方

### 方法1: スクリプト直接実行（推奨）
```bash
./restart-streamlit.sh
```

### 方法2: VSCode タスク
1. `Ctrl+Shift+P` (Mac: `Cmd+Shift+P`)
2. "Tasks: Run Task" を選択
3. **🔄 ローカル: Streamlit安全再起動** を選択

### 方法3: エイリアス（設定後）
```bash
restart
# または
再起動
```

## 📋 スクリプトの処理フロー

1. **既存プロセス停止**: `pkill -f 'streamlit run'`
2. **ポート確認**: 8503が使用中なら強制終了
3. **構文チェック**: `python3 -m py_compile app.py`
4. **バックグラウンド起動**: `nohup ./start-with-service-account.sh`
5. **起動確認**: `curl http://localhost:8503`

各ステップで状態を確認し、問題があれば詳細なエラー情報を表示します。

## 🔧 エイリアス設定（オプション）

より簡単に使えるよう、エイリアスを設定できます：

```bash
# ~/.bashrc または ~/.zshrc に追加
source /workspaces/aicast-app/aliases.sh
```

設定後は以下のコマンドが使えます：
- `restart` - Streamlit再起動
- `再起動` - Streamlit再起動（日本語）
- `deploy "メッセージ"` - VPSデプロイ
- `本番 "メッセージ"` - VPSデプロイ（日本語）

## 📊 ログ確認

起動ログを確認する場合：
```bash
tail -f /tmp/streamlit-restart.log
```

## ❌ トラブルシューティング

### 起動に失敗する場合

スクリプトが自動的にログの最後20行を表示します。

手動でログ確認：
```bash
cat /tmp/streamlit-restart.log
```

### ポートが解放されない場合

手動でポートを確認して終了：
```bash
lsof -i:8503
kill -9 <PID>
```

## 🆚 従来の方法との違い

### 従来（失敗しやすい）
```bash
pkill -f 'streamlit run'
python3 run.py &
```

### 新方式（安全・確実）
- ✅ ポート確認と強制解放
- ✅ 構文チェック
- ✅ 起動待機時間（5秒）
- ✅ 起動確認（curl）
- ✅ 詳細なログ出力
- ✅ エラー時の自動診断

## 📝 ファイル一覧

- **`restart-streamlit.sh`** - メインスクリプト
- **`aliases.sh`** - エイリアス定義
- **`.vscode/tasks.json`** - VSCodeタスク定義
- **`/tmp/streamlit-restart.log`** - 起動ログ

## 🎯 推奨利用シーン

- app.py編集後の再起動
- エラー発生時の再起動
- デバッグ後の再起動
- 定期メンテナンス
