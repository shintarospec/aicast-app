#!/usr/bin/env python3
"""
手動でOAuth認証を完了するスクリプト
"""
import json
import pickle
import os
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow

def manual_oauth():
    """手動でOAuth認証を完了"""
    
    # 認証情報の読み込み
    credentials_path = "credentials/credentials.json"
    if not os.path.exists(credentials_path):
        print("❌ credentials/credentials.json が見つかりません")
        return False
    
    # OAuth 2.0フローの設定
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    flow = Flow.from_client_secrets_file(
        credentials_path,
        scopes=SCOPES
    )
    
    # リダイレクトURIを設定（ランダムポートを使用）
    flow.redirect_uri = 'http://localhost:58591/'
    
    print("📍 認証URLを生成中...")
    auth_url, _ = flow.authorization_url(access_type='offline')
    
    print(f"🔗 認証URL: {auth_url}")
    print("\n📋 手順:")
    print("1. 上記URLをブラウザで開く")
    print("2. Google認証を完了")
    print("3. エラーページのURLをコピー")
    print("4. 下記に認証コードを入力")
    
    # 認証コードの入力
    auth_code = input("\n🔑 認証コードを入力してください: ").strip()
    
    try:
        # 認証コードを使用してトークンを取得
        flow.fetch_token(code=auth_code)
        
        # トークンを保存
        token_path = "credentials/token.pickle"
        with open(token_path, 'wb') as token:
            pickle.dump(flow.credentials, token)
        
        print(f"✅ OAuth認証が完了しました！")
        print(f"📁 トークンファイル: {token_path}")
        return True
        
    except Exception as e:
        print(f"❌ 認証エラー: {e}")
        return False

if __name__ == "__main__":
    manual_oauth()