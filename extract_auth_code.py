#!/usr/bin/env python3
"""
OAuth認証コード抽出ツール
URLから認証コードを自動抽出します。
"""

import re
import urllib.parse

def extract_auth_code_from_url(url):
    """URLから認証コードを抽出"""
    print("🔍 OAuth認証コード抽出ツール")
    print("=" * 40)
    
    # URLパラメータを解析
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    
    print(f"📝 入力URL: {url}")
    print(f"🔧 ホスト: {parsed.netloc}")
    print(f"📊 パラメータ: {list(params.keys())}")
    
    # 認証コードを抽出
    if 'code' in params:
        auth_code = params['code'][0]
        print(f"✅ 認証コード抽出成功:")
        print(f"   {auth_code}")
        
        # 他の重要な情報も表示
        if 'state' in params:
            print(f"🔐 ステート: {params['state'][0]}")
        if 'scope' in params:
            scopes = params['scope'][0].split(' ')
            print(f"📋 スコープ: {', '.join(scopes)}")
            
        return auth_code
    else:
        print("❌ 認証コードが見つかりません")
        print("💡 URLが正しくない可能性があります")
        return None

def main():
    """メイン実行"""
    # ユーザーが提供したURL
    problem_url = "http://localhost:47115/?state=GasDVmNe79q3Bw0wmaNwwxNK1C7qQs&code=4/0AVGzR1Cqm64LIYYddWSRe-2AKuaHFBcbCdh8yzXvGwOWCGLll-TTn9gTT23cRZj3VFKzuQ&scope=https://www.googleapis.com/auth/drive%20https://www.googleapis.com/auth/spreadsheets"
    
    auth_code = extract_auth_code_from_url(problem_url)
    
    print(f"\n" + "=" * 40)
    if auth_code:
        print("📋 AIcast Roomでの使用方法:")
        print("1. キャスト管理 → Google Sheets設定")
        print("2. 「テスト送信」をクリック")
        print("3. 認証コード入力欄に以下をコピー:")
        print(f"   {auth_code}")
        print("4. Enter押下で認証完了")
    else:
        print("⚠️ 認証コードを手動で確認してください")

if __name__ == "__main__":
    main()