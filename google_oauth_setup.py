#!/usr/bin/env python3
"""
Google OAuth設定ヘルパー
OAuth同意画面の設定状況を確認し、解決策を提示します。
"""

import json
import os

def check_oauth_config():
    """OAuth設定を確認"""
    creds_file = "credentials/client_secret_909115239455-fauih26mvj1g6hksfq9pub4okse90acg.apps.googleusercontent.com.json"
    
    if not os.path.exists(creds_file):
        print("❌ 認証ファイルが見つかりません")
        return
    
    with open(creds_file, 'r') as f:
        config = json.load(f)
    
    project_id = config['installed']['project_id']
    client_id = config['installed']['client_id']
    
    print("🔍 OAuth設定情報:")
    print(f"プロジェクトID: {project_id}")
    print(f"クライアントID: {client_id}")
    
    print("\n🛠️ 解決手順:")
    print("1. Google Cloud Console にアクセス:")
    print(f"   https://console.cloud.google.com/apis/credentials/consent?project={project_id}")
    
    print("\n2. 以下のいずれかを実行:")
    print("   【方法A：テストユーザー追加】")
    print("   - 「テストユーザー」セクションで「+ ADD USERS」")
    print("   - 使用するGoogleアカウント (info@oob.co.jp) を追加")
    
    print("\n   【方法B：本番環境に変更（推奨）】")
    print("   - 「公開ステータス」を「本番環境」に変更")
    print("   - 「アプリを公開」ボタンをクリック")
    
    print("\n3. 必要なスコープが含まれているか確認:")
    print("   - https://www.googleapis.com/auth/spreadsheets")
    print("   - https://www.googleapis.com/auth/drive.file")
    
    print("\n4. 保存後、数分待ってから再試行")

def show_direct_links():
    """直接リンクを表示"""
    project_id = "fine-tractor-473402-q4"
    
    print("\n🔗 直接アクセスリンク:")
    print(f"OAuth同意画面: https://console.cloud.google.com/apis/credentials/consent?project={project_id}")
    print(f"認証情報: https://console.cloud.google.com/apis/credentials?project={project_id}")
    print(f"APIライブラリ: https://console.cloud.google.com/apis/library?project={project_id}")

if __name__ == "__main__":
    print("🔐 Google OAuth 403エラー解決ヘルパー")
    print("=" * 50)
    check_oauth_config()
    show_direct_links()
    
    print("\n" + "=" * 50)
    print("✅ 設定完了後、AIcast Roomで再度Google Sheets設定をお試しください")