#!/usr/bin/env python3
"""
🔐 Google Drive認証コード処理
提供された認証コードを使用してトークンを生成
"""

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials/google_drive_credentials.json'
TOKEN_FILE = 'credentials/google_drive_token.pickle'

def manual_auth_with_code():
    """手動認証コード処理"""
    print("🔐 Google Drive 手動認証開始")
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ 認証ファイルが見つかりません: {CREDENTIALS_FILE}")
        return False
    
    try:
        # OAuth flow の初期化
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE, SCOPES)
        
        # 認証コードを直接設定
        auth_code = "4/0AVGzR1ATV7_YSmZVkQqXQ0zvcSPvrjTcqGwVQxiWHMugW5worSS-04G7bG0oPvos54AcTg"
        
        # リダイレクトURIを設定（認証情報ファイルに合わせる）
        flow.redirect_uri = 'http://localhost'
        
        # 認証コードからトークンを取得
        print("🔄 認証コードからトークンを生成中...")
        creds = flow.fetch_token(code=auth_code)
        
        # 認証情報オブジェクトを作成
        credentials = flow.credentials
        
        # トークンの保存
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)
        
        print("✅ 認証成功！トークンを保存しました")
        print(f"📄 トークンファイル: {TOKEN_FILE}")
        
        # 認証情報の確認
        print(f"🔑 アクセストークン: {credentials.token[:20]}...")
        print(f"🔄 リフレッシュトークン: {'あり' if credentials.refresh_token else 'なし'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 認証エラー: {e}")
        print("💡 以下を確認してください:")
        print("1. 認証コードが正しいか")
        print("2. 認証情報ファイルが正しいか")
        print("3. Google Drive APIが有効化されているか")
        return False

if __name__ == "__main__":
    if manual_auth_with_code():
        print("\n🎯 次のステップ:")
        print("python3 test_google_drive.py  # バックアップテスト")
    else:
        print("\n❌ 認証に失敗しました")