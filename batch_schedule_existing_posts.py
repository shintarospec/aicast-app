#!/usr/bin/env python3
"""
既存の承認済み投稿を一括予約するスクリプト
"""
import sqlite3
import datetime
import pytz

DB_PATH = "casting_office.db"
JST = pytz.timezone('Asia/Tokyo')

def execute_query(query, params=(), fetch=None):
    """データベースクエリ実行"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    
    if fetch == "one":
        result = cursor.fetchone()
    elif fetch == "all":
        result = cursor.fetchall()
    else:
        result = None
    
    conn.commit()
    conn.close()
    return result

def batch_schedule_posts():
    """承認済み投稿を一括予約"""
    print("=== 承認済み投稿の一括予約処理 ===")
    
    # 承認済み未予約の投稿を取得
    posts = execute_query("""
        SELECT id, cast_id, content, posted_at, scheduled_at
        FROM posts
        WHERE status = 'approved' 
        AND sent_status = 'not_sent'
        AND (posted_at IS NOT NULL OR scheduled_at IS NOT NULL)
        ORDER BY COALESCE(scheduled_at, posted_at) ASC
    """, fetch="all")
    
    if not posts:
        print("予約対象の投稿が見つかりませんでした")
        return
    
    print(f"対象投稿数: {len(posts)}件")
    
    scheduled_count = 0
    error_count = 0
    now = datetime.datetime.now()
    
    for post in posts:
        try:
            post_id = post['id']
            
            # scheduled_at または posted_at を使用
            time_str = post['scheduled_at'] or post['posted_at']
            
            # 時刻をパース
            try:
                target_datetime = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                # 時刻のみの場合
                time_only = datetime.datetime.strptime(time_str, '%H:%M:%S').time()
                target_datetime = datetime.datetime.combine(now.date(), time_only)
            
            # 過去時刻の場合は調整しない（スケジューラーが処理）
            scheduled_at_str = target_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            # 予約状態に更新
            execute_query("""
                UPDATE posts 
                SET sent_status = 'scheduled', scheduled_at = ?
                WHERE id = ?
            """, (scheduled_at_str, post_id))
            
            # 予約履歴を記録
            scheduled_at_log = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
            execute_query("""
                INSERT INTO send_history 
                (post_id, destination, sent_at, scheduled_datetime, status) 
                VALUES (?, ?, ?, ?, ?)
            """, (post_id, "x_api", scheduled_at_log, scheduled_at_str, 'scheduled'))
            
            scheduled_count += 1
            if scheduled_count % 50 == 0:
                print(f"進捗: {scheduled_count}件予約完了...")
        
        except Exception as e:
            print(f"エラー (投稿ID {post['id']}): {e}")
            error_count += 1
    
    print(f"\n=== 処理完了 ===")
    print(f"予約成功: {scheduled_count}件")
    print(f"エラー: {error_count}件")

if __name__ == "__main__":
    batch_schedule_posts()
