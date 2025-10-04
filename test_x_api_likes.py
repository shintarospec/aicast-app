#!/usr/bin/env python3
# X API いいね機能テストスクリプト

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from x_api_poster import x_poster
import sqlite3

def test_like_functionality():
    """いいね機能のテスト"""
    print("🐦 X API いいね機能テスト")
    print("=" * 50)
    
    # 1. グローバル認証テスト
    print("\n1️⃣ グローバル認証でのいいね機能テスト")
    success, message = x_poster.setup_credentials()
    print(f"グローバル認証: {'✅' if success else '❌'} {message}")
    
    if success:
        # テスト用の投稿ID（実際の投稿IDに置き換える必要があります）
        test_tweet_id = input("\n📝 テストしたい投稿のIDを入力してください（例: 1234567890123456789): ").strip()
        
        if test_tweet_id:
            # いいねテスト
            print(f"\n🧪 投稿 {test_tweet_id} にいいねをテスト中...")
            like_success, like_message = x_poster.like_tweet(test_tweet_id)
            print(f"いいね結果: {'✅' if like_success else '❌'} {like_message}")
            
            if like_success:
                # いいね取り消しテスト
                print(f"\n🧪 投稿 {test_tweet_id} のいいね取り消しをテスト中...")
                unlike_success, unlike_message = x_poster.unlike_tweet(test_tweet_id)
                print(f"いいね取り消し結果: {'✅' if unlike_success else '❌'} {unlike_message}")
        
        # いいね履歴取得テスト
        print(f"\n🧪 いいね履歴取得テスト中...")
        history_success, history_data = x_poster.get_liked_tweets(max_results=5)
        if history_success:
            print(f"✅ いいね履歴取得成功")
            print(f"アカウント: {history_data['account_type']}")
            print(f"いいね済み投稿数: {history_data['count']}件")
            
            if history_data['tweets']:
                print("\n📋 最近いいねした投稿:")
                for i, tweet in enumerate(history_data['tweets'][:3], 1):
                    print(f"  {i}. ID: {tweet['id']}")
                    print(f"     内容: {tweet['text'][:50]}...")
                    print(f"     作成日: {tweet['created_at']}")
        else:
            print(f"❌ いいね履歴取得失敗: {history_data}")
    
    # 2. キャスト別認証でのテスト
    print(f"\n2️⃣ キャスト別認証でのいいね機能テスト")
    
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
                        test_tweet_id = input(f"\n📝 キャスト用テスト投稿IDを入力してください: ").strip()
                        
                        if test_tweet_id:
                            # キャストでいいねテスト
                            print(f"\n🧪 キャスト {test_cast_id} で投稿 {test_tweet_id} にいいねをテスト中...")
                            like_success, like_message = x_poster.like_tweet(test_tweet_id, cast_id=test_cast_id)
                            print(f"いいね結果: {'✅' if like_success else '❌'} {like_message}")
                            
                            # キャストのいいね履歴取得テスト
                            print(f"\n🧪 キャスト {test_cast_id} のいいね履歴取得テスト中...")
                            history_success, history_data = x_poster.get_liked_tweets(cast_id=test_cast_id, max_results=3)
                            if history_success:
                                print(f"✅ キャストいいね履歴取得成功")
                                print(f"アカウント: {history_data['account_type']}")
                                print(f"いいね済み投稿数: {history_data['count']}件")
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
    print("🎭 AIcast Room - X API いいね機能テスト 🎭")
    print("キャラクター別投稿システム")
    print("=" * 60)
    
    test_like_functionality()
    
    print(f"\n" + "=" * 60)
    print("🎯 テスト完了!")
    print()
    print("💡 使用可能な機能:")
    print("  - like_tweet(tweet_id, cast_id=None): 投稿にいいね")
    print("  - unlike_tweet(tweet_id, cast_id=None): いいね取り消し")
    print("  - get_liked_tweets(cast_id=None): いいね履歴取得")
    print()
    print("📝 投稿IDの取得方法:")
    print("  1. X (Twitter)で投稿を開く")
    print("  2. URLの末尾の数字が投稿ID")
    print("     例: https://x.com/username/status/1234567890123456789")
    print("     → 投稿ID: 1234567890123456789")

if __name__ == "__main__":
    main()