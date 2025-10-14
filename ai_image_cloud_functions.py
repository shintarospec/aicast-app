# AI画像投稿用Cloud Functions連携モジュール
import requests
import json
import streamlit as st
from ai_image_db import update_img_post_status

class AIImageCloudFunctionsPoster:
    """AI画像投稿専用のCloud Functions投稿クライアント"""
    
    def __init__(self):
        # Cloud Functions URL（既存のものを使用）
        self.cloud_functions_url = "https://us-central1-aicast-472807.cloudfunctions.net/x-poster"
    
    def post_image_with_text(self, image_path, text, cast_credentials, img_post_id=None):
        """画像とテキストをCloud Functions経由でX APIに投稿"""
        
        try:
            # 画像ファイルを読み込み
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # Cloud Functionsに送信するペイロード
            payload = {
                "action": "post_with_image",
                "text": text,
                "image_data": image_data.hex(),  # バイナリデータを16進文字列に変換
                "credentials": {
                    "api_key": cast_credentials['api_key'],
                    "api_secret": cast_credentials['api_secret'],
                    "access_token": cast_credentials['access_token'],
                    "access_token_secret": cast_credentials['access_token_secret'],
                    "bearer_token": cast_credentials['bearer_token']
                }
            }
            
            # 投稿ステータスを更新
            if img_post_id:
                update_img_post_status(img_post_id, "posting")
            
            # Cloud Functionsに投稿
            response = requests.post(
                self.cloud_functions_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    tweet_id = result.get('tweet_id')
                    
                    # 成功時のステータス更新
                    if img_post_id:
                        update_img_post_status(
                            img_post_id, 
                            "posted",
                            tweet_id=tweet_id,
                            posted_at=datetime.datetime.now().isoformat()
                        )
                    
                    return True, f"✅ 投稿成功！Tweet ID: {tweet_id}"
                else:
                    error_msg = result.get('error', '不明なエラー')
                    
                    # 失敗時のステータス更新
                    if img_post_id:
                        update_img_post_status(
                            img_post_id, 
                            "failed",
                            error_message=error_msg
                        )
                    
                    return False, f"❌ 投稿失敗: {error_msg}"
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                
                # 失敗時のステータス更新
                if img_post_id:
                    update_img_post_status(
                        img_post_id, 
                        "failed",
                        error_message=error_msg
                    )
                
                return False, f"❌ Cloud Functions エラー: {error_msg}"
                
        except requests.exceptions.Timeout:
            error_msg = "タイムアウトエラー（30秒）"
            
            if img_post_id:
                update_img_post_status(img_post_id, "failed", error_message=error_msg)
            
            return False, f"❌ {error_msg}"
            
        except Exception as e:
            error_msg = str(e)
            
            if img_post_id:
                update_img_post_status(img_post_id, "failed", error_message=error_msg)
            
            return False, f"❌ 予期しないエラー: {error_msg}"
    
    def post_image_with_url(self, image_url, text, cast_credentials, img_post_id=None):
        """画像URLとテキストをCloud Functions経由でX APIに投稿"""
        
        try:
            # Cloud Functionsに送信するペイロード（URL版）
            payload = {
                "action": "post_with_image_url",
                "text": text,
                "image_url": image_url,
                "credentials": {
                    "api_key": cast_credentials['api_key'],
                    "api_secret": cast_credentials['api_secret'],
                    "access_token": cast_credentials['access_token'],
                    "access_token_secret": cast_credentials['access_token_secret'],
                    "bearer_token": cast_credentials['bearer_token']
                }
            }
            
            # 投稿ステータスを更新
            if img_post_id:
                update_img_post_status(img_post_id, "posting")
            
            # Cloud Functionsに投稿
            response = requests.post(
                self.cloud_functions_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    tweet_id = result.get('tweet_id')
                    
                    # 成功時のステータス更新
                    if img_post_id:
                        import datetime
                        update_img_post_status(
                            img_post_id, 
                            "posted",
                            tweet_id=tweet_id,
                            posted_at=datetime.datetime.now().isoformat()
                        )
                    
                    return True, f"✅ 投稿成功！Tweet ID: {tweet_id}"
                else:
                    error_msg = result.get('error', '不明なエラー')
                    
                    # 失敗時のステータス更新
                    if img_post_id:
                        update_img_post_status(
                            img_post_id, 
                            "failed",
                            error_message=error_msg
                        )
                    
                    return False, f"❌ 投稿失敗: {error_msg}"
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                
                # 失敗時のステータス更新
                if img_post_id:
                    update_img_post_status(
                        img_post_id, 
                        "failed",
                        error_message=error_msg
                    )
                
                return False, f"❌ Cloud Functions エラー: {error_msg}"
                
        except Exception as e:
            error_msg = str(e)
            
            if img_post_id:
                update_img_post_status(img_post_id, "failed", error_message=error_msg)
            
            return False, f"❌ 予期しないエラー: {error_msg}"

# グローバルインスタンス
ai_image_cf_poster = AIImageCloudFunctionsPoster()

# 便利関数
def post_ai_image_to_x(image_path, text, cast_credentials, img_post_id=None):
    """AI生成画像をX APIに投稿する便利関数"""
    return ai_image_cf_poster.post_image_with_text(
        image_path, text, cast_credentials, img_post_id
    )

def post_ai_image_url_to_x(image_url, text, cast_credentials, img_post_id=None):
    """AI生成画像（URL）をX APIに投稿する便利関数"""
    return ai_image_cf_poster.post_image_with_url(
        image_url, text, cast_credentials, img_post_id
    )