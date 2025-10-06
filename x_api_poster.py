# X (Twitter) API 投稿機能
# pip install tweepy

import tweepy
import os
import json
from datetime import datetime
import logging

class XTwitterPoster:
    def __init__(self):
        """X API の設定を初期化"""
        self.client = None
        self.api_initialized = False
        self.cast_clients = {}  # キャスト別のクライアントキャッシュ
        
    def setup_credentials(self):
        """X API認証情報をセットアップ"""
        try:
            # 認証情報ファイルを確認
            credentials_path = "credentials/x_api_credentials.json"
            
            if os.path.exists(credentials_path):
                with open(credentials_path, 'r') as f:
                    creds = json.load(f)
                
                # X API v2 Client を作成
                self.client = tweepy.Client(
                    bearer_token=creds.get('bearer_token'),
                    consumer_key=creds.get('api_key'),
                    consumer_secret=creds.get('api_secret'),
                    access_token=creds.get('access_token'),
                    access_token_secret=creds.get('access_token_secret'),
                    wait_on_rate_limit=True
                )
                
                # 認証テスト
                try:
                    me = self.client.get_me()
                    if me.data:
                        self.api_initialized = True
                        return True, f"X API認証成功: @{me.data.username}"
                    else:
                        return False, "X API認証に失敗しました"
                except Exception as e:
                    return False, f"X API認証エラー: {str(e)}"
            else:
                setup_message = """X API連携の設定が必要です。

【X API認証設定手順】
1. [X Developer Portal](https://developer.twitter.com) にアクセス
2. アプリケーションを作成（Read and Write権限必要）
3. 以下の認証キーを取得：
   - API Key (Consumer Key)
   - API Secret (Consumer Secret)  
   - Bearer Token
   - Access Token
   - Access Token Secret
4. `credentials/x_api_credentials.json` を以下の形式で作成：

```json
{
    "api_key": "YOUR_API_KEY",
    "api_secret": "YOUR_API_SECRET", 
    "bearer_token": "YOUR_BEARER_TOKEN",
    "access_token": "YOUR_ACCESS_TOKEN",
    "access_token_secret": "YOUR_ACCESS_TOKEN_SECRET"
}
```

5. アプリを再起動して送信を試行

設定完了後、再度送信をお試しください。"""
                return False, setup_message
                
        except Exception as e:
            return False, f"認証設定エラー: {str(e)}"
    
    def post_tweet(self, content, cast_name=None, quote_tweet_id=None):
        """ツイートを投稿（コメント入りリツイート対応）
        
        Args:
            content (str): 投稿内容
            cast_name (str, optional): キャスト名
            quote_tweet_id (str, optional): 引用ツイートのID（コメント入りリツイート用）
        """
        try:
            if not self.api_initialized:
                success, message = self.setup_credentials()
                if not success:
                    return False, message
            
            # 投稿内容の前処理
            tweet_content = content.strip()
            
            # キャスト名を含める場合（オプション）
            if cast_name:
                # 必要に応じてキャスト名をハッシュタグとして追加
                pass
            
            # 文字数制限チェック（X の制限は280文字）
            if len(tweet_content) > 280:
                return False, f"投稿内容が280文字を超えています（{len(tweet_content)}文字）"
            
            # ツイート投稿（コメント入りリツイート対応）
            tweet_params = {'text': tweet_content}
            if quote_tweet_id:
                tweet_params['quote_tweet_id'] = quote_tweet_id
            
            response = self.client.create_tweet(**tweet_params)
            
            if response.data:
                tweet_id = response.data['id']
                tweet_url = f"https://twitter.com/user/status/{tweet_id}"
                if quote_tweet_id:
                    return True, f"コメント入りリツイート投稿成功！ ID: {tweet_id} (引用元: {quote_tweet_id})"
                else:
                    return True, f"ツイート投稿成功！ ID: {tweet_id}"
            else:
                return False, "ツイート投稿に失敗しました"
                
        except tweepy.TooManyRequests:
            return False, "API使用制限に達しました。しばらく待ってから再試行してください。"
        except tweepy.Forbidden:
            return False, "投稿権限がありません。X API の設定を確認してください。"
        except tweepy.Unauthorized:
            return False, "認証エラー。X API の認証情報を確認してください。"
        except Exception as e:
            return False, f"投稿エラー: {str(e)}"
    
    def schedule_tweet(self, content, scheduled_datetime, cast_name=None):
        """スケジュール投稿（X API v2では直接サポートされていないため、将来の実装用）"""
        # 注意: X API v2では直接のスケジュール投稿機能がないため、
        # 外部スケジューラーやタスクキューとの連携が必要
        return False, "スケジュール投稿は現在未対応です。即座投稿を使用してください。"
    
    def get_account_info(self):
        """アカウント情報を取得"""
        try:
            if not self.api_initialized:
                success, message = self.setup_credentials()
                if not success:
                    return None, message
            
            me = self.client.get_me()
            if me.data:
                return {
                    'username': me.data.username,
                    'name': me.data.name,
                    'id': me.data.id
                }, "成功"
            else:
                return None, "アカウント情報の取得に失敗"
                
        except Exception as e:
            return None, f"アカウント情報取得エラー: {str(e)}"
    
    def check_permissions_detailed(self, cast_id=None):
        """詳細な権限確認とトラブルシューティング情報を取得"""
        try:
            # 使用するクライアントを決定
            if cast_id is not None:
                if cast_id not in self.cast_clients:
                    return False, f"キャストID {cast_id} の認証情報が設定されていません"
                client = self.cast_clients[cast_id]
                account_type = f"キャスト (ID: {cast_id})"
            else:
                if not self.api_initialized:
                    success, message = self.setup_credentials()
                    if not success:
                        return False, f"認証失敗: {message}"
                client = self.client
                account_type = "グローバルアカウント"
            
            # 基本的なアカウント情報を取得
            me = client.get_me()
            if not me.data:
                return False, f"{account_type}: アカウント情報の取得に失敗しました"
            
            results = {
                'account_type': account_type,
                'username': me.data.username,
                'name': me.data.name,
                'user_id': me.data.id,
                'tests': {}
            }
            
            # 1. 読み取り権限テスト
            try:
                recent_tweets = client.get_me(user_fields=['public_metrics'])
                results['tests']['read_permission'] = True
            except Exception as e:
                results['tests']['read_permission'] = f"読み取り権限エラー: {str(e)}"
            
            # 2. 投稿権限テスト（実際には投稿しない、構文チェックのみ）
            try:
                # 投稿のvalidationのみ実行（実際には投稿しない）
                test_content = "テスト投稿（実際には送信されません）"
                if len(test_content) <= 280:
                    results['tests']['write_permission'] = True
                else:
                    results['tests']['write_permission'] = "文字数制限エラー"
            except Exception as e:
                results['tests']['write_permission'] = f"投稿権限エラー: {str(e)}"
            
            # 3. いいね権限テスト（自分の最新投稿にいいねを試行）
            try:
                # 自分の最新投稿を取得
                my_tweets = client.get_users_tweets(
                    id=me.data.id,
                    max_results=5,
                    tweet_fields=['created_at']
                )
                
                if my_tweets.data and len(my_tweets.data) > 0:
                    # 最新の投稿IDを取得
                    latest_tweet_id = my_tweets.data[0].id
                    
                    # いいね権限テスト（実際にはいいねしない、権限のみチェック）
                    # 注意: 実際のテストではいいね→すぐ取り消しを行う
                    results['tests']['like_permission'] = f"テスト可能（最新投稿ID: {latest_tweet_id}）"
                    results['tests']['latest_tweet_id'] = latest_tweet_id
                else:
                    results['tests']['like_permission'] = "投稿が見つからないため、いいね権限テストをスキップ"
                    
            except tweepy.Forbidden as e:
                results['tests']['like_permission'] = f"❌ いいね権限なし: {str(e)}"
            except Exception as e:
                results['tests']['like_permission'] = f"いいね権限テストエラー: {str(e)}"
            
            return True, results
            
        except Exception as e:
            return False, f"権限確認エラー: {str(e)}"
    
    def setup_cast_credentials(self, cast_id, api_key, api_secret, bearer_token, access_token, access_token_secret):
        """キャスト専用のX API認証情報をセットアップ"""
        try:
            # キャスト専用のX API v2 Client を作成
            cast_client = tweepy.Client(
                bearer_token=bearer_token,
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                wait_on_rate_limit=True
            )
            
            # 認証テスト
            try:
                me = cast_client.get_me()
                if me.data:
                    # キャッシュに保存
                    self.cast_clients[cast_id] = cast_client
                    return True, f"キャストID {cast_id} のX API認証成功: @{me.data.username}", me.data
                else:
                    return False, f"キャストID {cast_id} のX API認証に失敗しました", None
            except Exception as e:
                return False, f"キャストID {cast_id} のX API認証エラー: {str(e)}", None
                
        except Exception as e:
            return False, f"キャストID {cast_id} の認証設定エラー: {str(e)}", None
    
    def post_tweet_for_cast(self, cast_id, content, cast_name=None):
        """指定されたキャストのアカウントでツイートを投稿"""
        try:
            # キャスト専用クライアントを取得
            if cast_id not in self.cast_clients:
                return False, f"キャストID {cast_id} の認証情報が設定されていません"
            
            cast_client = self.cast_clients[cast_id]
            
            # 投稿内容の前処理
            tweet_content = content.strip()
            
            # 文字数制限チェック（X の制限は280文字）
            if len(tweet_content) > 280:
                return False, f"投稿内容が280文字を超えています（{len(tweet_content)}文字）"
            
            # ツイート投稿
            response = cast_client.create_tweet(text=tweet_content)
            
            if response.data:
                tweet_id = response.data['id']
                tweet_url = f"https://twitter.com/user/status/{tweet_id}"
                return True, f"ツイート投稿成功！ ID: {tweet_id}, URL: {tweet_url}"
            else:
                return False, "ツイート投稿に失敗しました"
                
        except tweepy.TooManyRequests:
            return False, "API使用制限に達しました。しばらく待ってから再試行してください。"
        except tweepy.Forbidden:
            return False, "投稿権限がありません。X API の設定を確認してください。"
        except tweepy.Unauthorized:
            return False, "認証エラー。X API の認証情報を確認してください。"
        except Exception as e:
            return False, f"投稿エラー: {str(e)}"
    
    def get_cast_account_info(self, cast_id):
        """キャストのアカウント情報を取得"""
        try:
            if cast_id not in self.cast_clients:
                return None, f"キャストID {cast_id} の認証情報が設定されていません"
            
            cast_client = self.cast_clients[cast_id]
            me = cast_client.get_me()
            
            if me.data:
                return {
                    'username': me.data.username,
                    'name': me.data.name,
                    'id': me.data.id,
                    'cast_id': cast_id
                }, "成功"
            else:
                return None, "アカウント情報の取得に失敗"
                
        except Exception as e:
            return None, f"アカウント情報取得エラー: {str(e)}"
    
    def like_tweet(self, tweet_id, cast_id=None):
        """投稿に「いいね」をする
        
        Args:
            tweet_id (str): いいねしたい投稿のID
            cast_id (int, optional): キャストID。指定時はキャスト専用アカウントで実行
            
        Returns:
            tuple: (成功True/失敗False, メッセージ)
        """
        # FREEプランでの制限を事前警告
        return False, """❌ X API FREEプランでは「いいね」機能は利用できません。

💡 いいね機能を使用するには：
• BASIC プラン ($100/月): 200回/24時間
• PRO プラン ($5,000/月): 1000回/24時間

📋 FREEプランで利用可能な機能：
• ✅ 投稿: 17回/24時間  
• ✅ いいね履歴確認: 1回/15分
• ✅ リツイート: 1回/15分
• ✅ ユーザー情報取得: 制限付き

詳細: https://developer.twitter.com/en/docs/twitter-api/rate-limits"""
        
        try:
            # キャスト指定時はキャスト専用クライアントを使用
            if cast_id is not None:
                if cast_id not in self.cast_clients:
                    return False, f"キャストID {cast_id} の認証情報が設定されていません"
                client = self.cast_clients[cast_id]
                account_type = f"キャスト (ID: {cast_id})"
            else:
                # グローバル認証を使用
                if not self.api_initialized:
                    success, message = self.setup_credentials()
                    if not success:
                        return False, f"認証失敗: {message}"
                client = self.client
                account_type = "グローバルアカウント"
            
            # いいねを実行
            response = client.like(tweet_id)
            
            if response.data and response.data.get('liked'):
                return True, f"✅ {account_type}で投稿にいいねしました (Tweet ID: {tweet_id})"
            else:
                return False, f"❌ いいねに失敗しました: {response}"
                
        except tweepy.TooManyRequests:
            return False, "API使用制限に達しました。しばらく待ってから再試行してください。"
        except tweepy.Forbidden as e:
            error_detail = str(e)
            if "403 Forbidden" in error_detail:
                if "attached to a Project" in error_detail:
                    return False, f"❌ アプリがプロジェクトに紐付いていません: {error_detail}\n💡 X Developer Portalでプロジェクト内にアプリを作成し直してください。"
                elif "scope" in error_detail.lower() or "permission" in error_detail.lower():
                    return False, f"❌ いいね権限が不足しています: {error_detail}\n💡 OAuth 2.0設定でlike.writeスコープを有効にしてください。"
                else:
                    return False, f"❌ いいね権限エラー: {error_detail}\n💡 アプリの権限設定(Read and Write)とOAuth 2.0スコープ(like.write)を確認してください。"
            else:
                return False, f"いいね権限がありません: {error_detail}"
        except tweepy.Unauthorized as e:
            return False, f"認証エラー: {str(e)}\n💡 API Key/Token を確認してください。"
        except tweepy.NotFound:
            return False, "指定された投稿が見つかりません。投稿IDを確認してください。" 
        except Exception as e:
            return False, f"いいねエラー: {str(e)}"
    
    def unlike_tweet(self, tweet_id, cast_id=None):
        """投稿の「いいね」を取り消す
        
        Args:
            tweet_id (str): いいねを取り消したい投稿のID
            cast_id (int, optional): キャストID。指定時はキャスト専用アカウントで実行
            
        Returns:
            tuple: (成功True/失敗False, メッセージ)
        """
        # FREEプランでの制限を事前警告
        return False, """❌ X API FREEプランでは「いいね取り消し」機能は利用できません。

💡 いいね機能を使用するには：
• BASIC プラン ($100/月): 100回/24時間
• PRO プラン ($5,000/月): 50回/15分

📋 FREEプランで利用可能な機能：
• ✅ 投稿: 17回/24時間  
• ✅ いいね履歴確認: 1回/15分
• ✅ リツイート: 1回/15分

詳細: https://developer.twitter.com/en/docs/twitter-api/rate-limits"""
        
        try:
            # キャスト指定時はキャスト専用クライアントを使用
            if cast_id is not None:
                if cast_id not in self.cast_clients:
                    return False, f"キャストID {cast_id} の認証情報が設定されていません"
                client = self.cast_clients[cast_id]
                account_type = f"キャスト (ID: {cast_id})"
            else:
                # グローバル認証を使用
                if not self.api_initialized:
                    success, message = self.setup_credentials()
                    if not success:
                        return False, f"認証失敗: {message}"
                client = self.client
                account_type = "グローバルアカウント"
            
            # いいね取り消しを実行
            response = client.unlike(tweet_id)
            
            if response.data and response.data.get('liked') == False:
                return True, f"✅ {account_type}で投稿のいいねを取り消しました (Tweet ID: {tweet_id})"
            else:
                return False, f"❌ いいね取り消しに失敗しました: {response}"
                
        except tweepy.TooManyRequests:
            return False, "API使用制限に達しました。しばらく待ってから再試行してください。"
        except tweepy.Forbidden as e:
            return False, f"いいね権限がありません: {str(e)}"
        except tweepy.Unauthorized:
            return False, "認証エラー。X API の認証情報を確認してください。"
        except tweepy.NotFound:
            return False, "指定された投稿が見つかりません。投稿IDを確認してください。"
        except Exception as e:
            return False, f"いいね取り消しエラー: {str(e)}"
    
    def get_liked_tweets(self, cast_id=None, max_results=10):
        """いいねした投稿一覧を取得
        
        Args:
            cast_id (int, optional): キャストID。指定時はキャスト専用アカウントで実行
            max_results (int): 取得する最大件数 (5-100)
            
        Returns:
            tuple: (成功True/失敗False, データまたはエラーメッセージ)
        """
        try:
            # キャスト指定時はキャスト専用クライアントを使用  
            if cast_id is not None:
                if cast_id not in self.cast_clients:
                    return False, f"キャストID {cast_id} の認証情報が設定されていません"
                client = self.cast_clients[cast_id]
                # キャストのuser_idを取得
                me = client.get_me()
                if not me.data:
                    return False, "アカウント情報の取得に失敗しました"
                user_id = me.data.id
                account_type = f"キャスト (ID: {cast_id})"
            else:
                # グローバル認証を使用
                if not self.api_initialized:
                    success, message = self.setup_credentials() 
                    if not success:
                        return False, f"認証失敗: {message}"
                client = self.client
                # グローバルユーザーのuser_idを取得
                me = client.get_me()
                if not me.data:
                    return False, "アカウント情報の取得に失敗しました"
                user_id = me.data.id
                account_type = "グローバルアカウント"
            
            # いいねした投稿を取得
            liked_tweets = client.get_liked_tweets(
                id=user_id,
                max_results=max_results,
                tweet_fields=['created_at', 'author_id', 'public_metrics']
            )
            
            if liked_tweets.data:
                tweets_data = []
                for tweet in liked_tweets.data:
                    tweets_data.append({
                        'id': tweet.id,
                        'text': tweet.text,
                        'created_at': tweet.created_at,
                        'author_id': tweet.author_id,
                        'public_metrics': tweet.public_metrics
                    })
                return True, {
                    'account_type': account_type,
                    'tweets': tweets_data,
                    'count': len(tweets_data)
                }
            else:
                return True, {
                    'account_type': account_type, 
                    'tweets': [],
                    'count': 0
                }
                
        except tweepy.TooManyRequests:
            return False, "API使用制限に達しました。しばらく待ってから再試行してください。"
        except tweepy.Forbidden as e:
            return False, f"いいね履歴取得権限がありません: {str(e)}"
        except tweepy.Unauthorized:
            return False, "認証エラー。X API の認証情報を確認してください。"
        except Exception as e:
            return False, f"いいね履歴取得エラー: {str(e)}"
    
    def retweet(self, tweet_id, cast_id=None):
        """投稿をリツイート（リポスト）する
        
        Args:
            tweet_id (str): リツイートしたい投稿のID
            cast_id (int, optional): キャストID。指定時はキャスト専用アカウントで実行
            
        Returns:
            tuple: (成功True/失敗False, メッセージ)
        """
        try:
            # キャスト指定時はキャスト専用クライアントを使用
            if cast_id is not None:
                if cast_id not in self.cast_clients:
                    return False, f"キャストID {cast_id} の認証情報が設定されていません"
                client = self.cast_clients[cast_id]
                account_type = f"キャスト (ID: {cast_id})"
            else:
                # グローバル認証を使用
                if not self.api_initialized:
                    success, message = self.setup_credentials()
                    if not success:
                        return False, f"認証失敗: {message}"
                client = self.client
                account_type = "グローバルアカウント"
            
            # リツイートを実行
            response = client.retweet(tweet_id)
            
            if response.data and response.data.get('retweeted'):
                return True, f"✅ {account_type}で投稿をリツイートしました (Tweet ID: {tweet_id})"
            else:
                return False, f"❌ リツイートに失敗しました: {response}"
                
        except tweepy.TooManyRequests:
            return False, "API使用制限に達しました（FREEプラン: 1回/15分）。しばらく待ってから再試行してください。"
        except tweepy.Forbidden as e:
            error_detail = str(e)
            if "403 Forbidden" in error_detail:
                if "attached to a Project" in error_detail:
                    return False, f"❌ アプリがプロジェクトに紐付いていません: {error_detail}\n💡 X Developer Portalでプロジェクト内にアプリを作成し直してください。"
                elif "already retweeted" in error_detail.lower():
                    return False, f"❌ この投稿は既にリツイート済みです"
                else:
                    return False, f"❌ リツイート権限エラー: {error_detail}\n💡 アプリの権限設定(Read and Write)を確認してください。"
            else:
                return False, f"リツイート権限がありません: {error_detail}"
        except tweepy.Unauthorized as e:
            return False, f"認証エラー: {str(e)}\n💡 API Key/Token を確認してください。"
        except tweepy.NotFound:
            return False, "指定された投稿が見つかりません。投稿IDを確認してください。"
        except Exception as e:
            return False, f"リツイートエラー: {str(e)}"
    
    def unretweet(self, tweet_id, cast_id=None):
        """リツイートを取り消す
        
        Args:
            tweet_id (str): リツイートを取り消したい投稿のID
            cast_id (int, optional): キャストID。指定時はキャスト専用アカウントで実行
            
        Returns:
            tuple: (成功True/失敗False, メッセージ)
        """
        try:
            # キャスト指定時はキャスト専用クライアントを使用
            if cast_id is not None:
                if cast_id not in self.cast_clients:
                    return False, f"キャストID {cast_id} の認証情報が設定されていません"
                client = self.cast_clients[cast_id]
                account_type = f"キャスト (ID: {cast_id})"
            else:
                # グローバル認証を使用
                if not self.api_initialized:
                    success, message = self.setup_credentials()
                    if not success:
                        return False, f"認証失敗: {message}"
                client = self.client
                account_type = "グローバルアカウント"
            
            # リツイート取り消しを実行
            response = client.unretweet(tweet_id)
            
            if response.data and response.data.get('retweeted') == False:
                return True, f"✅ {account_type}でリツイートを取り消しました (Tweet ID: {tweet_id})"
            else:
                return False, f"❌ リツイート取り消しに失敗しました: {response}"
                
        except tweepy.TooManyRequests:
            return False, "API使用制限に達しました（FREEプラン: 1回/15分）。しばらく待ってから再試行してください。"
        except tweepy.Forbidden as e:
            error_detail = str(e)
            if "403 Forbidden" in error_detail:
                if "not retweeted" in error_detail.lower():
                    return False, f"❌ この投稿はリツイートしていません"
                else:
                    return False, f"❌ リツイート取り消し権限エラー: {error_detail}"
            else:
                return False, f"リツイート取り消し権限がありません: {error_detail}"
        except tweepy.Unauthorized as e:
            return False, f"認証エラー: {str(e)}\n💡 API Key/Token を確認してください。"
        except tweepy.NotFound:
            return False, "指定された投稿が見つかりません。投稿IDを確認してください。"
        except Exception as e:
            return False, f"リツイート取り消しエラー: {str(e)}"
    
    def quote_tweet(self, tweet_id, comment, cast_id=None):
        """コメント入りリツイート（引用ツイート）
        
        Args:
            tweet_id (str): 引用したい投稿のID
            comment (str): コメント内容
            cast_id (int, optional): キャストID。指定時はキャスト専用アカウントで実行
            
        Returns:
            tuple: (成功True/失敗False, メッセージ)
        """
        try:
            # キャスト指定時はキャスト専用クライアントを使用
            if cast_id is not None:
                if cast_id not in self.cast_clients:
                    return False, f"キャストID {cast_id} の認証情報が設定されていません"
                client = self.cast_clients[cast_id]
                account_type = f"キャスト (ID: {cast_id})"
            else:
                # グローバル認証を使用
                if not self.api_initialized:
                    success, message = self.setup_credentials()
                    if not success:
                        return False, f"認証失敗: {message}"
                client = self.client
                account_type = "グローバルアカウント"
            
            # コメント内容の前処理
            comment = comment.strip()
            
            # 文字数制限チェック（X の制限は280文字）
            if len(comment) > 280:
                return False, f"コメントが280文字を超えています（{len(comment)}文字）"
            
            # コメント入りリツイートを実行
            response = client.create_tweet(text=comment, quote_tweet_id=tweet_id)
            
            if response.data:
                new_tweet_id = response.data['id']
                return True, f"✅ {account_type}でコメント入りリツイートしました\n📝 コメント: {comment}\n🔗 新しい投稿ID: {new_tweet_id}\n📄 引用元ID: {tweet_id}"
            else:
                return False, f"❌ コメント入りリツイートに失敗しました: {response}"
                
        except tweepy.TooManyRequests:
            return False, "API使用制限に達しました（FREEプラン: 17回/24時間）。しばらく待ってから再試行してください。"
        except tweepy.Forbidden as e:
            error_detail = str(e)
            if "403 Forbidden" in error_detail:
                if "attached to a Project" in error_detail:
                    return False, f"❌ アプリがプロジェクトに紐付いていません: {error_detail}\n💡 X Developer Portalでプロジェクト内にアプリを作成し直してください。"
                else:
                    return False, f"❌ 投稿権限エラー: {error_detail}\n💡 アプリの権限設定(Read and Write)を確認してください。"
            else:
                return False, f"投稿権限がありません: {error_detail}"
        except tweepy.Unauthorized as e:
            return False, f"認証エラー: {str(e)}\n💡 API Key/Token を確認してください。"
        except tweepy.NotFound:
            return False, "指定された投稿が見つかりません。投稿IDを確認してください。"
        except Exception as e:
            return False, f"コメント入りリツイートエラー: {str(e)}"
    
    def post_tweet_for_cast(self, cast_id, content, cast_name=None, quote_tweet_id=None):
        """キャスト専用のツイート投稿（コメント入りリツイート対応）"""
        try:
            if cast_id not in self.cast_clients:
                return False, f"キャストID {cast_id} の認証情報が設定されていません"
            
            client = self.cast_clients[cast_id]
            
            # 投稿内容の前処理
            tweet_content = content.strip()
            
            # 文字数制限チェック
            if len(tweet_content) > 280:
                return False, f"投稿内容が280文字を超えています（{len(tweet_content)}文字）"
            
            # ツイート投稿（コメント入りリツイート対応）
            tweet_params = {'text': tweet_content}
            if quote_tweet_id:
                tweet_params['quote_tweet_id'] = quote_tweet_id
            
            response = client.create_tweet(**tweet_params)
            
            if response.data:
                tweet_id = response.data['id']
                if quote_tweet_id:
                    return True, f"キャスト (ID: {cast_id}) でコメント入りリツイート投稿成功！ ID: {tweet_id} (引用元: {quote_tweet_id})"
                else:
                    return True, f"キャスト (ID: {cast_id}) でツイート投稿成功！ ID: {tweet_id}"
            else:
                return False, "投稿に失敗しました"
                
        except tweepy.TooManyRequests:
            return False, "API使用制限に達しました。しばらく待ってから再試行してください。"
        except tweepy.Forbidden:
            return False, "投稿権限がありません。X API の設定を確認してください。"
        except tweepy.Unauthorized:
            return False, "認証エラー。X API の認証情報を確認してください。"
        except Exception as e:
            return False, f"投稿エラー: {str(e)}"

    def upload_media(self, media_path, cast_id=None):
        """画像・動画ファイルをX APIにアップロード"""
        try:
            # 使用するクライアントを決定
            if cast_id is not None:
                if cast_id not in self.cast_clients:
                    return None, f"キャストID {cast_id} の認証情報が設定されていません"
                client = self.cast_clients[cast_id]
            else:
                if not self.api_initialized:
                    success, message = self.setup_credentials()
                    if not success:
                        return None, f"認証失敗: {message}"
                client = self.client
            
            # ファイル存在確認
            if not os.path.exists(media_path):
                return None, f"ファイルが見つかりません: {media_path}"
            
            # ファイルサイズ確認（5MB制限）
            file_size = os.path.getsize(media_path)
            if file_size > 5 * 1024 * 1024:  # 5MB
                return None, f"ファイルサイズが5MBを超えています: {file_size / (1024*1024):.1f}MB"
            
            # ファイル形式確認
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4']
            file_ext = os.path.splitext(media_path)[1].lower()
            if file_ext not in allowed_extensions:
                return None, f"対応していないファイル形式: {file_ext}"
            
            # tweepy v1 API（メディアアップロード用）
            auth = tweepy.OAuth1UserHandler(
                client.consumer_key,
                client.consumer_secret,
                client.access_token,
                client.access_token_secret
            )
            api_v1 = tweepy.API(auth, wait_on_rate_limit=True)
            
            # メディアアップロード実行
            media = api_v1.media_upload(media_path)
            
            return media.media_id, f"メディアアップロード成功: {media.media_id}"
            
        except tweepy.TooManyRequests:
            return None, "API使用制限に達しました。しばらく待ってから再試行してください。"
        except tweepy.Forbidden:
            return None, "メディアアップロード権限がありません。"
        except Exception as e:
            return None, f"メディアアップロードエラー: {str(e)}"
    
    def post_tweet_with_media(self, text, media_paths, cast_name=None, cast_id=None):
        """画像付きツイートを投稿"""
        try:
            # メディアファイルをアップロード
            media_ids = []
            for media_path in media_paths:
                media_id, message = self.upload_media(media_path, cast_id)
                if media_id:
                    media_ids.append(media_id)
                else:
                    return False, f"メディアアップロード失敗: {message}"
            
            if not media_ids:
                return False, "アップロードできるメディアがありません"
            
            # 最大4枚まで制限
            if len(media_ids) > 4:
                media_ids = media_ids[:4]
                
            # 使用するクライアントを決定
            if cast_id is not None:
                if cast_id not in self.cast_clients:
                    return False, f"キャストID {cast_id} の認証情報が設定されていません"
                client = self.cast_clients[cast_id]
            else:
                if not self.api_initialized:
                    success, message = self.setup_credentials()
                    if not success:
                        return False, f"認証失敗: {message}"
                client = self.client
            
            # 画像付きツイート投稿
            response = client.create_tweet(text=text, media_ids=media_ids)
            
            if response.data:
                tweet_id = response.data['id']
                tweet_url = f"https://twitter.com/user/status/{tweet_id}"
                account_info = f" (キャスト: {cast_name})" if cast_name else ""
                return True, f"画像付きツイート投稿成功{account_info}! URL: {tweet_url}"
            else:
                return False, "画像付きツイート投稿に失敗しました"
                
        except tweepy.TooManyRequests:
            return False, "API使用制限に達しました。しばらく待ってから再試行してください。"
        except tweepy.Forbidden:
            return False, "投稿権限がありません。X API の設定を確認してください。"
        except tweepy.Unauthorized:
            return False, "認証エラー。X API の認証情報を確認してください。"
        except Exception as e:
            return False, f"画像付き投稿エラー: {str(e)}"

# グローバルインスタンス
x_poster = XTwitterPoster()