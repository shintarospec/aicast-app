#!/usr/bin/env python3
"""
ローカルスケジュール投稿チェッカー
Cloud Functionsの代わりにローカルでスケジュール投稿をテスト実行
"""

import sqlite3
import json
from config import Config
import requests
from datetime import datetime
import sys
import os
import subprocess
import pytz

# 自動生成バッチのインポート
try:
    from auto_generation_batch import run_auto_generation
    AUTO_GENERATION_AVAILABLE = True
except ImportError:
    AUTO_GENERATION_AVAILABLE = False
    print("⚠️  auto_generation_batch.py が見つかりません - 自動生成機能は無効です")

# 🔐 Security Feature Configuration
USE_SECRET_MANAGER = False  # Set to True to enable Secret Manager security features
                           # Currently disabled for development compatibility
                           # Future enhancement: Set to True for production security

def create_secret_manager_entry(account_id, db_path):
    """データベースからX API認証情報を取得してSecret Managerに自動設定
    
    🔐 セキュリティ機能: Secret Manager統合
    - 将来の機能拡張のためコードを保持
    - USE_SECRET_MANAGER = True で有効化可能
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # データベースから認証情報を取得
        cursor.execute("""
            SELECT api_key, api_secret, bearer_token, access_token, access_token_secret
            FROM cast_x_credentials cxc
            JOIN casts c ON cxc.cast_id = c.id
            WHERE c.name = ? AND cxc.is_active = 1
        """, (account_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            print(f"❌ {account_id} のデータベース認証情報が見つかりません")
            return False
            
        # Secret Manager用のJSON作成
        credentials = {
            "consumer_key": result[0],
            "consumer_secret": result[1], 
            "bearer_token": result[2],
            "access_token": result[3],
            "access_token_secret": result[4]
        }
        
        # Secret Managerに設定
        secret_name = f"x-api-{account_id}"
        
        # 一時ファイルに保存
        temp_file = f"/tmp/{secret_name}.json"
        with open(temp_file, 'w') as f:
            json.dump(credentials, f)
        
        # gcloud コマンドでSecret Manager作成
        result = subprocess.run([
            'gcloud', 'secrets', 'create', secret_name,
            '--data-file', temp_file
        ], capture_output=True, text=True)
        
        # 一時ファイル削除
        os.remove(temp_file)
        
        if result.returncode == 0:
            print(f"✅ Secret Manager設定完了: {secret_name}")
            return True
        else:
            print(f"❌ Secret Manager設定失敗: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Secret Manager自動設定エラー: {e}")
        return False

def sanitize_content_for_x_api(content):
    """X APIポリシーに準拠するよう投稿内容を調整"""
    # 問題のあるハッシュタグを調整
    content = content.replace('#キャバ嬢', '#接客業')
    content = content.replace('#六本木', '#東京')
    
    # その他の調整が必要な場合はここに追加
    
    return content

def get_account_id_for_cast(cast_name, db_path):
    """キャスト名からX APIアカウントIDを取得
    
    🔐 セキュリティ設定:
    - USE_SECRET_MANAGER = False: データベース直接取得（開発環境向け）
    - USE_SECRET_MANAGER = True:  Secret Manager統合（本番環境向け）
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cxc.twitter_username 
            FROM cast_x_credentials cxc
            JOIN casts c ON c.id = cxc.cast_id
            WHERE c.name = ?
        """, (cast_name,))
        result = cursor.fetchone()
        
        if result:
            account_id = result[0]
            
            # 🔐 Secret Manager統合機能（将来の機能拡張用）
            if USE_SECRET_MANAGER:
                # Secret Managerの存在確認
                secret_name = f"x-api-{account_id}"
                check_result = subprocess.run([
                    'gcloud', 'secrets', 'describe', secret_name
                ], capture_output=True, text=True)
                
                if check_result.returncode != 0:
                    print(f"⚠️  Secret Manager未設定: {secret_name}")
                    print(f"🔧 自動設定を実行中...")
                    
                    if create_secret_manager_entry(account_id, db_path):
                        print(f"✅ {account_id} の自動設定完了")
                    else:
                        print(f"❌ {account_id} の自動設定失敗 - 投稿をスキップします")
                        print(f"⚠️  各キャストは専用アカウントでのみ投稿可能です")
                        return None  # フォールバック禁止
            
            return account_id
        else:
            print(f"⚠️ {cast_name} のX API認証情報が見つかりません")
            return None
            
    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_scheduled_posts(db_path):
    """実行予定時刻に達した投稿を取得"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 日本時間のタイムゾーンを設定
        JST = pytz.timezone('Asia/Tokyo')
        UTC = pytz.timezone('UTC')
        
        # 現在の日本時間を取得
        current_time_jst = datetime.now(JST)
        current_time_local_str = current_time_jst.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"🕐 現在時刻(JST): {current_time_local_str}")
        
        cursor.execute("""
            SELECT p.id, p.cast_id, p.content, p.scheduled_at, c.name as cast_name
            FROM posts p
            JOIN casts c ON p.cast_id = c.id
            WHERE p.scheduled_at IS NOT NULL 
            AND datetime(p.scheduled_at) <= datetime(?)
            AND p.sent_status = 'scheduled'
            ORDER BY p.scheduled_at ASC
        """, (current_time_local_str,))
        
        posts = []
        for row in cursor.fetchall():
            cast_name = row[4]
            # キャスト名からX APIアカウントIDをデータベースから取得
            account_id = get_account_id_for_cast(cast_name, db_path)
            
            # account_idがNoneの場合はスキップ（各キャストは専用アカウントでのみ投稿）
            if account_id is None:
                print(f"⚠️  {cast_name} の投稿をスキップ（認証情報なし）")
                continue
            
            posts.append({
                'id': row[0],
                'cast_id': row[1],
                'content': row[2],
                'scheduled_at': row[3],
                'cast_name': cast_name,
                'x_account_id': account_id
            })
        
        conn.close()
        return posts
        
    except Exception as e:
        raise Exception(f"Failed to get scheduled posts: {str(e)}")

