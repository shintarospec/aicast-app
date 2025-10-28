#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OAuth 2.0トークンリフレッシュスクリプト

期限切れのAccess Tokenを Refresh Token で更新します。
"""

import os
import sys
import sqlite3
import tweepy
from datetime import datetime, timedelta

# 開発環境用（HTTP許可）
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def get_cast_oauth2_credentials(cast_id):
    """DBからOAuth 2.0認証情報を取得"""
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

def update_oauth2_tokens(cast_id, new_access_token, new_refresh_token, expires_at):
    """DBのOAuth 2.0トークンを更新"""
    conn = sqlite3.connect('casting_office.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE cast_x_credentials 
        SET oauth2_access_token = ?,
            oauth2_refresh_token = ?,
            oauth2_token_expires_at = ?,
            updated_at = ?
        WHERE cast_id = ?
    """, (new_access_token, new_refresh_token, expires_at, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cast_id))
    
    conn.commit()
    conn.close()

def refresh_oauth2_token(cast_id):
    """OAuth 2.0トークンをリフレッシュ"""
    print(f"=" * 60)
    print(f"OAuth 2.0トークンリフレッシュ")
    print(f"=" * 60)
    
    # 1. DBから認証情報を取得
    print(f"\n🔍 キャストID {cast_id} の認証情報を取得中...")
    creds = get_cast_oauth2_credentials(cast_id)
    
    if not creds:
        print(f"❌ キャストID {cast_id} の認証情報が見つかりません")
        return False
    
    if not creds.get('client_id') or not creds.get('client_secret'):
        print(f"❌ OAuth 2.0のClient IDまたはClient Secretが設定されていません")
        return False
    
    if not creds.get('oauth2_refresh_token'):
        print(f"❌ Refresh Tokenが設定されていません")
        print(f"💡 python3 x_oauth2_simple.py で再認証してください")
        return False
    
    print(f"✅ Client ID: {creds['client_id'][:20]}...")
    print(f"✅ Client Secret: {creds['client_secret'][:20]}...")
    print(f"✅ Refresh Token: {creds['oauth2_refresh_token'][:20]}...")
    
    # 2. OAuth 2.0ハンドラーを作成
    print(f"\n🔄 トークンをリフレッシュ中...")
    try:
        oauth2_user_handler = tweepy.OAuth2UserHandler(
            client_id=creds['client_id'],
            client_secret=creds['client_secret'],
            redirect_uri="http://127.0.0.1:8080/callback",
            scope=["tweet.read", "tweet.write", "users.read", "like.read", "like.write", "offline.access"]
        )
        
        # Refresh Tokenを使って新しいAccess Tokenを取得
        new_token = oauth2_user_handler.refresh_token(
            f"https://api.x.com/2/oauth2/token",
            refresh_token=creds['oauth2_refresh_token'],
            body=f"grant_type=refresh_token&client_id={creds['client_id']}"
        )
        
        new_access_token = new_token['access_token']
        new_refresh_token = new_token.get('refresh_token', creds['oauth2_refresh_token'])
        expires_in = new_token.get('expires_in', 7200)  # デフォルト2時間
        
        expires_at = (datetime.now() + timedelta(seconds=expires_in)).strftime('%Y-%m-%dT%H:%M:%S')
        
        print(f"✅ 新しいAccess Token: {new_access_token[:20]}...")
        print(f"✅ 新しいRefresh Token: {new_refresh_token[:20]}...")
        print(f"✅ 有効期限: {expires_at}")
        
        # 3. DBを更新
        print(f"\n💾 DBを更新中...")
        update_oauth2_tokens(cast_id, new_access_token, new_refresh_token, expires_at)
        print(f"✅ DB更新完了")
        
        print(f"\n" + "=" * 60)
        print(f"✅ トークンリフレッシュ完了！")
        print(f"=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        return False

def main():
    if len(sys.argv) > 1:
        cast_id = int(sys.argv[1])
    else:
        cast_id = int(input("キャストIDを入力してください: "))
    
    refresh_oauth2_token(cast_id)

if __name__ == "__main__":
    main()
