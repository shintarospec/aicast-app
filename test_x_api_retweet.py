#!/usr/bin/env python3
# X API リツイート機能テストスクリプト

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from x_api_poster import x_poster
import sqlite3

def test_retweet_functionality():
    """リツイート機能のテスト"""
    print("🔄 X API リツイート機能テスト")
    print("=" * 50)
    
    # 1. グローバル認証テスト
    print("\n1️⃣ グローバル認証でのリツイート機能テスト")
    success, message = x_poster.setup_credentials()
    print(f"グローバル認証: {'✅' if success else '❌'} {message}")
    
    if success:
        # テスト用の投稿ID
        test_tweet_id = input("\n📝 リツイートしたい投稿のIDを入力してください（例: 1234567890123456789): ").strip()
        
        if test_tweet_id:
            # リツイートテスト
            print(f"\n🧪 投稿 {test_tweet_id} をリツイート中...")
            rt_success, rt_message = x_poster.retweet(test_tweet_id)
            print(f"リツイート結果: {'✅' if rt_success else '❌'} {rt_message}")
            
            if rt_success:
                # リツイート取り消しテスト
                confirm = input(f"\n❓ リツイートを取り消しますか？ (y/N): ").strip().lower()
                if confirm == 'y':
                    print(f"\n🧪 投稿 {test_tweet_id} のリツイート取り消し中...")
                    unrt_success, unrt_message = x_poster.unretweet(test_tweet_id)
                    print(f"リツイート取り消し結果: {'✅' if unrt_success else '❌'} {unrt_message}")
        else:
            print("⚠️ 投稿IDが入力されませんでした")
    
    # 2. キャスト別認証でのテスト
    print(f"\n2️⃣ キャスト別認証でのリツイート機能テスト")
    
    # データベースからキャスト一覧を取得
    try:
        conn = sqlite3.connect('casting_office.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.id, c.name, cx.twitter_username 
            FROM casts c 
            JOIN cast_x_credentials cx ON c.id = cx.cast_id 
            WHERE cx.is_active = 1
        """)
        
        cast_credentials = cursor.fetchall()
        conn.close()
        
        if cast_credentials:
            print(f"✅ {len(cast_credentials)}個のキャストでX API認証が利用可能:")
            for cast_id, cast_name, twitter_username in cast_credentials:
                print(f"  - キャスト: {cast_name} (ID: {cast_id}) → @{twitter_username}")
            
            # テスト対象キャストを選択
            print(f"\n📝 テスト対象のキャストIDを入力してください:")
            try:
                test_cast_id = int(input("キャストID: ").strip())
                
                # 選択されたキャストの認証情報を取得
                conn = sqlite3.connect('casting_office.db')
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT api_key, api_secret, bearer_token, access_token, access_token_secret
                    FROM cast_x_credentials 
                    WHERE cast_id = ? AND is_active = 1
                """, (test_cast_id,))
                
                cred_data = cursor.fetchone()
                conn.close()
                
                if cred_data:
                    api_key, api_secret, bearer_token, access_token, access_token_secret = cred_data
                    
                    # キャスト認証をセットアップ
                    setup_success, setup_message = x_poster.setup_cast_credentials(
                        test_cast_id, api_key, api_secret, bearer_token, access_token, access_token_secret
                    )
                    print(f"キャスト認証: {'✅' if setup_success else '❌'} {setup_message}")
                    
                    if setup_success:
                        # テスト用の投稿ID
                        test_tweet_id = input(f"\n📝 キャスト用リツイート投稿IDを入力してください: ").strip()
                        
                        if test_tweet_id:
                            # キャストでリツイートテスト
                            print(f"\n🧪 キャスト {test_cast_id} で投稿 {test_tweet_id} をリツイート中...")
                            rt_success, rt_message = x_poster.retweet(test_tweet_id, cast_id=test_cast_id)
                            print(f"リツイート結果: {'✅' if rt_success else '❌'} {rt_message}")
                            
                            if rt_success:
                                # リツイート取り消し確認
                                confirm = input(f"\n❓ リツイートを取り消しますか？ (y/N): ").strip().lower()
                                if confirm == 'y':
                                    print(f"\n🧪 キャスト {test_cast_id} で投稿 {test_tweet_id} のリツイート取り消し中...")
                                    unrt_success, unrt_message = x_poster.unretweet(test_tweet_id, cast_id=test_cast_id)
                                    print(f"リツイート取り消し結果: {'✅' if unrt_success else '❌'} {unrt_message}")
                else:
                    print(f"❌ キャストID {test_cast_id} の認証情報が見つかりません")
                
            except ValueError:
                print("❌ 無効なキャストIDです")
        else:
            print("❌ X API認証が設定されたキャストがありません")
            print("💡 キャスト管理でX API認証情報を設定してください")
    
    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")

def main():
    """メイン関数"""
    print("🎭 AIcast Room - X API リツイート機能テスト 🎭")
    print("キャラクター別リツイートシステム")
    print("=" * 60)
    
    print("💰 **プラン別制限情報**")
    print("  FREEプラン: リツイート 1回/15分")
    print("  BASICプラン ($100/月): リツイート 5回/15分") 
    print("  PROプラン ($5,000/月): リツイート 50回/15分")
    print()
    
    test_retweet_functionality()
    
    print(f"\n" + "=" * 60)
    print("🎯 テスト完了!")
    print()
    print("💡 使用可能な機能:")
    print("  - retweet(tweet_id, cast_id=None): 投稿をリツイート")
    print("  - unretweet(tweet_id, cast_id=None): リツイート取り消し")
    print()
    print("📝 投稿IDの取得方法:")
    print("  1. X (Twitter)で投稿を開く")
    print("  2. URLの末尾の数字が投稿ID")
    print("     例: https://x.com/username/status/1234567890123456789")
    print("     → 投稿ID: 1234567890123456789")
    print()
    print("🎉 FREEプランでもリツイート機能が利用可能です！")

if __name__ == "__main__":
    main()