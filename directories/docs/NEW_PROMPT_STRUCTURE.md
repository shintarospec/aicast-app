# 🆕 新プロンプト構造仕様書

**最終更新日**: 2025年10月26日

---

## 📋 目次

1. [概要](#概要)
2. [新プロンプト構造の特徴](#新プロンプト構造の特徴)
3. [データベース設計](#データベース設計)
4. [CSV一括管理](#csv一括管理)
5. [UI構造](#ui構造)
6. [プロンプト生成関数](#プロンプト生成関数)
7. [移行完了項目](#移行完了項目)

---

## 概要

2025年10月に実施した、AIcast Roomの投稿生成プロンプト構造の大規模リファクタリングです。

### 🎯 目的
- **シンプル化**: シチュエーション機能を削除し、サンプル投稿のみで管理
- **柔軟性向上**: カテゴリをキャストごとに自由設定可能に
- **拡張性**: 運営指針、詳細ペルソナ、サンプルプロフィールを追加
- **保守性**: フォールバック機能を削除し、新構造専用に統一

### 🔄 旧構造との違い

| 項目 | 旧構造 | 新構造 |
|------|--------|--------|
| シチュエーション | ✅ あり | ❌ 削除（サンプル投稿で代替） |
| カテゴリ | 固定（全キャスト共通） | キャストごとに自由設定 |
| フォールバック | ✅ あり | ❌ 削除（シンプル化） |
| 運営指針 | ❌ なし | ✅ 5セクション追加 |
| 詳細ペルソナ | ❌ なし | ✅ 9項目追加 |
| サンプルプロフィール | ❌ なし | ✅ 追加 |

---

## 新プロンプト構造の特徴

### 🧩 プロンプト構成（7セクション）

新しいプロンプトは以下の7セクションで構成されます：

1. **基本ペルソナ** - 必須3項目（name, nickname, age）
2. **アカウント運営指針** - Markdown形式、5セクション
3. **詳細ペルソナ** - CSV形式、9項目（オプション）
4. **サンプルプロフィール** - テキスト形式
5. **サンプル投稿** - カテゴリ別、複数登録可能
6. **シチュエーション/指示** - 投稿生成時の具体的な指示
7. **生成ルール** - 文字数制限、注意事項

### 🎨 特徴

- **段階的な詳細度**: 基本→詳細→具体例の順に情報を提供
- **柔軟なカテゴリ管理**: キャストごとに独自のカテゴリを設定可能
- **オプション項目**: 運営指針、詳細ペルソナ、サンプルプロフィールはすべてオプション
- **CSV一括管理**: 全項目をCSVで一括インポート/エクスポート可能

---

## データベース設計

### 📊 新規追加テーブル（4つ）

#### 1. `account_mission` - アカウント運営指針

| カラム | 型 | 説明 |
|--------|------|------|
| `id` | INTEGER | PRIMARY KEY |
| `cast_id` | INTEGER | キャストID（UNIQUE） |
| `mission` | TEXT | アカウント運営指針 |
| `persona_design` | TEXT | ペルソナ設計 |
| `content_strategy` | TEXT | コンテンツ戦略 |
| `final_goal` | TEXT | 最終ゴール |
| `additional_notes` | TEXT | 補足事項 |
| `created_at` | TEXT | 作成日時 |
| `updated_at` | TEXT | 更新日時 |

**用途**: アカウント全体の方針、ターゲットペルソナ、投稿戦略を定義

---

#### 2. `persona_detailed` - 詳細ペルソナ

| カラム | 型 | 説明 |
|--------|------|------|
| `id` | INTEGER | PRIMARY KEY |
| `cast_id` | INTEGER | キャストID（UNIQUE） |
| `archetype` | TEXT | アーキタイプ |
| `occupation` | TEXT | 職業 |
| `residence` | TEXT | 居住地 |
| `family_structure` | TEXT | 家族構成 |
| `symbolic_quote` | TEXT | 象徴的な一言 |
| `x_usage_purpose` | TEXT | X利用目的 |
| `behavior_pattern` | TEXT | 行動パターン |
| `interested_topics` | TEXT | 関心トピック |
| `platform_pain_points` | TEXT | プラットフォーム不満 |
| `brand_relationship` | TEXT | ブランド関係 |
| `created_at` | TEXT | 作成日時 |
| `updated_at` | TEXT | 更新日時 |

**用途**: キャラクターの深層心理、行動傾向、価値観を定義

---

#### 3. `sample_profiles` - サンプルプロフィール

| カラム | 型 | 説明 |
|--------|------|------|
| `id` | INTEGER | PRIMARY KEY |
| `cast_id` | INTEGER | キャストID（UNIQUE） |
| `profile_text` | TEXT | プロフィール例 |
| `created_at` | TEXT | 作成日時 |
| `updated_at` | TEXT | 更新日時 |

**用途**: キャストのプロフィール文例を保存（AI生成時の参考）

---

#### 4. `sample_posts` - サンプル投稿

| カラム | 型 | 説明 |
|--------|------|------|
| `id` | INTEGER | PRIMARY KEY |
| `cast_id` | INTEGER | キャストID |
| `category` | TEXT | カテゴリ名 |
| `post_content` | TEXT | 投稿内容 |
| `sort_order` | INTEGER | 表示順（デフォルト0） |
| `created_at` | TEXT | 作成日時 |

**用途**: キャストごとの投稿例を保存（カテゴリ別に管理）

**注意**: 旧構造の`situations`テーブルは削除され、`sample_posts`に統合されました。

---

### 🔄 既存テーブルの変更

#### `casts` テーブル

**PERSONA_FIELDS整理**:

- **必須項目（3項目）**: `name`, `nickname`, `age`
- **オプション項目（13項目）**: `birthday`, `personality`, `strength`, `weakness`, `first_person`, `speech_style`, `catchphrase`, `occupation`, `hobby`, `likes`, `dislikes`, `dream`, `secret`

**削除された項目（6項目）**:
- `allowed_categories` → サンプル投稿のカテゴリに移行
- `birthplace` → 使用頻度低
- `appearance` → 詳細ペルソナに移行
- `customer_interaction` → 使用頻度低
- `holiday_activity` → 使用頻度低
- `reason_for_job` → 使用頻度低

---

## CSV一括管理

### 📥 CSV構造

#### 1. **キャスト基本情報 CSV** (`cast_master.csv`)

**38項目の全データを含む包括的なCSV**

##### 📋 CSV形式

```csv
name,nickname,age,archetype,occupation,residence,family_structure,symbolic_quote,x_usage_purpose,behavior_pattern,interested_topics,platform_pain_points,brand_relationship,birthday,personality,strength,weakness,first_person,speech_style,catchphrase,hobby,likes,dislikes,dream,secret,mission,persona_design,content_strategy,final_goal,additional_notes,sample_profile,x_api_key,x_api_secret,x_bearer_token,x_access_token,x_access_token_secret,x_twitter_username,x_twitter_user_id
@shiori_hoshino,星野 詩織,21,クリエイター,文学部の女子大生,東京,一人暮らし,「なんだか、素敵ですね」,日常の美しさを共有,静かな観察者,読書・映画・哲学,情報過多,好きなブランドはない,10月26日,物静かで穏やかな聞き上手,人の話に深く共感できる,少し人見知り,私,です・ます調,「なんだか、素敵ですね」,読書・フィルムカメラ,雨の日の匂い,大きな音・人混み,誰かの心を動かす物語を紡ぐこと,実は大のSF小説好き,このアカウントの目的は...,ターゲットペルソナは...,投稿内容は...,1年後には...,その他注意点...,東京在住の27歳。フリーランスデザイナー...,YOUR_API_KEY,YOUR_API_SECRET,YOUR_BEARER_TOKEN,YOUR_ACCESS_TOKEN,YOUR_ACCESS_TOKEN_SECRET,shiori_hoshino,1234567890
```

##### 📊 項目詳細

| セクション | 項目数 | 項目名 |
|-----------|--------|--------|
| **必須** | 3 | name, nickname, age |
| **詳細ペルソナ** | 9 | archetype, occupation, residence, family_structure, symbolic_quote, x_usage_purpose, behavior_pattern, interested_topics, platform_pain_points, brand_relationship |
| **キャラクター設定** | 13 | birthday, personality, strength, weakness, first_person, speech_style, catchphrase, hobby, likes, dislikes, dream, secret |
| **運営指針** | 5 | mission, persona_design, content_strategy, final_goal, additional_notes |
| **サンプルプロフィール** | 1 | sample_profile |
| **X API認証** | 7 | x_api_key, x_api_secret, x_bearer_token, x_access_token, x_access_token_secret, x_twitter_username, x_twitter_user_id |
| **合計** | **38項目** | |

---

#### 2. **サンプル投稿 CSV** (`sample_posts.csv`)

**キャスト名で紐付けた投稿例の管理**

##### 📋 CSV形式

```csv
username,category,post_content,sort_order
@shiori_hoshino,日常,雨の日の匂いって、なんだか素敵ですね,1
@shiori_hoshino,日常,今日も静かな一日でした,2
@shiori_hoshino,読書,この本、心に染みる一節がありました,1
@shiori_hoshino,読書,SF小説の世界観、奥深いですね,2
@shiori_hoshino,カメラ,フィルムカメラで撮った写真、味がありますね,1
```

##### 📊 項目詳細

| 項目 | 型 | 必須 | 説明 |
|------|------|------|------|
| `username` | TEXT | ✅ | キャスト名（@付き、キー項目） |
| `category` | TEXT | ✅ | カテゴリ名（キャストごとに自由設定） |
| `post_content` | TEXT | ✅ | 投稿内容 |
| `sort_order` | INTEGER | ⭕ | 表示順（省略時は0） |

---

### 📥📤 CSV管理機能

#### UI配置
- **場所**: キャスト管理 → ペルソナ管理タブ → CSV管理タブ

#### 機能

1. **📥 インポート（基本情報）**
   - `cast_master.csv`をアップロード
   - 必須項目: `name`（他はすべてオプション）
   - キャストが存在する場合は更新、存在しない場合は新規作成
   - X API認証情報も一括登録可能

2. **📤 エクスポート（基本情報）**
   - 全キャストデータを38項目のCSVでダウンロード
   - X API認証情報も含む（セキュリティに注意）

3. **📥 インポート（サンプル投稿）**
   - `sample_posts.csv`をアップロード
   - 同じキャスト・カテゴリの既存投稿は削除され、新しいデータで置換
   - 複数のカテゴリを一括登録可能

4. **📤 エクスポート（サンプル投稿）**
   - 全キャストのサンプル投稿をCSVでダウンロード
   - カテゴリ別に整理された状態で出力

---

## UI構造

### 🎨 キャスト管理ページ（4タブ構成）

#### 1. 👤 ペルソナ管理

**サブタブ構成**:
- **新規作成**: 必須3項目 + 詳細ペルソナ9項目（オプション）
- **編集・削除**: キャスト選択 → 編集フォーム
- **一覧表示**: 全キャストの必須項目表示
- **CSV管理**: 一括インポート/エクスポート（★NEW）

**主な機能**:
- キャストの新規作成（必須3項目のみでOK）
- 詳細ペルソナ（9項目）の追加・編集
- キャスト一覧の表示（name, nickname形式）
- CSV一括管理

---

#### 2. 📋 運営指針

**機能**:
- **アカウント運営指針**: 5セクションのMarkdown入力
  - ミッション
  - ペルソナ設計
  - コンテンツ戦略
  - 最終ゴール
  - 補足事項
- **サンプルプロフィール**: テキスト形式のプロフィール例
- **サンプル投稿**: カテゴリ別の投稿管理
  - 追加フォーム（カテゴリ + 投稿内容）
  - カテゴリ別グループ化表示
  - 削除機能

**注意**: すべてオプション項目。未設定の場合は空文字列として扱われます。

---

#### 3. 🎭 キャラクター設定

**機能**:
- オプション13項目の管理
  - birthday, personality, strength, weakness
  - first_person, speech_style, catchphrase
  - occupation, hobby, likes, dislikes
  - dream, secret

**注意**: すべてオプション項目。未設定の場合は空文字列として扱われます。

---

#### 4. 🔐 X API設定

**機能**:
- X (Twitter) API認証情報の管理
  - API Key (Consumer Key)
  - API Secret (Consumer Secret)
  - Bearer Token
  - Access Token
  - Access Token Secret
- 認証状況の確認
  - 連携済みTwitterアカウント表示
  - 認証テストボタン
- 認証情報の設定/編集/削除

**セキュリティ**:
- すべての認証情報は`cast_x_credentials`テーブルに暗号化せずに保存
- CSV経由での一括設定も可能（取り扱い注意）

---

## プロンプト生成関数

### 🔧 新規追加関数（5つ）

#### 1. `get_account_mission_prompt(cast_id)`

**用途**: アカウント運営指針を取得してMarkdown形式で返す

**戻り値**:
```
## アカウント運営指針
このアカウントの目的は...

## ペルソナ設計
ターゲットペルソナは...

## コンテンツ戦略
投稿内容は...

## 最終ゴール
1年後には...

## 補足事項
その他注意点...
```

**注意**: 未設定の場合は空文字列

---

#### 2. `get_detailed_persona_prompt(cast_id)`

**用途**: 詳細ペルソナを取得してCSV形式で返す

**戻り値**:
```
## 詳細ペルソナ
アーキタイプ: クリエイター
職業: 文学部の女子大生
居住地: 東京
家族構成: 一人暮らし
象徴的な一言: 「なんだか、素敵ですね」
X利用目的: 日常の美しさを共有
行動パターン: 静かな観察者
関心トピック: 読書・映画・哲学
プラットフォーム不満: 情報過多
ブランド関係: 好きなブランドはない
```

**注意**: 未設定の項目は出力されません

---

#### 3. `get_sample_profile_prompt(cast_id)`

**用途**: サンプルプロフィールを取得

**戻り値**:
```
## サンプルプロフィール
東京在住の27歳。
フリーランスデザイナーとして...
```

**注意**: 未設定の場合は空文字列

---

#### 4. `get_sample_posts_prompt(cast_id, category=None, limit=100)`

**用途**: サンプル投稿を取得（カテゴリ別にグループ化）

**パラメータ**:
- `cast_id`: キャストID
- `category`: カテゴリ名（省略時は全カテゴリ）
- `limit`: 取得件数上限（デフォルト100）

**戻り値**:
```
## サンプル投稿

### カテゴリ: 日常
- 雨の日の匂いって、なんだか素敵ですね
- 今日も静かな一日でした

### カテゴリ: 読書
- この本、心に染みる一節がありました
- SF小説の世界観、奥深いですね
```

**注意**: 未設定の場合は空文字列

---

#### 5. `build_full_prompt(cast_id, situation_or_instruction, char_limit=140, is_custom_instruction=False)`

**用途**: フルプロンプトを構築（新構造専用、フォールバックなし）

**パラメータ**:
- `cast_id`: キャストID
- `situation_or_instruction`: 投稿のシチュエーション/指示
- `char_limit`: 文字数制限（デフォルト140）
- `is_custom_instruction`: カスタム指示かどうか

**プロンプト構成（7セクション）**:
1. 基本ペルソナ（必須）
2. アカウント運営指針（オプション）
3. 詳細ペルソナ（オプション）
4. サンプルプロフィール（オプション）
5. サンプル投稿（オプション）
6. シチュエーション/指示
7. 生成ルール

**注意**: 
- フォールバック機能は削除済み
- 新プロンプト構造専用に設計

---

## 移行完了項目

### ✅ 完了事項

#### 1. データベース設計
- ✅ `account_mission`テーブル追加
- ✅ `persona_detailed`テーブル追加
- ✅ `sample_profiles`テーブル追加
- ✅ `sample_posts`テーブル追加
- ✅ `casts`テーブルのPERSONA_FIELDS整理

#### 2. プロンプト生成関数
- ✅ `get_account_mission_prompt()`実装
- ✅ `get_detailed_persona_prompt()`実装
- ✅ `get_sample_profile_prompt()`実装
- ✅ `get_sample_posts_prompt()`実装
- ✅ `build_full_prompt()`実装（フォールバック削除）

#### 3. 投稿生成ロジック更新
- ✅ 自動生成で`build_full_prompt()`使用
- ✅ カスタム指示で`build_full_prompt()`使用
- ✅ AI改善で`build_full_prompt()`使用
- ✅ 旧プロンプト構造のフォールバック削除

#### 4. PERSONA_FIELDS整理
- ✅ 必須3項目に分離（name, nickname, age）
- ✅ オプション13項目に分離
- ✅ 不要な6項目を削除

#### 5. UIタブ構造変更
- ✅ 4タブ構成に再構成
  - 👤 ペルソナ管理
  - 📋 運営指針
  - 🎭 キャラクター設定
  - 🔐 X API設定
- ✅ sqlite3.Rowオブジェクトのアクセス方法修正（.get()→辞書アクセス）

#### 6. CSV一括管理機能
- ✅ キャスト基本情報CSVインポート/エクスポート（38項目）
- ✅ サンプル投稿CSVインポート/エクスポート
- ✅ X API認証情報のCSV対応

#### 7. Google Cloud認証
- ✅ サービスアカウントキー認証に切り替え
- ✅ `start-with-service-account.sh`作成
- ✅ `run.py`でサービスアカウントキー優先に修正

#### 8. 動作確認・テスト
- ✅ 投稿生成成功（Vertex AI Gemini）
- ✅ CSV一括登録成功
- ✅ 全UIタブの動作確認完了

---

## 🎯 今後の拡張予定

### 候補機能

1. **サンプル投稿の充実**
   - カテゴリごとのテンプレート機能
   - AIによるサンプル投稿自動生成

2. **運営指針のテンプレート**
   - よく使うパターンのテンプレート化
   - 業種別テンプレート提供

3. **投稿生成のバリエーション**
   - カテゴリ別の生成ロジック
   - 時間帯・曜日別の投稿戦略

4. **パフォーマンス最適化**
   - プロンプト長の最適化
   - キャッシュ機構の導入

---

## 📚 関連ドキュメント

- [README.md](../../README.md) - プロジェクト全体の概要
- [SCHEDULE_POSTING_DEVELOPMENT_HISTORY.md](./SCHEDULE_POSTING_DEVELOPMENT_HISTORY.md) - 開発履歴
- [CAST_SPECIFIC_X_API_GUIDE.md](./CAST_SPECIFIC_X_API_GUIDE.md) - X API設定ガイド
- [README_SAKURA_VPS.md](./README_SAKURA_VPS.md) - 運用手順

---

## 💡 ベストプラクティス

### キャスト作成の推奨手順

1. **最小構成で開始**
   - 必須3項目（name, nickname, age）のみで作成
   - 動作確認

2. **段階的に拡張**
   - サンプル投稿を5-10件追加
   - カテゴリは3-5個程度から開始
   - 運営指針を設定（特にmissionとcontent_strategyは重要）

3. **オプション項目の追加**
   - キャラクター設定（personality, speech_style等）
   - 詳細ペルソナ（archetype, behavior_pattern等）

4. **X API設定**
   - 投稿テスト後に認証情報を設定

### CSV管理のベストプラクティス

1. **バックアップ**
   - 定期的にエクスポートしてバックアップ
   - Git等でバージョン管理

2. **段階的な更新**
   - 大量のキャストを一度に更新せず、少数で動作確認
   - エラーが出た場合は1行ずつ確認

3. **セキュリティ**
   - X API認証情報を含むCSVは厳重に管理
   - 公開リポジトリにコミットしない

---

**以上、新プロンプト構造仕様書でした。** 🎉
