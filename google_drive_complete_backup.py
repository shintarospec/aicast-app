#!/usr/bin/env python3
"""
🌟 AIcast Room - Google Drive完全バックアップシステム
MCF DEATH GUARD事故対策完全版
"""

import os
import sys
import json
import zipfile
import sqlite3
import datetime
import logging
import pickle
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("❌ Google Drive API依存関係が不足しています")
    print("実行: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

# 設定
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials/google_drive_credentials.json'
TOKEN_FILE = 'credentials/google_drive_token.pickle'
BACKUP_FOLDER_NAME = 'AIcast-Room-Backups'

# バックアップ対象設定
BACKUP_CONFIG = {
    'critical_files': [
        'app.py',                    # メインアプリケーション（6,377行）
        'run.py',                    # 起動スクリプト
        'local_schedule_checker.py', # スケジュール投稿システム
        'local_retweet_scheduler.py', # リツイートシステム
        'requirements.txt',          # 依存関係
        'style.css',                # UIスタイル
        'codespace_google_auth.py', # Google Drive認証システム
    ],
    'databases': [
        'casting_office.db'          # メインデータベース
    ],
    'directories': [
        'docs/',                     # 整理済み25個のMDファイル
        'cloud_functions/',          # Cloud Functions設定
    ],
    'exclude_patterns': [
        'credentials/',              # 認証情報（セキュリティ）
        '__pycache__/',             # Pythonキャッシュ
        '*.pyc',                    # コンパイル済みPython
        '.git/',                    # Git履歴
        'app.log',                  # ログファイル
        '*.backup',                 # バックアップファイル
        'backup_gdrive.log',        # このシステムのログ
        'json/',                    # 一時認証ファイル
        'test_backup_connection.txt' # テストファイル
    ],
    'logs': [
        'app.log',
        'schedule.log', 
        'retweet.log'
    ] if os.path.exists('app.log') else []
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

class GoogleDriveCompleteBackup:
    """Google Drive完全バックアップシステム"""
    
    def __init__(self):
        self.service = None
        self.backup_folder_id = None
        self.backup_stats = {
            'files_processed': 0,
            'total_size': 0,
            'errors': []
        }
        
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
    
    def create_backup_archive(self) -> Optional[str]:
        """完全バックアップアーカイブの作成"""
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_name = f"aicast_complete_backup_{timestamp}.zip"
        
        logger.info(f"📦 バックアップアーカイブ作成開始: {archive_name}")
        
        try:
            with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                
                # 1. 重要ファイルのバックアップ
                logger.info("📄 重要ファイルをバックアップ中...")
                for file_path in BACKUP_CONFIG['critical_files']:
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        zipf.write(file_path, f"critical/{file_path}")
                        self.backup_stats['files_processed'] += 1
                        self.backup_stats['total_size'] += file_size
                        
                        # app.pyの特別処理
                        if file_path == 'app.py':
                            lines = len(open(file_path).readlines())
                            logger.info(f"📄 app.py追加: {lines}行, {file_size/1024:.1f}KB")
                        else:
                            logger.info(f"📄 {file_path}追加: {file_size/1024:.1f}KB")
                
                # 2. データベースのバックアップ
                logger.info("🗃️ データベースをバックアップ中...")
                for db_file in BACKUP_CONFIG['databases']:
                    if os.path.exists(db_file):
                        # SQLiteダンプの作成
                        dump_file = f"{db_file}_{timestamp}.sql"
                        self._create_db_dump(db_file, dump_file)
                        
                        # データベースファイルとダンプの両方を追加
                        db_size = os.path.getsize(db_file)
                        zipf.write(db_file, f"databases/{db_file}")
                        zipf.write(dump_file, f"databases/{dump_file}")
                        
                        self.backup_stats['files_processed'] += 2
                        self.backup_stats['total_size'] += db_size + os.path.getsize(dump_file)
                        
                        os.remove(dump_file)  # 一時ファイル削除
                        logger.info(f"🗃️ {db_file}追加: {db_size/1024:.1f}KB (ダンプ付き)")
                
                # 3. ディレクトリのバックアップ
                logger.info("📁 ディレクトリをバックアップ中...")
                for dir_path in BACKUP_CONFIG['directories']:
                    if os.path.exists(dir_path):
                        dir_files = 0
                        dir_size = 0
                        
                        for root, dirs, files in os.walk(dir_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                if not self._should_exclude(file_path):
                                    file_size = os.path.getsize(file_path)
                                    zipf.write(file_path, f"directories/{file_path}")
                                    dir_files += 1
                                    dir_size += file_size
                        
                        self.backup_stats['files_processed'] += dir_files
                        self.backup_stats['total_size'] += dir_size
                        logger.info(f"📁 {dir_path}追加: {dir_files}ファイル, {dir_size/1024:.1f}KB")
                
                # 4. ログファイルのバックアップ（存在する場合）
                if BACKUP_CONFIG['logs']:
                    logger.info("📋 ログファイルをバックアップ中...")
                    for log_file in BACKUP_CONFIG['logs']:
                        if os.path.exists(log_file):
                            log_size = os.path.getsize(log_file)
                            zipf.write(log_file, f"logs/{log_file}")
                            self.backup_stats['files_processed'] += 1
                            self.backup_stats['total_size'] += log_size
                            logger.info(f"📋 {log_file}追加: {log_size/1024:.1f}KB")
                
                # 5. システム情報の保存
                system_info = self._collect_system_info(timestamp)
                zipf.writestr('system_info.json', json.dumps(system_info, indent=2, ensure_ascii=False))
                
                # 6. バックアップメタデータ
                metadata = {
                    'backup_date': timestamp,
                    'backup_type': 'complete_system',
                    'app_version': f"{len(open('app.py').readlines())} lines" if os.path.exists('app.py') else 'unknown',
                    'git_commit': self._get_git_commit(),
                    'files_count': len(zipf.namelist()),
                    'total_size_bytes': self.backup_stats['total_size'],
                    'mcf_death_guard_incident': 'recovered',
                    'github_security_bypass': 'active',
                    'secret_manager_status': 'disabled'
                }
                
                zipf.writestr('backup_metadata.json', json.dumps(metadata, indent=2, ensure_ascii=False))
                logger.info(f"📊 メタデータ追加: {len(zipf.namelist())}ファイル")
            
            # アーカイブサイズの確認
            archive_size = os.path.getsize(archive_name)
            logger.info(f"📦 アーカイブ作成完了: {archive_name}")
            logger.info(f"📏 サイズ: {archive_size / 1024 / 1024:.2f}MB")
            logger.info(f"📄 ファイル数: {self.backup_stats['files_processed']}")
            
            return archive_name
            
        except Exception as e:
            logger.error(f"❌ アーカイブ作成に失敗: {e}")
            if os.path.exists(archive_name):
                os.remove(archive_name)
            return None
    
    def upload_to_drive(self, file_path: str) -> bool:
        """Google Driveへのアップロード"""
        try:
            logger.info(f"☁️ Google Driveへアップロード開始: {os.path.basename(file_path)}")
            
            file_metadata = {
                'name': os.path.basename(file_path),
                'parents': [self.backup_folder_id],
                'description': f'AIcast Room完全バックアップ - MCF DEATH GUARD事故対策版'
            }
            
            media = MediaFileUpload(file_path, resumable=True)
            
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,size'
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"⬆️ アップロード進行: {progress}%")
            
            logger.info(f"✅ Google Driveアップロード完了: {response['name']}")
            logger.info(f"📄 ファイルID: {response['id']}")
            logger.info(f"📏 アップロードサイズ: {int(response['size']) / 1024 / 1024:.2f}MB")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Google Driveアップロード失敗: {e}")
            self.backup_stats['errors'].append(f"Upload failed: {e}")
            return False
    
    def cleanup_old_backups(self, keep_count: int = 10):
        """古いバックアップの削除"""
        try:
            logger.info("🧹 古いバックアップの整理中...")
            
            results = self.service.files().list(
                q=f"'{self.backup_folder_id}' in parents and name contains 'aicast_complete_backup_'",
                orderBy='createdTime desc',
                fields='files(id, name, createdTime, size)'
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"📋 バックアップファイル数: {len(files)}")
            
            if len(files) > keep_count:
                files_to_delete = files[keep_count:]
                total_freed = 0
                
                for file in files_to_delete:
                    try:
                        self.service.files().delete(fileId=file['id']).execute()
                        file_size = int(file.get('size', 0))
                        total_freed += file_size
                        logger.info(f"🗑️ 削除: {file['name']} ({file_size/1024/1024:.1f}MB)")
                    except Exception as e:
                        logger.error(f"❌ 削除失敗 {file['name']}: {e}")
                
                logger.info(f"🧹 {len(files_to_delete)}個の古いバックアップを削除")
                logger.info(f"💾 解放された容量: {total_freed/1024/1024:.1f}MB")
            else:
                logger.info("✅ 削除対象なし（保持数内）")
            
        except Exception as e:
            logger.error(f"❌ 古いバックアップの削除に失敗: {e}")
    
    def _create_db_dump(self, db_file: str, dump_file: str):
        """SQLiteダンプの作成"""
        try:
            conn = sqlite3.connect(db_file)
            with open(dump_file, 'w', encoding='utf-8') as f:
                # ヘッダー情報
                f.write(f"-- AIcast Room データベースダンプ\n")
                f.write(f"-- 作成日時: {datetime.datetime.now()}\n")
                f.write(f"-- 元ファイル: {db_file}\n")
                f.write(f"-- MCF DEATH GUARD事故復旧版\n\n")
                
                for line in conn.iterdump():
                    f.write('%s\n' % line)
            conn.close()
            logger.info(f"💾 SQLiteダンプ作成: {dump_file}")
        except Exception as e:
            logger.error(f"❌ データベースダンプ作成失敗: {e}")
    
    def _should_exclude(self, file_path: str) -> bool:
        """除外対象ファイルかどうかの判定"""
        for pattern in BACKUP_CONFIG['exclude_patterns']:
            if pattern in file_path:
                return True
        return False
    
    def _collect_system_info(self, timestamp: str) -> dict:
        """システム情報の収集"""
        try:
            return {
                'timestamp': timestamp,
                'system': {
                    'platform': os.uname() if hasattr(os, 'uname') else 'unknown',
                    'python_version': sys.version,
                    'working_directory': os.getcwd(),
                },
                'git_info': {
                    'commit': self._get_git_commit(),
                    'branch': self._get_git_branch(),
                    'status': self._get_git_status(),
                },
                'application': {
                    'app_py_lines': len(open('app.py').readlines()) if os.path.exists('app.py') else 0,
                    'database_size': os.path.getsize('casting_office.db') if os.path.exists('casting_office.db') else 0,
                    'docs_count': len(list(Path('docs').glob('*.md'))) if os.path.exists('docs') else 0,
                },
                'incident_recovery': {
                    'mcf_death_guard_status': 'terminated',
                    'secret_manager_status': 'disabled',
                    'github_security_bypass': 'active',
                    'recovery_date': '2025-10-05',
                }
            }
        except Exception as e:
            logger.warning(f"⚠️ システム情報収集で一部エラー: {e}")
            return {'error': str(e), 'timestamp': timestamp}
    
    def _get_git_commit(self) -> str:
        """現在のGitコミットハッシュ取得"""
        try:
            result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                  capture_output=True, text=True, timeout=5)
            return result.stdout.strip()[:12] if result.returncode == 0 else "unknown"
        except:
            return "unknown"
    
    def _get_git_branch(self) -> str:
        """現在のGitブランチ取得"""
        try:
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                  capture_output=True, text=True, timeout=5)
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"
    
    def _get_git_status(self) -> str:
        """Gitステータス取得"""
        try:
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return "clean" if not result.stdout.strip() else "modified"
            return "unknown"
        except:
            return "unknown"
    
    def run_complete_backup(self) -> bool:
        """完全バックアップの実行"""
        logger.info("🚀 AIcast Room 完全バックアップ開始")
        logger.info("="*60)
        logger.info("MCF DEATH GUARD事故対策 - GitHub Security回避版")
        logger.info("="*60)
        
        # 認証
        if not self.authenticate():
            return False
        
        # バックアップフォルダの確認
        if not self.get_backup_folder():
            return False
        
        # アーカイブ作成
        archive_path = self.create_backup_archive()
        if not archive_path:
            return False
        
        # Google Driveアップロード
        upload_success = self.upload_to_drive(archive_path)
        
        # ローカルアーカイブの削除
        if upload_success:
            os.remove(archive_path)
            logger.info(f"🗑️ ローカルアーカイブを削除: {archive_path}")
        
        # 古いバックアップの整理
        if upload_success:
            self.cleanup_old_backups()
        
        # 結果レポート
        if upload_success:
            logger.info("="*60)
            logger.info("✅ 完全バックアップ成功!")
            logger.info(f"📄 処理ファイル数: {self.backup_stats['files_processed']}")
            logger.info(f"📏 総サイズ: {self.backup_stats['total_size']/1024/1024:.2f}MB")
            logger.info(f"☁️ Google Drive保存完了")
            logger.info("🛡️ MCF DEATH GUARD事故対策完了")
            logger.info("="*60)
            return True
        else:
            logger.error("="*60)
            logger.error("❌ 完全バックアップ失敗")
            if self.backup_stats['errors']:
                for error in self.backup_stats['errors']:
                    logger.error(f"   {error}")
            logger.error("="*60)
            return False

def main():
    """メイン実行関数"""
    backup = GoogleDriveCompleteBackup()
    success = backup.run_complete_backup()
    
    if success:
        print("\n🎉 AIcast Room完全バックアップが正常に完了しました!")
        print("🛡️ GitHub Secret Scanning問題を回避した安全なバックアップが保存されました")
        print("📋 次回は以下のコマンドで自動化できます:")
        print("   crontab -e")
        print("   0 3 * * * cd /workspaces/aicast-app && python3 google_drive_complete_backup.py")
        return 0
    else:
        print("\n❌ バックアップに失敗しました")
        print("📋 backup_gdrive.log を確認してください")
        return 1

if __name__ == "__main__":
    sys.exit(main())