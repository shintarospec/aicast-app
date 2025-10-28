#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OAuth 2.0いいね機能テストスクリプト

キャストID 14（OAuth 2.0認証済み）でいいね機能をテストします。
"""

import sys
import os
import sqlite3

# x_api_poster をインポート
from x_api_poster import XTwitterPoster

def get_cast_oauth2_token(cast_id):
    """DBからOAuth 2.0トークンを取得"""
    conn = sqlite3.connect('casting_office.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT oauth2_access_token 
        FROM cast_x_credentials 
        WHERE cast_id = ? AND is_active = 1
    """, (cast_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result['oauth2_access_token']
    return None

def get_cast_credentials(cast_id):
    """DBからキャストの全認証情報を取得"""
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

def main():
    print("=" * 60)
    print("OAuth 2.0いいね機能テスト")
    print("=" * 60)
    
    # テストパラメータ
    CAST_ID = 14
    TEST_TWEET_ID = "1978113656660344837"  # テスト用投稿ID
    
    print(f"\n📋 テスト設定:")
    print(f"  - キャストID: {CAST_ID}")
    print(f"  - 投稿ID: {TEST_TWEET_ID}")
    
    # 1. OAuth 2.0トークンの確認
    print(f"\n🔍 ステップ1: OAuth 2.0トークンの確認")
    oauth2_token = get_cast_oauth2_token(CAST_ID)
    if oauth2_token:
        print(f"  ✅ OAuth 2.0トークンあり: {oauth2_token[:20]}...")
    else:
        print(f"  ❌ OAuth 2.0トークンなし")
        print(f"\n💡 解決方法: python3 x_oauth2_simple.py を実行してOAuth 2.0認証を完了してください")
        return
    
    # 2. 全認証情報の取得
    print(f"\n🔍 ステップ2: 全認証情報の取得")
    creds = get_cast_credentials(CAST_ID)
    if not creds:
        print(f"  ❌ キャストID {CAST_ID} の認証情報が見つかりません")
        return
    
    print(f"  ✅ API Key: {creds['api_key'][:10]}...")
    print(f"  ✅ API Secret: {creds['api_secret'][:10]}...")
    print(f"  ✅ Bearer Token: {creds['bearer_token'][:10]}...")
    print(f"  ✅ Access Token: {creds['access_token'][:10]}...")
    print(f"  ✅ Access Token Secret: {creds['access_token_secret'][:10]}...")
    print(f"  ✅ OAuth 2.0 Token: {creds['oauth2_access_token'][:10]}...")
    
    # 3. XAPIクライアント初期化
    print(f"\n🔍 ステップ3: XAPIクライアントの初期化")
    x_poster = XTwitterPoster()
    
    # 4. キャスト認証の設定
    print(f"\n🔍 ステップ4: キャスト認証の設定")
    success, message, user_data = x_poster.setup_cast_credentials(
        CAST_ID,
        creds['api_key'],
        creds['api_secret'],
        creds['bearer_token'],
        creds['access_token'],
        creds['access_token_secret'],
        oauth2_access_token=creds.get('oauth2_access_token')
    )
    
    if not success:
        print(f"  ❌ 認証設定失敗: {message}")
        return
    
    print(f"  ✅ {message}")
    if user_data:
        print(f"  📊 アカウント情報: @{user_data.username} ({user_data.name})")
    
    # 5. OAuth 2.0クライアントの確認
    print(f"\n🔍 ステップ5: OAuth 2.0クライアントの確認")
    print(f"  登録済みOAuth 1.0aクライアント: {list(x_poster.cast_clients.keys())}")
    print(f"  登録済みOAuth 2.0クライアント: {list(x_poster.cast_oauth2_clients.keys())}")
    
    if CAST_ID in x_poster.cast_oauth2_clients:
        print(f"  ✅ OAuth 2.0クライアント登録済み")
        oauth2_client = x_poster.cast_oauth2_clients[CAST_ID]
        print(f"  OAuth 2.0クライアントタイプ: {type(oauth2_client)}")
    else:
        print(f"  ❌ OAuth 2.0クライアント未登録")
        return
    
    # 6. いいねテスト
    print(f"\n🔍 ステップ6: いいね機能テスト")
    print(f"  投稿ID {TEST_TWEET_ID} にいいねします...")
    success, message = x_poster.like_tweet(TEST_TWEET_ID, cast_id=CAST_ID)
    
    if success:
        print(f"  ✅ {message}")
    else:
        print(f"  ❌ {message}")
        return
    
    # 7. いいね取り消しテスト
    print(f"\n🔍 ステップ7: いいね取り消しテスト")
    print(f"  投稿ID {TEST_TWEET_ID} のいいねを取り消します...")
    success, message = x_poster.unlike_tweet(TEST_TWEET_ID, cast_id=CAST_ID)
    
    if success:
        print(f"  ✅ {message}")
    else:
        print(f"  ❌ {message}")
        return
    
    # 8. 最終確認: もう一度いいね
    print(f"\n🔍 ステップ8: 最終確認（再度いいね）")
    success, message = x_poster.like_tweet(TEST_TWEET_ID, cast_id=CAST_ID)
    
    if success:
        print(f"  ✅ {message}")
    else:
        print(f"  ❌ {message}")
    
    print("\n" + "=" * 60)
    print("✅ OAuth 2.0いいね機能テスト完了！")
    print("=" * 60)

if __name__ == "__main__":
    main()
