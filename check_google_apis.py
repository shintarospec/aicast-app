#!/usr/bin/env python3
"""
Google APIs有効化確認スクリプト
必要なAPIが有効化されているかを確認し、有効化コマンドを提供します。
"""

def show_api_enable_commands():
    """API有効化コマンドを表示"""
    project_id = "fine-tractor-473402-q4"
    
    print("🔧 必要なGoogle APIs有効化コマンド:")
    print("=" * 50)
    
    apis = [
        ("Google Sheets API", "sheets.googleapis.com"),
        ("Google Drive API", "drive.googleapis.com"),
        ("Cloud Resource Manager API", "cloudresourcemanager.googleapis.com")
    ]
    
    print("以下のコマンドをGoogle Cloud Shellまたはローカルのgcloudで実行:")
    print()
    
    for name, api_name in apis:
        print(f"# {name}を有効化")
        print(f"gcloud services enable {api_name} --project={project_id}")
        print()
    
    print("または、Google Cloud Consoleで手動有効化:")
    print(f"https://console.cloud.google.com/apis/library?project={project_id}")
    
    print("\n" + "=" * 50)
    print("📋 チェックリスト:")
    print("□ Google Sheets API 有効化済み")
    print("□ Google Drive API 有効化済み")
    print("□ OAuth同意画面で本番環境に設定")
    print("□ 必要なスコープ設定済み")
    print("□ テストユーザー追加 (テスト環境の場合)")

def show_oauth_scopes():
    """必要なOAuthスコープを表示"""
    print("\n🔐 必要なOAuthスコープ:")
    print("=" * 30)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file"
    ]
    
    for scope in scopes:
        print(f"- {scope}")

if __name__ == "__main__":
    print("🛠️ Google APIs設定確認ツール")
    show_api_enable_commands()
    show_oauth_scopes()