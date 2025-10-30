# デザイン調整・UI変更ガイド

## 📋 新しいパッケージを追加する際の手順

このプロジェクトでは、**2つのPython環境**が存在します。UI/デザイン変更時に新しいパッケージを追加する場合は、両方の環境で正しく動作させる必要があります。

### Python環境の違い

1. **仮想環境（`.venv`）**
   - パス: `/workspaces/aicast-app/.venv`
   - 用途: 開発中の一時的なテスト用
   - 有効化: `source .venv/bin/activate`

2. **グローバル環境（システムPython）** ⭐ **重要**
   - コマンド: `python3`、`pip3`
   - 用途: `run.py`と`restart-streamlit.sh`が使用
   - **本番で実際に動く環境**

### ✅ 必須チェックリスト

新しいUIライブラリやデザイン関連パッケージを追加する際は、以下の手順を**必ず**実行してください：

#### 1. requirements.txtに追加
```bash
# requirements.txtに新しいパッケージを追加
echo "streamlit-option-menu" >> requirements.txt
```

#### 2. グローバル環境にインストール
```bash
# グローバル環境（本番環境）にインストール
pip3 install パッケージ名

# 例：
pip3 install streamlit-option-menu
```

#### 3. 再起動して動作確認
```bash
# 正しいスクリプトで再起動
./restart-streamlit.sh
```

### ⚠️ よくある失敗パターン

#### ❌ 失敗例：仮想環境のみにインストール
```bash
source .venv/bin/activate
pip install streamlit-option-menu  # ← これだけだとNG！
```

**問題点**: `restart-streamlit.sh`はグローバル環境のPythonを使用するため、アプリ起動時に`ModuleNotFoundError`が発生します。

#### ✅ 正しい方法：グローバル環境にインストール
```bash
# 仮想環境を有効化していない状態で
pip3 install streamlit-option-menu  # ← これが正解！
```

## 🎨 デザイン変更の実例

### streamlit-option-menuの導入（2025-10-28）

**目的**: サイドバーメニューをモダンなアイコン付きデザインに変更

**実施手順**:
1. `requirements.txt`に`streamlit-option-menu`を追加
2. `pip3 install streamlit-option-menu`でグローバル環境にインストール
3. `app.py`でインポートと実装
   ```python
   from streamlit_option_menu import option_menu
   
   selected_page = option_menu(
       menu_title="メニュー",
       options=menu_options,
       icons=menu_icons,
       # ...スタイル設定
   )
   ```
4. `./restart-streamlit.sh`で再起動

**結果**: ✅ 成功 - アイコン付きモダンメニューが表示

## 📦 デザイン関連パッケージ一覧

現在使用中のデザイン・UI関連パッケージ：

- `streamlit` - メインフレームワーク
- `streamlit-option-menu` - アイコン付きナビゲーションメニュー
- `pandas` - データ表示用

## 🚀 本番環境（VPS）へのデプロイ

VPSへデプロイする際、`requirements.txt`のパッケージが自動インストールされます。

```bash
# VPS上で実行される
pip3 install -r requirements.txt
```

そのため、**必ず`requirements.txt`を更新**してからデプロイしてください。

## 🔍 トラブルシューティング

### ModuleNotFoundErrorが発生した場合

1. **エラーメッセージを確認**
   ```
   ModuleNotFoundError: No module named 'パッケージ名'
   ```

2. **グローバル環境にインストールされているか確認**
   ```bash
   pip3 list | grep パッケージ名
   ```

3. **インストールされていない場合**
   ```bash
   pip3 install パッケージ名
   ./restart-streamlit.sh
   ```

### requirements.txtの確認方法

```bash
cat requirements.txt
```

現在の内容：
```
streamlit
streamlit-option-menu
pandas
google-cloud-aiplatform
google-cloud-secret-manager
gspread
google-auth
requests
python-dateutil
psutil
```

## 📝 コミット前のチェック

デザイン変更をコミットする前に確認：

- [ ] `requirements.txt`が更新されている
- [ ] グローバル環境（`pip3`）にインストールされている
- [ ] `./restart-streamlit.sh`で正常に起動する
- [ ] ブラウザで表示確認済み

## 🎯 まとめ

**覚えておくべき最重要ポイント**:

1. 新しいパッケージは`pip3`（グローバル環境）でインストール
2. `requirements.txt`への追加を忘れずに
3. `./restart-streamlit.sh`で動作確認

これらを守れば、デザイン変更時のトラブルを回避できます！
