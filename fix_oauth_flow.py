#!/usr/bin/env python3
"""
修正版OAuth認証スクリプト
redirect_uriを適切に設定してOAuth認証を完了します。
"""

import os
import json
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import gspread

def complete_oauth_with_manual_flow():
    """手動OAuth認証フロー"""
    print("🔐 手動OAuth認証フロー")
    print("=" * 30)
    
    # 認証ファイル
    creds_file = "credentials/client_secret_909115239455-fauih26mvj1g6hksfq9pub4okse90acg.apps.googleusercontent.com.json"
    token_file = creds_file.replace('.json', '_token.pickle')
    
    # スコープ
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    try:
        print(f"📂 認証ファイル: {creds_file}")
        
        # OAuth フロー（redirect_uri明示的に設定）
        flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
        
        # redirect_uriを明示的に設定
        flow.redirect_uri = "http://localhost"
        
        print("🔄 OAuth認証URL生成中...")
        auth_url, _ = flow.authorization_url(prompt='consent')
        
        print(f"🌐 認証URL: {auth_url}")
        print()
        print("📋 認証手順:")
        print("1. 上記URLにアクセス（既に完了済み）")
        print("2. Googleアカウントでログイン（既に完了済み）")
        print("3. アプリケーションを承認（既に完了済み）")
        print("4. 認証コードを取得（既に取得済み）")
        
        # 取得済み認証コード
        auth_code = "4/0AVGzR1D2lf7Sd-LHeAXOe2PnFoSeyaICrLAUB1osg0PyZckxgU2Y1Lm-ouQfiw0is9EpWA"
        
        print(f"🎫 認証コード: {auth_code[:20]}...")
        
        # 認証コードを使ってトークンを取得（redirect_uri追加）
        print("🔄 認証コードからトークン取得中...")
        flow.fetch_token(code=auth_code)
        
        credentials = flow.credentials
        
        # トークンファイルに保存
        with open(token_file, 'wb') as token:
            pickle.dump(credentials, token)
        
        print(f"✅ 認証トークン保存完了: {token_file}")
        
        # Google Sheets接続テスト
        print("🧪 Google Sheets接続テスト...")
        gc = gspread.authorize(credentials)
        
        # テスト用スプレッドシート
        test_sheet_id = "1B3TLHJsU8gH1eWIj6ZIBpsS7kEwIZKsawVQjQevTEtCoTk2-K5jRS2ckZPUnIlCQ"
        
        try:
            sheet = gc.open_by_key(test_sheet_id)
            worksheet = sheet.sheet1
            
            print(f"✅ スプレッドシート接続成功: {sheet.title}")
            
            # テストデータ書き込み
            from datetime import datetime
            test_data = [
                "AIcast Room テスト", 
                "OAuth認証完了", 
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "キャスト別Google Sheets機能"
            ]
            
            worksheet.append_row(test_data)
            print(f"✅ テストデータ書き込み成功")
            print(f"📊 Google Sheetsで確認してください")
            
        except Exception as e:
            print(f"❌ スプレッドシート接続エラー: {e}")
            
    except Exception as e:
        print(f"❌ OAuth認証エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    complete_oauth_with_manual_flow()
