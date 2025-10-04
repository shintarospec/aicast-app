#!/usr/bin/env python3
# X API いいね権限 診断スクリプト

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from x_api_poster import x_poster
import sqlite3

def diagnose_like_permissions():
    """いいね権限の詳細診断"""
    print("🔍 X API いいね権限診断スクリプト")
    print("=" * 50)
    
    # 1. グローバル認証での詳細確認
    print("\n1️⃣ グローバル認証での詳細権限確認")
    success, result = x_poster.check_permissions_detailed()
    
    if success:
        print(f"✅ アカウント: @{result['username']} ({result['name']})")
        print(f"📋 アカウントタイプ: {result['account_type']}")
        print(f"🆔 ユーザーID: {result['user_id']}")
        
        # 権限テスト結果
        print(f"\n📊 権限テスト結果:")
        for test_name, test_result in result['tests'].items():
            if test_name == 'latest_tweet_id':
                continue
            
            if test_result == True:
                print(f"  ✅ {test_name}: OK")
            else:
                print(f"  ❌ {test_name}: {test_result}")
        
        # いいね権限の実テスト
        if 'latest_tweet_id' in result['tests']:
            latest_tweet_id = result['tests']['latest_tweet_id']
            print(f"\n🧪 いいね権限実テスト (投稿ID: {latest_tweet_id})")
            
            # いいねテスト
            like_success, like_msg = x_poster.like_tweet(latest_tweet_id)
            print(f"👍 いいねテスト: {'✅' if like_success else '❌'} {like_msg}")
            
            if like_success:
                # すぐに取り消し
                unlike_success, unlike_msg = x_poster.unlike_tweet(latest_tweet_id)
                print(f"💔 いいね取消: {'✅' if unlike_success else '❌'} {unlike_msg}")
            else:
                # エラー分析
                print(f"\n🔍 エラー分析:")
                if "403 Forbidden" in like_msg:
                    if "attached to a Project" in like_msg:
                        print("  📌 原因: アプリがプロジェクトに紐付いていません")
                        print("  💡 対策: X Developer Portalでプロジェクト内にアプリを作成し直す")
                    elif "scope" in like_msg.lower() or "permission" in like_msg.lower():
                        print("  📌 原因: OAuth 2.0スコープでlike.writeが有効になっていません")
                        print("  💡 対策: User authentication settingsでlike.writeスコープを有効化")
                    else:
                        print("  📌 原因: いいね権限が不足しています")
                        print("  💡 対策: App permissionsをRead and Writeに設定")
                
    else:
        print(f"❌ 詳細確認失敗: {result}")
    
    # 2. キャスト別認証での確認
    print(f"\n2️⃣ キャスト別認証での権限確認")
    
    try:
        conn = sqlite3.connect('casting_office.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.id, c.name, cx.twitter_username 
            FROM casts c 
            JOIN cast_x_credentials cx ON c.id = cx.cast_id 
            WHERE cx.is_active = 1
            LIMIT 3
        """)
        
        cast_credentials = cursor.fetchall()
        conn.close()
        
        if cast_credentials:
            print(f"✅ {len(cast_credentials)}個のキャストでテスト実行:")
            
            for cast_id, cast_name, twitter_username in cast_credentials:
                print(f"\n🎭 キャスト: {cast_name} (@{twitter_username})")
                
                # キャスト認証をセットアップ
                conn = sqlite3.connect('casting_office.db')
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT api_key, api_secret, bearer_token, access_token, access_token_secret
                    FROM cast_x_credentials 
                    WHERE cast_id = ? AND is_active = 1
                """, (cast_id,))
                
                cred_data = cursor.fetchone()
                conn.close()
                
                if cred_data:
                    api_key, api_secret, bearer_token, access_token, access_token_secret = cred_data
                    
                    setup_success, setup_message = x_poster.setup_cast_credentials(
                        cast_id, api_key, api_secret, bearer_token, access_token, access_token_secret
                    )
                    
                    if setup_success:
                        # キャスト権限詳細確認
                        cast_success, cast_result = x_poster.check_permissions_detailed(cast_id=cast_id)
                        
                        if cast_success:
                            print(f"  ✅ @{cast_result['username']} 権限確認完了")
                            
                            # いいね権限テスト
                            if 'latest_tweet_id' in cast_result['tests']:
                                latest_tweet_id = cast_result['tests']['latest_tweet_id']
                                like_success, like_msg = x_poster.like_tweet(latest_tweet_id, cast_id=cast_id)
                                print(f"  👍 いいねテスト: {'✅' if like_success else '❌'} {like_msg}")
                                
                                if like_success:
                                    unlike_success, unlike_msg = x_poster.unlike_tweet(latest_tweet_id, cast_id=cast_id)
                                    print(f"  💔 いいね取消: {'✅' if unlike_success else '❌'} {unlike_msg}")
                            else:
                                print(f"  ⚠️ いいねテスト用の投稿が見つかりません")
                        else:
                            print(f"  ❌ 権限確認失敗: {cast_result}")
                    else:
                        print(f"  ❌ 認証失敗: {setup_message}")
                
        else:
            print("❌ X API認証が設定されたキャストがありません")
    
    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")
    
    print(f"\n" + "=" * 50)
    print("🎯 診断完了!")
    print()
    print("💡 解決方法まとめ:")
    print("1. X Developer Portal → プロジェクト作成 → その中でアプリ作成")
    print("2. App permissions → Read and Write に設定")
    print("3. User authentication settings → OAuth 2.0 有効化")
    print("4. Scopes → like.write を含む全スコープを有効化")
    print("5. 新しいAPI Key/Token を発行・設定")
    print("6. AIcast Room で認証情報を更新")

def main():
    """メイン関数"""
    print("🎭 AIcast Room - X API いいね権限 診断ツール 🎭")
    print("=" * 60)
    
    diagnose_like_permissions()

if __name__ == "__main__":
    main()