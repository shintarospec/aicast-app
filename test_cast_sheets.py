#!/usr/bin/env python3
# キャスト別Google Sheets連携テストスクリプト

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import sqlite3
from datetime import datetime
from app import send_to_google_sheets, get_cast_sheets_config

def test_cast_sheets_integration():
    """キャスト別Google Sheets連携のテスト"""
    print("📊 キャスト別Google Sheets連携テスト")
    print("=" * 50)
    
    # データベースからキャスト一覧を取得
    try:
        conn = sqlite3.connect('casting_office.db')
        cursor = conn.cursor()
        
        # 全キャスト取得
        cursor.execute("SELECT id, name FROM casts ORDER BY name")
        all_casts = cursor.fetchall()
        
        if not all_casts:
            print("❌ キャストが登録されていません")
            return
            
        print(f"✅ {len(all_casts)}個のキャストが登録済み:")
        for cast_id, cast_name in all_casts:
            print(f"  - {cast_name} (ID: {cast_id})")
        
        # Google Sheets設定済みキャスト確認
        cursor.execute("""
            SELECT c.id, c.name, cs.spreadsheet_id, cs.sheet_name, cs.credentials_file_path
            FROM casts c 
            JOIN cast_sheets_config cs ON c.id = cs.cast_id 
            WHERE cs.is_active = 1
        """)
        
        configured_casts = cursor.fetchall()
        conn.close()
        
        if configured_casts:
            print(f"\n📋 Google Sheets設定済みキャスト ({len(configured_casts)}個):")
            for cast_id, cast_name, sheet_id, sheet_name, creds_path in configured_casts:
                print(f"  - {cast_name} (ID: {cast_id})")
                print(f"    📊 スプレッドシートID: {sheet_id[:20]}...")
                print(f"    📄 シート名: {sheet_name}")
                print(f"    🔐 認証ファイル: {creds_path}")
                
                # 認証ファイル存在確認
                if os.path.exists(creds_path):
                    print(f"    ✅ 認証ファイル存在")
                else:
                    print(f"    ❌ 認証ファイル不存在")
                print()
        else:
            print("⚠️ Google Sheets設定済みキャストがありません")
            print("💡 AIcast Room → キャスト管理 → 個別管理 → Google Sheets設定で設定してください")
        
        # テスト送信実行
        if configured_casts:
            print("🧪 テスト送信を実行しますか？")
            test_cast_id = input("テスト対象キャストIDを入力（Enterでスキップ）: ").strip()
            
            if test_cast_id:
                try:
                    test_cast_id = int(test_cast_id)
                    
                    # キャスト名取得
                    cast_name = None
                    for cast_id, name in all_casts:
                        if cast_id == test_cast_id:
                            cast_name = name
                            break
                    
                    if not cast_name:
                        print(f"❌ キャストID {test_cast_id} が見つかりません")
                        return
                    
                    # テスト投稿内容
                    test_content = f"🧪 キャスト別Google Sheets連携テスト - {cast_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    test_datetime = datetime.now()
                    
                    print(f"\n🚀 テスト送信実行中...")
                    print(f"キャスト: {cast_name} (ID: {test_cast_id})")
                    print(f"内容: {test_content}")
                    
                    # 送信実行
                    success, message = send_to_google_sheets(
                        cast_name, 
                        test_content, 
                        test_datetime, 
                        cast_id=test_cast_id
                    )
                    
                    if success:
                        print(f"✅ テスト送信成功: {message}")
                    else:
                        print(f"❌ テスト送信失敗: {message}")
                        
                        # エラー対処法を表示
                        print(f"\n💡 トラブルシューティング:")
                        print(f"1. 認証ファイルが正しい場所にあるか確認")
                        print(f"2. Google Sheets API、Google Drive APIが有効化されているか確認")
                        print(f"3. スプレッドシートIDが正しいか確認")
                        print(f"4. スプレッドシートの共有設定を確認")
                        
                except ValueError:
                    print("❌ 無効なキャストIDです")
        
        # デフォルト設定での送信テスト
        print(f"\n🔧 デフォルト設定でのテスト送信:")
        default_test = input("デフォルト設定でもテストしますか？ (y/N): ").strip().lower()
        
        if default_test == 'y':
            test_content = f"🧪 デフォルトGoogle Sheets連携テスト - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            test_datetime = datetime.now()
            
            print(f"🚀 デフォルト設定テスト送信中...")
            success, message = send_to_google_sheets("テストキャスト", test_content, test_datetime)
            
            if success:
                print(f"✅ デフォルト送信成功: {message}")
            else:
                print(f"❌ デフォルト送信失敗: {message}")
    
    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")

def show_config_instructions():
    """設定手順を表示"""
    print("\n" + "=" * 60)
    print("📖 キャスト別Google Sheets設定手順")
    print("=" * 60)
    
    print("""
🎯 目的: 各キャストが独自のGoogle Sheetsスプレッドシート・Googleアカウントを使用

📋 手順:
1. 【Google Cloud Console設定】
   - https://console.cloud.google.com にアクセス
   - プロジェクト作成 (キャスト毎 or 統合)
   - Google Sheets API、Google Drive API を有効化

2. 【OAuth認証設定】
   - 「APIとサービス」→「認証情報」
   - 「認証情報を作成」→「OAuthクライアントID」
   - アプリケーションタイプ: デスクトップアプリケーション
   - 認証ファイルをダウンロード

3. 【認証ファイル配置】
   - ダウンロードしたJSONファイルを適切な場所に配置
   - 例: credentials/cast1_credentials.json
   - キャスト毎に異なるファイル名を使用

4. 【スプレッドシート準備】
   - Google Sheetsで新しいスプレッドシートを作成
   - URLからスプレッドシートIDを取得
   - 例: https://docs.google.com/spreadsheets/d/【ここがID】/edit

5. 【AIcast Room設定】
   - キャスト管理 → 個別管理 → キャスト選択
   - 「📊 Google Sheets設定」で各項目を入力
   - 設定保存後、テスト送信で動作確認

💡 利点:
- キャスト毎に異なるGoogleアカウント使用可能
- スプレッドシートの分離でデータ管理しやすい
- 権限管理を細かく設定可能

⚠️ 注意点:
- 認証ファイルのパスは正確に設定
- Google APIs有効化を忘れずに
- スプレッドシートの共有設定に注意
""")

def main():
    """メイン関数"""
    print("🎭 AIcast Room - キャスト別Google Sheets連携テスト 🎭")
    print("=" * 60)
    
    test_cast_sheets_integration()
    show_config_instructions()
    
    print(f"\n" + "=" * 60)
    print("🎯 テスト完了!")
    print()
    print("📈 次のステップ:")
    print("1. 各キャストのGoogle Sheets設定を完了")
    print("2. 実際の投稿でキャスト別送信をテスト")
    print("3. 複数Googleアカウントでの運用を確認")

if __name__ == "__main__":
    main()