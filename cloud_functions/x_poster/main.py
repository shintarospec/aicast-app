import functions_framework
import tweepy
import json
import os
from google.cloud import secretmanager

@functions_framework.http
def x_poster(request):
    """ミニマムX投稿エンジン - 実行毎IP分散による安全投稿"""
    
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
        action = data.get('action', 'post')  # デフォルトは既存のpost動作
        
        # アクション別処理
        if action == 'post':
            # 既存の投稿機能（変更なし）
            text = data.get('text')
            image_url = data.get('image_url')
            
            if not account_id or not text:
                return (json.dumps({
                    "status": "error",
                    "message": "account_id and text are required"
                }), 400, headers)
            
            # Secret Managerから認証情報取得
            credentials = get_credentials(account_id)
            
            # X投稿実行
            result = post_tweet(credentials, text, image_url)
            
            return (json.dumps({
                "status": "success",
                "tweet_id": result.get('id'),
                "account_id": account_id,
                "text_preview": text[:50] + "..." if len(text) > 50 else text,
                "execution_timestamp": data.get('execution_timestamp', '')
            }), 200, headers)
            
        elif action == 'retweet':
            # 新機能：リツイート
            tweet_id = data.get('tweet_id')
            
            if not account_id or not tweet_id:
                return (json.dumps({
                    "status": "error",
                    "message": "account_id and tweet_id are required for retweet"
                }), 400, headers)
            
            # Secret Managerから認証情報取得
            credentials = get_credentials(account_id)
            
            # リツイート実行
            result = retweet_post(credentials, tweet_id)
            
            return (json.dumps({
                "status": "success",
                "action": "retweet",
                "original_tweet_id": tweet_id,
                "account_id": account_id,
                "execution_timestamp": data.get('execution_timestamp', '')
            }), 200, headers)
            
        elif action == 'quote_tweet':
            # 新機能：引用ツイート
            tweet_id = data.get('tweet_id')
            comment = data.get('comment', '')
            
            if not account_id or not tweet_id or not comment:
                return (json.dumps({
                    "status": "error", 
                    "message": "account_id, tweet_id and comment are required for quote_tweet"
                }), 400, headers)
            
            # Secret Managerから認証情報取得
            credentials = get_credentials(account_id)
            
            # 引用ツイート実行
            result = quote_tweet_post(credentials, tweet_id, comment)
            
            return (json.dumps({
                "status": "success",
                "action": "quote_tweet",
                "tweet_id": result.get('id'),
                "original_tweet_id": tweet_id,
                "account_id": account_id,
                "comment_preview": comment[:50] + "..." if len(comment) > 50 else comment,
                "execution_timestamp": data.get('execution_timestamp', '')
            }), 200, headers)
            
        else:
            return (json.dumps({
                "status": "error",
                "message": f"Unknown action: {action}. Supported actions: post, retweet, quote_tweet"
            }), 400, headers)
        
    except Exception as e:
        return (json.dumps({
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }), 500, headers)

