# AI画像投稿専用データベース管理モジュール
import sqlite3
import datetime
import os

# 画像投稿専用DBファイル
IMAGE_DB_FILE = "aicast_images.db"

def execute_image_query(query, params=(), fetch=None):
    """画像投稿専用データベース操作関数 - MCF DBと完全分離"""
    conn = None
    try:
        conn = sqlite3.connect(IMAGE_DB_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute(query, params)
        
        if fetch == "one":
            result = cursor.fetchone()
        elif fetch == "all":
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.lastrowid if cursor.lastrowid else None
        return result
    except sqlite3.Error as e:
        print(f"画像投稿DBエラー: {e}")
        return None if fetch else False
    finally:
        if conn:
            conn.close()

def init_image_db():
    """画像投稿専用データベースを初期化"""
    
    # 画像投稿テーブル
    img_posts_table = """
    CREATE TABLE IF NOT EXISTS img_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prompt TEXT NOT NULL,
        generated_image_path TEXT,
        generated_image_url TEXT,
        tweet_content TEXT,
        status TEXT DEFAULT 'draft',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        posted_at TIMESTAMP,
        tweet_id TEXT,
        cast_id INTEGER NOT NULL,
        cast_name TEXT NOT NULL,
        error_message TEXT,
        generation_params TEXT,
        image_size TEXT DEFAULT '1024x1024',
        model_used TEXT DEFAULT 'imagen-2'
    )
    """
    
    # 画像生成履歴テーブル
    img_generation_history_table = """
    CREATE TABLE IF NOT EXISTS img_generation_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prompt TEXT NOT NULL,
        model_used TEXT DEFAULT 'imagen-2',
        generation_time REAL,
        image_size TEXT DEFAULT '1024x1024',
        success INTEGER DEFAULT 1,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        cast_id INTEGER,
        cast_name TEXT
    )
    """
    
    # AI画像投稿設定テーブル
    img_settings_table = """
    CREATE TABLE IF NOT EXISTS img_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT UNIQUE NOT NULL,
        setting_value TEXT,
        description TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # テーブル作成
    execute_image_query(img_posts_table)
    execute_image_query(img_generation_history_table)
    execute_image_query(img_settings_table)
    
    # デフォルト設定の挿入
    default_settings = [
        ("max_daily_generations", "10", "1日あたりの最大画像生成数"),
        ("default_image_size", "1024x1024", "デフォルト画像サイズ"),
        ("auto_caption_enabled", "true", "自動キャプション生成の有効/無効"),
        ("cleanup_days", "7", "画像ファイル自動削除日数"),
    ]
    
    for key, value, desc in default_settings:
        execute_image_query(
            "INSERT OR IGNORE INTO img_settings (setting_key, setting_value, description) VALUES (?, ?, ?)",
            (key, value, desc)
        )
    
    print("✅ 画像投稿専用データベースを初期化しました")

def get_img_setting(key, default_value=None):
    """画像投稿設定を取得"""
    result = execute_image_query(
        "SELECT setting_value FROM img_settings WHERE setting_key = ?",
        (key,), fetch="one"
    )
    return result['setting_value'] if result else default_value

def set_img_setting(key, value, description=None):
    """画像投稿設定を更新"""
    execute_image_query(
        """INSERT OR REPLACE INTO img_settings 
           (setting_key, setting_value, description, updated_at) 
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
        (key, value, description)
    )

def save_img_post(prompt, cast_id, cast_name, tweet_content="", generation_params=None):
    """画像投稿データを保存"""
    return execute_image_query(
        """INSERT INTO img_posts 
           (prompt, cast_id, cast_name, tweet_content, generation_params) 
           VALUES (?, ?, ?, ?, ?)""",
        (prompt, cast_id, cast_name, tweet_content, generation_params)
    )

def update_img_post_status(post_id, status, **kwargs):
    """画像投稿ステータスを更新"""
    set_clauses = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
    params = [status]
    
    for key, value in kwargs.items():
        if key in ['generated_image_path', 'generated_image_url', 'tweet_content', 
                   'posted_at', 'tweet_id', 'error_message']:
            set_clauses.append(f"{key} = ?")
            params.append(value)
    
    params.append(post_id)
    
    query = f"UPDATE img_posts SET {', '.join(set_clauses)} WHERE id = ?"
    return execute_image_query(query, params)

def get_img_post(post_id):
    """画像投稿データを取得"""
    return execute_image_query(
        "SELECT * FROM img_posts WHERE id = ?",
        (post_id,), fetch="one"
    )

def get_img_posts_by_status(status=None, cast_id=None, limit=50):
    """ステータス別画像投稿一覧を取得"""
    query = "SELECT * FROM img_posts"
    params = []
    conditions = []
    
    if status:
        conditions.append("status = ?")
        params.append(status)
    
    if cast_id:
        conditions.append("cast_id = ?")
        params.append(cast_id)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    return execute_image_query(query, params, fetch="all")

def log_generation_history(prompt, model_used, generation_time, success=True, 
                          error_message=None, cast_id=None, cast_name=None):
    """画像生成履歴を記録"""
    return execute_image_query(
        """INSERT INTO img_generation_history 
           (prompt, model_used, generation_time, success, error_message, cast_id, cast_name) 
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (prompt, model_used, generation_time, 1 if success else 0, 
         error_message, cast_id, cast_name)
    )

def get_daily_generation_count(cast_id=None):
    """本日の画像生成回数を取得"""
    today = datetime.date.today().isoformat()
    
    if cast_id:
        return execute_image_query(
            """SELECT COUNT(*) as count FROM img_generation_history 
               WHERE DATE(created_at) = ? AND cast_id = ?""",
            (today, cast_id), fetch="one"
        )['count']
    else:
        return execute_image_query(
            "SELECT COUNT(*) as count FROM img_generation_history WHERE DATE(created_at) = ?",
            (today,), fetch="one"
        )['count']

def cleanup_old_images():
    """古い画像ファイルを削除"""
    cleanup_days = int(get_img_setting("cleanup_days", "7"))
    cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=cleanup_days)).isoformat()
    
    # 削除対象のファイルパスを取得
    old_posts = execute_image_query(
        "SELECT generated_image_path FROM img_posts WHERE created_at < ? AND generated_image_path IS NOT NULL",
        (cutoff_date,), fetch="all"
    )
    
    deleted_count = 0
    for post in old_posts:
        if post['generated_image_path'] and os.path.exists(post['generated_image_path']):
            try:
                os.remove(post['generated_image_path'])
                deleted_count += 1
            except OSError:
                pass
    
    # データベースからも削除
    execute_image_query(
        "DELETE FROM img_posts WHERE created_at < ?",
        (cutoff_date,)
    )
    
    return deleted_count

# データベース初期化（モジュール読み込み時に実行）
if __name__ == "__main__":
    init_image_db()
    print("画像投稿専用データベースの初期化が完了しました")