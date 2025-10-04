#!/usr/bin/env python3
# X API コメント入りリツイート機能テストスクリプト

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from x_api_poster import x_poster
import sqlite3

def test_quote_tweet_functionality():
    """コメント入りリツイート機能のテスト"""
    print("💬 X API コメント入りリツイート機能テスト")
    print("=" * 50)
    
    # 1. グローバル認証テスト
    print("\n1️⃣ グローバル認証でのコメント入りリツイート機能テスト")
    success, message = x_poster.setup_credentials()
    print(f"グローバル認証: {'✅' if success else '❌'} {message}")
    
    if success:
        # テスト用の投稿ID
        test_tweet_id = input("\n📝 コメント付きでリツイートしたい投稿のIDを入力してください（例: 1234567890123456789): ").strip()
        
        if test_tweet_id:
            # コメント入力
            comment = input("💬 コメント内容を入力してください（280文字以内): ").strip()
            
            if comment:
                # 文字数チェック
                if len(comment) > 280:
                    print(f"❌ コメントが280文字を超えています（{len(comment)}文字）")
                else:
                    # コメント入りリツイートテスト
                    print(f"\n🧪 投稿 {test_tweet_id} をコメント付きでリツイート中...")
                    print(f"📝 コメント: {comment}")
                    
                    qt_success, qt_message = x_poster.quote_tweet(test_tweet_id, comment)
                    print(f"コメント入りリツイート結果: {'✅' if qt_success else '❌'} {qt_message}")
            else:
                print("⚠️ コメントが入力されませんでした")
        else:
            print("⚠️ 投稿IDが入力されませんでした")
    
    # 2. キャスト別認証でのテスト
    print(f"\n2️⃣ キャスト別認証でのコメント入りリツイート機能テスト")
    
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
                        test_tweet_id = input(f"\n📝 キャスト用コメント入りリツイート投稿IDを入力してください: ").strip()
                        
                        if test_tweet_id:
                            # コメント入力
                            comment = input("💬 キャストのコメント内容を入力してください（280文字以内): ").strip()
                            
                            if comment:
                                # 文字数チェック
                                if len(comment) > 280:
                                    print(f"❌ コメントが280文字を超えています（{len(comment)}文字）")
                                else:
                                    # キャストでコメント入りリツイートテスト
                                    print(f"\n🧪 キャスト {test_cast_id} で投稿 {test_tweet_id} をコメント付きでリツイート中...")
                                    print(f"📝 コメント: {comment}")
                                    
                                    qt_success, qt_message = x_poster.quote_tweet(test_tweet_id, comment, cast_id=test_cast_id)
                                    print(f"コメント入りリツイート結果: {'✅' if qt_success else '❌'} {qt_message}")
                            else:
                                print("⚠️ コメントが入力されませんでした")
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
    print("🎭 AIcast Room - X API コメント入りリツイート機能テスト 🎭")
    print("キャラクター別引用ツイートシステム")
    print("=" * 60)
    
    print("💰 **プラン別制限情報** (通常の投稿制限と同じ)")
    print("  FREEプラン: 17回/24時間")
    print("  BASICプラン ($100/月): 1,667回/24時間") 
    print("  PROプラン ($5,000/月): 10,000回/24時間")
    print()
    
    test_quote_tweet_functionality()
    
    print(f"\n" + "=" * 60)
    print("🎯 テスト完了!")
    print()
    print("💡 使用可能な機能:")
    print("  - quote_tweet(tweet_id, comment, cast_id=None): コメント入りリツイート")
    print("  - post_tweet(content, cast_name=None, quote_tweet_id=None): 引用ツイート対応投稿")
    print()
    print("📝 投稿IDの取得方法:")
    print("  1. X (Twitter)で投稿を開く")
    print("  2. URLの末尾の数字が投稿ID")
    print("     例: https://x.com/username/status/1234567890123456789")
    print("     → 投稿ID: 1234567890123456789")
    print()
    print("💬 コメント入りリツイートの特徴:")
    print("  - 元の投稿を引用しながら自分のコメントを追加")
    print("  - 280文字以内でコメントを記述")
    print("  - 通常の投稿として扱われるため投稿制限を消費")
    print("  - フォロワーのタイムラインに表示される")
    print()
    print("🎉 FREEプランでもコメント入りリツイート機能が利用可能です！")

if __name__ == "__main__":
    main()