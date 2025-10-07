#!/usr/bin/env python3
"""
AIcast Room - Google Driveバックアップからの復元ツール
"""

import os
import sys
import pickle
import zipfile
import logging
from datetime import datetime
from typing import List, Dict, Optional

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
except ImportError:
    print("❌ Google Drive API依存関係が不足しています")
    print("実行: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

# 設定
SCOPES = ['https://www.googleapis.com/auth/drive.file']
TOKEN_FILE = 'credentials/google_drive_token.pickle'
BACKUP_FOLDER_NAME = 'AIcast-Room-Backups'

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GoogleDriveRestorer:
    def __init__(self):
        self.service = None
        self.backup_folder_id = None

    def authenticate(self) -> bool:
        """Google Drive認証を実行"""
        if not os.path.exists(TOKEN_FILE):
            logger.error("❌ 認証トークンが見つかりません")
            logger.info("最初に python3 codespace_google_auth.py を実行してください")
            return False

        try:
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)

            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    with open(TOKEN_FILE, 'wb') as token:
                        pickle.dump(creds, token)
                else:
                    logger.error("❌ 認証トークンが無効です")
                    return False

            self.service = build('drive', 'v3', credentials=creds)
            logger.info("✅ Google Drive認証成功")
            return True

        except Exception as e:
            logger.error(f"❌ Google Drive認証失敗: {e}")
            return False

    def get_backup_folder(self) -> Optional[str]:
        """バックアップフォルダの取得"""
        try:
            results = self.service.files().list(
                q=f"name='{BACKUP_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder'",
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            folders = results.get('files', [])

            if folders:
                self.backup_folder_id = folders[0]['id']
                logger.info(f"📁 バックアップフォルダを確認: {folders[0]['name']}")
                return self.backup_folder_id
            else:
                logger.error("❌ バックアップフォルダが見つかりません")
                return None

        except Exception as e:
            logger.error(f"❌ バックアップフォルダの取得に失敗: {e}")
            return None

    def list_backups(self) -> List[Dict]:
        """バックアップファイル一覧を取得"""
        try:
            query = f"'{self.backup_folder_id}' in parents and name contains 'aicast_complete_backup'"
            results = self.service.files().list(
                q=query, 
                orderBy='createdTime desc',
                fields='files(id, name, createdTime, size)'
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"📋 バックアップファイル数: {len(files)}")
            
            return files

        except Exception as e:
            logger.error(f"❌ バックアップ一覧の取得に失敗: {e}")
            return []

    def download_backup(self, file_id: str, filename: str) -> bool:
        """バックアップファイルをダウンロード"""
        try:
            logger.info(f"📥 ダウンロード開始: {filename}")
            
            request = self.service.files().get_media(fileId=file_id)
            with open(filename, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    logger.info(f"📥 ダウンロード進行: {int(status.progress() * 100)}%")

            logger.info(f"✅ ダウンロード完了: {filename}")
            return True

        except Exception as e:
            logger.error(f"❌ ダウンロード失敗: {e}")
            return False

    def extract_backup(self, zip_filename: str) -> bool:
        """バックアップファイルを展開"""
        try:
            logger.info(f"📦 バックアップ展開開始: {zip_filename}")
            
            with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
                zip_ref.extractall('.')
                
            logger.info("✅ バックアップ展開完了")
            return True
            
        except Exception as e:
            logger.error(f"❌ バックアップ展開失敗: {e}")
            return False

def main():
    print("🌟 AIcast Room - Google Drive復元ツール")
    print("=" * 50)
    
    restorer = GoogleDriveRestorer()
    
    # 認証
    if not restorer.authenticate():
        return False
    
    # バックアップフォルダ取得
    if not restorer.get_backup_folder():
        return False
    
    # バックアップ一覧表示
    backups = restorer.list_backups()
    
    if not backups:
        logger.error("❌ バックアップファイルが見つかりません")
        return False
    
    print("\n📋 利用可能なバックアップ:")
    for i, backup in enumerate(backups):
        created = backup.get('createdTime', 'Unknown')
        size = backup.get('size', 'Unknown')
        print(f"{i+1}. {backup['name']}")
        print(f"   作成: {created}")
        print(f"   サイズ: {size} bytes")
        print()
    
    # バックアップ選択
    try:
        choice = input(f"復元するバックアップを選択してください (1-{len(backups)}): ")
        choice_idx = int(choice) - 1
        
        if choice_idx < 0 or choice_idx >= len(backups):
            logger.error("❌ 無効な選択です")
            return False
            
        selected_backup = backups[choice_idx]
        logger.info(f"📋 選択されたバックアップ: {selected_backup['name']}")
        
        # 確認
        confirm = input("⚠️ 現在のファイルを上書きしますか？ (yes/no): ")
        if confirm.lower() != 'yes':
            logger.info("❌ 復元をキャンセルしました")
            return False
        
        # ダウンロード
        zip_filename = selected_backup['name']
        if restorer.download_backup(selected_backup['id'], zip_filename):
            # 展開
            if restorer.extract_backup(zip_filename):
                # 一時ファイル削除
                os.remove(zip_filename)
                logger.info("🗑️ 一時ファイルを削除")
                
                print("\n🎉 復元が完了しました！")
                print("VPSにデプロイするには:")
                print("  scp app.py ubuntu@153.126.194.114:/home/ubuntu/aicast-app/")
                print("  ssh ubuntu@153.126.194.114 'cd aicast-app && pkill -f streamlit && nohup .venv/bin/python run.py > app.log 2>&1 &'")
                return True
        
        return False
        
    except (ValueError, KeyboardInterrupt):
        logger.info("❌ 復元をキャンセルしました")
        return False

if __name__ == "__main__":
    main()