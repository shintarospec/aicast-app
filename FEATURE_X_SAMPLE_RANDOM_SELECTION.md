# Xアカウントサンプル ランダム3つ選択機能

## 📋 概要

**実装日:** 2025-10-27  
**ブランチ:** clean-production  
**目的:** アカウント運営指針テキストから、XアカウントサンプルのID/ニックネームリストを抽出し、ランダムに3つを選択してペルソナ詳細に保存する機能を実装

---

## 🎯 機能要件

### ユーザーストーリー
> 「アカウント運営指針に記載された複数のXサンプルアカウントから、ランダムに3つを選択して、ペルソナ詳細に自動登録したい」

### 入力形式
```csv
アカウントID,ニックネーム
Honne_no_Maruko,本音のまる子
Uragawa_no_Sazae,裏側のサザエさん
Yofukashi_Akachan,夜ふかしおばけのQ太郎
Kimama_na_Heidi,気ままなハイジ
Guchi_no_Moomin,愚痴のムーミン
Tada_no_Minami,ただの南ちゃん
Yoidore_Kiki,酔いどれキキ
Hinekure_Alice,ひねくれアリス
Taida_na_Akemi,怠惰な明美
Bonno_no_Ikkyusan,煩悩の一休さん
Ningen_rashii_Hamtaro,人間らしいハム太郎
Otona_no_Anpanman,大人のアンパンマン
Yaburekabure_Usagi,やぶれかぶれウサギ
Honne_dake_Pekochan,本音だけペコちゃん
Neko_to_Watashi,猫と私と時々欲望
```

### 出力（データベース）
- `persona_detailed`テーブルに6つの新規カラム:
  - `x_sample_id_1` TEXT
  - `x_sample_name_1` TEXT
  - `x_sample_id_2` TEXT
  - `x_sample_name_2` TEXT
  - `x_sample_id_3` TEXT
  - `x_sample_name_3` TEXT

### UI仕様
- **セクション名:** 🎲 Xアカウントサンプル（ランダム3つ選択）
- **フィールド構成:**
  - XサンプルID #1 / Xサンプルニックネーム #1
  - XサンプルID #2 / Xサンプルニックネーム #2
  - XサンプルID #3 / Xサンプルニックネーム #3
- **ヘルプテキスト:** "運営指針テキストから自動抽出された、参考Xアカウントサンプル（ランダム選択）"

---

## 🔧 実装詳細

### 1. データベーススキーマ更新

**ファイル:** `app.py` (lines ~445-463)

```python
# 既存のpersona_detailedテーブルに新規カラムを追加
execute_query(f"""
    ALTER TABLE persona_detailed 
    ADD COLUMN x_sample_id_1 TEXT
""", fetch=False)

execute_query(f"""
    ALTER TABLE persona_detailed 
    ADD COLUMN x_sample_name_1 TEXT
""", fetch=False)

execute_query(f"""
    ALTER TABLE persona_detailed 
    ADD COLUMN x_sample_id_2 TEXT
""", fetch=False)

execute_query(f"""
    ALTER TABLE persona_detailed 
    ADD COLUMN x_sample_name_2 TEXT
""", fetch=False)

execute_query(f"""
    ALTER TABLE persona_detailed 
    ADD COLUMN x_sample_id_3 TEXT
""", fetch=False)

execute_query(f"""
    ALTER TABLE persona_detailed 
    ADD COLUMN x_sample_name_3 TEXT
""", fetch=False)
```

**特徴:**
- `try-except`ブロック内で実装（カラムが既に存在する場合はスキップ）
- すべてTEXT型（アンダースコア付きIDに対応）

---

### 2. テキスト抽出ロジック

**ファイル:** `app.py` (lines ~5545-5570)

```python
import random
import csv
from io import StringIO

# Xサンプルアカウント抽出（ランダム3つ選択）
x_sample_csv_match = re.search(
    r'アカウントID,ニックネーム\s*\n(.+?)(?=\n\n|---|\Z)', 
    bulk_text, 
    re.DOTALL
)

if x_sample_csv_match:
    csv_content = x_sample_csv_match.group(1).strip()
    csv_lines = [line for line in csv_content.split('\n') if line.strip()]
    
    # 3つ以上あればランダム選択、少なければすべて使用
    num_to_select = min(3, len(csv_lines))
    selected_lines = random.sample(csv_lines, num_to_select) if num_to_select > 0 else []
    
    # CSV解析して保存
    for idx, line in enumerate(selected_lines, 1):
        try:
            reader = csv.reader(StringIO(line))
            row = next(reader)
            if len(row) >= 2:
                st.session_state[f'parsed_x_sample_id_{idx}_{cast_id}'] = row[0].strip()
                st.session_state[f'parsed_x_sample_name_{idx}_{cast_id}'] = row[1].strip()
        except Exception:
            pass  # CSV解析エラーはスキップ
    
    # 選択されなかった残りのスロットはクリア
    for idx in range(num_to_select + 1, 4):
        st.session_state[f'parsed_x_sample_id_{idx}_{cast_id}'] = ""
        st.session_state[f'parsed_x_sample_name_{idx}_{cast_id}'] = ""
```

