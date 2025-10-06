#!/usr/bin/env python3
"""
新しい認証コード取得ヘルパー
期限切れ認証コードの問題を解決するため、新しい認証URLと認証コードを取得します。
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow

def generate_fresh_auth_url():
    """新しい認証URLを生成"""
    print("🔄 新しいOAuth認証コード取得ヘルパー")
    print("=" * 50)
    
    # 認証ファイル
    creds_file = "credentials/client_secret_909115239455-fauih26mvj1g6hksfq9pub4okse90acg.apps.googleusercontent.com.json"
    
    # スコープ
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    try:
        # OAuth フロー作成
        flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
        flow.redirect_uri = "http://localhost"
        
        # 新しい認証URLを生成
        auth_url, state = flow.authorization_url(prompt='consent')
        
        print("✅ 新しい認証URL生成完了！")
        print()
        print("🌐 新しい認証URL:")
        print(f"   {auth_url}")
        print()
        print("📋 手順:")
        print("1. 上記URLをコピーしてブラウザで開く")
        print("2. Googleアカウントでログイン")
        print("3. アプリを承認")
        print("4. 表示される新しい認証コードをコピー")
        print("5. AIcast Roomで新しい認証コードを入力")
        print()
        print("💡 ヒント:")
        print("- 認証コードは1回限り使用です")
        print("- 取得後は素早く入力してください")
        print("- エラーが続く場合は「認証をリセット」ボタンを使用")
        
        return auth_url
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return None

if __name__ == "__main__":
    generate_fresh_auth_url()