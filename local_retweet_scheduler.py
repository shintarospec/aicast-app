#!/usr/bin/env python3
"""
リツイート予約専用スケジューラー
既存のlocal_schedule_checker.pyとは完全に独立したシステム
"""

from config import Config
import sqlite3
import json
import requests
from datetime import datetime
import sys
import os
import subprocess
import pytz

# 設定値
# 動的パス解決
current_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(current_dir, 'casting_office.db')
CLOUD_FUNCTION_URL = Config.get_cloud_functions_url()
JST = pytz.timezone('Asia/Tokyo')

def get_account_id_for_cast(cast_name, db_path):
    """キャスト名からX APIアカウントIDを取得"""
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
            return result[0]
        else:
            print(f"⚠️ {cast_name} のX API認証情報が見つかりません")
            return None
            
    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_scheduled_retweets(db_path):
    """実行予定時刻に達したリツイート予約を取得"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 日本時間のタイムゾーンを設定
        current_time_jst = datetime.now(JST)
        current_time_local_str = current_time_jst.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"🕐 現在時刻(JST): {current_time_local_str}")
        
        cursor.execute("""
            SELECT rs.id, rs.cast_id, rs.tweet_id, rs.comment, rs.scheduled_at, 
                   c.name as cast_name
            FROM retweet_schedules rs
            JOIN casts c ON rs.cast_id = c.id
            WHERE rs.scheduled_at IS NOT NULL 
            AND datetime(rs.scheduled_at) <= datetime(?)
            AND rs.status = 'scheduled'
            ORDER BY rs.scheduled_at ASC
        """, (current_time_local_str,))
        
        retweets = []
        for row in cursor.fetchall():
            cast_name = row['cast_name']
            account_id = get_account_id_for_cast(cast_name, db_path)
            
            if account_id:
                retweets.append({
                    'id': row['id'],
                    'cast_id': row['cast_id'],
                    'cast_name': cast_name,
                    'x_account_id': account_id,
                    'tweet_id': row['tweet_id'],
                    'comment': row['comment'],
                    'scheduled_at': row['scheduled_at']
                })
            else:
                print(f"⚠️ {cast_name} の投稿をスキップ（認証情報なし）")
                update_retweet_status(db_path, row['id'], 'failed', 
                                    error_message=f"{cast_name}の認証情報が見つかりません")
        
        return retweets
        
    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")
        return []
    finally:
        if conn:
            conn.close()

def execute_retweet(retweet):
    """Cloud Functions経由でリツイート/引用ツイートを実行"""
    try:
        # リツイートタイプを決定
        if retweet['comment'] and retweet['comment'].strip():
            # コメントがある場合は引用ツイート
            action = "quote_tweet"
            payload = {
                "action": action,
                "account_id": retweet['x_account_id'],
                "tweet_id": retweet['tweet_id'],
                "comment": retweet['comment'].strip()
            }
        else:
            # コメントがない場合は通常のリツイート
            action = "retweet"
            payload = {
                "action": action,
                "account_id": retweet['x_account_id'],
                "tweet_id": retweet['tweet_id']
            }
        
        print(f"📡 Cloud Functions呼び出し中...")
        print(f"🔍 アクション: {action}")
        print(f"🔍 送信データ: {payload}")
        
        response = requests.post(
            CLOUD_FUNCTION_URL,
            json=payload,
            timeout=30
        )
        
        print(f"🔍 レスポンス状態: {response.status_code}")
        print(f"🔍 レスポンス内容: {response.text[:200]}...")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                result_tweet_id = result.get('tweet_id', '')  # 引用ツイートの場合の新しいツイートID
                print(f"✅ {action}成功: {retweet['cast_name']}")
                if result_tweet_id:
                    print(f"   新しいツイートID: {result_tweet_id}")
                print(f"   元ツイートID: {retweet['tweet_id']}")
                
                return {
                    'status': 'success',
                    'result_tweet_id': result_tweet_id,
                    'message': f"{action}完了 for {retweet['cast_name']}"
                }
            else:
                error_msg = result.get('message', '不明なエラー')
                print(f"❌ {action}失敗: {error_msg}")
                return {
                    'status': 'error',
                    'message': error_msg
                }
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            print(f"❌ HTTP エラー: {error_msg}")
            return {
                'status': 'error',
                'message': error_msg
            }
            
    except requests.RequestException as e:
        error_msg = f"リクエストエラー: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            'status': 'error',
            'message': error_msg
        }
    except Exception as e:
        error_msg = f"予期しないエラー: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            'status': 'error',
            'message': error_msg
        }

def update_retweet_status(db_path, retweet_id, status, result_tweet_id=None, error_message=None):
    """リツイート予約の状態を更新"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        executed_at = datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            UPDATE retweet_schedules 
            SET status = ?, executed_at = ?, result_tweet_id = ?, error_message = ?
            WHERE id = ?
        """, (status, executed_at, result_tweet_id, error_message, retweet_id))
        
        conn.commit()
        print(f"📝 リツイート予約 ID {retweet_id} の状態を '{status}' に更新")
        
    except sqlite3.Error as e:
        print(f"❌ 状態更新エラー: {e}")
    finally:
        if conn:
            conn.close()

def check_cron_status():
    """cronサービスの状態確認"""
    try:
        result = subprocess.run(['service', 'cron', 'status'], 
                              capture_output=True, text=True, timeout=10)
        if "active (running)" in result.stdout:
            print("✅ cronサービス動作中")
            return True
        else:
            print("⚠️ cronサービス停止中")
            return False
    except Exception as e:
        print(f"⚠️ cronサービス状態確認エラー: {e}")
        return False

def main():
    """メイン処理"""
    print("🔄 リツイート予約スケジューラー - ローカルテスト")
    print(f"現在時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # cronサービス状態確認
    check_cron_status()
    
    # 実行予定のリツイート予約を取得
    retweets = get_scheduled_retweets(DB_PATH)
    
    if not retweets:
        print("📭 実行対象のリツイート予約はありません")
        return
    
    print(f"📅 {len(retweets)}件のリツイート予約を発見")
    
    # 各リツイート予約を実行
    for retweet in retweets:
        try:
            print(f"\n🎯 実行中: {retweet['cast_name']} - ツイートID: {retweet['tweet_id']}")
            print(f"   予定時刻: {retweet['scheduled_at']}")
            if retweet['comment']:
                print(f"   コメント: {retweet['comment'][:50]}...")
            
            result = execute_retweet(retweet)
            
            if result['status'] == 'success':
                update_retweet_status(DB_PATH, retweet['id'], 'completed', 
                                    result_tweet_id=result.get('result_tweet_id'))
                print(f"✅ {result['message']}")
            else:
                update_retweet_status(DB_PATH, retweet['id'], 'failed', 
                                    error_message=result['message'])
                print(f"❌ 失敗: {result['message']}")
                
        except Exception as e:
            error_msg = f"予期しないエラー: {str(e)}"
            print(f"❌ {error_msg}")
            update_retweet_status(DB_PATH, retweet['id'], 'failed', 
                                error_message=error_msg)

if __name__ == "__main__":
    main()