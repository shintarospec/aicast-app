#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OAuth 2.0で直接X API v2を呼び出していいね機能をテスト
"""

import requests
import sqlite3

def get_cast_credentials(cast_id):
    """DBからキャスト認証情報を取得"""
    conn = sqlite3.connect('casting_office.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * 
        FROM cast_x_credentials 
        WHERE cast_id = ? AND is_active = 1
    """, (cast_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    return None

def like_tweet_direct(oauth2_token, tweet_id, twitter_user_id):
    """OAuth 2.0で直接X API v2のいいねエンドポイントを呼び出す"""
    url = f"https://api.x.com/2/users/{twitter_user_id}/likes"
    
    headers = {
        "Authorization": f"Bearer {oauth2_token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "tweet_id": tweet_id
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    return response

def main():
    print("=" * 60)
    print("OAuth 2.0直接API呼び出しテスト")
    print("=" * 60)
    
    CAST_ID = 14
    TEST_TWEET_ID = "1978113656660344837"
    
    # 認証情報を取得
    creds = get_cast_credentials(CAST_ID)
    
    if not creds:
        print(f"❌ キャストID {CAST_ID} の認証情報が見つかりません")
        return
    
    oauth2_token = creds.get('oauth2_access_token')
    twitter_user_id = creds.get('twitter_user_id')
    
    if not oauth2_token:
        print(f"❌ OAuth 2.0 Access Tokenが設定されていません")
        return
    
    if not twitter_user_id:
        print(f"❌ Twitter User IDが設定されていません")
        return
    
    print(f"\n📋 テスト設定:")
    print(f"  - キャストID: {CAST_ID}")
    print(f"  - 投稿ID: {TEST_TWEET_ID}")
    print(f"  - Twitter User ID: {twitter_user_id}")
    print(f"  - OAuth 2.0 Token: {oauth2_token[:20]}...")
    
    print(f"\n🔍 いいね実行中...")
    response = like_tweet_direct(oauth2_token, TEST_TWEET_ID, twitter_user_id)
    
    print(f"\n📊 レスポンス:")
    print(f"  - ステータスコード: {response.status_code}")
    print(f"  - レスポンス: {response.text}")
    
    if response.status_code == 200:
        print(f"\n✅ いいね成功！")
    else:
        print(f"\n❌ いいね失敗")

if __name__ == "__main__":
    main()
