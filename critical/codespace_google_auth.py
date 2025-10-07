#!/usr/bin/env python3
"""
🌐 Codespace対応 Google Drive OAuth認証
ERR_CONNECTION_REFUSED問題を解決したCodespace専用認証システム
"""

import os
import pickle
import webbrowser
from urllib.parse import urlparse, parse_qs
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials/google_drive_credentials.json'
TOKEN_FILE = 'credentials/google_drive_token.pickle'

def codespace_auth():
    """Codespace環境対応のOAuth認証"""
    print("🌐 Codespace対応 Google Drive認証開始")
    print("=" * 50)
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ 認証ファイルが見つかりません: {CREDENTIALS_FILE}")
        return False
    
    try:
        creds = None
        
        # 既存トークンの確認
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
            
            if creds and creds.valid:
                print("✅ 既存の有効なトークンが見つかりました")
                return test_drive_connection(creds)
        
        # 新規認証が必要
        print("🔐 新規認証が必要です")
        print("\n📋 Codespace環境での認証手順:")
        print("1. 以下のURLをクリックしてブラウザで開く")
        print("2. Googleアカウントでログイン")
        print("3. 権限を許可")
        print("4. 表示された認証コードをコピー")
        print("5. この画面に認証コードを貼り付け")
        
        # OAuth flow初期化
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE, SCOPES)
        
        # 認証URLの生成（リダイレクトURIなし）
        flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
        
        auth_url, _ = flow.authorization_url(prompt='consent')
        
        print(f"\n🔗 認証URL:")
        print(f"{auth_url}")
        print("\n" + "="*80)
        
        # 認証コードの入力待ち
        auth_code = input("\n📝 認証コードを貼り付けてください: ").strip()
        
        if not auth_code:
            print("❌ 認証コードが入力されませんでした")
            return False
        
        print("🔄 認証コードからトークンを取得中...")
        
        # トークンの取得
        flow.fetch_token(code=auth_code)
        creds = flow.credentials
        
        # トークンの保存
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
        
        print("✅ 認証成功！トークンを保存しました")
        
        return test_drive_connection(creds)
        
    except Exception as e:
        print(f"❌ 認証エラー: {e}")
        print("\n💡 トラブルシューティング:")
        print("1. 認証コードが正しいかご確認ください")
        print("2. 認証コードの有効期限（通常10分）を確認してください")
        print("3. Google Cloud ConsoleでOAuth認証情報を確認してください")
        return False

def test_drive_connection(creds):
    """Google Drive API接続テスト"""
    try:
        print("\n🔄 Google Drive API 接続テスト中...")
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
            print("📁 バックアップフォルダを新規作成中...")
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
        
        # テストファイルのアップロード
        print("\n🧪 テストファイルアップロード中...")
        test_content = f"""# AIcast Room バックアップテスト

作成日時: {os.popen('date').read().strip()}
環境: GitHub Codespace
認証方式: OAuth 2.0 (urn:ietf:wg:oauth:2.0:oob)

✅ Google Drive API接続成功
📁 バックアップフォルダ: {folder_name}
🆔 フォルダID: {folder_id}

このファイルはテスト用です。削除して構いません。
"""
        
        test_file_path = 'test_backup_connection.txt'
        with open(test_file_path, 'w') as f:
            f.write(test_content)
        
        # アップロード実行
        file_metadata = {
            'name': f'backup_test_{os.popen("date +%Y%m%d_%H%M%S").read().strip()}.txt',
            'parents': [folder_id]
        }
        
        from googleapiclient.http import MediaFileUpload
        media = MediaFileUpload(test_file_path, mimetype='text/plain')
        
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name'
        ).execute()
        
        # テストファイル削除
        os.remove(test_file_path)
        
        print(f"✅ テストファイルアップロード成功: {uploaded_file['name']}")
        print(f"📄 ファイルID: {uploaded_file['id']}")
        
        print("\n🎯 Google Drive バックアップシステム準備完了！")
        print("\n📋 次のステップ:")
        print("1. python3 google_drive_backup.py  # 完全バックアップ実行")
        print("2. ./cron_backup_setup.sh         # 自動化設定")
        
        return True
        
    except Exception as e:
        print(f"❌ Google Drive API接続エラー: {e}")
        return False

if __name__ == "__main__":
    print("🌟 AIcast Room - Codespace対応 Google Drive認証")
    print("GitHub Codespace環境でのOAuth認証問題を解決")
    print("=" * 60)
    
    if codespace_auth():
        print("\n🎉 認証・テスト完了！")
        print("Google Driveバックアップシステムの利用準備が整いました。")
    else:
        print("\n❌ 認証に失敗しました")
        print("詳細なエラー情報を確認して再試行してください。")