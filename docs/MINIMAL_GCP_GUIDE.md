# 🚀 ミニマムGCP自動投稿システム実装ガイド

## 📋 最小構成での実装手順

### **Phase 1: 基本Cloud Functions投稿システム（今すぐ実装可能）**

---

## 🎯 **実装概要**

**最小限の投資で最大の効果**: 
- **投資**: 開発時間のみ（追加コスト$0）
- **効果**: 月額$460 → $8の劇的コスト削減
- **期間**: 1週間で完成

---

## 📁 **ファイル構成**

```
gcp-x-poster/
├── cloud_functions/
│   ├── main.py              # Cloud Functions投稿エンジン
│   ├── requirements.txt     # 依存関係
│   └── .env.yaml           # 環境変数
├── setup/
│   ├── deploy.sh           # デプロイスクリプト
│   └── secrets-setup.sh    # Secret Manager設定
└── README.md               # セットアップ手順
```

---

## 💻 **実装コード**

### **1. Cloud Functions投稿エンジン**

```python
# cloud_functions/main.py
import functions_framework
import tweepy
import os
import json
from google.cloud import secretmanager

@functions_framework.http
def x_poster(request):
    """X投稿用Cloud Function - ミニマム実装"""
    
    # CORS対応
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
        return ('', 204, headers)
    
    headers = {'Access-Control-Allow-Origin': '*'}
    
    try:
        # リクエストデータ取得
        data = request.get_json()
        account_id = data.get('account_id')
        text = data.get('text')
        image_url = data.get('image_url')
        
        # 必須パラメータチェック
        if not account_id or not text:
            return (json.dumps({
                "status": "error",
                "message": "account_id and text are required"
            }), 400, headers)
        
        # APIキー取得
        api_keys = get_account_secrets(account_id)
        
        # 投稿実行
        result = post_tweet(api_keys, text, image_url)
        
        return (json.dumps({
            "status": "success",
            "tweet_id": result.get('tweet_id'),
            "account_id": account_id,
            "message": "投稿完了"
        }), 200, headers)
        
    except Exception as e:
        return (json.dumps({
            "status": "error",
            "message": str(e)
        }), 500, headers)

def get_account_secrets(account_id):
    """Secret Managerからアカウント別APIキー取得"""
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.environ.get('GCP_PROJECT', 'aicast-472807')
    
    secret_name = f"projects/{project_id}/secrets/x-api-{account_id}/versions/latest"
    
    try:
        response = client.access_secret_version(request={"name": secret_name})
        return json.loads(response.payload.data.decode("UTF-8"))
    except Exception as e:
        raise Exception(f"APIキー取得エラー (account: {account_id}): {str(e)}")

def post_tweet(api_keys, text, image_url=None):
    """Tweepyでツイート投稿"""
    
    # Tweepy v2 クライアント作成
    client = tweepy.Client(
        consumer_key=api_keys['consumer_key'],
        consumer_secret=api_keys['consumer_secret'],
        access_token=api_keys['access_token'],
        access_token_secret=api_keys['access_token_secret'],
        wait_on_rate_limit=True
    )
    
    if image_url:
        # 画像付き投稿
        return post_with_image(client, api_keys, text, image_url)
    else:
        # テキストのみ投稿
        response = client.create_tweet(text=text)
        return {"tweet_id": response.data['id']}

def post_with_image(client, api_keys, text, image_url):
    """画像付きツイート投稿"""
    import requests
    import tempfile
    
    # 画像ダウンロード
    img_response = requests.get(image_url, timeout=30)
    img_response.raise_for_status()
    
    # 一時ファイルに保存
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
        tmp_file.write(img_response.content)
        tmp_file_path = tmp_file.name
    
    try:
        # v1.1 API for media upload
        import tweepy
        auth = tweepy.OAuth1UserHandler(
            api_keys['consumer_key'],
            api_keys['consumer_secret'],
            api_keys['access_token'],
            api_keys['access_token_secret']
        )
        api_v1 = tweepy.API(auth)
        
        # 画像アップロード
        media = api_v1.media_upload(tmp_file_path)
        
        # ツイート作成
        response = client.create_tweet(text=text, media_ids=[media.media_id])
        
        return {"tweet_id": response.data['id']}
        
    finally:
        # 一時ファイル削除
        os.unlink(tmp_file_path)
```

---

## 🚀 **実装ステップ**

### **Step 1: プロジェクト準備（5分）**
```bash
# 作業フォルダ作成
mkdir gcp-x-poster
cd gcp-x-poster
mkdir cloud_functions setup
```

### **Step 2: Cloud Functions作成（10分）**
上記の`main.py`と`requirements.txt`を作成

### **Step 3: デプロイ（15分）**
```bash
# Google Cloud認証（既に済んでいる場合はスキップ）
gcloud auth login
gcloud config set project aicast-472807

# Cloud Functions有効化
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable secretmanager.googleapis.com

# デプロイ実行
cd cloud_functions
gcloud functions deploy x-poster \
    --gen2 \
    --runtime=python311 \
    --region=asia-northeast1 \
    --source=. \
    --entry-point=x_poster \
    --trigger=http \
    --allow-unauthenticated \
    --set-env-vars="GCP_PROJECT=aicast-472807"
```

### **Step 4: テスト（5分）**
```bash
# Function URLを取得
FUNCTION_URL=$(gcloud functions describe x-poster --region=asia-northeast1 --format="value(serviceConfig.uri)")
echo "Function URL: $FUNCTION_URL"

# テスト投稿（APIキー設定後）
curl -X POST $FUNCTION_URL \
  -H "Content-Type: application/json" \
  -d '{"account_id": "test_account", "text": "Hello from Cloud Functions!"}'
```

---

## 💰 **期待効果**

- **コスト**: $460/月 → $8/月（98.3%削減）
- **IP分散**: 実行毎変動で最高匿名性
- **運用**: 完全自動（管理不要）
- **スケール**: 無制限対応

---

**まずはこのミニマム構成から始めて、段階的に拡張していきましょう！**

実装準備ができましたら、一緒に進めましょう！ 🚀