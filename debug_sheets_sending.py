#!/usr/bin/env python3
"""
Google Sheets送信デバッグスクリプト
キャスト別Google Sheets設定をテストして、詳細なエラー情報を取得します。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import sqlite3
import traceback
from datetime import datetime
from app import send_to_google_sheets, get_cast_sheets_config, execute_query

def debug_cast_sheets_config():
    """キャスト設定をデバッグ"""
    print("🔍 キャスト別Google Sheets設定デバッグ")
    print("=" * 50)
    
    try:
        # 設定済みキャスト一覧
        query = """
            SELECT c.id, c.name, cs.spreadsheet_id, cs.sheet_name, cs.credentials_file_path, cs.is_active
            FROM casts c 
            LEFT JOIN cast_sheets_config cs ON c.id = cs.cast_id 
            ORDER BY c.name
        """
        
        result = execute_query(query)
        
        if result['success']:
            rows = result['data']
            print(f"✅ {len(rows)}個のキャストを確認:")
            
            for row in rows:
                cast_id, cast_name, sheet_id, sheet_name, creds_path, is_active = row
                print(f"\n📝 {cast_name} (ID: {cast_id})")
                
                if sheet_id:
                    print(f"   📊 スプレッドシートID: {sheet_id}")
                    print(f"   📄 シート名: {sheet_name}")
                    print(f"   🔐 認証ファイル: {creds_path}")
                    print(f"   ✅ アクティブ: {'はい' if is_active else 'いいえ'}")
                    
                    # 認証ファイル存在確認
                    if os.path.exists(creds_path):
                        print(f"   ✅ 認証ファイル存在")
                    else:
                        print(f"   ❌ 認証ファイル不存在: {creds_path}")
                        
                    # テスト送信実行
                    print(f"   🧪 テスト送信実行中...")
                    test_content = f"🔍 デバッグテスト - {cast_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    try:
                        success, message = send_to_google_sheets(
                            cast_name, 
                            test_content, 
                            datetime.now(), 
                            cast_id=cast_id
                        )
                        
                        if success:
                            print(f"   ✅ 送信成功: {message}")
                        else:
                            print(f"   ❌ 送信失敗: {message}")
                            
                    except Exception as e:
                        print(f"   ❌ 送信エラー: {e}")
                        print(f"   📋 詳細エラー:")
                        traceback.print_exc()
                else:
                    print(f"   ⚠️ Google Sheets未設定")
        else:
            print(f"❌ データベースエラー: {result['error']}")
            
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        traceback.print_exc()

def test_direct_oauth():
    """OAuth認証を直接テスト"""
    print(f"\n🔐 OAuth認証直接テスト")
    print("=" * 30)
    
    creds_file = "credentials/client_secret_909115239455-fauih26mvj1g6hksfq9pub4okse90acg.apps.googleusercontent.com.json"
    
    if not os.path.exists(creds_file):
        print(f"❌ 認証ファイルが見つかりません: {creds_file}")
        return
    
    try:
        import gspread
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        import pickle
        import json
        
        print(f"✅ 認証ファイル存在: {creds_file}")
        
        # 認証ファイル内容確認
        with open(creds_file, 'r') as f:
            config = json.load(f)
        
        print(f"✅ プロジェクトID: {config['installed']['project_id']}")
        print(f"✅ クライアントID: {config['installed']['client_id'][:20]}...")
        
        # OAuth フロー
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]
        
        print(f"🔄 OAuth認証開始...")
        flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
        
        # 認証トークンファイル確認
        token_file = creds_file.replace('.json', '_token.pickle')
        
        if os.path.exists(token_file):
            print(f"✅ 既存認証トークン発見: {token_file}")
        else:
            print(f"⚠️ 認証トークン未作成: {token_file}")
            print(f"💡 初回OAuth認証が必要です")
        
    except ImportError as e:
        print(f"❌ 必要なライブラリがインストールされていません: {e}")
    except Exception as e:
        print(f"❌ OAuth認証エラー: {e}")
        traceback.print_exc()

def check_streamlit_session():
    """Streamlitセッション状態確認"""
    print(f"\n🔄 Streamlitプロセス確認")
    print("=" * 30)
    
    try:
        import psutil
        
        # Streamlitプロセス検索
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if 'streamlit' in proc.info['name'] or any('streamlit' in cmd for cmd in proc.info['cmdline'] or []):
                print(f"✅ Streamlitプロセス発見:")
                print(f"   PID: {proc.info['pid']}")
                print(f"   コマンド: {' '.join(proc.info['cmdline'])}")
                
                # メモリ使用量
                memory = proc.memory_info()
                print(f"   メモリ使用量: {memory.rss / 1024 / 1024:.1f} MB")
                
    except ImportError:
        print(f"⚠️ psutil未インストール（psutil install required）")
    except Exception as e:
        print(f"❌ プロセス確認エラー: {e}")

def main():
    """メイン関数"""
    print("🐛 AIcast Room - Google Sheets送信デバッグツール 🐛")
    print("=" * 60)
    
    debug_cast_sheets_config()
    test_direct_oauth()
    check_streamlit_session()
    
    print(f"\n" + "=" * 60)
    print("💡 トラブルシューティング提案:")
    print("1. 認証ファイルパスが正確か確認")
    print("2. OAuth初回認証が完了しているか確認")
    print("3. Streamlitアプリを再起動してみる")
    print("4. ブラウザのデベロッパーツールでコンソールエラー確認")

if __name__ == "__main__":
    main()