def execute_real_post(post):
    """実際にX APIで投稿実行"""
    print(f"🚀 実際の投稿実行:")
    print(f"   キャスト: {post['cast_name']}")
    print(f"   アカウント: {post['x_account_id']}")
    print(f"   内容: {post['content'][:50]}...")
    print(f"   予定時刻: {post['scheduled_at']}")
    
    try:
        # Cloud Functions のX-poster APIを呼び出し
        CLOUD_FUNCTION_URL = Config.get_cloud_functions_url()
        
        # 投稿内容をX APIポリシーに準拠するよう調整
        sanitized_content = sanitize_content_for_x_api(post['content'])
        
        # 二重チェック: account_idが正しくマッピングされているか確認
        # 動的パス解決
        current_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(current_dir, 'casting_office.db')
        expected_account = get_account_id_for_cast(post['cast_name'], db_path)
        if post['x_account_id'] != expected_account:
            print(f"🚨 CRITICAL ERROR: アカウントマッピング不一致!")
            print(f"   キャスト: {post['cast_name']}")
            print(f"   期待アカウント: {expected_account}")
            print(f"   実際アカウント: {post['x_account_id']}")
            print(f"   → 投稿を緊急停止します")
            return {
                'status': 'error',
                'message': f"アカウントマッピング不一致により投稿停止"
            }
        
        payload = {
            "action": "post",
            "account_id": post['x_account_id'],
            "text": sanitized_content  # 調整済み内容を使用
        }
        
        print(f"📡 Cloud Functions呼び出し中...")
        print(f"🔍 送信データ: {payload}")
        response = requests.post(
            CLOUD_FUNCTION_URL,
            json=payload,
            timeout=30
        )
        
        print(f"🔍 レスポンス状態: {response.status_code}")
        print(f"🔍 レスポンス内容: {response.text[:200]}...")  # 最初の200文字のみ表示
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':  # 'success' -> 'status' == 'success'に修正
                tweet_id = result.get('tweet_id', 'ID不明')
                print(f"✅ 投稿成功: Tweet ID {tweet_id}")
                return {
                    'status': 'success',
                    'tweet_id': tweet_id,
                    'message': f"投稿完了 for {post['cast_name']}"
                }
            else:
                error_msg = result.get('error', '不明なエラー')
                print(f"❌ 投稿失敗: {error_msg}")
                return {
                    'status': 'error',
                    'message': f"投稿失敗: {error_msg}"
                }
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            print(f"❌ Cloud Functions呼び出し失敗: {error_msg}")
            return {
                'status': 'error',
                'message': f"Cloud Functions失敗: {error_msg}"
            }
            
    except requests.exceptions.Timeout:
        print(f"❌ タイムアウトエラー")
        return {
            'status': 'error',
            'message': "Cloud Functions呼び出しタイムアウト"
        }
    except Exception as e:
        print(f"❌ 投稿エラー: {str(e)}")
        return {
            'status': 'error',
            'message': f"投稿エラー: {str(e)}"
        }

