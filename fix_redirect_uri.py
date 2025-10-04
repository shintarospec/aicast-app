#!/usr/bin/env python3
"""
Google Cloud Console OAuth設定修正ガイド
redirect_uri エラーを解決するための設定手順を表示します。
"""

def show_redirect_uri_fix():
    """redirect_uri エラーの修正手順を表示"""
    print("🔧 Google Cloud Console OAuth設定修正ガイド")
    print("=" * 60)
    
    project_id = "fine-tractor-473402-q4"
    client_id = "909115239455-fauih26mvj1g6hksfq9pub4okse90acg.apps.googleusercontent.com"
    
    print("❌ 現在のエラー: Missing required parameter: redirect_uri")
    print("💡 解決方法: 承認済みリダイレクトURIを追加")
    print()
    
    print("📋 修正手順:")
    print("=" * 20)
    
    print("1. Google Cloud Consoleにアクセス:")
    print(f"   https://console.cloud.google.com/apis/credentials?project={project_id}")
    print()
    
    print("2. OAuth 2.0 クライアントIDを編集:")
    print(f"   - クライアントID: {client_id}")
    print("   - 「編集」ボタンをクリック")
    print()
    
    print("3. 承認済みのリダイレクト URI に以下を追加:")
    print("   ✅ http://localhost")
    print("   ✅ http://localhost:8080")
    print("   ✅ http://localhost:8502")
    print("   ✅ urn:ietf:wg:oauth:2.0:oob")
    print()
    
    print("4. 「保存」ボタンをクリック")
    print()
    
    print("5. 数分待ってから AIcast Room で再試行")
    
    print()
    print("🔗 直接リンク:")
    print(f"https://console.cloud.google.com/apis/credentials/oauthclient/{client_id}?project={project_id}")

def show_alternative_auth_method():
    """代替認証方法を表示"""
    print("\n" + "=" * 60)
    print("🔄 代替認証方法: サービスアカウント使用")
    print("=" * 60)
    
    print("OAuth認証の代わりにサービスアカウントを使用する方法:")
    print()
    print("1. Google Cloud Console → IAM と管理 → サービスアカウント")
    print("2. 「サービスアカウントを作成」")
    print("3. 名前: aicast-sheets-service")
    print("4. 役割: 「エディタ」を追加")
    print("5. 「キーを作成」→ JSON 形式でダウンロード")
    print("6. ファイルを credentials/ フォルダに配置")
    print("7. Google Sheets で共有設定:")
    print("   - サービスアカウントのメールアドレスに「編集者」権限を付与")
    
    print()
    print("💡 サービスアカウント方式の利点:")
    print("- ブラウザ認証不要")
    print("- 自動化に最適")
    print("- redirect_uri エラーなし")

if __name__ == "__main__":
    show_redirect_uri_fix()
    show_alternative_auth_method()
    
    print(f"\n" + "=" * 60)
    print("⚡ 即座に解決したい場合:")
    print("1. 上記の Google Cloud Console 設定を実行")
    print("2. または、サービスアカウント方式に変更")
    print("3. AIcast Room でテスト送信を再実行")