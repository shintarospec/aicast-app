# AI画像投稿機能 詳細設計書

## 概要
AIcast Roomに独立した画像投稿機能を追加し、AI生成画像とカスタムテキストでX（旧Twitter）に投稿する機能を実装する。

## 設計方針
- **MCFスケジューリングシステムと完全独立**
- **既存Cloud Functions インフラを活用**
- **Vertex AI Imagen 2による高品質画像生成**
- **ユーザビリティ重視のシンプルなUI**

## 機能要件

### 1. メニュー構成
```
💬 投稿管理
📊 分析
👥 キャスト管理
🎨 AI画像投稿    ← 新規追加
⚙️ 設定
```

### 2. 画像投稿画面の機能
- **プロンプト入力**: AI画像生成用のテキストプロンプト
- **画像生成**: Vertex AI Imagen 2による画像生成
- **プレビュー**: 生成された画像の確認
- **投稿テキスト**: 画像に添付するツイートテキスト（自動生成+編集可能）
- **キャスト選択**: 投稿するキャストの選択
- **投稿実行**: Cloud Functions経由でX APIに投稿

### 3. 状態管理
- **draft**: 下書き状態
- **generated**: 画像生成完了
- **ready**: 投稿準備完了
- **posting**: 投稿中
- **posted**: 投稿完了
- **failed**: 投稿失敗

## 技術仕様

### 1. データベース設計

#### 新規テーブル: image_posts
```sql
CREATE TABLE image_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt TEXT NOT NULL,              -- AI画像生成プロンプト
    generated_image_url TEXT,          -- 生成された画像のURL
    local_image_path TEXT,             -- ローカル保存された画像パス
    tweet_content TEXT,                -- ツイート本文
    status TEXT DEFAULT 'draft',       -- 投稿状態
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    posted_at TIMESTAMP,               -- 投稿完了日時
    tweet_id TEXT,                     -- X API返却のツイートID
    cast_id INTEGER,                   -- 投稿キャストID
    error_message TEXT,                -- エラーメッセージ
    generation_params TEXT,            -- 画像生成パラメータ（JSON）
    FOREIGN KEY (cast_id) REFERENCES personas (id)
);
```

### 2. AI画像生成仕様

#### Vertex AI Imagen 2 設定
```python
from vertexai.preview.vision_models import ImageGenerationModel

model = ImageGenerationModel.from_pretrained("imagegeneration@006")
images = model.generate_images(
    prompt=user_prompt,
    number_of_images=1,
    aspect_ratio="1:1",        # SNS投稿に最適
    safety_filter_level="allow_most",
    person_generation="allow_adult"
)
```

#### 生成パラメータ
- **解像度**: 1024x1024 (1:1アスペクト比)
- **品質**: 高品質モード
- **安全フィルター**: 標準設定
- **生成数**: 1枚

### 3. UI設計

#### 画像投稿画面レイアウト
```
🎨 AI画像投稿
┌─────────────────────────────────────┐
│ プロンプト入力                        │
│ [___________________________]       │
│ 例: "夕日に向かって走る猫"             │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ キャスト選択                          │
│ [Dropdown: キャスト一覧]             │
└─────────────────────────────────────┘

[🎨 画像生成] ボタン

┌─────────────────────────────────────┐
│ 生成画像プレビュー                     │
│ [Image Preview Area]                │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ ツイートテキスト                      │
│ [___________________________]       │
│ [AI自動生成] ボタン                   │
└─────────────────────────────────────┘

[📤 投稿する] ボタン
```

### 4. 処理フロー

#### 4.1 画像生成フロー
```
1. ユーザーがプロンプト入力
2. Vertex AI Imagen 2で画像生成
3. 生成画像をローカル保存
4. プレビュー表示
5. AI自動キャプション生成（オプション）
```

#### 4.2 投稿フロー
```
1. ユーザーが投稿ボタンクリック
2. image_posts テーブルに記録
3. Cloud Functions に画像+テキスト送信
4. X API経由で投稿実行
5. 結果をデータベースに記録
```

### 5. Cloud Functions連携

#### 既存 post_with_image() 関数活用
```python
# Cloud Functions呼び出し例
payload = {
    "action": "post_with_image",
    "text": tweet_content,
    "image_urls": [generated_image_url],
    "cast_credentials": selected_cast_credentials
}

response = requests.post(
    CLOUD_FUNCTIONS_URL,
    json=payload,
    headers={"Authorization": f"Bearer {auth_token}"}
)
```

## ファイル構成

### 新規追加ファイル
- `ai_image_generator.py`: Vertex AI画像生成ロジック
- `image_post_manager.py`: 画像投稿管理ロジック

### 修正ファイル
- `app.py`: メニュー追加、画像投稿画面実装
- `casting_office.db`: image_posts テーブル追加

## セキュリティ考慮事項

### 1. 画像生成制限
- プロンプト内容のフィルタリング
- 不適切コンテンツの生成防止
- レート制限（1日あたりの生成回数制限）

### 2. ファイル管理
- 生成画像の自動削除（24時間後）
- 一時ファイルの適切な管理
- ストレージ容量制限

### 3. API呼び出し制限
- Vertex AI APIの使用量監視
- エラー時のリトライ制限
- タイムアウト設定

## 運用考慮事項

### 1. コスト管理
- Vertex AI Imagen 2の従量課金監視
- 画像生成回数の月次制限設定
- Cloud Storage使用量管理

### 2. パフォーマンス
- 画像生成の非同期処理
- プログレスバー表示
- タイムアウト処理（最大30秒）

### 3. 利用状況分析
- 画像生成回数の統計
- 人気プロンプトの分析
- 投稿成功率の監視

## マイルストーン

### Phase 1: 基盤実装 (3-5日)
- [ ] データベース拡張
- [ ] AI画像生成機能
- [ ] 基本UI実装

### Phase 2: 投稿機能 (2-3日)
- [ ] Cloud Functions連携
- [ ] 投稿状態管理
- [ ] エラーハンドリング

### Phase 3: 最適化 (1-2日)
- [ ] UI/UX改善
- [ ] パフォーマンス最適化
- [ ] テスト・デバッグ

## 成功基準
- ✅ 1クリックでAI画像生成
- ✅ 直感的なUI操作
- ✅ 既存システムへの影響なし
- ✅ 高品質な画像生成
- ✅ 安定したX API投稿

この設計に基づいて、段階的に実装を進めていきます。