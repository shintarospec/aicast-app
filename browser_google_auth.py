#!/usr/bin/env python3
"""
🔐 Google Drive ブラウザ認証
標準的なOAuth フローを使用
"""

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials/google_drive_credentials.json'
TOKEN_FILE = 'credentials/google_drive_token.pickle'

def browser_auth():
    """ブラウザを使った標準認証"""
    print("🔐 Google Drive ブラウザ認証開始")
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ 認証ファイルが見つかりません: {CREDENTIALS_FILE}")
        return False
    
    try:
        creds = None
        
        # 既存トークンの確認
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        
        # 認証が必要な場合
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 トークンをリフレッシュ中...")
                creds.refresh(Request())
            else:
                print("🌐 ブラウザ認証を開始します...")
                print("📝 ブラウザが開きます。Googleアカウントでログインして認証を完了してください。")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                
                # ローカルサーバーを使った認証
                creds = flow.run_local_server(port=8080)
            
            # トークンの保存
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
            print("✅ 認証完了！トークンを保存しました")
        else:
            print("✅ 既存の有効なトークンが見つかりました")
        
        # Google Drive API の接続テスト
        print("🔄 Google Drive API 接続テスト中...")
        service = build('drive', 'v3', credentials=creds)
        
        # バックアップフォルダの確認/作成
        folder_name = 'AIcast-Room-Backups'
        results = service.files().list(
            q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        folders = results.get('files', [])
        
        if folders:
            folder_id = folders[0]['id']
            print(f"📁 既存バックアップフォルダを確認: {folders[0]['name']}")
        else:
            # 新規フォルダ作成
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            folder_id = folder.get('id')
            print(f"📁 新規バックアップフォルダを作成: {folder_name}")
        
        print(f"📂 フォルダID: {folder_id}")
        print("✅ Google Drive バックアップシステム準備完了！")
        
        return True
        
    except Exception as e:
        print(f"❌ 認証エラー: {e}")
        return False

if __name__ == "__main__":
    print("🌟 AIcast Room Google Drive バックアップ認証")
    print("=" * 50)
    
    if browser_auth():
        print("\n🎯 認証成功！次のステップ:")
        print("1. python3 test_google_drive.py  # 接続テスト")
        print("2. python3 google_drive_backup.py  # 完全バックアップ")
        print("3. ./cron_backup_setup.sh  # 自動化設定")
    else:
        print("\n❌ 認証に失敗しました")
        print("💡 トラブルシューティング:")
        print("1. Google Cloud Console でOAuth認証情報を確認")
        print("2. Google Drive API が有効化されているか確認")
        print("3. ポート8080が使用可能か確認")