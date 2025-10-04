import functions_framework
import tweepy
import os
import json
import requests
import tempfile
from google.cloud import secretmanager

@functions_framework.http
def x_poster(request):
    """X投稿用Cloud Function - 本格実装"""
    
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
        if not data:
            return (json.dumps({
                "status": "error",
                "message": "No JSON data provided"
            }), 400, headers)
        
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
            "message": "投稿完了",
            "function_ip": request.environ.get('X-Forwarded-For', 'unknown')
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
    
    # 画像ダウンロード
    img_response = requests.get(image_url, timeout=30)
    img_response.raise_for_status()
    
    # 一時ファイルに保存
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
        tmp_file.write(img_response.content)
        tmp_file_path = tmp_file.name
    
    try:
        # v1.1 API for media upload
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