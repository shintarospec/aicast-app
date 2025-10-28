#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAuth 2.0認証フロー"""

import os
import sqlite3
import tweepy
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def get_all_casts():
    conn = sqlite3.connect('casting_office.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, name, nickname FROM casts WHERE is_active = 1 ORDER BY id")
    except sqlite3.OperationalError:
        # is_activeカラムがない場合
        cursor.execute("SELECT id, name, nickname FROM casts ORDER BY id")
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def update_cast_oauth2_credentials(cast_id, client_id, client_secret, access_token, refresh_token, expires_at):
    conn = sqlite3.connect('casting_office.db')
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE cast_x_credentials 
        SET client_id = ?, client_secret = ?, oauth2_access_token = ?,
            oauth2_refresh_token = ?, oauth2_token_expires_at = ?, updated_at = ?
        WHERE cast_id = ?
    """, (client_id, client_secret, access_token, refresh_token, expires_at,
          datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cast_id))
    conn.commit()
    conn.close()

def main():
    print("=" * 80)
    print("OAuth 2.0認証フロー")
    print("=" * 80)
    
    client_id = input("\nClient ID [a21EX2p6ZjU0R21SR0NHLU9PX0I6MTpjaQ]: ").strip()
    if not client_id:
        client_id = "a21EX2p6ZjU0R21SR0NHLU9PX0I6MTpjaQ"
    
    client_secret = input("Client Secret [DjF679OlDBSKXjyeDtb3fz9a3zYgEcwOd-unv3dKPCMMahsVAf]: ").strip()
    if not client_secret:
        client_secret = "DjF679OlDBSKXjyeDtb3fz9a3zYgEcwOd-unv3dKPCMMahsVAf"
    
    redirect_uri = "http://127.0.0.1:8080/callback"
    scopes = ["tweet.read", "tweet.write", "users.read", "like.read", "like.write", "offline.access"]
    
    try:
        oauth2_user_handler = tweepy.OAuth2UserHandler(
            client_id=client_id, client_secret=client_secret,
            redirect_uri=redirect_uri, scope=scopes
        )
        
        auth_url = oauth2_user_handler.get_authorization_url()
        
        print("\n" + "=" * 80)
        print("以下のURLをブラウザで開いて認証してください：")
        print("=" * 80)
        print(f"\n{auth_url}\n")
        print("=" * 80)
        
        callback_url = input("\n認証後のコールバックURL全体を貼り付けてください: ").strip()
        
        if not callback_url:
            print("コールバックURLが入力されませんでした")
            return
        
        query_params = parse_qs(urlparse(callback_url).query)
        if 'code' not in query_params:
            print("codeパラメータが見つかりません")
            return
        
        auth_code = query_params['code'][0]
        print(f"\n認証コード: {auth_code[:20]}...")
        
        # コールバックURL全体を渡してstateを検証
        token = oauth2_user_handler.fetch_token(callback_url)
        
        access_token = token['access_token']
        refresh_token = token.get('refresh_token')
        expires_in = token.get('expires_in', 7200)
        expires_at = (datetime.now() + timedelta(seconds=expires_in)).strftime('%Y-%m-%dT%H:%M:%S')
        
        print(f"\nAccess Token: {access_token[:30]}...")
        print(f"有効期限: {expires_at}")
        
        casts = get_all_casts()
        print("\n利用可能なキャスト：")
        for cast in casts:
            print(f"  {cast['id']}. {cast['name']}")
        
        cast_id_input = input("\nキャストID [14]: ").strip()
        cast_id = int(cast_id_input) if cast_id_input else 14
        
        update_cast_oauth2_credentials(cast_id, client_id, client_secret, access_token, refresh_token, expires_at)
        
        print(f"\n保存完了！キャストID {cast_id}")
        print("python3 test_oauth2_like.py でテストしてください")
        
    except Exception as e:
        print(f"\nエラー: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