def update_post_status(db_path, post_id, status, tweet_id=None):
    """投稿ステータスを更新"""
    try:
        print(f"🔍 update_post_status - DBパス: {db_path}")
        print(f"🔍 update_post_status - ファイル存在: {os.path.exists(db_path)}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # VPSはJST環境のため、datetime.now()で問題なし
        current_time = datetime.now().isoformat()
        
        if status == 'sent':
            cursor.execute("""
                UPDATE posts 
                SET sent_status = 'sent', sent_at = ?, posted_at = ?
                WHERE id = ?
            """, (current_time, current_time, post_id))
        else:
            cursor.execute("""
                UPDATE posts 
                SET sent_status = ?
                WHERE id = ?
            """, (status, post_id))
        
        conn.commit()
        conn.close()
        print(f"✅ update_post_status - 投稿ID {post_id} を {status} に更新完了")
        
    except Exception as e:
        print(f"❌ update_post_status - エラー: {str(e)}")
        raise Exception(f"Failed to update post status: {str(e)}")

def main():
    """メイン処理"""
    print("🕐 スケジュール投稿チェッカー - ローカルテスト")
    print(f"現在時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # cronサービスの動作確認
    try:
        result = subprocess.run(['pgrep', 'cron'], capture_output=True)
        if result.returncode != 0:
            print("⚠️  cronサービスが停止しています！")
            print("🔧 cronサービスを再開してください: sudo service cron start")
        else:
            print("✅ cronサービス動作中")
    except Exception as e:
        print(f"⚠️  cronサービス確認エラー: {e}")
    
    print()
    
    # 🤖 自動生成バッチ実行（毎時00分台、重複防止付き）
    current_time = datetime.now()
    if AUTO_GENERATION_AVAILABLE and current_time.minute == 0:
        # 重複実行防止: 現在時刻（時）をフラグファイルで管理
        current_dir = os.path.dirname(os.path.abspath(__file__))
        flag_file = os.path.join(current_dir, '.auto_generation_last_run')
        current_hour_key = current_time.strftime('%Y-%m-%d-%H')
        
        # 前回実行時刻を確認
        should_run = True
        if os.path.exists(flag_file):
            try:
                with open(flag_file, 'r') as f:
                    last_run_hour = f.read().strip()
                    if last_run_hour == current_hour_key:
                        should_run = False
                        print(f"⏭️  自動生成バッチは既に実行済み（{current_hour_key}）")
            except:
                pass
        
        if should_run:
            print("🤖 投稿案の自動生成バッチを実行中...")
            try:
                run_auto_generation()
                # 実行成功時にフラグファイルを更新
                with open(flag_file, 'w') as f:
                    f.write(current_hour_key)
                print("✅ 自動生成バッチ完了")
            except Exception as e:
                print(f"❌ 自動生成バッチエラー: {e}")
        print()
    
    # 動的パス解決: 実行ディレクトリからデータベースを探す
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'casting_office.db')
    
    print(f"🔍 デバッグ情報:")
    print(f"   - スクリプトディレクトリ: {current_dir}")
    print(f"   - データベースパス: {db_path}")
    print(f"   - ファイル存在: {os.path.exists(db_path)}")
    
    try:
        # スケジュールされた投稿を検索
        scheduled_posts = get_scheduled_posts(db_path)
        
        if not scheduled_posts:
            print("📭 実行対象のスケジュール投稿はありません")
            return
        
        print(f"📅 {len(scheduled_posts)}件のスケジュール投稿を発見:")
        
        # 各投稿を処理
        processed_count = 0
        errors = []
        
        for post in scheduled_posts:
            print(f"\n--- 投稿ID: {post['id']} ---")
            try:
                result = execute_real_post(post)
                if result['status'] == 'success':
                    processed_count += 1
                    # 投稿状態を更新
                    update_post_status(db_path, post['id'], 'sent', result.get('tweet_id'))
                    print(f"✅ {result['message']}")
                else:
                    # 失敗時もステータスを更新
                    update_post_status(db_path, post['id'], 'failed')
                    errors.append(f"Post {post['id']}: {result['message']}")
                    print(f"❌ 失敗: {result['message']}")
                    
            except Exception as e:
                # 例外発生時もステータスを更新
                update_post_status(db_path, post['id'], 'failed')
                errors.append(f"Post {post['id']}: {str(e)}")
                print(f"❌ エラー: {str(e)}")
        
        print(f"\n🎉 処理完了:")
        print(f"   成功: {processed_count}件")
        print(f"   失敗: {len(errors)}件")
        
        if errors:
            print(f"\n❌ エラー詳細:")
            for error in errors:
                print(f"   - {error}")
        
    except Exception as e:
        print(f"❌ 全体エラー: {str(e)}")
        print(f"❌ エラータイプ: {type(e).__name__}")
        import traceback
        print(f"❌ スタックトレース:")
        traceback.print_exc()

if __name__ == "__main__":
    main()