**ポイント:**
- `random.sample()` で重複なしランダム選択
- 3つ未満の場合はすべて使用
- `csv.reader()` で正しくパース（カンマ、クォート対応）
- セッションステートに`parsed_*`として保存

---

### 3. UIフィールド作成

**ファイル:** `app.py` (lines ~5490-5520)

```python
# 🎲 Xアカウントサンプル（ランダム3つ選択）
st.markdown("#### 🎲 Xアカウントサンプル（ランダム3つ選択）")
st.caption("運営指針テキストから自動抽出された、参考Xアカウントサンプル（ランダム選択）")

for i in range(1, 4):
    col_x1, col_x2 = st.columns(2)
    
    # セッションステートから取得（存在しない場合は空文字）
    edit_key_id = f'edit_x_sample_id_{i}_{selected_cast_id}'
    edit_key_name = f'edit_x_sample_name_{i}_{selected_cast_id}'
    parsed_key_id = f'parsed_x_sample_id_{i}_{selected_cast_id}'
    parsed_key_name = f'parsed_x_sample_name_{i}_{selected_cast_id}'
    
    # parsed_*からedit_*へコピー（自動反映）
    if parsed_key_id in st.session_state:
        st.session_state[edit_key_id] = st.session_state[parsed_key_id]
    if parsed_key_name in st.session_state:
        st.session_state[edit_key_name] = st.session_state[parsed_key_name]
    
    # UIフィールド（keyのみ、valueは使わない）
    col_x1.text_input(
        f"XサンプルID #{i}", 
        key=edit_key_id
    )
    col_x2.text_input(
        f"Xサンプルニックネーム #{i}", 
        key=edit_key_name
    )
```

**重要な実装パターン:**
- **Streamlit警告回避:** `value`パラメータを使わず、`key`のみを使用
- **セッションステートコピー:** `parsed_*` → `edit_*` でUIフィールドに自動反映
- **動的キー管理:** ループでインデックス（1〜3）を使ってキー名を生成

---

### 4. データベース保存処理

**ファイル:** `app.py` (lines ~5914-5937)

```python
# UPDATEクエリ
update_query = """
    UPDATE persona_detailed 
    SET archetype=?, occupation=?, residence=?, family_structure=?, 
        symbolic_quote=?, x_usage_purpose=?, behavior_pattern=?, 
        interested_topics=?, main_follow_targets=?, platform_pain_points=?, 
        brand_relationship=?,
        x_sample_id_1=?, x_sample_name_1=?,
        x_sample_id_2=?, x_sample_name_2=?,
        x_sample_id_3=?, x_sample_name_3=?
    WHERE cast_id=?
"""

update_values = (
    edit_archetype, edit_occupation, edit_residence, edit_family,
    edit_quote, edit_x_purpose, edit_behavior, edit_topics,
    edit_follow, edit_pain, edit_brand,
    edit_x_sample_id_1, edit_x_sample_name_1,
    edit_x_sample_id_2, edit_x_sample_name_2,
    edit_x_sample_id_3, edit_x_sample_name_3,
    selected_cast_id
)

# INSERTクエリ（新規作成時）
insert_query = """
    INSERT INTO persona_detailed (
        cast_id, archetype, occupation, residence, family_structure, 
        symbolic_quote, x_usage_purpose, behavior_pattern, 
        interested_topics, main_follow_targets, platform_pain_points, 
        brand_relationship,
        x_sample_id_1, x_sample_name_1,
        x_sample_id_2, x_sample_name_2,
        x_sample_id_3, x_sample_name_3
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""
```

**ポイント:**
- 既存のUPDATE/INSERTクエリに6フィールドを追加
- パラメータバインディングで安全にSQL実行
- すべてのフィールドが空でも保存可能（NULL許容）

---

## 🐛 トラブルシューティング履歴

### 問題1: UIフィールドに値が反映されない

**現象:**
- セッションステート（`parsed_*`）には正しく保存されている
- UIフィールド（`edit_*`）には`None`が表示される

**原因:**
- Streamlitの`text_input`は、`key`が既に存在する場合、`value`パラメータを無視する
- 初回レンダリング時に`edit_*`が`None`で作成され、`parsed_*`の値が反映されない

**解決策:**
1. `text_input`の`value`パラメータを削除
2. UIフィールド作成**前に**、`parsed_*`から`edit_*`へコピー:
   ```python
   if parsed_key_id in st.session_state:
       st.session_state[edit_key_id] = st.session_state[parsed_key_id]
   ```

---

### 問題2: Streamlit警告が表示される

**警告メッセージ:**
> "The widget with key "edit_x_sample_id_1_4" was created with a default value but also had its value set via the Session State API."

**原因:**
- `text_input`の`value`パラメータと`st.session_state[key]`の両方で値を設定

**解決策:**
- `value`パラメータを完全に削除し、セッションステートのみで管理

---

### 問題3: 保存ボタンが消えた

**現象:**
- UI実装後、保存ボタンが画面に表示されなくなった

**原因:**
- 保存ボタンが`with sample_post_edit_tab:`のスコープ内に入っていた
- 他のタブを開いているときは表示されない

