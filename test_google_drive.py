#!/usr/bin/env python3
"""
🌟 AIcast Room - Google Drive自動バックアップシステム
GitHub Securityの制約を回避した安全なバックアップソリューション
"""

import os
import sys
import json
import zipfile
import sqlite3
import datetime
import logging
from pathlib import Path
from typing import List, Dict, Optional

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    import pickle
except ImportError:
    print("⚠️ Google Drive API依存関係が不足しています")
    print("インストール: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

# 設定
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials/google_drive_credentials.json'
TOKEN_FILE = 'credentials/google_drive_token.pickle'
BACKUP_FOLDER_NAME = 'AIcast-Room-Backups'

# バックアップ対象設定
BACKUP_CONFIG = {
    'critical_files': [
        'app.py',
        'run.py', 
        'local_schedule_checker.py',
        'local_retweet_scheduler.py',
        'requirements.txt',
        'style.css'
    ],
    'databases': [
        'casting_office.db'
    ],
    'directories': [
        'docs/',
        'cloud_functions/'
    ],
    'exclude_patterns': [
        'credentials/',
        '__pycache__/',
        '*.pyc',
        '.git/',
        'app.log',
        '*.backup'
    ],
    'logs': [
        'app.log',
        'schedule.log', 
        'retweet.log'
    ]
}

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup_gdrive.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GoogleDriveBackup:
    """Google Drive自動バックアップシステム"""
    
    def __init__(self):
        self.service = None
        self.backup_folder_id = None
        
    def authenticate(self) -> bool:
        """Google Drive認証を実行"""
        creds = None
        
        # 既存トークンの読み込み
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        
        # 認証情報の確認・更新
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_FILE):
                    logger.error(f"❌ 認証ファイルが見つかりません: {CREDENTIALS_FILE}")
                    logger.info("📝 Google Cloud Console で OAuth2 認証情報を作成してください")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # トークンの保存
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        
        try:
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("✅ Google Drive認証成功")
            return True
        except Exception as e:
            logger.error(f"❌ Google Drive認証失敗: {e}")
            return False
    
    def get_or_create_backup_folder(self) -> Optional[str]:
        """バックアップフォルダの取得または作成"""
        try:
            # 既存フォルダの検索
            results = self.service.files().list(
                q=f"name='{BACKUP_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder'",
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            folders = results.get('files', [])
            
            if folders:
                self.backup_folder_id = folders[0]['id']
                logger.info(f"📁 既存バックアップフォルダを使用: {folders[0]['name']}")
            else:
                # 新規フォルダ作成
                folder_metadata = {
                    'name': BACKUP_FOLDER_NAME,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = self.service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
                
                self.backup_folder_id = folder.get('id')
                logger.info(f"📁 新規バックアップフォルダを作成: {BACKUP_FOLDER_NAME}")
            
            return self.backup_folder_id
            
        except Exception as e:
            logger.error(f"❌ バックアップフォルダの操作に失敗: {e}")
            return None

def main():
    """メイン実行関数 - 簡易テスト版"""
    print("🧪 Google Drive認証テスト開始")
    print("=" * 50)
    
    backup = GoogleDriveBackup()
    
    # 認証テスト
    print("1. 認証テスト中...")
    if not backup.authenticate():
        print("❌ 認証失敗")
        return 1
    print("✅ 認証成功")
    
    # バックアップフォルダテスト
    print("\n2. バックアップフォルダテスト中...")
    if not backup.get_or_create_backup_folder():
        print("❌ バックアップフォルダ作成失敗")
        return 1
    print("✅ バックアップフォルダ準備完了")
    
    print(f"\n🎯 テスト成功!")
    print(f"📁 Google Drive バックアップフォルダID: {backup.backup_folder_id}")
    print("\n🚀 次のステップ:")
    print("1. 完全バックアップ実行の準備完了")
    print("2. cronジョブで自動化設定可能")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())