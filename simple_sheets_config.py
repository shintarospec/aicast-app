#!/usr/bin/env python3
"""
シンプルなGoogle Sheets設定
同一Googleアカウントで複数のスプレッドシートを管理する設定ツール
"""

import sqlite3
import os

def setup_simple_sheets_config():
    """シンプルなGoogle Sheets設定を適用"""
    print("🔧 シンプルGoogle Sheets設定")
    print("=" * 40)
    
    # デフォルト設定
    default_config = {
        'credentials_file': 'credentials/credentials.json',
        'spreadsheet_id': '1VPSyQOp0p2U9bPHghP4JZiyePsev2Uoq3nVbbC26VAo',
        'sheet_name': '投稿メッセージリスト'
    }
    
    print(f"📊 スプレッドシートID: {default_config['spreadsheet_id']}")
    print(f"📄 シート名: {default_config['sheet_name']}")
    print(f"🔐 認証ファイル: {default_config['credentials_file']}")
    
    # 認証ファイル存在確認
    if os.path.exists(default_config['credentials_file']):
        print("✅ 認証ファイル存在")
    else:
        print("❌ 認証ファイル不存在")
        return
    
    # 既存のキャスト別設定をクリア（オプション）
    clear_cast_config = input("\nキャスト別Google Sheets設定をクリアしますか？ (y/N): ").strip().lower()
    
    if clear_cast_config == 'y':
        try:
            conn = sqlite3.connect('casting_office.db')
            cursor = conn.cursor()
            
            # キャスト別設定を無効化
            cursor.execute("UPDATE cast_sheets_config SET is_active = 0")
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            print(f"✅ {deleted_count}個のキャスト別設定を無効化しました")
            
        except sqlite3.Error as e:
            print(f"❌ データベースエラー: {e}")
    
    print("\n" + "=" * 40)
    print("🎯 シンプル設定完了!")
    print()
    print("📋 使用方法:")
    print("1. AIcast Room → 投稿作成")
    print("2. 送信先で「Google Sheets」を選択")
    print("3. 初回のみOAuth認証（1回だけ）")
    print("4. 以降は自動的に同じスプレッドシートに送信")
    print()
    print("💡 同一Googleアカウントなら複数スプレッドシートも設定可能")

def test_simple_sheets():
    """シンプル設定での送信テスト"""
    print(f"\n🧪 シンプル設定テスト")
    print("=" * 30)
    
    try:
        from app import send_to_google_sheets
        from datetime import datetime
        
        test_content = f"🧪 シンプル設定テスト - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        test_datetime = datetime.now()
        
        print(f"🚀 テスト送信実行中...")
        print(f"内容: {test_content}")
        
        success, message = send_to_google_sheets("テストキャスト", test_content, test_datetime)
        
        if success:
            print(f"✅ 送信成功: {message}")
        else:
            print(f"❌ 送信失敗: {message}")
            
    except ImportError as e:
        print(f"⚠️ テスト実行にはStreamlitアプリの起動が必要です")
    except Exception as e:
        print(f"❌ テストエラー: {e}")

if __name__ == "__main__":
    setup_simple_sheets_config()
    
    # テスト実行確認
    run_test = input("\nシンプル設定のテストを実行しますか？ (y/N): ").strip().lower()
    if run_test == 'y':
        test_simple_sheets()