def get_credentials(account_id):
    """Secret Managerから認証情報取得"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.environ.get('GCP_PROJECT', 'aicast-472807')
        
        secret_name = f"projects/{project_id}/secrets/x-api-{account_id}/versions/latest"
        response = client.access_secret_version(request={"name": secret_name})
        
        credentials = json.loads(response.payload.data.decode("UTF-8"))
        
        # 必要なキーの存在確認
        required_keys = ['consumer_key', 'consumer_secret', 'access_token', 'access_token_secret']
        for key in required_keys:
            if key not in credentials:
                raise ValueError(f"Missing required credential: {key}")
        
        return credentials
        
    except Exception as e:
        raise Exception(f"Failed to get credentials for account {account_id}: {str(e)}")

def post_tweet(credentials, text, image_url=None):
    """X投稿実行 - 各実行で異なるGoogle Cloud IPを使用"""
    try:
        # Tweepy v4 Client初期化
        client = tweepy.Client(
            consumer_key=credentials['consumer_key'],
            consumer_secret=credentials['consumer_secret'],
            access_token=credentials['access_token'],
            access_token_secret=credentials['access_token_secret']
        )
        
        if image_url:
            # 画像投稿（将来実装）
            return post_with_image(client, text, image_url, credentials)
        else:
            # テキスト投稿
            response = client.create_tweet(text=text)
            return response.data
            
    except tweepy.TooManyRequests:
        raise Exception("Rate limit exceeded. Please wait before retrying.")
    except tweepy.Unauthorized:
        raise Exception("Invalid credentials. Please check API keys.")
    except tweepy.Forbidden:
        raise Exception("Action forbidden. Check account status and permissions.")
    except Exception as e:
        raise Exception(f"Tweet posting failed: {str(e)}")

def post_with_image(client, text, image_url, credentials):
    """画像付き投稿"""
    try:
        import requests
        import tempfile
        
        # v1.1 API for media upload
        auth = tweepy.OAuth1UserHandler(
            credentials['consumer_key'],
            credentials['consumer_secret'],
            credentials['access_token'],
            credentials['access_token_secret']
        )
        api_v1 = tweepy.API(auth)
        
        # 画像ダウンロード
        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()
        
        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            tmp_file.write(img_response.content)
            tmp_file_path = tmp_file.name
        
        # メディアアップロード
        media = api_v1.media_upload(tmp_file_path)
        
        # ツイート作成
        response = client.create_tweet(text=text, media_ids=[media.media_id])
        
        # 一時ファイル削除
        os.unlink(tmp_file_path)
        
        return response.data
        
    except Exception as e:
        raise Exception(f"Image tweet posting failed: {str(e)}")

def retweet_post(credentials, tweet_id):
    """リツイート実行"""
    try:
        client = tweepy.Client(
            consumer_key=credentials['consumer_key'],
            consumer_secret=credentials['consumer_secret'],
            access_token=credentials['access_token'],
            access_token_secret=credentials['access_token_secret']
        )
        
        response = client.retweet(tweet_id)
        return {"retweeted": True, "original_tweet_id": tweet_id}
        
    except tweepy.TooManyRequests:
        raise Exception("Rate limit exceeded. Free Tier: 50 retweets/24h. Please wait before retrying.")
    except tweepy.Unauthorized:
        raise Exception("Invalid credentials. Please check API keys.")
    except tweepy.Forbidden as e:
        if "already retweeted" in str(e).lower() or "cannot retweet" in str(e).lower():
            # 重複リツイートエラーを特別扱い
            raise Exception("DUPLICATE_RETWEET: このツイートは既にリツイート済みです。")
        raise Exception("Retweet forbidden. Check account status and permissions.")
    except Exception as e:
        # 400エラーで重複リツイートの場合を特別処理
        error_msg = str(e).lower()
        if "already retweeted" in error_msg or "cannot retweet" in error_msg or "duplicate" in error_msg:
            raise Exception("DUPLICATE_RETWEET: このツイートは既にリツイート済みです。")
        raise Exception(f"Retweet failed: {str(e)}")

def quote_tweet_post(credentials, tweet_id, comment):
    """引用ツイート実行"""
    try:
        client = tweepy.Client(
            consumer_key=credentials['consumer_key'],
            consumer_secret=credentials['consumer_secret'],
            access_token=credentials['access_token'],
            access_token_secret=credentials['access_token_secret']
        )
        
        response = client.create_tweet(text=comment, quote_tweet_id=tweet_id)
        return response.data
        
    except tweepy.TooManyRequests:
        raise Exception("Rate limit exceeded. Please wait before retrying.")
    except tweepy.Unauthorized:
        raise Exception("Invalid credentials. Please check API keys.")
    except tweepy.Forbidden:
        raise Exception("Quote tweet forbidden. Check account status and permissions.")
    except Exception as e:
        raise Exception(f"Quote tweet failed: {str(e)}")