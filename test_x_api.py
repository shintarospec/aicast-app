#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X (Twitter) API 接続テストスクリプト
"""

import os
import sys
import json
from x_api_poster import x_poster

def test_x_api_connection():
    """X APIの接続をテスト"""
    print("=== X (Twitter) API 接続テスト ===\n")
    
    # 認証情報の確認
    print("1. 認証ファイルの確認...")
    credentials_path = "credentials/x_api_credentials.json"
    
    if not os.path.exists(credentials_path):
        print("❌ X API認証ファイルが見つかりません")
        print(f"📁 必要なファイル: {credentials_path}")
        print("\n📋 設定手順:")
        print("1. X Developer Portal (https://developer.twitter.com) でアプリを作成")
        print("2. API Keys とTokens を取得")
        print("3. credentials/x_api_credentials.json を作成")
        print("4. 認証情報を入力")
        print("\n💡 **新機能**: キャスト別認証")
        print("   各キャストに個別のX APIアカウントを設定可能になりました！")
        print("   アプリ内の「キャスト管理」→「個別管理」→「X API設定」で設定してください。")
        return False
    else:
        print("✅ 認証ファイルが見つかりました")
    
    # 認証テスト
    print("\n2. X API認証テスト...")
    success, message = x_poster.setup_credentials()
    
    if success:
        print(f"✅ {message}")
        
        # アカウント情報取得
        print("\n3. アカウント情報取得...")
        account_info, info_message = x_poster.get_account_info()
        
        if account_info:
            print(f"✅ アカウント情報取得成功")
            print(f"   ユーザー名: @{account_info['username']}")
            print(f"   表示名: {account_info['name']}")
            print(f"   ユーザーID: {account_info['id']}")
            
            # テスト投稿（コメントアウト - 実際には投稿しない）
            print("\n4. テスト投稿機能確認（実際には投稿しません）")
            test_content = "AIcast Room からのテスト投稿です 🤖 #AIcast"
            print(f"   テスト投稿内容: {test_content}")
            print(f"   文字数: {len(test_content)}文字 (制限: 280文字)")
            
            if len(test_content) <= 280:
                print("✅ 文字数制限内です")
                print("💡 実際に投稿する場合は x_poster.post_tweet() を使用")
                print("💡 キャスト別投稿は x_poster.post_tweet_for_cast(cast_id, content) を使用")
            else:
                print("❌ 文字数制限を超えています")
            
            return True
        else:
            print(f"❌ アカウント情報取得失敗: {info_message}")
            return False
    else:
        print(f"❌ {message}")
        print("\n💡 **キャスト別認証について**:")
        print("   グローバル認証が設定されていない場合も、")
        print("   各キャストに個別のX API認証を設定すれば投稿可能です。")
        return False

def test_cast_specific_api():
    """キャスト別API認証のテスト"""
    print("\n=== キャスト別 X API 機能テスト ===\n")
    
    try:
        import sqlite3
        # データベースから認証情報を取得
        conn = sqlite3.connect('casting_office.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.name, cx.* 
            FROM casts c 
            JOIN cast_x_credentials cx ON c.id = cx.cast_id 
            WHERE cx.is_active = 1
        """)
        
        cast_credentials = cursor.fetchall()
        conn.close()
        
        if not cast_credentials:
            print("❌ キャスト別のX API認証情報が設定されていません")
            print("📋 設定方法:")
            print("1. アプリを起動")
            print("2. 「キャスト管理」→「個別管理」→「既存キャストの編集・削除」")
            print("3. キャストを選択して「X API設定」セクションで設定")
            return False
        
        print(f"✅ {len(cast_credentials)}件のキャスト別認証情報が見つかりました\n")
        
        for cast_data in cast_credentials:
            cast_name = cast_data[0]
            cast_id = cast_data[1]
            print(f"🎭 キャスト: {cast_name} (ID: {cast_id})")
            
            # 認証テスト
            success, message, user_data = x_poster.setup_cast_credentials(
                cast_id, cast_data[3], cast_data[4], cast_data[5], cast_data[6], cast_data[7]
            )
            
            if success:
                print(f"   ✅ 認証成功: {message}")
                if user_data:
                    print(f"   🔗 連携アカウント: @{user_data.username} ({user_data.name})")
            else:
                print(f"   ❌ 認証失敗: {message}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ キャスト別認証テスト中にエラー: {e}")
        return False

def show_usage_examples():
    """使用例を表示"""
    print("\n=== 使用例 ===")
    
    print("\n📝 基本的な投稿:")
    print("```python")
    print("from x_api_poster import x_poster")
    print("success, message = x_poster.post_tweet('投稿内容', 'キャスト名')")
    print("if success:")
    print("    print('投稿成功!')")
    print("else:")
    print("    print(f'投稿失敗: {message}')")
    print("```")
    
    print("\n🔍 アカウント情報取得:")
    print("```python")
    print("account_info, message = x_poster.get_account_info()")
    print("if account_info:")
    print("    print(f'@{account_info[\"username\"]}')")
    print("```")
    
    print("\n⚠️  注意事項:")
    print("- X API の使用制限にご注意ください")
    print("- 投稿内容は280文字以内にしてください")
    print("- APIキーの取り扱いには十分注意してください")

if __name__ == "__main__":
    try:
        # グローバル認証テスト
        success = test_x_api_connection()
        
        # キャスト別認証テスト
        cast_success = test_cast_specific_api()
        
        if success or cast_success:
            print("\n🎉 X API接続テスト完了！")
            if success and cast_success:
                print("✅ グローバル認証とキャスト別認証の両方が利用可能です。")
            elif success:
                print("✅ グローバル認証が利用可能です。")
                print("💡 キャスト別認証を設定すると、各キャストが独自のアカウントで投稿できます。")
            else:
                print("✅ キャスト別認証が利用可能です。")
                print("💡 各キャストが独自のTwitterアカウントで投稿できます。")
            print("AIcast Room からX (Twitter) への投稿準備が完了しました。")
        else:
            print("\n❌ X API接続テストに失敗しました。")
            print("設定を確認してから再度お試しください。")
        
        show_usage_examples()
        
    except Exception as e:
        print(f"\n💥 予期しないエラーが発生しました: {e}")
        sys.exit(1)