**解決策:**
- 保存ボタンと削除ボタンをタブの外（全タブ共通エリア）に移動
- インデントを調整して正しいスコープに配置

---

## ✅ テスト結果

### テストケース1: 正常な抽出（15件のリスト）

**入力:**
```csv
アカウントID,ニックネーム
Honne_no_Maruko,本音のまる子
Uragawa_no_Sazae,裏側のサザエさん
...（15件）
```

**結果:**
- ✅ ランダムに3つが選択される
- ✅ セッションステートに正しく保存される
- ✅ UIフィールドに自動反映される
- ✅ 保存ボタンでDBに保存される
- ✅ 毎回異なる組み合わせになる（ランダム性確認）

---

### テストケース2: 3件未満のリスト

**入力:**
```csv
アカウントID,ニックネーム
Account_A,ニックネームA
Account_B,ニックネームB
```

**結果:**
- ✅ すべて（2件）が選択される
- ✅ 3つ目のフィールドは空になる
- ✅ エラーなく動作

---

### テストケース3: リストが空

**入力:**
```csv
アカウントID,ニックネーム

```

**結果:**
- ✅ すべてのフィールドが空になる
- ✅ エラーなく動作

---

## 📊 データフロー図

```
┌─────────────────────────────────────────┐
│  アカウント運営指針テキスト（ペースト）   │
└─────────────────┬───────────────────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  正規表現で抽出     │
         │  (CSV全体)          │
         └────────┬───────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  random.sample()   │
         │  (3つランダム選択)  │
         └────────┬───────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  csv.reader()      │
         │  (ID/Name分離)     │
         └────────┬───────────┘
                  │
                  ▼
    ┌────────────────────────────┐
    │  セッションステート保存      │
    │  parsed_x_sample_id_1_*    │
    │  parsed_x_sample_name_1_*  │
    │  ...                       │
    └────────────┬───────────────┘
                  │
                  ▼
    ┌────────────────────────────┐
    │  セッションステートコピー    │
    │  parsed_* → edit_*         │
    └────────────┬───────────────┘
                  │
                  ▼
    ┌────────────────────────────┐
    │  UIフィールド自動反映       │
    │  text_input (key=edit_*)   │
    └────────────┬───────────────┘
                  │
                  ▼ 保存ボタンクリック
    ┌────────────────────────────┐
    │  データベース保存           │
    │  UPDATE persona_detailed   │
    │  SET x_sample_id_1=?, ...  │
    └────────────────────────────┘
```

---

## 📝 コミットメッセージ

```
feat: Xサンプルアカウントのランダム3つ選択機能を追加

- persona_detailedテーブルに6カラム追加（x_sample_id/name 1-3）
- アカウントID/ニックネームリストからrandom.sample()で3つランダム選択
- UIフィールド自動反映（parsed_*からedit_*へのセッションステートコピー）
- UPDATE/INSERTクエリに新フィールドを追加
- Streamlit警告を回避（valueパラメータ削除、keyのみ使用）
- ACCOUNT_GUIDELINES_MAPPING.md更新（抽出パターン、セッションステートキー、更新履歴）
- FEATURE_X_SAMPLE_RANDOM_SELECTION.md作成（完全な実装ドキュメント）

Fixes: UIフィールド自動反映問題、保存ボタン表示問題
```

---

## 🎓 学んだこと

### 1. Streamlitセッションステート管理
- `text_input`の`key`が存在する場合、`value`は無視される
- セッションステートで値を設定する場合、`value`パラメータは不要（警告の原因）
- **ベストプラクティス:** UIフィールド作成前に、セッションステートに値をコピー

### 2. Pythonランダム選択
- `random.sample(list, k)` は重複なしでk個を選択
- `min(3, len(list))` で要素数が少ない場合に対応
- `enumerate(list, 1)` で1から始まるインデックスを生成

### 3. CSV解析の堅牢性
- `csv.reader(StringIO(line))` で1行をCSVとしてパース
- カンマ、クォート、特殊文字に対応
- `try-except` でパース失敗時はスキップ

### 4. Streamlitタブスコープ
- `with tab:`内のコードは、そのタブが選択されている時のみ実行
- 保存ボタンなど共通UIは、タブの外に配置する必要がある

---

## 🚀 今後の拡張可能性

### 1. 再選択機能
- 「🔄 再選択」ボタンを追加
- クリックで別の3つをランダム選択
- 気に入った組み合わせが出るまで試せる

### 2. 選択数のカスタマイズ
- スライダーで選択数を1〜5に変更可能
- DBカラム数も動的に対応

### 3. 手動選択モード
- ドロップダウンでリストから手動選択
- ランダムと手動のハイブリッド

### 4. プレビュー表示
- 選択されたアカウントのプロフィールを表示
- Xアカウントの詳細情報を確認できる

---

## 📚 関連ドキュメント

- `ACCOUNT_GUIDELINES_MAPPING.md` - テキスト項目とCSVフィールド対応表
- `README.md` - プロジェクト全体のドキュメント
- `.github/copilot-instructions.md` - Copilot用開発ガイドライン
