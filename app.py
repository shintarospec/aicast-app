import streamlit as st
import pandas as pd
import datetime
import time
import random
import sqlite3
import vertexai
try:
    # 新しいVertex AI SDK を試す
    from vertexai.generative_models import GenerativeModel
except ImportError:
    # フォールバック: 古いAPI
    from vertexai.preview.generative_models import GenerativeModel
import os
import io
import re
import gspread
from google.oauth2.service_account import Credentials
import pickle

# 🔐 認証システムのインポート
from auth_system import check_password, show_auth_status

# 🔐 認証チェック（アプリの最初に実行）
if not check_password():
    st.stop()

# 🔐 認証状態表示
show_auth_status()

from config import Config

# X API投稿機能
from x_api_poster import x_poster

# Cloud Functions投稿クライアント
import requests
import json

# 🌐 Streamlit Cloud Production Environment Setup
def setup_production_environment():
    """
    Initialize production environment for Streamlit Cloud
    🎖️ MCF: Maintains all Mission-Critical Functions in production
    """
    # Production environment detection
    if Config.is_production_environment():
        st.sidebar.success("🌐 Production Environment: Streamlit Cloud")
        
        # MCF Production validation
        mcf_errors = Config.validate_mcf_settings()
        if mcf_errors:
            st.sidebar.error("🚨 MCF Production Alert:")
            for error in mcf_errors:
                st.sidebar.error(f"   • {error}")
        else:
            st.sidebar.success("🎖️ MCF: All systems operational")
    
    # Database initialization for production
    initialize_database_for_production()

def initialize_database_for_production():
    """
    Initialize database for production environment
    🎖️ MCF: Ensures database availability in all environments
    """
    try:
        # Ensure database exists
        if not os.path.exists(Config.DATABASE_PATH):
            # Create database with required tables
            execute_query("""
                CREATE TABLE IF NOT EXISTS casts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    nickname TEXT,
                    x_account_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            execute_query("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cast_id INTEGER,
                    content TEXT NOT NULL,
                    scheduled_at DATETIME,
                    sent_status TEXT DEFAULT 'draft',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cast_id) REFERENCES casts (id)
                )
            """)
            
            execute_query("""
                CREATE TABLE IF NOT EXISTS retweet_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cast_id INTEGER,
                    tweet_url TEXT NOT NULL,
                    scheduled_at DATETIME,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cast_id) REFERENCES casts (id)
                )
            """)
            
            st.success("🎖️ MCF Database initialized for production")
    except Exception as e:
        st.error(f"Database initialization error: {e}")

# Initialize production environment
setup_production_environment()

class CloudFunctionsPoster:
    """Cloud Functions経由のX投稿クライアント"""
    
    def __init__(self, function_url=None):
        self.function_url = function_url or os.environ.get('CLOUD_FUNCTIONS_URL')
    
    def post_tweet(self, account_id, text, image_url=None):
        """Cloud Functions経由でX投稿"""
        if not self.function_url:
            return {"status": "error", "message": "Cloud Functions URL not configured"}
        
        payload = {
            "account_id": account_id,
            "text": text,
            "image_url": image_url
        }
        
        try:
            response = requests.post(
                self.function_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

class DualPostingSystem:
    """デュアル投稿システム：スプレッドシート + Cloud Functions"""
    
    def __init__(self):
        self.cf_poster = CloudFunctionsPoster()
        
    def send_post(self, cast_name, content, scheduled_datetime, cast_id=None, 
                  posting_method="auto", image_urls=None):
        """投稿方式を選択して送信"""
        
        if posting_method == "cloud_functions":
            return self.send_via_cloud_functions(cast_id, content, image_urls)
        elif posting_method == "google_sheets":
            return send_to_google_sheets(cast_name, content, scheduled_datetime, 
                                       cast_id, 'post', image_urls)
        elif posting_method == "auto":
            # 自動選択ロジック
            return self.auto_select_method(cast_name, content, scheduled_datetime, 
                                         cast_id, image_urls)
        else:
            return {"status": "error", "message": "Invalid posting method"}
    
    def send_via_cloud_functions(self, cast_id, content, image_urls=None):
        """Cloud Functions経由で直接投稿"""
        try:
            # アカウント情報取得
            account_info = execute_query(
                "SELECT x_account_id FROM casts WHERE id = ?",
                (cast_id,),
                fetch="one"
            )
            
            if not account_info:
                return {"status": "error", "message": "Cast account not found"}
            
            account_id = account_info['x_account_id']
            image_url = image_urls[0] if image_urls else None
            
            # Cloud Functions投稿実行
            result = self.cf_poster.post_tweet(account_id, content, image_url)
            
            if result.get("status") == "success":
                # 投稿履歴を記録
                self.record_posting_history(cast_id, content, "cloud_functions", 
                                          result.get("tweet_id"))
                return {"status": "success", "message": "Cloud Functions投稿完了"}
            else:
                return result
                
        except Exception as e:
            return {"status": "error", "message": f"Cloud Functions投稿エラー: {str(e)}"}
    
    def auto_select_method(self, cast_name, content, scheduled_datetime, 
                          cast_id, image_urls=None):
        """自動的に最適な投稿方式を選択"""
        
        # スケジュール投稿の場合はスプレッドシート
        if scheduled_datetime and scheduled_datetime > datetime.now():
            return send_to_google_sheets(cast_name, content, scheduled_datetime, 
                                       cast_id, 'post', image_urls)
        
        # 即座投稿でCloud Functions設定済みなら直接投稿
        if self.cf_poster.function_url:
            cf_result = self.send_via_cloud_functions(cast_id, content, image_urls)
            if cf_result.get("status") == "success":
                return cf_result
        
        # フォールバック：スプレッドシート経由
        return send_to_google_sheets(cast_name, content, scheduled_datetime, 
                                   cast_id, 'post', image_urls)
    
    def record_posting_history(self, cast_id, content, method, tweet_id=None):
        """投稿履歴を記録"""
        execute_query(
            "INSERT INTO send_history (cast_id, content, method, tweet_id, sent_at) VALUES (?, ?, ?, ?, ?)",
            (cast_id, content, method, tweet_id, datetime.now().isoformat())
        )

# デュアル投稿システム初期化
dual_poster = DualPostingSystem()

# Cloud Functions投稿クライアント初期化
cf_poster = CloudFunctionsPoster()

# pandasの参照を保護
pandas_lib = pd

# 認証エラー用のヘルパー関数
def get_guidance_advice(category_id=None):
    """指針アドバイスを取得する関数"""
    advice_parts = []
    
    # グローバル指針アドバイスを取得
    global_advices = execute_query(
        "SELECT title, content FROM global_advice WHERE is_active = 1 ORDER BY sort_order, created_at",
        fetch="all"
    )
    
    if global_advices:
        advice_parts.append("【グローバル指針】")
        for advice in global_advices:
            advice_parts.append(f"■ {advice['title']}: {advice['content']}")
    
    # カテゴリ別指針アドバイスを取得（カテゴリIDが指定されている場合）
    if category_id:
        category_advices = execute_query(
            "SELECT title, content FROM category_advice WHERE category_id = ? AND is_active = 1 ORDER BY sort_order, created_at",
            (category_id,),
            fetch="all"
        )
        
        if category_advices:
            # カテゴリ名も取得
            category_name = execute_query(
                "SELECT name FROM situation_categories WHERE id = ?",
                (category_id,),
                fetch="one"
            )
            category_display = category_name['name'] if category_name else f"カテゴリID:{category_id}"
            
            advice_parts.append(f"\n【{category_display}カテゴリ専用指針】")
            for advice in category_advices:
                advice_parts.append(f"■ {advice['title']}: {advice['content']}")
    
    return "\n".join(advice_parts) if advice_parts else ""

def show_auth_error_guidance(error_msg, context="AI生成"):
    """認証エラー時の案内を表示する共通関数"""
    st.error(f"🔐 **Google Cloud認証エラー ({context})**")
    
    # 認証関連のエラーかチェック
    auth_keywords = ["credential", "authentication", "unauthorized", "permission", "quota", "token"]
    is_auth_error = any(keyword.lower() in str(error_msg).lower() for keyword in auth_keywords)
    
    if is_auth_error:
        st.markdown(f"""
        **📋 認証エラーの解決方法:**
        1. 左サイドバーの「**システム設定**」をクリック
        2. 「**🔐 Google Cloud認証**」タブを開く
        3. 認証情報を確認・再設定してください
        
        **💡 よくある原因:**
        - 認証の有効期限切れ
        - プロジェクト設定の不備
        - API制限の到達
        
        **エラー詳細:** `{error_msg}`
        """)
        
        if st.button("🔧 認証設定に移動", type="primary", key=f"auth_btn_{context}"):
            st.session_state['redirect_to_settings'] = True
            st.rerun()
    else:
        st.error(f"エラー詳細: {error_msg}")
        st.info("💡 問題が継続する場合は、システム設定で認証状況を確認してください。")

# --- 設定 ---
project_id = os.environ.get("GCP_PROJECT")
if not project_id:
    project_id = os.environ.get("DEVSHELL_PROJECT_ID", "aicast-472807")
# Vertex AI基本地域（最も確実）
location = "us-central1"  # Vertex AIの基本地域
DB_FILE = "casting_office.db"
JST = datetime.timezone(datetime.timedelta(hours=9))

# --- データベースの列定義 ---
PERSONA_FIELDS = [
    "name", "nickname", "age", "birthday", "birthplace", "appearance",
    "personality", "strength", "weakness", "first_person", "speech_style", "catchphrase", "customer_interaction",
    "occupation", "hobby", "likes", "dislikes", "holiday_activity", "dream", "reason_for_job", "secret",
    "allowed_categories"
]

# --- データベース関数 ---
def execute_query(query, params=(), fetch=None):
    """データベース接続、クエリ実行、接続切断を安全に行う"""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
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
        if "UNIQUE constraint failed" in str(e):
            st.error(f"データベースエラー: 同じ内容が既に存在するため、追加できません。")
        else:
            st.error(f"データベースエラー: {e}")
        return None if fetch else False
    finally:
        if conn:
            conn.close()

def init_db():
    """データベースとテーブルを初期化する"""
    persona_columns = ", ".join([f"{field} TEXT" for field in PERSONA_FIELDS if field != 'name'])
    casts_table_query = f"CREATE TABLE IF NOT EXISTS casts (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, {persona_columns})"
    posts_table_query = "CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, cast_id INTEGER, created_at TEXT, content TEXT, theme TEXT, evaluation TEXT, advice TEXT, free_advice TEXT, status TEXT DEFAULT 'draft', posted_at TEXT, sent_status TEXT DEFAULT 'not_sent', sent_at TEXT, generated_at TEXT, FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE)"
    situations_table_query = "CREATE TABLE IF NOT EXISTS situations (id INTEGER PRIMARY KEY, content TEXT NOT NULL UNIQUE, time_slot TEXT DEFAULT 'いつでも', category_id INTEGER, FOREIGN KEY(category_id) REFERENCES situation_categories(id) ON DELETE CASCADE)"
    categories_table_query = "CREATE TABLE IF NOT EXISTS situation_categories (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)"
    advice_table_query = 'CREATE TABLE IF NOT EXISTS advice_master (id INTEGER PRIMARY KEY, content TEXT NOT NULL UNIQUE)'
    groups_table_query = "CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, content TEXT NOT NULL)"
    cast_groups_table_query = "CREATE TABLE IF NOT EXISTS cast_groups (cast_id INTEGER, group_id INTEGER, PRIMARY KEY (cast_id, group_id), FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE, FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE)"
    tuning_history_table_query = "CREATE TABLE IF NOT EXISTS tuning_history (id INTEGER PRIMARY KEY, post_id INTEGER, timestamp TEXT, previous_content TEXT, advice_used TEXT, FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE)"
    custom_fields_table_query = "CREATE TABLE IF NOT EXISTS custom_fields (id INTEGER PRIMARY KEY, field_name TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL, field_type TEXT DEFAULT 'text', placeholder TEXT DEFAULT '', is_required INTEGER DEFAULT 0, sort_order INTEGER DEFAULT 0)"
    send_history_table_query = "CREATE TABLE IF NOT EXISTS send_history (id INTEGER PRIMARY KEY, post_id INTEGER, destination TEXT, sent_at TEXT, scheduled_datetime TEXT, status TEXT DEFAULT 'pending', error_message TEXT, FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE)"
    app_settings_table_query = "CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, description TEXT DEFAULT '', category TEXT DEFAULT 'general')"
    global_advice_table_query = "CREATE TABLE IF NOT EXISTS global_advice (id INTEGER PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL, is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP, sort_order INTEGER DEFAULT 0)"
    category_advice_table_query = "CREATE TABLE IF NOT EXISTS category_advice (id INTEGER PRIMARY KEY, category_id INTEGER, title TEXT NOT NULL, content TEXT NOT NULL, is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP, sort_order INTEGER DEFAULT 0, FOREIGN KEY(category_id) REFERENCES situation_categories(id) ON DELETE CASCADE)"
    cast_x_credentials_table_query = "CREATE TABLE IF NOT EXISTS cast_x_credentials (id INTEGER PRIMARY KEY, cast_id INTEGER UNIQUE, api_key TEXT, api_secret TEXT, bearer_token TEXT, access_token TEXT, access_token_secret TEXT, twitter_username TEXT, twitter_user_id TEXT, is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE)"
    cast_sheets_config_table_query = "CREATE TABLE IF NOT EXISTS cast_sheets_config (id INTEGER PRIMARY KEY, cast_id INTEGER UNIQUE, spreadsheet_id TEXT, sheet_name TEXT DEFAULT 'sheet1', credentials_file_path TEXT, is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE)"

    queries = [casts_table_query, posts_table_query, situations_table_query, categories_table_query, advice_table_query, groups_table_query, cast_groups_table_query, tuning_history_table_query, custom_fields_table_query, send_history_table_query, app_settings_table_query, global_advice_table_query, category_advice_table_query, cast_x_credentials_table_query, cast_sheets_config_table_query]
    for query in queries: execute_query(query)
    
    # generated_atカラムが存在しない場合は追加
    try:
        # まずカラムの存在を確認
        column_check = execute_query("PRAGMA table_info(posts)", fetch="all")
        column_names = [col['name'] for col in column_check]
        
        if 'generated_at' not in column_names:
            execute_query("ALTER TABLE posts ADD COLUMN generated_at TEXT")
    except Exception as e:
        # カラム追加でエラーが発生した場合は無視（既に存在する場合など）
        pass
    
    if execute_query("SELECT COUNT(*) as c FROM situation_categories", fetch="one")['c'] == 0:
        for cat in ["日常", "学生", "社会人", "イベント", "恋愛"]: execute_query("INSERT INTO situation_categories (name) VALUES (?)", (cat,))
    
    if execute_query("SELECT COUNT(*) as c FROM groups", fetch="one")['c'] == 0:
        default_groups = [("喫茶アルタイル", "あなたは銀座の路地裏にある、星をテーマにした小さな喫茶店「アルタイル」の店員です。"), ("文芸サークル", "あなたは大学の文芸サークルに所属しています。")]
        for group in default_groups: execute_query("INSERT INTO groups (name, content) VALUES (?, ?)", group)

    if not execute_query("SELECT id FROM casts WHERE name = ?", ("星野 詩織",), fetch="one"):
        default_cast_data = { "name": "星野 詩織", "nickname": "しおりん", "age": "21歳", "birthday": "10月26日", "birthplace": "神奈川県", "appearance": "黒髪ロングで物静かな雰囲気。古着のワンピースをよく着ている。", "personality": "物静かで穏やかな聞き上手", "strength": "人の話に深く共感できる", "weakness": "少し人見知り", "first_person": "私", "speech_style": "です・ます調の丁寧な言葉遣い", "catchphrase": "「なんだか、素敵ですね」", "customer_interaction": "お客様の心に寄り添うように、静かに話を聞く", "occupation": "文学部の女子大生", "hobby": "読書、フィルムカメラ、古い喫茶店巡り", "likes": "雨の日の匂い、万年筆のインク", "dislikes": "大きな音、人混み", "holiday_activity": "一日中家で本を読んでいるか、目的もなく電車に乗る", "dream": "自分の言葉で、誰かの心を動かす物語を紡ぐこと", "reason_for_job": "様々な人の物語に触れたいから", "secret": "実は、大のSF小説好き", "allowed_categories": "日常,学生,恋愛" }
        columns = ', '.join(default_cast_data.keys()); placeholders = ', '.join(['?'] * len(default_cast_data)); values = tuple(default_cast_data.values())
        execute_query(f"INSERT INTO casts ({columns}) VALUES ({placeholders})", values)

    if execute_query("SELECT COUNT(*) as c FROM situations", fetch="one")['c'] == 0:
        cat_rows = execute_query("SELECT id, name FROM situation_categories", fetch="all"); cat_map = {row['name']: row['id'] for row in cat_rows}
        default_situations = [("静かな雨が降る夜", "夜", cat_map.get("日常")), ("気持ちの良い秋晴れの昼下がり", "昼", cat_map.get("日常")), ("お気に入りの喫茶店で読書中", "いつでも", cat_map.get("学生")), ("初めてのお給料日", "いつでも", cat_map.get("社会人"))]
        for sit in default_situations: execute_query("INSERT INTO situations (content, time_slot, category_id) VALUES (?, ?, ?)", sit)

    if execute_query("SELECT COUNT(*) as c FROM advice_master", fetch="one")['c'] == 0:
        default_advice = [("もっと可愛く",), ("もっと大人っぽく",), ("意外な一面を見せて",), ("豆知識を加えて",), ("句読点を工夫して",), ("少しユーモアを",)]
        for adv in default_advice: execute_query("INSERT INTO advice_master (content) VALUES (?)", adv)
    
    # アプリ設定のデフォルト値を初期化
    if execute_query("SELECT COUNT(*) as c FROM app_settings", fetch="one")['c'] == 0:
        default_settings = [
            ("default_char_limit", "140", "デフォルト文字数制限", "投稿生成"),
            ("default_post_count", "5", "デフォルト生成数", "投稿生成"),
            ("situation_placeholder", "例：お気に入りの喫茶店で読書中", "シチュエーション入力プレースホルダ", "UI設定"),
            ("campaign_placeholder", "例：「グッチセール」というキーワードと、URL「https://gucci.com/sale」を必ず文末に入れて、セールをお知らせする投稿を作成してください。", "一斉指示プレースホルダ", "UI設定"),
            ("name_pairs_placeholder", "例：\n@hanao_tanaka,田中 花音\n@misaki_sato,佐藤 美咲\n@aina_suzuki,鈴木 愛菜", "名前ペア入力プレースホルダ", "UI設定"),
            ("ai_generation_instruction", "魅力的で個性豊かなキャラクター", "AI生成時のデフォルト指示", "AI設定"),
            # キャスト登録フォームのプレースホルダー
            ("cast_name_placeholder", "@shiori_hoshino", "ユーザー名プレースホルダー", "キャスト管理"),
            ("cast_nickname_placeholder", "星野 詩織", "名前（表示名）プレースホルダー", "キャスト管理"),
            ("cast_age_placeholder", "21歳", "年齢プレースホルダー", "キャスト管理"),
            ("cast_birthday_placeholder", "10月26日", "誕生日プレースホルダー", "キャスト管理"),
            ("cast_birthplace_placeholder", "神奈川県", "出身地プレースホルダー", "キャスト管理"),
            ("cast_appearance_placeholder", "黒髪ロングで物静かな雰囲気。古着のワンピースをよく着ている。", "外見の特徴プレースホルダー", "キャスト管理"),
            ("cast_personality_placeholder", "物静かで穏やかな聞き上手", "性格プレースホルダー", "キャスト管理"),
            ("cast_strength_placeholder", "人の話に深く共感できる", "長所プレースホルダー", "キャスト管理"),
            ("cast_weakness_placeholder", "少し人見知り", "短所プレースホルダー", "キャスト管理"),
            ("cast_first_person_placeholder", "私", "一人称プレースホルダー", "キャスト管理"),
            ("cast_speech_style_placeholder", "です・ます調の丁寧な言葉遣い", "口調・語尾プレースホルダー", "キャスト管理"),
            ("cast_catchphrase_placeholder", "「なんだか、素敵ですね」", "口癖プレースホルダー", "キャスト管理"),
            ("cast_occupation_placeholder", "文学部の女子大生", "職業／学業プレースホルダー", "キャスト管理"),
            ("cast_hobby_placeholder", "読書、フィルムカメラ、古い喫茶店巡り", "趣味や特技プレースホルダー", "キャスト管理"),
            ("cast_likes_placeholder", "雨の日の匂い、万年筆のインク", "好きなものプレースホルダー", "キャスト管理"),
            ("cast_dislikes_placeholder", "大きな音、人混み", "嫌いなものプレースホルダー", "キャスト管理"),
            ("cast_holiday_activity_placeholder", "一日中家で本を読んでいるか、目的もなく電車に乗る", "休日の過ごし方プレースホルダー", "キャスト管理"),
            ("cast_dream_placeholder", "自分の言葉で、誰かの心を動かす物語を紡ぐこと", "将来の夢プレースホルダー", "キャスト管理"),
            ("cast_reason_for_job_placeholder", "様々な人の物語に触れたいから", "なぜこの仕事をしているのかプレースホルダー", "キャスト管理"),
            ("cast_secret_placeholder", "実は、大のSF小説好き", "ちょっとした秘密プレースホルダー", "キャスト管理"),
            ("cast_customer_interaction_placeholder", "お客様の心に寄り添うように、静かに話を聞く", "お客様への接し方プレースホルダー", "キャスト管理"),
        ]
        for setting in default_settings:
            execute_query("INSERT OR REPLACE INTO app_settings (key, value, description, category) VALUES (?, ?, ?, ?)", setting)
    
    # 既存のpostsテーブルに新しいカラムを追加（マイグレーション）
    # カラムの存在確認と追加
    def add_column_if_not_exists(table_name, column_name, column_definition):
        try:
            # カラムの存在確認
            cursor_info = execute_query(f"PRAGMA table_info({table_name})", fetch="all")
            existing_columns = [col['name'] for col in cursor_info] if cursor_info else []
            
            if column_name not in existing_columns:
                execute_query(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
        except Exception as e:
            # すでに存在する場合やその他のエラーは無視
            pass
    
    add_column_if_not_exists("posts", "sent_status", "TEXT DEFAULT 'not_sent'")
    add_column_if_not_exists("posts", "sent_at", "TEXT")

def initialize_default_settings():
    """デフォルト設定を初期化"""
    # app_settingsテーブルが存在するか確認
    tables = execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name='app_settings'", fetch="all")
    if not tables:
        # テーブルが存在しない場合は作成
        execute_query("""
            CREATE TABLE app_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                description TEXT,
                category TEXT DEFAULT 'その他'
            )
        """)
    
    # デフォルト設定を挿入
    default_settings = [
        ("default_char_count", "300", "デフォルト文字数", "投稿生成"),
        ("default_placeholder", "今日の出来事について教えて", "デフォルトプレースホルダー", "投稿生成"),
        ("ai_temperature", "0.8", "AI創造性レベル", "AI設定"),
        ("ai_max_tokens", "1000", "AI最大トークン数", "AI設定"),
        ("ui_theme_color", "#FF6B6B", "テーマカラー", "UI設定"),
        ("ui_sidebar_width", "300", "サイドバー幅", "UI設定"),
        ("cast_name_placeholder", "星野 詩織", "名前プレースホルダー", "キャスト管理"),
        ("cast_nickname_placeholder", "しおりん", "ニックネームプレースホルダー", "キャスト管理"),
        ("cast_age_placeholder", "21歳", "年齢プレースホルダー", "キャスト管理"),
        ("cast_birthday_placeholder", "10月26日", "誕生日プレースホルダー", "キャスト管理"),
        ("cast_birthplace_placeholder", "神奈川県", "出身地プレースホルダー", "キャスト管理"),
        ("cast_appearance_placeholder", "黒髪ロングで物静かな雰囲気。古着のワンピースをよく着ている。", "外見の特徴プレースホルダー", "キャスト管理"),
        ("cast_personality_placeholder", "物静かで穏やかな聞き上手", "性格プレースホルダー", "キャスト管理"),
        ("cast_strength_placeholder", "人の話に深く共感できる", "長所プレースホルダー", "キャスト管理"),
        ("cast_weakness_placeholder", "少し人見知り", "短所プレースホルダー", "キャスト管理"),
        ("cast_first_person_placeholder", "私", "一人称プレースホルダー", "キャスト管理"),
        ("cast_speech_style_placeholder", "です・ます調の丁寧な言葉遣い", "口調・語尾プレースホルダー", "キャスト管理"),
        ("cast_catchphrase_placeholder", "「なんだか、素敵ですね」", "口癖プレースホルダー", "キャスト管理"),
        ("cast_occupation_placeholder", "文学部の女子大生", "職業・学業プレースホルダー", "キャスト管理"),
        ("cast_hobby_placeholder", "読書、フィルムカメラ、古い喫茶店巡り", "趣味や特技プレースホルダー", "キャスト管理"),
        ("cast_likes_placeholder", "雨の日の匂い、万年筆のインク", "好きなものプレースホルダー", "キャスト管理"),
        ("cast_dislikes_placeholder", "大きな音、人混み", "嫌いなものプレースホルダー", "キャスト管理"),
        ("cast_holiday_activity_placeholder", "一日中家で本を読んでいるか、目的もなく電車に乗る", "休日の過ごし方プレースホルダー", "キャスト管理"),
        ("cast_dream_placeholder", "自分の言葉で、誰かの心を動かす物語を紡ぐこと", "将来の夢プレースホルダー", "キャスト管理"),
        ("cast_reason_for_job_placeholder", "様々な人の物語に触れたいから", "なぜこの仕事をしているのかプレースホルダー", "キャスト管理"),
        ("cast_secret_placeholder", "実は、大のSF小説好き", "ちょっとした秘密プレースホルダー", "キャスト管理"),
        ("cast_customer_interaction_placeholder", "お客様の心に寄り添うように、静かに話を聞く", "お客様への接し方プレースホルダー", "キャスト管理"),
    ]
    
    for key, value, description, category in default_settings:
        execute_query("INSERT OR REPLACE INTO app_settings (key, value, description, category) VALUES (?, ?, ?, ?)", (key, value, description, category))

def format_persona(cast_id, cast_data):
    if not cast_data: return "ペルソナデータがありません。"
    group_rows = execute_query("SELECT g.name, g.content FROM groups g JOIN cast_groups cg ON g.id = cg.group_id WHERE cg.cast_id = ?", (cast_id,), fetch="all")
    group_text = "\n\n## 4. 所属グループ共通設定\n" + "".join([f"- **{row['name']}**: {row['content']}\n" for row in group_rows]) if group_rows else ""
    return f"""
# キャラクター設定シート：{cast_data.get('name', '')}
## 1. 基本情報
- 名前: {cast_data.get('name', '')}, ニックネーム: {cast_data.get('nickname', '')}, 年齢: {cast_data.get('age', '')}, 誕生日: {cast_data.get('birthday', '')}, 出身地: {cast_data.get('birthplace', '')}, 外見の特徴: {cast_data.get('appearance', '')}
## 2. 性格・話し方
- 性格: {cast_data.get('personality', '')}, 長所: {cast_data.get('strength', '')}, 短所: {cast_data.get('weakness', '')}, 一人称: {cast_data.get('first_person', '')}, 口調・語尾: {cast_data.get('speech_style', '')}, 口癖: {cast_data.get('catchphrase', '')}, お客様への接し方: {cast_data.get('customer_interaction', '')}
## 3. 背景ストーリー
- 職業／学業: {cast_data.get('occupation', '')}, 趣味や特技: {cast_data.get('hobby', '')}, 好きなもの: {cast_data.get('likes', '')}, 嫌いなもの: {cast_data.get('dislikes', '')}, 休日の過ごし方: {cast_data.get('holiday_activity', '')}, 将来の夢: {cast_data.get('dream', '')}, なぜこの仕事をしているのか: {cast_data.get('reason_for_job', '')}, ちょっとした秘密: {cast_data.get('secret', '')}
{group_text}
"""

def load_css(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSSファイル '{file_name}' が見つかりません。")

def get_dynamic_persona_fields():
    """動的に定義されたペルソナフィールドを取得"""
    custom_fields = execute_query("SELECT field_name FROM custom_fields ORDER BY sort_order", fetch="all")
    if custom_fields:
        custom_field_names = [field['field_name'] for field in custom_fields]
        return PERSONA_FIELDS + custom_field_names
    return PERSONA_FIELDS

def parse_ai_profile(ai_text, name, nickname, categories):
    """AIが生成したプロフィールテキストを構造化データに変換"""
    import re
    
    # デフォルト値
    cast_data = {field: "" for field in PERSONA_FIELDS}
    cast_data['name'] = name
    cast_data['nickname'] = nickname  # 入力された表示名を使用
    cast_data['allowed_categories'] = ",".join(categories)
    
    # 正規表現パターンでフィールドを抽出
    patterns = {
        'nickname': r'ニックネーム[：:\s]*([^\n]+)',
        'age': r'年齢[：:\s]*([^\n]+)',
        'birthday': r'誕生日[：:\s]*([^\n]+)',
        'birthplace': r'出身地[：:\s]*([^\n]+)',
        'appearance': r'外見[の特徴：:\s]*([^\n]+)',
        'personality': r'性格[：:\s]*([^\n]+)',
        'strength': r'長所[：:\s]*([^\n]+)',
        'weakness': r'短所[：:\s]*([^\n]+)',
        'first_person': r'一人称[：:\s]*([^\n]+)',
        'speech_style': r'口調[・語尾：:\s]*([^\n]+)',
        'catchphrase': r'口癖[：:\s]*([^\n]+)',
        'customer_interaction': r'お客様への接し方[：:\s]*([^\n]+)',
        'occupation': r'職業[／/学業：:\s]*([^\n]+)',
        'hobby': r'趣味[や特技：:\s]*([^\n]+)',
        'likes': r'好きなもの[：:\s]*([^\n]+)',
        'dislikes': r'嫌いなもの[：:\s]*([^\n]+)',
        'holiday_activity': r'休日の過ごし方[：:\s]*([^\n]+)',
        'dream': r'将来の夢[：:\s]*([^\n]+)',
        'reason_for_job': r'なぜこの仕事[をしているのか：:\s]*([^\n]+)',
        'secret': r'ちょっとした秘密[：:\s]*([^\n]+)'
    }
    
    # パターンマッチングで情報を抽出
    for field, pattern in patterns.items():
        match = re.search(pattern, ai_text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # 「」で囲まれている場合は除去
            value = re.sub(r'^[「『"]([^」』"]+)[」』"]$', r'\1', value)
            cast_data[field] = value
    
    # フォールバック：基本的な値が取得できなかった場合のデフォルト設定
    if not cast_data['nickname']:
        cast_data['nickname'] = name.split()[-1] if ' ' in name else name
    if not cast_data['age']:
        cast_data['age'] = "20歳"
    if not cast_data['first_person']:
        cast_data['first_person'] = "私"
    if not cast_data['speech_style']:
        cast_data['speech_style'] = "です・ます調"
    if not cast_data['personality']:
        cast_data['personality'] = "明るく親しみやすい"
    
    return cast_data

def safe_generate_content(model, prompt, delay_seconds=1.0):
    """レート制限対策を含む安全なコンテンツ生成"""
    try:
        # レート制限回避のため少し待機
        time.sleep(delay_seconds)
        
        response = model.generate_content(prompt)
        return response
    except Exception as e:
        if "429" in str(e) or "Quota exceeded" in str(e):
            st.error("⚠️ API使用量制限に達しました。数分お待ちください。")
            st.info("💡 制限回避のため、生成間隔を空けるか、しばらく時間を置いてから再実行してください。")
            time.sleep(5)  # 5秒待機
            raise e
        else:
            raise e

def clean_generated_content(content):
    """生成されたコンテンツから不要な指示文・例文を除去し、最初の投稿のみを返す"""
    if not content:
        return content
    
    import re
    
    # 元のコンテンツをバックアップ
    original_content = content.strip()
    
    # デバッグ用：生成された内容をログ出力
    print(f"🔍 [DEBUG] 生成された内容: {repr(original_content)}")
    
    # まず、明らかなプロンプト漏れパターンをチェック
    prompt_leak_indicators = [
        'ペルソナ：',
        'のSNS投稿案',
        '例1',
        '例2', 
        '例3',
        '例4',
        '例5',
        '投稿案:',
        '投稿案：',
        'テスト1',
        'テスト2',
        'テスト3',
        'テスト実施中',
        '進捗順調',
        'ご協力ありがとうございます',
        '(仕事への自虐)',
        '(山口愛)',
        '(短髪ネタ)',
        '(年齢を感じさせる)',
        '(秘密を匂わせる)',
        '実際の投稿例',
        '投稿例'
    ]
    
    # プロンプト漏れが検出された場合
    if any(indicator in original_content for indicator in prompt_leak_indicators):
        print(f"⚠️ [DEBUG] プロンプト漏れを検出しました")
        
        # 行ごとに分割して処理
        lines = original_content.split('\n')
        content_lines = []
        
        for line in lines:
            line = line.strip()
            # スキップする行の条件
            skip_conditions = [
                line.startswith('ペルソナ：'),
                'のSNS投稿案' in line,
                line.startswith('例') and ('(' in line and ')' in line),
                line.startswith('例') and ':' in line,
                line == '',
                '投稿案' in line and len(line) < 15,
                line.startswith('1.') or line.startswith('2.') or line.startswith('3.'),
                line.startswith('例1') or line.startswith('例2') or line.startswith('例3') or line.startswith('例4') or line.startswith('例5'),
                '(' in line and ')' in line and ':' in line and len(line) < 30,
                'テスト' in line and ('実施中' in line or '進捗' in line or 'ご協力' in line),
                line.startswith('テスト1') or line.startswith('テスト2') or line.startswith('テスト3'),
                '実際の投稿例' in line or '投稿例' in line
            ]
            
            if not any(skip_conditions):
                content_lines.append(line)
                print(f"✅ [DEBUG] 有効な行: {line}")
            else:
                print(f"❌ [DEBUG] スキップした行: {line}")
        
        # 最初の有効な投稿を抽出
        if content_lines:
            first_post = content_lines[0]
            # ハッシュタグがある場合は、それを含む行まで取得
            if '#' in first_post:
                result = first_post
            else:
                # ハッシュタグが次の行にある可能性をチェック
                for i in range(1, min(len(content_lines), 3)):
                    if content_lines[i].startswith('#'):
                        result = f"{first_post} {content_lines[i]}"
                        break
                else:
                    result = first_post
                    
            print(f"🎯 [DEBUG] クリーニング結果: {repr(result)}")
            return result
        else:
            print(f"⚠️ [DEBUG] 有効な行が見つかりませんでした。元の内容を返します。")
            return original_content
    
    # プロンプト漏れが検出されなかった場合は、元のコンテンツをそのまま返す
    # ただし、複数の改行は整理
    cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', original_content)
    cleaned = re.sub(r'^\s*\n+', '', cleaned)
    cleaned = re.sub(r'\n+\s*$', '', cleaned)
    
    result = cleaned.strip()
    print(f"✨ [DEBUG] 最終結果: {repr(result)}")
    return result

def setup_google_sheets_oauth_simple():
    """シンプル版Google Sheets OAuth認証（共通認証ファイル使用）"""
    try:
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        import pickle
        
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials_path = "credentials/credentials.json"
        token_path = "credentials/token.pickle"
        
        creds = None
        
        # 既存のトークンを確認
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
                
                # 辞書形式の場合はCredentialsオブジェクトに変換
                if isinstance(creds, dict):
                    from google.oauth2.credentials import Credentials
                    creds = Credentials(
                        token=creds.get('access_token'),
                        refresh_token=creds.get('refresh_token'),
                        token_uri=creds.get('token_uri'),
                        client_id=creds.get('client_id'),
                        client_secret=creds.get('client_secret'),
                        scopes=creds.get('scopes', SCOPES)
                    )
        
        # 認証が必要な場合
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_path):
                    return None, "共通認証ファイルが見つかりません: credentials/credentials.json"
                
                # シンプル版：自動ブラウザ認証
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # トークンを保存
            os.makedirs("credentials", exist_ok=True)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds, "認証成功"
    except Exception as e:
        return None, f"OAuth認証エラー: {str(e)}"

def setup_google_sheets_oauth(credentials_path="credentials/credentials.json"):
    """Google Sheets OAuth認証の初期設定（複雑版 - 下位互換用）"""
    # 複雑版のコードは後で削除予定
    if credentials_path == "credentials/credentials.json":
        # デフォルトパスの場合はシンプル版を使用
        return setup_google_sheets_oauth_simple()
    
    try:
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        import pickle
        
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        
        creds = None
        # シンプル版：固定の共通トークンファイル
        token_path = "credentials/token.pickle"
        
        # 既存のトークンを確認
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
                
                # 辞書形式の場合はCredentialsオブジェクトに変換
                if isinstance(creds, dict):
                    from google.oauth2.credentials import Credentials
                    creds = Credentials(
                        token=creds.get('access_token'),
                        refresh_token=creds.get('refresh_token'),
                        token_uri=creds.get('token_uri'),
                        client_id=creds.get('client_id'),
                        client_secret=creds.get('client_secret'),
                        scopes=creds.get('scopes', ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
                    )
        
        # 認証が必要な場合
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_path):
                    return None, "OAuth認証ファイルが見つかりません。設定が必要です。"
                
                # セッション状態を使用して認証フローを管理
                auth_session_key = f"oauth_state_{os.path.basename(credentials_path)}"
                
                # 初回の場合、認証フローを初期化
                if auth_session_key not in st.session_state:
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                    flow.redirect_uri = "http://localhost"
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    
                    st.session_state[auth_session_key] = {
                        'flow': flow,
                        'auth_url': auth_url,
                        'authenticated': False,
                        'error_message': None
                    }
                
                # セッションから認証情報を取得
                auth_state = st.session_state[auth_session_key]
                
                # 認証が完了していない場合、フォームを表示
                if not auth_state['authenticated']:
                    st.info("🔐 Google OAuth認証が必要です")
                    st.markdown(f"**[👆 Google認証を開始してください]({auth_state['auth_url']})**")
                    
                    # エラーメッセージがある場合は表示
                    if auth_state.get('error_message'):
                        st.error(auth_state['error_message'])
                        st.info("💡 新しい認証コードを取得してください")
                    
                    # 安定したフォーム
                    with st.form(key=f"persistent_oauth_form_{auth_session_key}", clear_on_submit=False):
                        st.write("**認証コードを入力してください:**")
                        auth_code = st.text_input(
                            "認証コード:",
                            placeholder="4/0AVGzR1...",
                            help="Google認証画面で取得したコードを貼り付けてください",
                            key=f"auth_code_{auth_session_key}"
                        )
                        
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            submit_button = st.form_submit_button("✅ 認証コードを送信", use_container_width=True)
                        with col2:
                            reset_button = st.form_submit_button("🔄 認証をリセット", use_container_width=True)
                    
                    # リセットボタンが押された場合
                    if reset_button:
                        del st.session_state[auth_session_key]
                        st.rerun()
                    
                    # 認証コードが送信された場合
                    if submit_button and auth_code:
                        st.info(f"🔄 認証コード処理中... ({auth_code[:20]}...)")
                        
                        try:
                            flow = auth_state['flow']
                            
                            # デバッグ情報
                            st.write(f"📝 使用中のredirect_uri: {flow.redirect_uri}")
                            st.write(f"📊 認証コード長: {len(auth_code)} 文字")
                            
                            # 認証コードでトークンを取得
                            flow.fetch_token(code=auth_code.strip())
                            creds = flow.credentials
                            
                            st.success("🎉 トークン取得成功！")
                            
                            # トークンを保存
                            os.makedirs("credentials", exist_ok=True)
                            with open(token_path, 'wb') as token:
                                pickle.dump(creds, token)
                            
                            st.success(f"💾 トークンファイル保存完了: {token_path}")
                            
                            # 認証完了をマーク
                            st.session_state[auth_session_key]['authenticated'] = True
                            st.success("✅ OAuth認証完了！認証トークンを保存しました。")
                            
                            # 2秒待ってからリロード
                            time.sleep(2)
                            st.rerun()
                            
                        except Exception as auth_error:
                            error_msg = str(auth_error)
                            st.error(f"❌ 認証処理エラー: {error_msg}")
                            
                            # 詳細なエラー情報
                            if "invalid_grant" in error_msg.lower():
                                st.warning("⚠️ 認証コードが期限切れまたは既に使用済みです")
                                st.info("💡 新しい認証コードを取得してください")
                            elif "invalid_request" in error_msg.lower():
                                st.warning("⚠️ リクエスト形式エラー")
                                st.info("💡 認証をリセットして再試行してください")
                            
                            # エラーをセッションに保存（フォームを維持）
                            st.session_state[auth_session_key]['error_message'] = f"認証エラー: {error_msg}"
                            
                            # 自動リセット（新しい認証URLを生成）
                            if st.button("🔄 新しい認証URLを生成"):
                                del st.session_state[auth_session_key]
                                st.rerun()
                    
                    # 認証待機中はここで処理を停止（フォームを維持）
                    st.stop()
            
            # トークンを保存
            os.makedirs("credentials", exist_ok=True)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds, "認証成功"
    except Exception as e:
        return None, f"OAuth認証エラー: {str(e)}"

def convert_google_drive_url(url):
    """Google Drive共有URLを直接アクセス可能なURLに変換"""
    if not url or 'drive.google.com' not in url:
        return url
    
    # Google Drive共有URLのパターンを検出
    import re
    
    # パターン1: https://drive.google.com/file/d/FILE_ID/view?usp=sharing
    pattern1 = r'https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)/view'
    match1 = re.search(pattern1, url)
    if match1:
        file_id = match1.group(1)
        return f"https://drive.google.com/uc?export=view&id={file_id}"
    
    # パターン2: https://drive.google.com/open?id=FILE_ID
    pattern2 = r'https://drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)'
    match2 = re.search(pattern2, url)
    if match2:
        file_id = match2.group(1)
        return f"https://drive.google.com/uc?export=view&id={file_id}"
    
    # 既に変換済みのURL
    if 'uc?export=view&id=' in url:
        return url
    
    return url  # 変換できない場合は元のURLを返す

def send_to_google_sheets(cast_name, post_content, scheduled_datetime, cast_id=None, action_type='post', image_urls=None):
    """Google Sheetsにデータを送信する（アクション別シート対応・Google Drive URL対応）"""
    try:
        os.makedirs("credentials", exist_ok=True)
        
        # キャスト別・アクション別スプレッドシート設定をチェック
        cast_config = None
        if cast_id:
            cast_config = get_cast_sheets_config(cast_id, action_type)
        
        if cast_config:
            # キャスト別スプレッドシート設定を使用
            spreadsheet_id = cast_config['spreadsheet_id']
            sheet_name = cast_config['sheet_name'] or 'Sheet1'
        else:
            # デフォルト設定を使用
            spreadsheet_id = "1VPSyQOp0p2U9bPHghP4JZiyePsev2Uoq3nVbbC26VAo"  # デフォルトスプレッドシート
            sheet_name = "Sheet1"
        
        # シンプル版OAuth認証を実行（共通認証ファイル使用）
        creds, auth_message = setup_google_sheets_oauth_simple()
        if not creds:
            return False, auth_message
        
        client = gspread.authorize(creds)
        
        # スプレッドシートを開く
        try:
            if cast_config and cast_config['spreadsheet_id']:
                # スプレッドシートIDで直接開く
                spreadsheet = client.open_by_key(cast_config['spreadsheet_id'])
                try:
                    sheet = spreadsheet.worksheet(sheet_name)
                except gspread.WorksheetNotFound:
                    # シートが存在しない場合は作成
                    sheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
                    sheet.append_row(["datetime", "content", "name"])
            else:
                # デフォルト動作：名前でスプレッドシートを開く
                try:
                    sheet = client.open(spreadsheet_id).sheet1
                except gspread.SpreadsheetNotFound:
                    # スプレッドシートが存在しない場合は作成
                    spreadsheet = client.create(spreadsheet_id)
                    sheet = spreadsheet.sheet1
                    # ヘッダー行を追加
                    sheet.append_row(["datetime", "content", "name"])
        except Exception as e:
            return False, f"スプレッドシートアクセスエラー: {str(e)}"
        
        # データを追加（日時, 投稿内容, name, 画像URL1-4 の順）
        formatted_datetime = scheduled_datetime.strftime('%Y-%m-%d %H:%M:%S')
        
        # 画像URLを4列分に分割（最大4枚対応・Google Drive URL変換）
        image_url_columns = ['', '', '', '']  # 空の4列を準備
        if image_urls:
            for i, url in enumerate(image_urls[:4]):  # 最大4枚まで
                if url:
                    # Google Drive URLを直接アクセス可能な形式に変換
                    converted_url = convert_google_drive_url(url)
                    image_url_columns[i] = converted_url
        
        # ヘッダーが存在しない場合は作成
        try:
            headers = sheet.row_values(1)
            if not headers or len(headers) < 7:  # datetime, content, name, image1-4
                sheet.clear()
                sheet.append_row(["datetime", "content", "name", "image_url1", "image_url2", "image_url3", "image_url4"])
        except:
            # シートが空の場合
            sheet.append_row(["datetime", "content", "name", "image_url1", "image_url2", "image_url3", "image_url4"])
        
        # データ行を追加
        row_data = [formatted_datetime, post_content, cast_name] + image_url_columns
        sheet.append_row(row_data)
        
        if cast_config:
            return True, f"キャスト専用Google Sheetsに送信しました。(スプレッドシートID: {cast_config['spreadsheet_id'][:10]}...)"
        else:
            return True, "デフォルトGoogle Sheetsに送信しました。"
        
    except Exception as e:
        return False, f"Google Sheets送信エラー: {str(e)}"

def send_retweet_to_google_sheets(cast_id, tweet_id, comment, scheduled_datetime):
    """リツイート予約をGoogle Sheetsに送信"""
    try:
        # リツイート用の設定を取得
        config = get_cast_sheets_config(cast_id, 'retweet')
        if not config:
            return False, "リツイート用Google Sheets設定が見つかりません"
        
        # 認証
        creds, auth_message = setup_google_sheets_oauth_simple()
        if not creds:
            return False, auth_message
        
        client = gspread.authorize(creds)
        
        # スプレッドシートを開く
        try:
            spreadsheet = client.open_by_key(config['spreadsheet_id'])
            try:
                sheet = spreadsheet.worksheet(config['sheet_name'])
            except gspread.WorksheetNotFound:
                # シートが存在しない場合は作成
                sheet = spreadsheet.add_worksheet(title=config['sheet_name'], rows=1000, cols=10)
                # ヘッダー行を追加（GASのretweetMain関数に合わせる）
                sheet.append_row(["実行日時", "ツイートID", "コメント", "ステータス", "実行完了日時"])
        except Exception as e:
            return False, f"スプレッドシートアクセスエラー: {str(e)}"
        
        # データを追加（GASの形式に合わせる）
        formatted_datetime = scheduled_datetime.strftime('%Y-%m-%d %H:%M:%S')
        sheet.append_row([formatted_datetime, tweet_id, comment or '', '', ''])
        
        return True, f"リツイート予約をGoogle Sheetsに送信しました。(ID: {tweet_id})"
        
    except Exception as e:
        return False, f"リツイート予約送信エラー: {str(e)}"

def send_retweet_to_gas_direct(cast_id, tweet_id, comment, scheduled_datetime):
    """GAS Direct API経由でリツイート予約を送信（スプレッドシート不要）"""
    try:
        # GAS Web AppのURLを設定から取得
        config = get_cast_sheets_config(cast_id, 'retweet')
        if not config:
            return False, "リツイート用Google Sheets設定が見つかりません"
        
        # GAS Web App URLを取得（新しい設定項目として想定）
        gas_web_app_url = config.get('gas_web_app_url')
        if not gas_web_app_url:
            return False, "GAS Web App URLが設定されていません。設定で 'gas_web_app_url' を追加してください。"
        
        # キャスト名を取得
        cast_name = get_cast_name_by_id(cast_id)
        
        # リクエストペイロード
        payload = {
            "action": "schedule_retweet",
            "tweet_id": tweet_id,
            "comment": comment if comment and comment.strip() else "",
            "scheduled_at": scheduled_datetime.isoformat(),
            "cast_name": cast_name
        }
        
        # GAS Web Appに直接POST
        response = requests.post(
            gas_web_app_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                return True, f"GAS直接予約が完了しました。(ID: {tweet_id}, トリガーID: {result['data'].get('trigger_id', 'N/A')})"
            else:
                return False, f"GAS応答エラー: {result.get('message', 'Unknown error')}"
        else:
            return False, f"GAS接続エラー: HTTP {response.status_code} - {response.text}"
            
    except Exception as e:
        return False, f"GAS Direct API送信エラー: {str(e)}"

def execute_retweet_via_gas_direct(cast_id, tweet_id, comment):
    """GAS Direct API経由でリツイートを即座に実行"""
    try:
        # 設定取得
        config = get_cast_sheets_config(cast_id, 'retweet')
        if not config:
            return False, "リツイート用Google Sheets設定が見つかりません"
        
        gas_web_app_url = config.get('gas_web_app_url')
        if not gas_web_app_url:
            return False, "GAS Web App URLが設定されていません"
        
        cast_name = get_cast_name_by_id(cast_id)
        
        # 即座に実行
        if comment and comment.strip():
            action = "quote_tweet"
            payload = {
                "action": action,
                "tweet_id": tweet_id,
                "comment": comment.strip(),
                "cast_name": cast_name
            }
        else:
            action = "retweet"
            payload = {
                "action": action,
                "tweet_id": tweet_id,
                "cast_name": cast_name
            }
        
        response = requests.post(
            gas_web_app_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                return True, f"GAS経由での{action}が完了しました。(ID: {tweet_id})"
            else:
                return False, f"GAS実行エラー: {result.get('message', 'Unknown error')}"
        else:
            return False, f"GAS接続エラー: HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"GAS Direct実行エラー: {str(e)}"

def save_retweet_to_database(cast_id, tweet_id, comment, scheduled_datetime):
    """リツイート予約をデータベースに保存（Cloud Functions経由）"""
    try:
        created_at = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
        
        # scheduled_datetimeがnaiveの場合はJSTとして扱う
        if scheduled_datetime.tzinfo is None:
            scheduled_datetime = scheduled_datetime.replace(tzinfo=JST)
        
        # JSTで統一してデータベースに保存
        scheduled_at_str = scheduled_datetime.astimezone(JST).strftime('%Y-%m-%d %H:%M:%S')
        
        execute_query("""
            INSERT INTO retweet_schedules 
            (cast_id, tweet_id, comment, scheduled_at, status, created_at)
            VALUES (?, ?, ?, ?, 'scheduled', ?)
        """, (cast_id, tweet_id, comment or '', scheduled_at_str, created_at))
        
        retweet_type = "引用ツイート" if comment and comment.strip() else "リツイート"
        return True, f"✅ {retweet_type}予約を作成しました（実行予定: {scheduled_datetime.astimezone(JST).strftime('%Y-%m-%d %H:%M')}）"
        
    except Exception as e:
        return False, f"❌ リツイート予約保存エラー: {str(e)}"

def display_retweet_schedules(cast_id=None):
    """リツイート予約一覧を表示"""
    try:
        # クエリ条件
        if cast_id:
            query = """
                SELECT rs.id, rs.tweet_id, rs.comment, rs.scheduled_at, rs.status, 
                       rs.created_at, rs.executed_at, rs.result_tweet_id, rs.error_message,
                       c.name as cast_name, c.nickname
                FROM retweet_schedules rs
                JOIN casts c ON rs.cast_id = c.id
                WHERE rs.cast_id = ?
                ORDER BY rs.scheduled_at DESC
            """
            retweets = execute_query(query, (cast_id,), fetch="all")
        else:
            query = """
                SELECT rs.id, rs.tweet_id, rs.comment, rs.scheduled_at, rs.status, 
                       rs.created_at, rs.executed_at, rs.result_tweet_id, rs.error_message,
                       c.name as cast_name, c.nickname
                FROM retweet_schedules rs
                JOIN casts c ON rs.cast_id = c.id
                ORDER BY rs.scheduled_at DESC
            """
            retweets = execute_query(query, fetch="all")
        
        if not retweets:
            st.info("📭 予約されたリツイートはありません")
            return
        
        st.write(f"📊 {len(retweets)}件の予約があります")
        
        for retweet in retweets:
            # ステータスに応じた表示色
            if retweet['status'] == 'scheduled':
                status_color = "🔄"
                status_text = "予約中"
            elif retweet['status'] == 'completed':
                status_color = "✅"
                status_text = "完了"
            elif retweet['status'] == 'failed':
                status_color = "❌"
                status_text = "失敗"
            else:
                status_color = "❓"
                status_text = retweet['status']
            
            # キャスト表示名
            cast_display = f"{retweet['cast_name']}（{retweet['nickname']}）" if retweet['nickname'] else retweet['cast_name']
            
            # リツイートタイプ
            retweet_type = "引用ツイート" if retweet['comment'] and retweet['comment'].strip() else "通常リツイート"
            
            # 予約詳細表示
            with st.expander(f"{status_color} {status_text} | {cast_display} | {retweet['scheduled_at']} | {retweet_type}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**🆔 ツイートID:** {retweet['tweet_id']}")
                    st.write(f"**👤 キャスト:** {cast_display}")
                    st.write(f"**⏰ 実行予定:** {retweet['scheduled_at']}")
                    st.write(f"**📅 予約作成:** {retweet['created_at']}")
                    
                with col2:
                    st.write(f"**📝 タイプ:** {retweet_type}")
                    if retweet['comment'] and retweet['comment'].strip():
                        st.write(f"**💬 コメント:** {retweet['comment']}")
                    
                    if retweet['executed_at']:
                        st.write(f"**✅ 実行完了:** {retweet['executed_at']}")
                    
                    if retweet['result_tweet_id']:
                        st.write(f"**🔗 結果ツイートID:** {retweet['result_tweet_id']}")
                    
                    if retweet['error_message']:
                        # エラータイプに応じた表示と対処方法
                        error_msg = retweet['error_message']
                        
                        # 重複リツイートエラーの場合
                        if "DUPLICATE_RETWEET" in error_msg or "already retweeted" in error_msg.lower():
                            st.warning(f"⚠️ **重複エラー:** {error_msg}")
                            st.info("""
                            **重複リツイートについて:**
                            - 同じツイートを複数回リツイートすることはできません
                            - 既にリツイート済みのため処理をスキップしました
                            
                            **対処方法:**
                            1. 🗑️ この予約を削除する
                            2. 💬 コメント付き（引用ツイート）に変更する
                            3. 🔍 別のツイートIDを指定する
                            """)
                        
                        # レート制限エラーの場合
                        elif "rate limit" in error_msg.lower():
                            st.error(f"**❌ エラー:** {error_msg}")
                            st.warning("⏰ **レート制限について**")
                            st.info("""
                            **X API レート制限:**
                            - Free Tier: 50 リツイート/24時間
                            - Basic Plan: 300 リツイート/15分
                            
                            **対処方法:**
                            1. ⏰ 時間を置いて再実行
                            2. 📅 予約スケジュールを分散
                            3. 💰 有料プランへのアップグレード検討
                            """)
                            
                            # 次回実行可能時間の計算
                            current_time = datetime.datetime.now(JST)
                            next_possible = current_time + datetime.timedelta(hours=1)
                            st.info(f"🕐 推奨再実行時刻: {next_possible.strftime('%H:%M')} 以降")
                        
                        # その他のエラー
                        else:
                            st.error(f"**❌ エラー:** {error_msg}")
                
                # 管理操作ボタン
                if retweet['status'] == 'scheduled':
                    col3, col4 = st.columns(2)
                    with col3:
                        if st.button(f"❌ 削除", key=f"delete_retweet_{retweet['id']}"):
                            delete_retweet_schedule(retweet['id'])
                            st.success("🗑️ リツイート予約を削除しました")
                            st.rerun()
                    
                    with col4:
                        if st.button(f"⚡ 今すぐ実行", key=f"execute_now_{retweet['id']}"):
                            execute_retweet_now(retweet)
                            st.rerun()
                
                elif retweet['status'] == 'failed':
                    # 失敗したリツイートの再スケジュール機能
                    st.markdown("#### 🔄 再スケジュール")
                    
                    with st.form(key=f"reschedule_form_{retweet['id']}"):
                        col_r1, col_r2, col_r3 = st.columns(3)
                        
                        with col_r1:
                            default_date = datetime.datetime.now(JST) + datetime.timedelta(hours=2)  # 2時間後をデフォルト
                            new_date = st.date_input(
                                "📅 新しい実行日",
                                value=default_date.date(),
                                key=f"new_date_{retweet['id']}"
                            )
                        
                        with col_r2:
                            new_time = st.time_input(
                                "⏰ 新しい実行時刻",
                                value=default_date.time(),
                                key=f"new_time_{retweet['id']}"
                            )
                        
                        with col_r3:
                            st.write("")  # スペース調整
                            if st.form_submit_button("🔄 再スケジュール実行", type="primary"):
                                # JSTタイムゾーン付きのdatetimeオブジェクトを作成
                                new_datetime = datetime.datetime.combine(new_date, new_time).replace(tzinfo=JST)
                                
                                # 現在時刻より未来かチェック（JST基準）
                                current_time_jst = datetime.datetime.now(JST)
                                if new_datetime <= current_time_jst:
                                    st.error("⚠️ 未来の日時を指定してください")
                                else:
                                    success = reschedule_retweet(retweet['id'], new_datetime)
                                    if success:
                                        st.success(f"✅ {new_datetime.strftime('%Y-%m-%d %H:%M')} に再スケジュールしました")
                                        st.rerun()
                                    else:
                                        st.error("❌ 再スケジュールに失敗しました")
                    
                    # エラータイプに応じたクイックオプション
                    error_msg = retweet.get('error_message', '')
                    is_duplicate_error = "DUPLICATE_RETWEET" in error_msg or "already retweeted" in error_msg.lower()
                    
                    if is_duplicate_error:
                        # 重複リツイートエラーの場合の特別オプション
                        st.markdown("#### 🔄 重複エラー対応オプション")
                        col_dup1, col_dup2 = st.columns(2)
                        
                        with col_dup1:
                            if st.button(f"🗑️ 予約削除", key=f"delete_duplicate_{retweet['id']}"):
                                delete_retweet_schedule(retweet['id'])
                                st.success("🗑️ 重複予約を削除しました")
                                st.rerun()
                        
                        with col_dup2:
                            if st.button(f"💬 引用ツイートに変更", key=f"convert_quote_{retweet['id']}"):
                                st.info("コメントを追加して引用ツイートとして再予約してください：")
                                with st.form(key=f"quote_form_{retweet['id']}"):
                                    quote_comment = st.text_area(
                                        "引用ツイート用コメント",
                                        placeholder="このツイートについてのコメントを入力...",
                                        key=f"quote_comment_{retweet['id']}"
                                    )
                                    if st.form_submit_button("🔄 引用ツイートとして再作成"):
                                        if quote_comment.strip():
                                            # 元の予約を削除して新しい引用ツイート予約を作成
                                            delete_retweet_schedule(retweet['id'])
                                            success, message = save_retweet_to_database(
                                                retweet['cast_id'],
                                                retweet['tweet_id'],
                                                quote_comment.strip(),
                                                datetime.datetime.strptime(retweet['scheduled_at'], '%Y-%m-%d %H:%M:%S')
                                            )
                                            if success:
                                                st.success("✅ 引用ツイートとして再作成しました")
                                                st.rerun()
                                            else:
                                                st.error(f"❌ 再作成失敗: {message}")
                                        else:
                                            st.error("⚠️ コメントを入力してください")
                    else:
                        # 通常のエラー（レート制限など）の場合のクイックオプション
                        st.markdown("#### ⚡ クイックオプション")
                        col_quick1, col_quick2, col_quick3, col_quick4 = st.columns(4)
                        
                        with col_quick1:
                            if st.button(f"⚡ 今すぐ再実行", key=f"retry_now_{retweet['id']}"):
                                execute_retweet_now(retweet)
                                st.rerun()
                        
                        with col_quick2:
                            if st.button(f"🕐 1時間後", key=f"retry_1h_{retweet['id']}"):
                                new_time = datetime.datetime.now(JST) + datetime.timedelta(hours=1)
                                if reschedule_retweet(retweet['id'], new_time):
                                    st.success(f"✅ {new_time.strftime('%H:%M')} に再スケジュール")
                                    st.rerun()
                        
                        with col_quick3:
                            if st.button(f"🕕 6時間後", key=f"retry_6h_{retweet['id']}"):
                                new_time = datetime.datetime.now(JST) + datetime.timedelta(hours=6)
                                if reschedule_retweet(retweet['id'], new_time):
                                    st.success(f"✅ {new_time.strftime('%m-%d %H:%M')} に再スケジュール")
                                    st.rerun()
                        
                        with col_quick4:
                            if st.button(f"🗑️ 削除", key=f"delete_failed_{retweet['id']}"):
                                delete_retweet_schedule(retweet['id'])
                                st.success("🗑️ 失敗したリツイート予約を削除しました")
                                st.rerun()
                            st.rerun()
        
    except Exception as e:
        st.error(f"❌ リツイート予約一覧取得エラー: {str(e)}")

def delete_retweet_schedule(retweet_id):
    """リツイート予約を削除"""
    try:
        execute_query("DELETE FROM retweet_schedules WHERE id = ?", (retweet_id,))
        return True
    except Exception as e:
        st.error(f"❌ 削除エラー: {str(e)}")
        return False

def reschedule_retweet(retweet_id, new_datetime):
    """失敗したリツイートを再スケジュール"""
    try:
        # new_datetimeがnaiveの場合はJSTとして扱う
        if new_datetime.tzinfo is None:
            new_datetime = new_datetime.replace(tzinfo=JST)
        
        # JSTで統一してデータベースに保存
        formatted_datetime = new_datetime.astimezone(JST).strftime('%Y-%m-%d %H:%M:%S')
        
        execute_query("""
            UPDATE retweet_schedules 
            SET scheduled_at = ?, 
                status = 'scheduled', 
                error_message = NULL,
                executed_at = NULL
            WHERE id = ?
        """, (formatted_datetime, retweet_id))
        return True
    except Exception as e:
        st.error(f"❌ 再スケジュールエラー: {str(e)}")
        return False

def execute_retweet_now(retweet):
    """リツイート予約を今すぐ実行"""
    try:
        import requests
        
        # 実行タイプを決定
        if retweet['comment'] and retweet['comment'].strip():
            action = "quote_tweet"
            payload = {
                "action": action,
                "account_id": get_account_id_for_cast_local(retweet['cast_name']),
                "tweet_id": retweet['tweet_id'],
                "comment": retweet['comment'].strip()
            }
        else:
            action = "retweet"
            payload = {
                "action": action,
                "account_id": get_account_id_for_cast_local(retweet['cast_name']),
                "tweet_id": retweet['tweet_id']
            }
        
        # Cloud Functions呼び出し
        CLOUD_FUNCTION_URL = Config.get_cloud_functions_url()
        response = requests.post(CLOUD_FUNCTION_URL, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                # 成功時の状態更新
                executed_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                result_tweet_id = result.get('tweet_id', '')
                
                execute_query("""
                    UPDATE retweet_schedules 
                    SET status = 'completed', executed_at = ?, result_tweet_id = ?
                    WHERE id = ?
                """, (executed_at, result_tweet_id, retweet['id']))
                
                st.success(f"✅ {action}を実行しました！")
                if result_tweet_id:
                    st.info(f"🔗 新しいツイートID: {result_tweet_id}")
            else:
                error_msg = result.get('message', '不明なエラー')
                execute_query("""
                    UPDATE retweet_schedules 
                    SET status = 'failed', error_message = ?
                    WHERE id = ?
                """, (error_msg, retweet['id']))
                st.error(f"❌ 実行失敗: {error_msg}")
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            execute_query("""
                UPDATE retweet_schedules 
                SET status = 'failed', error_message = ?
                WHERE id = ?
            """, (error_msg, retweet['id']))
            st.error(f"❌ HTTP エラー: {error_msg}")
            
    except Exception as e:
        error_msg = f"実行エラー: {str(e)}"
        execute_query("""
            UPDATE retweet_schedules 
            SET status = 'failed', error_message = ?
            WHERE id = ?
        """, (error_msg, retweet['id']))
        st.error(f"❌ {error_msg}")

def execute_retweet_via_gas_direct_now(retweet):
    """GAS Direct API経由でリツイートを今すぐ実行"""
    try:
        # キャスト名からキャストIDを取得して設定を読み込み
        cast_id = get_cast_id_by_name(retweet['cast_name'])
        if not cast_id:
            st.error(f"❌ キャスト '{retweet['cast_name']}' が見つかりません")
            return
        
        success, message = execute_retweet_via_gas_direct(
            cast_id, 
            retweet['tweet_id'], 
            retweet['comment']
        )
        
        if success:
            # 成功時の状態更新
            executed_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            execute_query("""
                UPDATE retweet_schedules 
                SET status = 'completed', executed_at = ?
                WHERE id = ?
            """, (executed_at, retweet['id']))
            st.success(f"✅ GAS Direct経由で実行完了: {message}")
        else:
            execute_query("""
                UPDATE retweet_schedules 
                SET status = 'failed', error_message = ?
                WHERE id = ?
            """, (message, retweet['id']))
            st.error(f"❌ GAS Direct実行失敗: {message}")
            
    except Exception as e:
        error_msg = f"GAS Direct実行エラー: {str(e)}"
        execute_query("""
            UPDATE retweet_schedules 
            SET status = 'failed', error_message = ?
            WHERE id = ?
        """, (error_msg, retweet['id']))
        st.error(f"❌ {error_msg}")

def execute_retweet_via_sheets_now(retweet):
    """Google Sheets経由でリツイートを今すぐ実行"""
    try:
        # 現在時刻でGoogle Sheetsに送信
        cast_id = get_cast_id_by_name(retweet['cast_name'])
        if not cast_id:
            st.error(f"❌ キャスト '{retweet['cast_name']}' が見つかりません")
            return
        
        current_time = datetime.datetime.now()
        success, message = send_retweet_to_google_sheets(
            cast_id, 
            retweet['tweet_id'], 
            retweet['comment'], 
            current_time
        )
        
        if success:
            # 成功時の状態更新
            executed_at = current_time.strftime('%Y-%m-%d %H:%M:%S')
            execute_query("""
                UPDATE retweet_schedules 
                SET status = 'completed', executed_at = ?
                WHERE id = ?
            """, (executed_at, retweet['id']))
            st.success(f"✅ Google Sheets経由で送信完了: {message}")
        else:
            execute_query("""
                UPDATE retweet_schedules 
                SET status = 'failed', error_message = ?
                WHERE id = ?
            """, (message, retweet['id']))
            st.error(f"❌ Google Sheets送信失敗: {message}")
            
    except Exception as e:
        error_msg = f"Google Sheets実行エラー: {str(e)}"
        execute_query("""
            UPDATE retweet_schedules 
            SET status = 'failed', error_message = ?
            WHERE id = ?
        """, (error_msg, retweet['id']))
        st.error(f"❌ {error_msg}")

def get_cast_id_by_name(cast_name):
    """キャスト名からIDを取得"""
    try:
        result = execute_query("""
            SELECT id FROM casts WHERE name = ?
        """, (cast_name,))
        
        if result:
            return result[0][0]
        return None
    except Exception as e:
        print(f"キャストID取得エラー: {e}")
        return None

def get_cast_name_by_id(cast_id):
    """キャストIDから名前を取得"""
    try:
        result = execute_query("""
            SELECT name FROM casts WHERE id = ?
        """, (cast_id,))
        
        if result:
            return result[0][0]
        return f"Cast_{cast_id}"  # フォールバック
    except Exception as e:
        print(f"キャスト名取得エラー: {e}")
        return f"Cast_{cast_id}"

def get_account_id_for_cast_local(cast_name):
    """キャスト名からX APIアカウントIDを取得（ローカル用）"""
    try:
        result = execute_query("""
            SELECT cxc.twitter_username 
            FROM cast_x_credentials cxc
            JOIN casts c ON c.id = cxc.cast_id
            WHERE c.name = ?
        """, (cast_name,), fetch="one")
        return result['twitter_username'] if result else None
    except Exception as e:
        st.error(f"❌ アカウントID取得エラー: {str(e)}")
        return None

def send_to_x_api(cast_name, post_content, scheduled_datetime=None, cast_id=None):
    """Cloud Functions経由でX (Twitter) APIに投稿を送信する"""
    try:
        # Cloud Functions投稿クライアントを初期化
        cloud_poster = CloudFunctionsPoster(Config.get_cloud_functions_url())
        
        # キャストIDに基づいてアカウントIDを決定
        account_id = get_account_id_for_cast_local(cast_name)
        if not account_id:
            return False, f"❌ キャスト '{cast_name}' のX APIアカウント設定が見つかりません"
        
        # Cloud Functions経由で投稿
        result = cloud_poster.post_tweet(account_id, post_content)
        
        if result.get("status") == "success":
            tweet_id = result.get("tweet_id", "")
            return True, f"✅ X (Twitter) に投稿しました！ Tweet ID: {tweet_id}"
        else:
            error_msg = result.get("message", "投稿に失敗しました")
            return False, f"❌ X API投稿エラー: {error_msg}"
            
    except Exception as e:
        return False, f"❌ Cloud Functions X API送信エラー: {str(e)}"

def get_cast_x_credentials(cast_id):
    """キャストのX API認証情報を取得"""
    result = execute_query(
        "SELECT * FROM cast_x_credentials WHERE cast_id = ? AND is_active = 1", 
        (cast_id,), 
        fetch="one"
    )
    
    # sqlite3.Rowを辞書形式に変換
    if result:
        return dict(result)
    else:
        return None

def save_cast_x_credentials(cast_id, api_key, api_secret, bearer_token, access_token, access_token_secret, twitter_username=None, twitter_user_id=None):
    """キャストのX API認証情報を保存"""
    try:
        # 既存の認証情報があるかチェック
        existing = get_cast_x_credentials(cast_id)
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if existing:
            # 更新
            execute_query("""
                UPDATE cast_x_credentials 
                SET api_key = ?, api_secret = ?, bearer_token = ?, access_token = ?, access_token_secret = ?, 
                    twitter_username = ?, twitter_user_id = ?, updated_at = ?
                WHERE cast_id = ?
            """, (api_key, api_secret, bearer_token, access_token, access_token_secret, twitter_username, twitter_user_id, current_time, cast_id))
        else:
            # 新規作成
            execute_query("""
                INSERT INTO cast_x_credentials 
                (cast_id, api_key, api_secret, bearer_token, access_token, access_token_secret, twitter_username, twitter_user_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cast_id, api_key, api_secret, bearer_token, access_token, access_token_secret, twitter_username, twitter_user_id, current_time, current_time))
        
        return True
    except Exception as e:
        st.error(f"認証情報の保存中にエラーが発生しました: {e}")
        return False

def delete_cast_x_credentials(cast_id):
    """キャストのX API認証情報を削除"""
    try:
        execute_query("UPDATE cast_x_credentials SET is_active = 0 WHERE cast_id = ?", (cast_id,))
        # キャッシュからも削除
        if cast_id in x_poster.cast_clients:
            del x_poster.cast_clients[cast_id]
        return True
    except Exception as e:
        st.error(f"認証情報の削除中にエラーが発生しました: {e}")
        return False

def get_cast_sheets_config(cast_id, action_type='post'):
    """キャストのGoogle Sheets設定を取得（アクション別対応）"""
    # 新しいテーブルから設定を取得（gas_web_app_url含む）
    result = execute_query(
        "SELECT id, cast_id, action_type, spreadsheet_id, sheet_name, gas_web_app_url, is_active, created_at, updated_at FROM cast_action_sheets WHERE cast_id = ? AND action_type = ? AND is_active = 1", 
        (cast_id, action_type), 
        fetch="one"
    )
    
    if result:
        return dict(result)
    
    # 新しいテーブルにない場合は、既存テーブルから取得（互換性）
    if action_type == 'post':
        result_old = execute_query(
            "SELECT id, cast_id, spreadsheet_id, sheet_name, is_active, created_at, updated_at FROM cast_sheets_config WHERE cast_id = ? AND is_active = 1", 
            (cast_id,), 
            fetch="one"
        )
        if result_old:
            config = dict(result_old)
            config['action_type'] = 'post'  # アクションタイプを追加
            config['gas_web_app_url'] = None  # 既存テーブルにはGAS URLはない
            return config
    
    return None

def save_cast_sheets_config(cast_id, spreadsheet_id, sheet_name=None):
    """キャストのGoogle Sheets設定を保存（シンプル版）"""
    try:
        # 既存の設定があるかチェック
        existing = get_cast_sheets_config(cast_id)
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if existing:
            # 更新
            execute_query("""
                UPDATE cast_sheets_config 
                SET spreadsheet_id = ?, sheet_name = ?, updated_at = ?
                WHERE cast_id = ?
            """, (spreadsheet_id, sheet_name or 'Sheet1', current_time, cast_id))
        else:
            # 新規作成
            execute_query("""
                INSERT INTO cast_sheets_config 
                (cast_id, spreadsheet_id, sheet_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (cast_id, spreadsheet_id, sheet_name or 'Sheet1', current_time, current_time))
        
        return True
    except Exception as e:
        st.error(f"Google Sheets設定保存エラー: {str(e)}")
        return False

def save_cast_action_sheets_config(cast_id, action_type, spreadsheet_id, sheet_name=None):
    """キャストのアクション別Google Sheets設定を保存"""
    try:
        # 既存の設定があるかチェック
        existing = get_cast_sheets_config(cast_id, action_type)
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if existing and 'action_type' in existing:
            # 更新
            execute_query("""
                UPDATE cast_action_sheets 
                SET spreadsheet_id = ?, sheet_name = ?, updated_at = ?
                WHERE cast_id = ? AND action_type = ?
            """, (spreadsheet_id, sheet_name or 'Sheet1', current_time, cast_id, action_type))
        else:
            # 新規作成
            execute_query("""
                INSERT INTO cast_action_sheets 
                (cast_id, action_type, spreadsheet_id, sheet_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cast_id, action_type, spreadsheet_id, sheet_name or 'Sheet1', current_time, current_time))
        
        return True
    except Exception as e:
        st.error(f"アクション別Google Sheets設定保存エラー: {str(e)}")
        return False

def save_cast_action_sheets_config_with_gas_url(cast_id, action_type, spreadsheet_id, sheet_name=None, gas_web_app_url=None):
    """キャストのアクション別Google Sheets設定をGAS Web App URLと一緒に保存"""
    try:
        # 既存の設定があるかチェック
        existing = get_cast_sheets_config(cast_id, action_type)
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if existing and 'action_type' in existing:
            # 更新
            execute_query("""
                UPDATE cast_action_sheets 
                SET spreadsheet_id = ?, sheet_name = ?, gas_web_app_url = ?, updated_at = ?
                WHERE cast_id = ? AND action_type = ?
            """, (spreadsheet_id, sheet_name or 'Sheet1', gas_web_app_url, current_time, cast_id, action_type))
        else:
            # 新規作成
            execute_query("""
                INSERT INTO cast_action_sheets 
                (cast_id, action_type, spreadsheet_id, sheet_name, gas_web_app_url, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (cast_id, action_type, spreadsheet_id, sheet_name or 'Sheet1', gas_web_app_url, current_time, current_time))
        
        return True
    except Exception as e:
        st.error(f"アクション別Google Sheets設定（GAS URL含む）保存エラー: {str(e)}")
        return False

def delete_cast_sheets_config(cast_id):
    """キャストのGoogle Sheets設定を削除"""
    try:
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execute_query(
            "UPDATE cast_sheets_config SET is_active = 0, updated_at = ? WHERE cast_id = ?",
            (current_time, cast_id)
        )
        return True
    except Exception as e:
        st.error(f"Google Sheets設定削除エラー: {str(e)}")
        return False

def send_post_to_destination(cast_name, post_content, scheduled_datetime, destination, cast_id=None):
    """投稿を指定した送信先に送信する統合関数（キャスト別設定対応）"""
    if destination == "google_sheets":
        return send_to_google_sheets(cast_name, post_content, scheduled_datetime, cast_id)
    elif destination == "x_api":
        return send_to_x_api(cast_name, post_content, scheduled_datetime, cast_id)
    elif destination == "both":
        # 両方に送信
        sheets_success, sheets_message = send_to_google_sheets(cast_name, post_content, scheduled_datetime, cast_id)
        x_success, x_message = send_to_x_api(cast_name, post_content, scheduled_datetime, cast_id)
        
        if sheets_success and x_success:
            return True, "Google Sheets と X (Twitter) 両方に送信しました！"
        elif sheets_success:
            return True, f"Google Sheets に送信しました。X投稿エラー: {x_message}"
        elif x_success:
            return True, f"X (Twitter) に投稿しました。Sheets送信エラー: {sheets_message}"
        else:
            return False, f"両方の送信に失敗: Sheets({sheets_message}), X({x_message})"
    else:
        return False, "不明な送信先です"

def add_column_to_casts_table(field_name):
    """castsテーブルに新しい列を追加"""
    try:
        execute_query(f"ALTER TABLE casts ADD COLUMN {field_name} TEXT")
        return True
    except Exception as e:
        st.error(f"列の追加中にエラーが発生しました: {e}")
        return False

def remove_column_from_casts_table(field_name):
    """castsテーブルから列を削除（SQLiteでは直接削除できないため、テーブルを再作成）"""
    try:
        # 現在のデータを取得
        current_fields = get_dynamic_persona_fields()
        remaining_fields = [f for f in current_fields if f != field_name]
        
        # 新しいテーブル構造を作成
        columns_def = ", ".join([f"{field} TEXT" if field != 'name' else f"{field} TEXT NOT NULL UNIQUE" for field in remaining_fields])
        execute_query(f"CREATE TABLE casts_new (id INTEGER PRIMARY KEY, {columns_def})")
        
        # データを移行
        columns_list = ", ".join(remaining_fields)
        execute_query(f"INSERT INTO casts_new (id, {columns_list}) SELECT id, {columns_list} FROM casts")
        
        # 古いテーブルを削除し、新しいテーブルをリネーム
        execute_query("DROP TABLE casts")
        execute_query("ALTER TABLE casts_new RENAME TO casts")
        
        return True
    except Exception as e:
        st.error(f"列の削除中にエラーが発生しました: {e}")
        return False

# --- コールバック関数 ---
def quick_approve(post_id):
    created_at_row = execute_query("SELECT created_at FROM posts WHERE id = ?", (post_id,), fetch="one")
    if created_at_row:
        created_at = created_at_row['created_at']
        posted_at_time = created_at.split(' ')[1] if ' ' in created_at else created_at
        execute_query("UPDATE posts SET evaluation = '◎', status = 'approved', posted_at = ? WHERE id = ?", (posted_at_time, post_id))
        st.session_state.page_status_message = ("success", "投稿をクイック承認しました！")
    else:
        st.session_state.page_status_message = ("error", f"エラー: 投稿ID {post_id} が見つかりません。")

def quick_reject(post_id):
    """投稿を却下状態にする"""
    created_at_row = execute_query("SELECT created_at FROM posts WHERE id = ?", (post_id,), fetch="one")
    if created_at_row:
        created_at = created_at_row['created_at']
        posted_at_time = created_at.split(' ')[1] if ' ' in created_at else created_at
        execute_query("UPDATE posts SET evaluation = '×', status = 'rejected', posted_at = ? WHERE id = ?", (posted_at_time, post_id))
        st.session_state.page_status_message = ("success", "投稿を却下しました！")
    else:
        st.session_state.page_status_message = ("error", f"エラー: 投稿ID {post_id} が見つかりません。")

def set_editing_post(post_id):
    st.session_state.editing_post_id = post_id

def clear_editing_post():
    if 'editing_post_id' in st.session_state:
        st.session_state.editing_post_id = None

def get_app_setting(key, default_value=""):
    """アプリ設定を取得"""
    result = execute_query("SELECT value FROM app_settings WHERE key = ?", (key,), fetch="one")
    return result['value'] if result else default_value

def update_app_setting(key, value, description="", category="general"):
    """アプリ設定を更新（存在しない場合は作成）"""
    existing = execute_query("SELECT key FROM app_settings WHERE key = ?", (key,), fetch="one")
    if existing:
        execute_query("UPDATE app_settings SET value = ? WHERE key = ?", (value, key))
    else:
        execute_query("INSERT INTO app_settings (key, value, description, category) VALUES (?, ?, ?, ?)", (key, value, description, category))

def main():
    st.set_page_config(layout="wide")
    load_css("style.css")
    init_db()
    initialize_default_settings()  # デフォルト設定を初期化

    try:
        import vertexai
        if 'auth_done' not in st.session_state:
            # 🌐 Streamlit Cloud production environment support
            if Config.is_production_environment() and "gcp_service_account" in st.secrets:
                # Use Streamlit Cloud secrets for GCP authentication
                from google.oauth2 import service_account
                credentials_info = dict(st.secrets["gcp_service_account"])
                credentials = service_account.Credentials.from_service_account_info(credentials_info)
                vertexai.init(project=project_id, location=location, credentials=credentials)
                st.sidebar.success("🌐 Streamlit Cloud認証完了")
            else:
                # Local development or default authentication
                vertexai.init(project=project_id, location=location)
                st.sidebar.success("✅ Googleサービス認証完了")
            st.session_state.auth_done = True
    except Exception as e:
        st.sidebar.error(f"🚨 Google Cloud認証エラー")
        if Config.is_production_environment():
            st.error("🌐 **Streamlit Cloud認証エラー**")
            st.markdown("""
            **📋 Production環境認証エラー:**
            - Streamlit Cloud secrets.tomlの設定を確認してください
            - GCP Service Account情報が正しく設定されているか確認
            """)
        else:
            st.error("🔐 **Google Cloud認証が必要です**")
            st.markdown(f"""
            **エラー詳細:** `{e}`
            
            **📋 解決方法:**
            1. 左サイドバーの「**システム設定**」をクリック
            2. 「**🔐 Google Cloud認証**」タブを開く
            3. 認証情報を設定するか、以下のコマンドを実行:
        ```bash
        gcloud auth application-default login --no-launch-browser
        ```
        
        **💡 ヒント:** システム設定画面で認証状況を確認・管理できます。
        """)
        
        # システム設定への直接リンクボタン
        if st.button("🔧 システム設定に移動", type="primary", use_container_width=True):
            st.session_state['redirect_to_settings'] = True
            st.rerun()
        
        st.stop()

    if 'gemini_model' not in st.session_state:
        try:
            # APIインポートを動的に決定
            try:
                from vertexai.generative_models import GenerativeModel
                api_version = "stable"
            except ImportError:
                from vertexai.preview.generative_models import GenerativeModel
                api_version = "preview"
            
            # Gemini 2.0 Flash 専用設定（フォールバック制御）
            force_mode = st.session_state.get('force_gemini_2_flash', True)
            
            # シンプルモデル選択（フォールバックなし）
            selected_model = st.session_state.get('selected_model_name', 'gemini-2.5-flash')
            
            if not selected_model or selected_model.strip() == "":
                selected_model = 'gemini-2.5-flash'  # デフォルト
            
            try:
                st.session_state.gemini_model = GenerativeModel(selected_model)
                st.sidebar.success(f"🤖 AIモデル: {selected_model} ({api_version})")
                model_initialized = True
            except Exception as model_error:
                st.sidebar.error(f"❌ モデル読み込み失敗: {selected_model}")
                st.sidebar.warning(f"エラー: {str(model_error)[:80]}...")
                model_initialized = False
            
            if not model_initialized:
                raise Exception(f"指定されたモデル '{selected_model}' の読み込みに失敗しました。サイドバーで別のモデルを選択してください。エラー: {model_error}")
                
        except Exception as e:
            st.error("🤖 **Geminiモデルの初期化エラー**")
            st.markdown(f"""
            **エラー詳細:** `{e}`
            
            **📋 解決方法:**
            1. 左サイドバーの「**システム設定**」をクリック
            2. 「**🔐 Google Cloud認証**」タブで認証を確認
            3. 認証が切れている場合は再設定してください
            
            **💡 よくある原因:**
            - Google Cloud認証の有効期限切れ
            - プロジェクトIDの設定不備
            - Vertex AI APIの有効化不備
            """)
            
            if st.button("🔧 認証設定を確認", type="primary", use_container_width=True):
                st.session_state['redirect_to_settings'] = True
                st.rerun()
                
            st.session_state.gemini_model = None

    st.sidebar.title("AIcast room")
    
    # AIモデル設定（シンプル入力方式）
    with st.sidebar.expander("🤖 AIモデル設定", expanded=False):
        # プリセットモデル選択
        preset_models = [
            "gemini-2.5-flash",
            "gemini-2.5-pro", 
            "gemini-2.0-flash-exp",
            "gemini-1.5-flash-001",
            "gemini-1.5-pro-001",
            "カスタム入力"
        ]
        
        # モデル説明
        model_descriptions = {
            "gemini-2.5-flash": "🚀 最新・価格パフォーマンス最適",
            "gemini-2.5-pro": "🧠 最新・最高性能モデル",
            "gemini-2.0-flash-exp": "⚡ 2.0 Flash実験版",
            "gemini-1.5-flash-001": "💨 1.5 Flash安定版",
            "gemini-1.5-pro-001": "🎯 1.5 Pro安定版",
            "カスタム入力": "✏️ 任意のモデル名を入力"
        }
        
        selected_preset = st.selectbox(
            "モデル選択",
            options=preset_models,
            index=0,
            format_func=lambda x: f"{x} - {model_descriptions.get(x, '')}",
            help="プリセットから選択するか、カスタム入力で任意のモデル名を指定"
        )
        
        if selected_preset == "カスタム入力":
            custom_model = st.text_input(
                "カスタムモデル名",
                value=st.session_state.get('custom_model_name', 'gemini-2.5-flash'),
                placeholder="例: gemini-2.5-pro, gemini-3.0-flash-exp",
                help="正確なモデル名を入力してください"
            )
            st.session_state.custom_model_name = custom_model
            selected_model = custom_model
        else:
            selected_model = selected_preset
        
        # 選択されたモデルを保存
        st.session_state.selected_model_name = selected_model
        
        # モデル情報表示
        if selected_model:
            st.info(f"🎯 使用モデル: `{selected_model}`")
            
            # モデル強制更新ボタン
            if st.button("🔄 モデルを再読み込み", use_container_width=True):
                if 'gemini_model' in st.session_state:
                    del st.session_state.gemini_model
                st.rerun()
    
    # メニューの選択肢
    menu_options = ["📊 ダッシュボード", "投稿管理", "一斉指示", "キャスト管理", "シチュエーション管理", "カテゴリ管理", "グループ管理", "アドバイス管理", "指針アドバイス", "システム設定"]
    
    # リダイレクト機能
    if st.session_state.get('redirect_to_settings'):
        page = "システム設定"
        default_index = menu_options.index("システム設定")
        st.session_state.redirect_to_settings = False  # リセット
    elif st.session_state.get('dashboard_redirect'):
        page = st.session_state.dashboard_redirect
        default_index = menu_options.index(page) if page in menu_options else 1  # 投稿管理のインデックス
        # リダイレクト情報は後で削除する
    else:
        default_index = 0  # デフォルトはダッシュボード
        
    # サイドバーメニューを常に表示
    selected_page = st.sidebar.radio("メニュー", menu_options, index=default_index)
    
    # リダイレクトがある場合は指定されたページを使用、それ以外は選択されたページを使用
    if st.session_state.get('redirect_to_settings') or st.session_state.get('dashboard_redirect'):
        # リダイレクト時は既に設定されたpageを使用
        pass
    else:
        page = selected_page
    if page == "📊 ダッシュボード":
        st.title("📊 AIcast Room ダッシュボード")
        
        # 全体統計の取得
        total_casts = execute_query("SELECT COUNT(*) as count FROM casts", fetch="one")['count']
        total_posts = execute_query("SELECT COUNT(*) as count FROM posts", fetch="one")['count']
        
        # 全体サマリー（コンパクト版）
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📝 キャスト", total_casts)
        with col2:
            st.metric("📰 総投稿", total_posts)
        with col3:
            today_posts = execute_query("SELECT COUNT(*) as count FROM posts WHERE DATE(generated_at) = DATE('now')", fetch="all")
            today_count = today_posts[0]['count'] if today_posts else 0
            st.metric("🗓️ 今日", today_count)
        with col4:
            sent_posts = execute_query("SELECT COUNT(*) as count FROM posts WHERE sent_status = 'sent'", fetch="one")['count']
            st.metric("📤 送信済", sent_posts)
        
        st.markdown("")  # 軽い間隔
        
        # キャスト別統計の取得
        casts = execute_query("SELECT id, name, nickname FROM casts ORDER BY name", fetch="all")
        
        if not casts:
            st.warning("キャスト未登録です。「キャスト管理」で作成してください。")
            st.stop()
        
        st.subheader("🎭 キャスト別投稿状況")
        
        # キャスト別統計データを取得
        cast_stats = []
        for cast in casts:
            cast_id = cast['id']
            cast_name = cast['name']
            cast_nickname = cast['nickname']
            
            # 各ステータスの投稿数を取得（却下済みは除外）
            drafts = execute_query("SELECT COUNT(*) as count FROM posts WHERE cast_id = ? AND status = 'draft'", (cast_id,), fetch="one")['count']
            approved = execute_query("SELECT COUNT(*) as count FROM posts WHERE cast_id = ? AND status = 'approved' AND (sent_status = 'not_sent' OR sent_status = 'scheduled' OR sent_status IS NULL)", (cast_id,), fetch="one")['count']
            sent = execute_query("SELECT COUNT(*) as count FROM posts WHERE cast_id = ? AND sent_status = 'sent'", (cast_id,), fetch="one")['count']
            rejected = execute_query("SELECT COUNT(*) as count FROM posts WHERE cast_id = ? AND status = 'rejected'", (cast_id,), fetch="one")['count']
            
            cast_stats.append({
                'id': cast_id,
                'name': cast_name,
                'nickname': cast_nickname,
                'drafts': drafts,
                'approved': approved,
                'sent': sent,
                'total': drafts + approved + sent + rejected  # 却下も総数には含める
            })
        
        # キャスト一覧を1行形式で表示（コンパクト版）
        for i, cast in enumerate(cast_stats):
            display_name = f"{cast['name']}（{cast['nickname']}）" if cast['nickname'] else cast['name']
            
            # 1行レイアウト: キャスト名、統計、ボタン
            col_name, col_stats, col_action = st.columns([3, 4, 2])
            
            with col_name:
                st.markdown(f"**🎭 {display_name}**")
            
            with col_stats:
                # 統計を横並びで表示（却下済みを除外、総投稿数を追加）
                stat_text = []
                if cast['drafts'] > 0:
                    stat_text.append(f"📝 **{cast['drafts']}**")
                else:
                    stat_text.append(f"📝 {cast['drafts']}")
                
                if cast['approved'] > 0:
                    stat_text.append(f"✅ **{cast['approved']}**")
                else:
                    stat_text.append(f"✅ {cast['approved']}")
                
                if cast['sent'] > 0:
                    stat_text.append(f"📤 **{cast['sent']}**")
                else:
                    stat_text.append(f"📤 {cast['sent']}")
                
                # 総投稿数を右端に追加
                stat_text.append(f"📊 {cast['total']}件")
                
                st.markdown(" | ".join(stat_text))
            
            with col_action:
                if st.button(f"➕ 管理", key=f"manage_{cast['id']}", type="primary", use_container_width=True):
                    st.session_state.selected_cast_name = cast['name']
                    st.session_state.dashboard_redirect = "投稿管理"
                    st.rerun()
            
            # 最後の要素以外に薄い区切り線を追加
            if i < len(cast_stats) - 1:
                st.markdown("<hr style='margin: 0.5rem 0; border: none; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)
        
        # 最近の活動セクションは一時的に非表示
        # st.subheader("📈 最近の活動")
        # ...
    
    elif page == "投稿管理":
        # ダッシュボードからのリダイレクト処理
        if st.session_state.get('dashboard_redirect'):
            del st.session_state.dashboard_redirect
        
        casts = execute_query("SELECT id, name, nickname FROM casts ORDER BY name", fetch="all")
        if not casts:
            st.warning("キャスト未登録です。「キャスト管理」で作成してください。"); st.stop()

        # --- 編集ページか一覧ページかを判定 ---
        if st.session_state.get('editing_post_id') is not None:
            # --- 投稿チューニング（詳細編集）ページ ---
            st.title("📝 投稿チューニング")
            edit_status_placeholder = st.empty()
            # ...existing code...
            if "edit_status_message" in st.session_state:
                msg_type, msg_content = st.session_state.edit_status_message
                if msg_type == "success": edit_status_placeholder.success(msg_content)
                elif msg_type == "error": edit_status_placeholder.error(msg_content)
                elif msg_type == "warning": edit_status_placeholder.warning(msg_content)
                elif msg_type == "auth_error":
                    with edit_status_placeholder.container():
                        show_auth_error_guidance(msg_content, "投稿再生成")
                del st.session_state.edit_status_message
                if msg_type != "auth_error":  # 認証エラーの場合は自動で消さない
                    time.sleep(2); edit_status_placeholder.empty()

            post_id = st.session_state.editing_post_id
            post = execute_query("SELECT p.*, c.name as cast_name FROM posts p JOIN casts c ON p.cast_id = c.id WHERE p.id = ?", (post_id,), fetch="one")
            if not post:
                st.error("投稿の読み込みに失敗しました。一覧に戻ります。")
                clear_editing_post(); st.rerun()

            selected_cast_id = post['cast_id']
            selected_cast_details_row = execute_query(f"SELECT * FROM casts WHERE id = ?", (selected_cast_id,), fetch="one")
            selected_cast_details = dict(selected_cast_details_row) if selected_cast_details_row else None
            st.session_state.selected_cast_name = post['cast_name']

            if st.button("← 投稿案一覧に戻る"):
                clear_editing_post(); st.rerun()

            st.caption(f"作成日時: {post['created_at']} | テーマ: {post['theme']}")
            st.text_area("投稿内容", value=post['content'], height=150, key=f"content_{post_id}")
            eval_options = ['未評価', '◎', '◯', '△', '✕']; current_eval = post['evaluation'] if post['evaluation'] in eval_options else '未評価'
            st.selectbox("評価", eval_options, index=eval_options.index(current_eval), key=f"eval_{post_id}")

            advice_master_rows = execute_query("SELECT content FROM advice_master ORDER BY id", fetch="all")
            advice_options = [row['content'] for row in advice_master_rows] if advice_master_rows else []
            current_advice_list = post['advice'].split(',') if post['advice'] else []
            valid_current_advice = [adv for adv in current_advice_list if adv in advice_options]
            
            # セッション状態にない場合のみ、デフォルト値を設定
            if f"advice_{post_id}" not in st.session_state:
                st.session_state[f"advice_{post_id}"] = valid_current_advice
            if f"free_advice_{post_id}" not in st.session_state:
                st.session_state[f"free_advice_{post_id}"] = post['free_advice'] or ""
            if f"regen_char_limit_{post_id}" not in st.session_state:
                st.session_state[f"regen_char_limit_{post_id}"] = 140

            # セッション状態から値を取得してwidgetを表示
            st.multiselect("アドバイス", advice_options, key=f"advice_{post_id}")
            st.text_input("追加のアドバイス（自由入力）", key=f"free_advice_{post_id}")
            st.number_input("再生成時の文字数（以内）", min_value=20, max_value=300, key=f"regen_char_limit_{post_id}")

            c1, c2, c3, c4 = st.columns(4)
            do_regenerate = c1.button("🔁 アドバイスを元に再生成", use_container_width=True, key=f"regen_{post_id}")
            do_approve = c2.button("✅ 承認する", type="primary", use_container_width=True, key=f"approve_detail_{post_id}")
            do_save = c3.button("💾 保存", use_container_width=True, key=f"save_{post_id}")
            do_reject = c4.button("❌ 却下", use_container_width=True, key=f"reject_detail_{post_id}")

            if do_regenerate:
                with edit_status_placeholder:
                    with st.spinner("AIが投稿を書き直しています..."):
                        try:
                            advice_list = st.session_state.get(f"advice_{post_id}", []); free_advice = st.session_state.get(f"free_advice_{post_id}", ""); regen_char_limit = st.session_state.get(f"regen_char_limit_{post_id}", 140)
                            combined_advice_list = advice_list[:]
                            if free_advice and free_advice.strip(): combined_advice_list.append(free_advice.strip())
                            final_advice_str = ", ".join(combined_advice_list)
                            history_ts = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                            persona_sheet = format_persona(selected_cast_id, selected_cast_details)
                            regeneration_prompt = f"""# ペルソナ\n{persona_sheet}\n\n# シチュエーション\n{post['theme']}\n\n# 以前の投稿（これは失敗作です）\n{post['content']}\n\n# プロデューサーからの改善アドバイス\n「{final_advice_str}」\n\n# 指示\n以前の投稿を改善アドバイスを元に書き直してください。\n\n# ルール\n- **{regen_char_limit}文字以内**で生成。"""
                            response = safe_generate_content(st.session_state.gemini_model, regeneration_prompt)
                            # 履歴に保存：前の投稿内容とアドバイス、そして新しい投稿内容
                            execute_query("INSERT INTO tuning_history (post_id, timestamp, previous_content, advice_used) VALUES (?, ?, ?, ?)", 
                                      (post_id, history_ts, f"<span style='color: #888888'>前回の投稿:</span>\n<span style='color: #888888'>{post['content']}</span>\n\n**新しい投稿:**\n{clean_generated_content(response.text)}", final_advice_str))
                            execute_query("UPDATE posts SET content = ?, evaluation = '未評価', advice = '', free_advice = '' WHERE id = ?", (clean_generated_content(response.text), post_id))
                            # --- 再生成後にウィジェットのセッションキーを削除して初期化 ---
                            for k in [f"advice_{post_id}", f"free_advice_{post_id}", f"regen_char_limit_{post_id}"]:
                                if k in st.session_state:
                                    del st.session_state[k]
                            # 再生成後の選択項目のリセット
                            st.session_state[f"advice_{post_id}"] = []  # アドバイスをクリア
                            st.session_state[f"free_advice_{post_id}"] = ""  # 追加アドバイスをクリア
                            st.session_state[f"regen_char_limit_{post_id}"] = 140  # 文字数を初期値に
                            st.session_state.edit_status_message = ("success", "投稿を再生成しました！")
                        except Exception as e:
                            # 認証エラーの可能性をチェック
                            auth_keywords = ["credential", "authentication", "unauthorized", "permission", "quota", "token"]
                            if any(keyword.lower() in str(e).lower() for keyword in auth_keywords):
                                st.session_state.edit_status_message = ("auth_error", str(e))
                            else:
                                st.session_state.edit_status_message = ("error", f"再生成中にエラーが発生しました: {str(e)}")
                st.rerun()

            if do_approve:
                content = st.session_state.get(f"content_{post_id}", ""); evaluation = st.session_state.get(f"eval_{post_id}", "未評価"); advice = ",".join(st.session_state.get(f"advice_{post_id}", [])); free_advice = st.session_state.get(f"free_advice_{post_id}", "")
                created_at_row = execute_query("SELECT created_at FROM posts WHERE id = ?", (post_id,), fetch="one")
                if created_at_row:
                    created_at = created_at_row['created_at']; posted_at_time = created_at.split(' ')[1] if ' ' in created_at else created_at
                    execute_query("UPDATE posts SET content = ?, evaluation = ?, advice = ?, free_advice = ?, status = 'approved', posted_at = ? WHERE id = ?", (content, evaluation, advice, free_advice, posted_at_time, post_id))
                    st.session_state.page_status_message = ("success", "投稿を承認しました！"); clear_editing_post(); st.rerun()
                else:
                    st.session_state.edit_status_message = ("error", f"エラー: 投稿ID {post_id} が見つかりません。"); st.rerun()

            if do_save:
                content = st.session_state.get(f"content_{post_id}", ""); evaluation = st.session_state.get(f"eval_{post_id}", "未評価"); advice = ",".join(st.session_state.get(f"advice_{post_id}", [])); free_advice = st.session_state.get(f"free_advice_{post_id}", "")
                execute_query("UPDATE posts SET content = ?, evaluation = ?, advice = ?, free_advice = ? WHERE id = ?", (content, evaluation, advice, free_advice, post_id))
                st.session_state.edit_status_message = ("success", "変更を保存しました！"); st.rerun()

            if do_reject:
                execute_query("UPDATE posts SET status = 'rejected' WHERE id = ?", (post_id,))
                st.session_state.page_status_message = ("warning", "投稿を却下しました。"); clear_editing_post(); st.rerun()

            with st.expander("チューニング履歴を表示"):
                history = execute_query("SELECT * FROM tuning_history WHERE post_id = ? ORDER BY timestamp DESC", (post_id,), fetch="all")
                if history:
                    for i, item in enumerate(history):
                        if i > 0:  # 最初の項目以外の前に点線を追加
                            st.markdown("---")
                        st.caption(f"{item['timestamp']} のアドバイス: {item['advice_used']}")
                        st.markdown(item['previous_content'], unsafe_allow_html=True)
                else: st.write("この投稿にはまだチューニング履歴がありません。")
        else:
            # --- 投稿管理（一覧）ページ ---
            st.title("📝 投稿管理")
            # selected_cast_name の初期化
            if 'selected_cast_name' not in st.session_state or st.session_state.selected_cast_name not in [c['name'] for c in casts]:
                st.session_state.selected_cast_name = casts[0]['name']
            top_status_placeholder = st.empty()
            if "page_status_message" in st.session_state:
                msg_type, msg_content = st.session_state.page_status_message
                if msg_type == "success": top_status_placeholder.success(msg_content)
                elif msg_type == "error": top_status_placeholder.error(msg_content)
                elif msg_type == "warning": top_status_placeholder.warning(msg_content)
                del st.session_state.page_status_message
                time.sleep(2); top_status_placeholder.empty()

            def update_selected_cast():
                # 表示名から実際のキャスト名に変換
                display_name = st.session_state.cast_selector
                st.session_state.selected_cast_name = cast_name_mapping[display_name]
            
            # キャスト表示名を「name（nickname）」形式で作成
            cast_display_options = []
            cast_name_mapping = {}
            for c in casts:
                display_name = f"{c['name']}（{c['nickname']}）" if c['nickname'] else c['name']
                cast_display_options.append(display_name)
                cast_name_mapping[display_name] = c['name']
            
            # 現在選択されているキャストの表示名を取得
            current_cast = next((c for c in casts if c['name'] == st.session_state.selected_cast_name), None)
            current_display = f"{current_cast['name']}（{current_cast['nickname']}）" if current_cast and current_cast['nickname'] else st.session_state.selected_cast_name
            current_index = cast_display_options.index(current_display) if current_display in cast_display_options else 0
            
            selected_display_name = st.selectbox("キャストを選択", cast_display_options, key='cast_selector', index=current_index, on_change=update_selected_cast)
            selected_cast_name = cast_name_mapping[selected_display_name]
            selected_cast_id = next((c['id'] for c in casts if c['name'] == selected_cast_name), None)
            selected_cast_details_row = execute_query(f"SELECT * FROM casts WHERE id = ?", (selected_cast_id,), fetch="one")
            selected_cast_details = dict(selected_cast_details_row) if selected_cast_details_row else None

            st.header("投稿案を生成する")
            
            # タブで生成方法を選択
            tab_auto, tab_custom = st.tabs(["🎲 自動生成", "✍️ 直接指示"])
            
            with tab_auto:
                st.subheader("シチュエーションベース自動生成")
                allowed_categories_str = selected_cast_details.get('allowed_categories', '')
                allowed_categories = allowed_categories_str.split(',') if allowed_categories_str else []
                # 存在しないカテゴリを除外
                all_category_rows = execute_query("SELECT name FROM situation_categories", fetch="all")
                existing_category_names = [row['name'] for row in all_category_rows] if all_category_rows else []
                valid_allowed_categories = [cat for cat in allowed_categories if cat in existing_category_names]
                
                if not valid_allowed_categories:
                    if allowed_categories:
                        st.warning(f"キャスト「{selected_cast_name}」に設定されたカテゴリが削除されています。「キャスト管理」で再設定してください。")
                    else:
                        st.warning(f"キャスト「{selected_cast_name}」に使用が許可されたカテゴリがありません。「キャスト管理」で設定してください。")
                else:
                    placeholders = ','.join('?' for _ in valid_allowed_categories)
                    query = f"SELECT s.content, s.time_slot FROM situations s JOIN situation_categories sc ON s.category_id = sc.id WHERE sc.name IN ({placeholders})"
                    situations_rows = execute_query(query, valid_allowed_categories, fetch="all")
                    col1, col2 = st.columns(2)
                    default_post_count = int(get_app_setting("default_post_count", "5"))
                    num_posts = col1.number_input("生成する数", min_value=1, max_value=50, value=default_post_count, key="auto_post_num")
                    default_char_limit = int(get_app_setting("default_char_limit", "140"))
                    char_limit = col2.number_input("文字数（以内）", min_value=20, max_value=300, value=default_char_limit, key="auto_char_limit")

                    if st.button("自動生成開始", type="primary", key="auto_generate"):
                        if st.session_state.get('gemini_model'):
                            if not situations_rows:
                                st.error("キャストに許可されたカテゴリに属するシチュエーションがありません。"); st.stop()
                            with top_status_placeholder:
                                with st.spinner("投稿を生成中です..."):
                                    persona_sheet = format_persona(selected_cast_id, selected_cast_details)
                                    successful_posts = 0
                                    error_occurred = False
                                    error_message = None
                                    
                                    for i in range(num_posts):
                                        selected_situation = random.choice(situations_rows)
                                        prompt_template = f"""# ペルソナ\n{persona_sheet}\n\n# シチュエーション\n{selected_situation['content']}\n\n# ルール\nSNS投稿を**{char_limit}文字以内**で生成。\n\n# 出力形式\n投稿内容のみを出力してください。例文、説明、番号付けは不要です。"""
                                        
                                        # リトライ機能付きAPI呼び出し
                                        max_retries = 3
                                        retry_delay = 10  # 秒
                                        
                                        for retry in range(max_retries):
                                            try:
                                                response = safe_generate_content(st.session_state.gemini_model, prompt_template)
                                                generated_text = clean_generated_content(response.text)
                                                time_slot_map = {"朝": (7, 11), "昼": (12, 17), "夜": (18, 23)}
                                                hour_range = time_slot_map.get(selected_situation['time_slot'], (0, 23))
                                                random_hour = random.randint(hour_range[0], hour_range[1]); random_minute = random.randint(0, 59)
                                                created_at = datetime.datetime.now(JST).replace(hour=random_hour, minute=random_minute, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
                                                generated_at = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                                                execute_query("INSERT INTO posts (cast_id, created_at, content, theme, generated_at) VALUES (?, ?, ?, ?, ?)", (selected_cast_id, created_at, generated_text, selected_situation['content'], generated_at))
                                                successful_posts += 1
                                                break  # 成功したらリトライループを抜ける
                                                
                                            except Exception as e:
                                                error_message = str(e)
                                                
                                                # 429エラーの場合はリトライ
                                                if "429" in error_message or "Resource exhausted" in error_message:
                                                    if retry < max_retries - 1:  # 最後のリトライでない場合
                                                        st.info(f"⏱️ API制限により待機中... ({retry + 1}/{max_retries}回目のリトライ)")
                                                        time.sleep(retry_delay * (retry + 1))  # 段階的に待機時間を増加
                                                        continue
                                                    else:
                                                        error_occurred = True
                                                        break
                                                else:
                                                    # 429エラー以外は即座にエラー
                                                    error_occurred = True
                                                    break
                                        
                                        if error_occurred:
                                            break  # エラー時は投稿生成ループを抜ける
                                        
                                        # 成功時は短い間隔で次の投稿へ
                                        time.sleep(2)
                                # 結果に応じてメッセージを表示
                                if error_occurred:
                                    # API制限エラーの特別処理
                                    if "429" in error_message or "Resource exhausted" in error_message:
                                        top_status_placeholder.error("⏱️ API制限に達しました")
                                        with st.expander("🔍 API制限エラーの解決方法", expanded=True):
                                            st.warning("**429 Resource Exhausted エラー**")
                                            st.markdown("""
                                            **原因:** Google Cloud Vertex AIのAPI制限に達しています。
                                            
                                            **解決方法:**
                                            1. **⏰ 待機**: 5-10分後に再試行してください
                                            2. **📉 リクエスト数を減らす**: 生成する投稿数を減らしてください
                                            3. **⏱️ 間隔を空ける**: 連続生成を避け、時間を空けて実行
                                            
                                            **💡 ヒント:**
                                            - 一度に大量生成せず、数件ずつ分けて実行
                                            - 他のユーザーと同じAPIを共有している可能性があります
                                            
                                            **🔗 詳細情報:**
                                            [Google Cloud Vertex AI 制限について](https://cloud.google.com/vertex-ai/generative-ai/docs/error-code-429)
                                            """)
                                            
                                            if st.button("🔄 5分後に自動再試行（推奨）", type="primary"):
                                                st.info("⏰ 5分後に再試行します...")
                                                time.sleep(5)  # デモ用に短縮（実際は300秒）
                                                st.rerun()
                                    else:
                                        top_status_placeholder.error("❌ AI生成エラーが発生しました")
                                        with st.expander("🔍 エラーの詳細と解決方法", expanded=True):
                                            show_auth_error_guidance(error_message, "投稿生成")
                                elif successful_posts > 0:
                                    top_status_placeholder.success(f"✅ {successful_posts}件の投稿案を正常に生成・保存しました！")
                                    st.balloons(); time.sleep(2); top_status_placeholder.empty(); st.rerun()
                                else:
                                    top_status_placeholder.warning("⚠️ 投稿の生成に失敗しました。")
                        else: 
                            top_status_placeholder.error("AIモデルの読み込みに失敗しているため、投稿を生成できません。")
            
            with tab_custom:
                st.subheader("✍️ 直接指示による投稿生成")
                st.info("具体的な投稿内容や指示を入力して、キャラクターに合った投稿を生成します。")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    custom_num_posts = st.number_input("生成する数", min_value=1, max_value=20, value=1, key="custom_post_num")
                
                with col2:
                    custom_char_limit = st.number_input("文字数（以内）", min_value=20, max_value=300, value=int(get_app_setting("default_char_limit", "140")), key="custom_char_limit")
                
                with col3:
                    time_slot = st.selectbox(
                        "投稿予定時間帯",
                        options=["朝", "昼", "夜", "現在時刻"],
                        key="custom_time_slot"
                    )
                
                # 直接指示入力
                custom_instruction = st.text_area(
                    "投稿指示・内容",
                    placeholder="""例：
• 今日は雨が降っているので、おうち時間の過ごし方について投稿して
• カフェで飲んだコーヒーがとても美味しかったという投稿
• 最近読んだ本の感想を投稿してください
• 新しいヘアスタイルにチャレンジしたことを報告する投稿""",
                    height=150,
                    key="custom_instruction"
                )
                
                if st.button("直接指示で生成", type="primary", key="custom_generate"):
                    if not custom_instruction.strip():
                        st.error("投稿指示・内容を入力してください。")
                    elif st.session_state.get('gemini_model'):
                        with top_status_placeholder:
                            with st.spinner(f"{custom_num_posts}件のカスタム投稿を生成中です..."):
                                # ペルソナシートを作成
                                persona_sheet = format_persona(selected_cast_id, selected_cast_details)
                                successful_posts = 0
                                error_occurred = False
                                error_message = None
                                
                                # 進捗表示
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                # 指定された数だけ生成
                                for i in range(custom_num_posts):
                                    try:
                                        status_text.text(f"投稿 {i+1}/{custom_num_posts} を生成中...")
                                        
                                        # 複数生成時は少しずつ内容を変える指示を追加
                                        variation_instruction = ""
                                        if custom_num_posts > 1:
                                            variation_instruction = f"\n\n# バリエーション指示\n同じテーマで{i+1}番目の投稿として、少し異なる視点や表現で投稿してください。"
                                        
                                        # 直接指示用プロンプト
                                        custom_prompt = f"""# ペルソナ
{persona_sheet}

# 投稿指示
{custom_instruction.strip()}{variation_instruction}

# ルール
上記の指示に従って、このキャラクターらしいSNS投稿を**{custom_char_limit}文字以内**で生成してください。キャラクターの個性、口調、趣味嗜好を反映させてください。"""

                                        # AI生成実行（リトライ機能付き）
                                        max_retries = 3
                                        retry_delay = 5
                                        
                                        for retry in range(max_retries):
                                            try:
                                                response = safe_generate_content(st.session_state.gemini_model, custom_prompt)
                                                generated_text = clean_generated_content(response.text)
                                                
                                                # 投稿予定時刻を設定（複数生成時は少しずつずらす）
                                                if time_slot == "現在時刻":
                                                    post_datetime = datetime.datetime.now(JST) + datetime.timedelta(minutes=i*5)
                                                else:
                                                    time_slot_map = {"朝": (7, 11), "昼": (12, 17), "夜": (18, 23)}
                                                    hour_range = time_slot_map.get(time_slot, (0, 23))
                                                    random_hour = random.randint(hour_range[0], hour_range[1])
                                                    random_minute = random.randint(0, 59)
                                                    post_datetime = datetime.datetime.now(JST).replace(hour=random_hour, minute=random_minute, second=0, microsecond=0)
                                                
                                                created_at = post_datetime.strftime('%Y-%m-%d %H:%M:%S')
                                                generated_at = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                                                
                                                # データベースに保存
                                                theme_text = f"直接指示: {custom_instruction[:50]}..." if len(custom_instruction) > 50 else f"直接指示: {custom_instruction}"
                                                execute_query("INSERT INTO posts (cast_id, created_at, content, theme, generated_at) VALUES (?, ?, ?, ?, ?)", 
                                                            (selected_cast_id, created_at, generated_text, theme_text, generated_at))
                                                
                                                successful_posts += 1
                                                break  # 成功したらリトライループを抜ける
                                                
                                            except Exception as e:
                                                retry_error = str(e)
                                                if "429" in retry_error or "Resource exhausted" in retry_error:
                                                    if retry < max_retries - 1:
                                                        status_text.text(f"API制限により待機中... ({retry + 1}/{max_retries}回目のリトライ)")
                                                        time.sleep(retry_delay * (retry + 1))
                                                        continue
                                                    else:
                                                        error_occurred = True
                                                        error_message = retry_error
                                                        break
                                                else:
                                                    error_occurred = True
                                                    error_message = retry_error
                                                    break
                                        
                                        if error_occurred:
                                            break  # エラー時は生成ループを抜ける
                                        
                                        # 進捗更新
                                        progress_bar.progress((i + 1) / custom_num_posts)
                                        time.sleep(1)  # API制限対策
                                        
                                    except Exception as e:
                                        error_occurred = True
                                        error_message = str(e)
                                        break
                                
                                # プログレスバーとステータステキストをクリア
                                progress_bar.empty()
                                status_text.empty()
                                
                                # 結果表示
                                if error_occurred:
                                    if "429" in error_message or "Resource exhausted" in error_message:
                                        top_status_placeholder.error("⏱️ API制限に達しました")
                                        st.info("しばらく待ってから再試行してください。")
                                    else:
                                        top_status_placeholder.error(f"❌ 生成エラー: {error_message}")
                                        show_auth_error_guidance(error_message, "カスタム投稿生成")
                                elif successful_posts > 0:
                                    top_status_placeholder.success(f"✅ {successful_posts}件のカスタム投稿を生成・保存しました！")
                                    st.balloons()
                                    time.sleep(2)
                                    top_status_placeholder.empty()
                                    st.rerun()
                                else:
                                    top_status_placeholder.warning("⚠️ 投稿の生成に失敗しました。")
                    else:
                        st.error("AIモデルの読み込みに失敗しているため、投稿を生成できません。")

            st.markdown("---")
            # 選択されたキャストの表示名を作成
            current_cast = next((c for c in casts if c['name'] == selected_cast_name), None)
            cast_display_name = f"{current_cast['name']}（{current_cast['nickname']}）" if current_cast and current_cast['nickname'] else selected_cast_name
            st.header(f"「{cast_display_name}」の投稿一覧")
            
            tab1, tab2, tab3, tab4, tab_schedule, tab_retweet = st.tabs(["投稿案 (Drafts)", "承認済み (Approved)", "送信済み (Sent)", "却下済み (Rejected)", "📅 スケジュール投稿", "🔄 リツイート予約"])

            with tab1:
                # 最新データを確実に取得するため、キャッシュをクリア
                draft_posts = execute_query("SELECT * FROM posts WHERE cast_id = ? AND status = 'draft' ORDER BY created_at DESC", (selected_cast_id,), fetch="all")
                if draft_posts:
                    st.info(f"{len(draft_posts)}件の投稿案があります。")
                    
                    # 一括操作パネル
                    with st.expander("📋 一括操作", expanded=False):
                        col_bulk1, col_bulk2 = st.columns(2)
                        
                        with col_bulk1:
                            st.subheader("✅ 一括承認")
                            if st.button("選択した投稿を一括承認", type="primary", use_container_width=True):
                                selected_posts = [post_id for post_id, selected in st.session_state.items() 
                                                if post_id.startswith('select_draft_') and selected]
                                
                                if selected_posts:
                                    approved_count = 0
                                    current_time = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                                    
                                    for post_key in selected_posts:
                                        post_id = post_key.replace('select_draft_', '')
                                        execute_query("UPDATE posts SET status = 'approved', posted_at = ? WHERE id = ?", 
                                                    (current_time, post_id))
                                        approved_count += 1
                                        # チェックボックスの状態をクリア
                                        st.session_state[post_key] = False
                                    
                                    st.session_state.page_status_message = ("success", f"✅ {approved_count}件の投稿を一括承認しました！")
                                    st.rerun()
                                else:
                                    st.warning("承認する投稿を選択してください。")
                        
                        with col_bulk2:
                            st.subheader("❌ 一括却下")
                            if st.button("選択した投稿を一括却下", type="secondary", use_container_width=True):
                                selected_posts = [post_id for post_id, selected in st.session_state.items() 
                                                if post_id.startswith('select_draft_') and selected]
                                
                                if selected_posts:
                                    rejected_count = 0
                                    current_time = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                                    
                                    for post_key in selected_posts:
                                        post_id = post_key.replace('select_draft_', '')
                                        execute_query("UPDATE posts SET status = 'rejected', posted_at = ? WHERE id = ?", 
                                                    (current_time, post_id))
                                        rejected_count += 1
                                        # チェックボックスの状態をクリア
                                        st.session_state[post_key] = False
                                    
                                    st.session_state.page_status_message = ("success", f"❌ {rejected_count}件の投稿を一括却下しました！")
                                    st.rerun()
                                else:
                                    st.warning("却下する投稿を選択してください。")
                    
                    # 一括チューニング（AI改善）セクションを追加
                    with st.expander("💡 一括チューニング（AI改善）", expanded=False):
                        st.subheader("🎯 選択した投稿をAIで改善")
                        
                        # アドバイス選択
                        advice_options = execute_query("SELECT content FROM advice_master ORDER BY content", fetch="all")
                        advice_list = [advice['content'] for advice in advice_options]
                        
                        if len(advice_list) == 0:
                            st.warning("⚠️ アドバイスマスターにデータがありません。")
                            if st.button("🔧 デフォルトアドバイスを追加", key="add_default_advice"):
                                    default_advice_list = [
                                        "もう少し感情表現を豊かに",
                                        "具体的なエピソードを追加",
                                        "読みやすさを改善",
                                        "キャラクターらしさを強調",
                                        "文字数を調整"
                                    ]
                                    for advice in default_advice_list:
                                        execute_query("INSERT OR IGNORE INTO advice_master (content) VALUES (?)", (advice,))
                                    st.success("デフォルトアドバイスを追加しました！")
                                    st.rerun()
                            
                            selected_advice = st.multiselect(
                                "改善アドバイスを選択",
                                advice_list,
                                key="bulk_advice_select"
                            )
                            
                            custom_advice = st.text_area(
                                "カスタム改善指示（任意）",
                                placeholder="具体的な改善指示を入力...",
                                key="bulk_custom_advice"
                            )
                            
                            if st.button("選択した投稿を一括チューニング（AI改善）", type="primary", use_container_width=True):
                                selected_posts = [post_id for post_id, selected in st.session_state.items() 
                                                if post_id.startswith('select_draft_') and selected]
                                
                                if selected_posts and (selected_advice or custom_advice.strip()):
                                    if 'gemini_model' not in st.session_state:
                                        st.error("AIモデルが読み込まれていません。ページを更新してください。")
                                        return
                                    
                                    # 改善指示を統合
                                    improvement_instructions = []
                                    if selected_advice:
                                        improvement_instructions.extend(selected_advice)
                                    if custom_advice.strip():
                                        improvement_instructions.append(custom_advice.strip())
                                    
                                    instructions_text = "\n- ".join(improvement_instructions)
                                    
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                    improved_count = 0
                                    total_posts = len(selected_posts)
                                    
                                    for i, post_key in enumerate(selected_posts):
                                        try:
                                            post_id = post_key.replace('select_draft_', '')
                                            status_text.text(f"投稿ID {post_id} を改善中... ({i+1}/{total_posts})")
                                            
                                            # 元の投稿を取得
                                            original_post = execute_query("SELECT * FROM posts WHERE id = ?", (post_id,), fetch="one")
                                            if not original_post:
                                                continue
                                            
                                            # キャスト情報を取得
                                            cast_info = execute_query("SELECT * FROM casts WHERE id = ?", (original_post['cast_id'],), fetch="one")
                                            if not cast_info:
                                                continue
                                            
                                            # ペルソナシートを作成
                                            persona_sheet = ""
                                            for field in PERSONA_FIELDS:
                                                if cast_info[field]:
                                                    persona_sheet += f"**{field}**: {cast_info[field]}\n"
                                            
                                            # 改善プロンプトを作成
                                            improvement_prompt = f"""# ペルソナ
{persona_sheet}

# 元の投稿
{original_post['content']}

# 改善指示
- {instructions_text}

# ルール
上記の改善指示に従って投稿を改善してください。キャラクターの個性を保ちながら、指示された点を改善した新しい投稿を生成してください。元の投稿のテーマとメッセージは維持してください。"""

                                            # AI で改善
                                            response = safe_generate_content(st.session_state.gemini_model, improvement_prompt)
                                            improved_content = clean_generated_content(response.text)
                                            
                                            # チューニング履歴に記録
                                            timestamp = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                                            combined_advice = ",".join(selected_advice) if selected_advice else ""
                                            execute_query("INSERT INTO tuning_history (post_id, timestamp, previous_content, advice_used) VALUES (?, ?, ?, ?)", 
                                                        (post_id, timestamp, original_post['content'], instructions_text))
                                            
                                            # 投稿内容を更新
                                            execute_query("UPDATE posts SET content = ?, advice = ?, free_advice = ? WHERE id = ?", 
                                                        (improved_content, combined_advice, custom_advice.strip(), post_id))
                                            
                                            improved_count += 1
                                            progress_bar.progress((i + 1) / total_posts)
                                            time.sleep(1)  # API制限対策
                                            
                                        except Exception as e:
                                            st.error(f"投稿ID {post_id} の改善中にエラーが発生しました: {str(e)}")
                                            continue
                                    
                                    progress_bar.empty()
                                    status_text.empty()
                                    
                                    if improved_count > 0:
                                        st.session_state.page_status_message = ("success", f"� {improved_count}件の投稿を改善しました！")
                                        st.success(f"✅ 処理完了: {improved_count}件の投稿をAIで改善しました")
                                        
                                        # チェックボックスの状態をクリア
                                        for post_key in selected_posts:
                                            st.session_state[post_key] = False
                                        
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        st.error("投稿の改善に失敗しました。")
                                        
                                else:
                                    if not selected_posts:
                                        st.warning("改善する投稿を選択してください。")
                                    else:
                                        st.warning("改善指示を入力してください。")
                    
                    st.markdown("---")
                    
                    # 全選択/全解除ボタン
                    col_select1, col_select2, col_select3 = st.columns([1,1,4])
                    with col_select1:
                        if st.button("🔲 全選択", use_container_width=True):
                            for post in draft_posts:
                                st.session_state[f'select_draft_{post["id"]}'] = True
                            st.rerun()
                    
                    with col_select2:
                        if st.button("☐ 全解除", use_container_width=True):
                            for post in draft_posts:
                                st.session_state[f'select_draft_{post["id"]}'] = False
                            st.rerun()
                    
                    # 投稿一覧表示
                    for post in draft_posts:
                        post_id = post['id']
                        with st.container():
                            col_check, col_content, col_tune, col_approve, col_reject = st.columns([0.5, 4.5, 1, 1, 1])
                            
                            with col_check:
                                st.checkbox("選択", key=f"select_draft_{post_id}", label_visibility="collapsed")
                            
                            with col_content:
                                # 実際の生成時刻と投稿予定時刻を表示
                                scheduled_time = datetime.datetime.strptime(post['created_at'], '%Y-%m-%d %H:%M:%S')
                                scheduled_display = scheduled_time.strftime('%H:%M')
                                
                                if post['generated_at']:
                                    actual_generated_time = datetime.datetime.strptime(post['generated_at'], '%Y-%m-%d %H:%M:%S')
                                    actual_display = actual_generated_time.strftime('%m-%d %H:%M')
                                    st.caption(f"⏰ 作成: {actual_display} | 🕐 投稿予定: {scheduled_display} | 📝 テーマ: {post['theme']}")
                                else:
                                    # 古いデータ（generated_atがない場合）
                                    st.caption(f"🕐 生成時刻: {scheduled_display} | 📝 テーマ: {post['theme']}")
                                
                                # アドバイスが設定されている場合は表示（デバッグ情報付き）
                                st.write(f"🔍 投稿ID {post['id']}: advice='{post['advice']}', free_advice='{post['free_advice']}'")
                                
                                if post['advice'] or post['free_advice']:
                                    advice_parts = []
                                    if post['advice'] and post['advice'].strip():
                                        advice_parts.extend([a.strip() for a in post['advice'].split(',') if a.strip()])
                                    if post['free_advice'] and post['free_advice'].strip():
                                        advice_parts.append(post['free_advice'].strip())
                                    
                                    if advice_parts:
                                        st.caption(f"💡 アドバイス: {', '.join(advice_parts)}")
                                    else:
                                        st.caption("🔍 アドバイスデータはあるが空白です")
                                else:
                                    st.caption("🔍 アドバイス未設定")
                                
                                st.write(post['content'])
                            
                            with col_tune:
                                st.button("チューニング", key=f"edit_{post_id}", on_click=set_editing_post, args=(post_id,), use_container_width=True)
                            
                            with col_approve:
                                st.button("承認", type="primary", key=f"quick_approve_{post_id}", on_click=quick_approve, args=(post_id,), use_container_width=True)
                            
                            with col_reject:
                                st.button("却下", key=f"quick_reject_{post_id}", on_click=quick_reject, args=(post_id,), use_container_width=True)
                            
                            st.markdown("---")
                else: 
                    st.info("チューニング対象の投稿案はありません。")

            with tab2:
                # Google Sheets連携の設定状況を表示
                credentials_path = "credentials/credentials.json"
                token_path = "credentials/token.pickle"
                
                if os.path.exists(token_path):
                    st.success("✅ Google Sheets連携設定済み（OAuth認証完了）", icon="🔗")
                elif os.path.exists(credentials_path):
                    st.info("📋 OAuth認証ファイル設定済み（初回送信時にブラウザ認証が開始されます）", icon="🔐")
                else:
                    with st.expander("⚠️ Google Sheets連携未設定（OAuth設定方法を表示）", expanded=False):
                        st.warning("""Google Sheets送信機能を使用するにはOAuth認証設定が必要です。

【OAuth認証設定手順】
1. [Google Cloud Console](https://console.cloud.google.com) にアクセス
2. 新しいプロジェクトを作成または既存プロジェクト選択
3. 「APIとサービス」> 「ライブラリ」で以下を有効化：
   - **Google Sheets API**
   - **Google Drive API**
4. 「APIとサービス」> 「認証情報」> 「認証情報を作成」> **「OAuthクライアントID」**
5. 同意画面の設定（初回のみ）：
   - ユーザータイプ：**外部**
   - アプリ名、メールアドレスを入力
6. OAuthクライアントID作成：
   - アプリケーションの種類：**「デスクトップアプリケーション」**
   - 名前：任意（例：AIcast Room）
7. **ダウンロードボタン**をクリックしてJSONファイルを取得
8. ダウンロードしたファイルを **`credentials/credentials.json`** として保存
9. アプリを再起動して送信ボタンをクリック（ブラウザで認証画面が開きます）

**注意**: 初回送信時にブラウザでGoogle認証が必要です。認証後はトークンが自動保存されます。""")
                
                approved_posts = execute_query("SELECT * FROM posts WHERE cast_id = ? AND status = 'approved' AND (sent_status = 'not_sent' OR sent_status = 'scheduled' OR sent_status IS NULL) ORDER BY posted_at DESC", (selected_cast_id,), fetch="all")
                if approved_posts:
                    st.info(f"{len(approved_posts)}件の承認済み投稿があります。")
                    
                    # 一括送信パネル
                    with st.expander("📤 一括送信", expanded=False):
                        st.subheader("📤 選択した投稿を一括送信")
                        
                        # 送信先選択
                        bulk_destination_options = [
                            ("📊 Google Sheets", "google_sheets"),
                            ("🐦 X (Twitter)", "x_api"),
                            ("📊🐦 両方に送信", "both")
                        ]
                        
                        bulk_destination = st.selectbox(
                            "一括送信先",
                            options=[opt[0] for opt in bulk_destination_options],
                            key="bulk_destination"
                        )
                        
                        bulk_destination_value = next((opt[1] for opt in bulk_destination_options if opt[0] == bulk_destination), "google_sheets")
                        
                        st.info(f"選択した投稿を元の投稿予定時刻で{bulk_destination}に一括送信します。")
                        
                        # 一括送信実行
                        if st.button("📤 選択した投稿を一括送信", type="primary", use_container_width=True):
                            selected_posts = [post_id for post_id, selected in st.session_state.items() 
                                            if post_id.startswith('select_approved_') and selected]
                            
                            if selected_posts:
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                sent_count = 0
                                total_posts = len(selected_posts)
                                
                                # キャスト名とIDを取得
                                current_cast = next((c for c in casts if c['name'] == selected_cast_name), None)
                                cast_name_only = current_cast['name'] if current_cast else selected_cast_name
                                cast_id = current_cast['id'] if current_cast else None
                                
                                for i, post_key in enumerate(selected_posts):
                                    try:
                                        post_id = post_key.replace('select_approved_', '')
                                        status_text.text(f"投稿ID {post_id} を送信中... ({i+1}/{total_posts})")
                                        
                                        # 投稿データを取得
                                        post_data = next((p for p in approved_posts if str(p['id']) == post_id), None)
                                        if not post_data:
                                            continue
                                        
                                        # 元の投稿予定時刻を使用
                                        original_datetime = datetime.datetime.strptime(post_data['created_at'], '%Y-%m-%d %H:%M:%S')
                                        
                                        # 指定された送信先に送信（キャストIDを渡す）
                                        success, message = send_post_to_destination(cast_name_only, post_data['content'], original_datetime, bulk_destination_value, cast_id)
                                        
                                        if success:
                                            # 送信成功時のデータベース更新
                                            sent_at = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                                            execute_query("UPDATE posts SET sent_status = 'sent', sent_at = ? WHERE id = ?", (sent_at, post_id))
                                            execute_query("INSERT INTO send_history (post_id, destination, sent_at, scheduled_datetime, status) VALUES (?, ?, ?, ?, ?)", 
                                                        (post_id, bulk_destination_value, sent_at, original_datetime.strftime('%Y-%m-%d %H:%M:%S'), 'completed'))
                                            sent_count += 1
                                        else:
                                            # 送信失敗時のログ記録
                                            failed_at = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                                            execute_query("INSERT INTO send_history (post_id, destination, sent_at, scheduled_datetime, status, error_message) VALUES (?, ?, ?, ?, ?, ?)", 
                                                        (post_id, bulk_destination_value, failed_at, original_datetime.strftime('%Y-%m-%d %H:%M:%S'), 'failed', message))
                                        
                                        progress_bar.progress((i + 1) / total_posts)
                                        time.sleep(0.5)  # 短い間隔で高速処理
                                        
                                    except Exception as e:
                                        st.error(f"投稿ID {post_id} の送信中にエラーが発生しました: {str(e)}")
                                        continue
                                
                                progress_bar.empty()
                                status_text.empty()
                                
                                if sent_count > 0:
                                    st.session_state.page_status_message = ("success", f"📤 {sent_count}件の投稿を{bulk_destination}に一括送信しました！")
                                    st.success(f"✅ 処理完了: {sent_count}件の投稿を一括送信しました")
                                    
                                    # チェックボックスの状態をクリア
                                    for post_key in selected_posts:
                                        st.session_state[post_key] = False
                                    
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error("投稿の送信に失敗しました。")
                            else:
                                st.warning("送信する投稿を選択してください。")
                    
                    # 画像付き投稿セクション
                    with st.expander("📸 画像付き投稿", expanded=False):
                        st.subheader("📸 画像付きX投稿")
                        st.info("画像ファイルをアップロードして、投稿と一緒にX（Twitter）に送信できます。")
                        
                        # 投稿テキスト入力
                        image_post_text = st.text_area(
                            "投稿テキスト",
                            placeholder="画像付き投稿のテキストを入力してください...",
                            max_chars=280,
                            help="最大280文字まで入力可能"
                        )
                        
                        # 画像ファイルアップロード
                        uploaded_images = st.file_uploader(
                            "画像ファイル（最大4枚）",
                            type=['jpg', 'jpeg', 'png', 'gif', 'webp'],
                            accept_multiple_files=True,
                            help="対応形式: JPG, PNG, GIF, WebP（各5MB以下、最大4枚）"
                        )
                        
                        # アップロードされた画像の確認
                        if uploaded_images:
                            if len(uploaded_images) > 4:
                                st.warning("⚠️ 画像は最大4枚まで添付できます。最初の4枚が使用されます。")
                                uploaded_images = uploaded_images[:4]
                            
                            st.write(f"📸 アップロード済み画像: {len(uploaded_images)}枚")
                            
                            # 画像プレビュー
                            cols = st.columns(len(uploaded_images))
                            for i, img in enumerate(uploaded_images):
                                with cols[i]:
                                    st.image(img, caption=f"画像{i+1}: {img.name}", use_column_width=True)
                        
                        # 投稿ボタン
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("📸 画像付きでX投稿", type="primary", use_container_width=True):
                                if not image_post_text.strip():
                                    st.error("⚠️ 投稿テキストを入力してください")
                                elif not uploaded_images:
                                    st.error("⚠️ 画像をアップロードしてください")
                                else:
                                    with st.spinner("画像付き投稿を送信中..."):
                                        try:
                                            # アップロードされた画像を一時保存
                                            temp_image_paths = []
                                            os.makedirs("temp_images", exist_ok=True)
                                            
                                            for img in uploaded_images:
                                                temp_path = f"temp_images/{img.name}"
                                                with open(temp_path, "wb") as f:
                                                    f.write(img.getvalue())
                                                temp_image_paths.append(temp_path)
                                            
                                            # 画像付き投稿実行
                                            current_cast = next((c for c in casts if c['name'] == selected_cast_name), None)
                                            cast_id = current_cast['id'] if current_cast else None
                                            
                                            success, message = x_poster.post_tweet_with_media(
                                                text=image_post_text,
                                                media_paths=temp_image_paths,
                                                cast_name=selected_cast_name,
                                                cast_id=cast_id
                                            )
                                            
                                            # 一時ファイル削除
                                            for temp_path in temp_image_paths:
                                                try:
                                                    os.remove(temp_path)
                                                except:
                                                    pass
                                            
                                            if success:
                                                st.success(f"✅ {message}")
                                                st.rerun()
                                            else:
                                                st.error(f"❌ {message}")
                                                
                                        except Exception as e:
                                            st.error(f"❌ 画像付き投稿エラー: {str(e)}")
                        
                        with col2:
                            st.info("💡 ヒント\n・画像は自動リサイズされます\n・X APIのFREEプランで利用可能\n・最大4枚まで同時投稿可能")
                    
                    # Google Sheets画像URL送信セクション
                    with st.expander("📊 Google Drive → Google Sheets送信", expanded=False):
                        st.subheader("� Google Drive画像付きGoogle Sheets送信")
                        st.info("Google Drive画像URLを指定してGoogle Sheetsに送信し、GASで自動画像投稿できます。")
                        
                        # 使用方法の説明
                        with st.expander("📋 Google Drive URL取得方法", expanded=False):
                            st.markdown("""
                            **🔗 Google Drive画像の共有URL取得手順:**
                            1. Google Driveで画像ファイルを右クリック
                            2. 「共有」を選択
                            3. 「リンクを知っている全員」に変更
                            4. 「リンクをコピー」をクリック
                            5. 下記にペーストしてください
                            
                            **📝 対応するURL形式:**
                            - `https://drive.google.com/file/d/FILE_ID/view?usp=sharing`
                            - `https://drive.google.com/open?id=FILE_ID`
                            - 自動的に直接アクセス可能な形式に変換されます
                            """)
                        
                        # 投稿テキスト入力
                        sheets_post_text = st.text_area(
                            "投稿テキスト",
                            placeholder="Google Sheets送信用のテキストを入力してください...",
                            max_chars=280,
                            help="GASで自動投稿されるテキスト"
                        )
                        
                        # Google Drive画像URL入力（最大4つ）
                        st.write("� Google Drive画像URL（最大4つ）")
                        image_urls = []
                        for i in range(4):
                            url = st.text_input(
                                f"Google Drive画像URL {i+1}",
                                placeholder=f"https://drive.google.com/file/d/FILE_ID/view?usp=sharing",
                                key=f"sheets_drive_url_{i}",
                                help="Google Drive共有URL（自動変換されます）"
                            )
                            if url.strip():
                                image_urls.append(url.strip())
                        
                        if image_urls:
                            st.write(f"🔗 設定済みGoogle Drive画像: {len(image_urls)}個")
                            for i, url in enumerate(image_urls):
                                converted_url = convert_google_drive_url(url)
                                st.caption(f"{i+1}. 元URL: {url[:40]}{'...' if len(url) > 40 else ''}")
                                if converted_url != url:
                                    st.caption(f"   → 変換後: {converted_url[:40]}{'...' if len(converted_url) > 40 else ''}")
                        
                        # 送信ボタン
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("� Google Drive画像付きでSheets送信", type="primary", use_container_width=True):
                                if not sheets_post_text.strip():
                                    st.error("⚠️ 投稿テキストを入力してください")
                                else:
                                    with st.spinner("Google Sheetsに送信中..."):
                                        try:
                                            # Google Sheets送信実行
                                            current_cast = next((c for c in casts if c['name'] == selected_cast_name), None)
                                            cast_id = current_cast['id'] if current_cast else None
                                            
                                            success, message = send_to_google_sheets(
                                                cast_name=selected_cast_name,
                                                post_content=sheets_post_text,
                                                scheduled_datetime=datetime.datetime.now(),
                                                cast_id=cast_id,
                                                action_type='post',
                                                image_urls=image_urls if image_urls else None
                                            )
                                            
                                            if success:
                                                st.success(f"✅ {message}")
                                                if image_urls:
                                                    st.info(f"� Google Drive画像 {len(image_urls)}個も送信されました。GASで自動的に画像付き投稿されます。")
                                                st.rerun()
                                            else:
                                                st.error(f"❌ {message}")
                                                
                                        except Exception as e:
                                            st.error(f"❌ Google Sheets送信エラー: {str(e)}")
                        
                        with col2:
                            st.info("💡 Google Drive連携\n・Drive URLを自動変換\n・GASで画像付き投稿実行\n・チーム共有も簡単")
                    
                    st.markdown("---")
                    
                    # 全選択/全解除ボタン
                    col_select1, col_select2, col_select3 = st.columns([1,1,4])
                    with col_select1:
                        if st.button("🔲 全選択", key="approved_select_all", use_container_width=True):
                            for post in approved_posts:
                                st.session_state[f'select_approved_{post["id"]}'] = True
                            st.rerun()
                    
                    with col_select2:
                        if st.button("☐ 全解除", key="approved_deselect_all", use_container_width=True):
                            for post in approved_posts:
                                st.session_state[f'select_approved_{post["id"]}'] = False
                            st.rerun()
                    
                    # 投稿一覧表示
                    for post in approved_posts:
                        with st.container():
                            col_check, col_content, col_datetime, col_action = st.columns([0.5, 2.5, 1, 1])
                            
                            with col_check:
                                st.checkbox("選択", key=f"select_approved_{post['id']}", label_visibility="collapsed")
                            with col_content:
                                full_advice_list = []; 
                                if post['advice']: full_advice_list.extend(post['advice'].split(','))
                                if post['free_advice']: full_advice_list.append(post['free_advice'])
                                full_advice_str = ", ".join(full_advice_list)
                                
                                # スケジュール情報の表示
                                scheduled_time = datetime.datetime.strptime(post['created_at'], '%Y-%m-%d %H:%M:%S')
                                scheduled_display = scheduled_time.strftime('%H:%M')
                                
                                # スケジュール状態の確認
                                status_info = ""
                                if post['scheduled_at']:
                                    scheduled_at = datetime.datetime.strptime(post['scheduled_at'], '%Y-%m-%d %H:%M:%S')
                                    if post['sent_status'] == 'scheduled':
                                        status_info = f" | 📅 スケジュール済み: {scheduled_at.strftime('%m-%d %H:%M')}"
                                    else:
                                        status_info = f" | 📅 予定: {scheduled_at.strftime('%m-%d %H:%M')}"
                                
                                if post['generated_at']:
                                    actual_generated_time = datetime.datetime.strptime(post['generated_at'], '%Y-%m-%d %H:%M:%S')
                                    actual_display = actual_generated_time.strftime('%m-%d %H:%M')
                                    st.caption(f"⏰ 作成: {actual_display} | 🕐 投稿予定: {scheduled_display} | 承認: {post['posted_at']} | 評価: {post['evaluation']} | アドバイス: {full_advice_str}{status_info}")
                                else:
                                    # 古いデータ（generated_atがない場合）
                                    st.caption(f"🕐 生成時刻: {scheduled_display} | 承認: {post['posted_at']} | 評価: {post['evaluation']} | アドバイス: {full_advice_str}{status_info}")
                                
                                # スケジュール状態に応じたアイコン表示
                                if post['sent_status'] == 'scheduled':
                                    st.info(post['content'], icon="📅")
                                else:
                                    st.success(post['content'], icon="✔")
                            
                            with col_datetime:
                                # 投稿時刻の取得（スケジュール投稿がある場合は scheduled_at を優先）
                                if post['scheduled_at'] and post['sent_status'] == 'scheduled':
                                    # スケジュール投稿として保存されている場合
                                    current_scheduled_datetime = datetime.datetime.strptime(post['scheduled_at'], '%Y-%m-%d %H:%M:%S')
                                    original_datetime = current_scheduled_datetime
                                    st.caption(f"📅 スケジュール時刻: {current_scheduled_datetime.strftime('%m-%d %H:%M')} | 🕒 元の投稿時刻: {datetime.datetime.strptime(post['created_at'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M')}")
                                else:
                                    # 通常の投稿または未スケジュール
                                    original_datetime = datetime.datetime.strptime(post['created_at'], '%Y-%m-%d %H:%M:%S')
                                    st.caption(f"🕒 元の投稿時刻: {original_datetime.strftime('%H:%M')}")
                                
                                # 日時選択オプション
                                time_options = [
                                    ("元の投稿時刻を使用", original_datetime),
                                    ("カスタム時刻を指定", None)
                                ]
                                
                                selected_option = st.selectbox(
                                    "送信時刻の設定", 
                                    options=[opt[0] for opt in time_options],
                                    key=f"time_option_{post['id']}"
                                )
                                
                                if selected_option == "元の投稿時刻を使用":
                                    scheduled_datetime = original_datetime
                                    st.info(f"📅 {original_datetime.strftime('%Y-%m-%d %H:%M')} で送信")
                                else:
                                    # カスタム送信日時設定
                                    col_date, col_time_method = st.columns([1, 1])
                                    
                                    with col_date:
                                        send_date = st.date_input("送信日", key=f"date_{post['id']}", min_value=datetime.date.today())
                                    
                                    with col_time_method:
                                        time_method = st.radio(
                                            "時刻設定方法",
                                            ["プリセット時間", "カスタム時間"],
                                            key=f"time_method_{post['id']}"
                                        )
                                    
                                    if time_method == "プリセット時間":
                                        # プリセット時間選択
                                        # 現在の時刻を取得（スケジュール時刻があればそれを、なければ元の時刻を使用）
                                        current_time_for_preset = original_datetime.time()
                                        
                                        preset_times = [
                                            ("07:00 - 朝", datetime.time(7, 0)),
                                            ("09:00 - 朝", datetime.time(9, 0)),
                                            ("12:00 - 昼", datetime.time(12, 0)),
                                            ("15:00 - 午後", datetime.time(15, 0)),
                                            ("18:00 - 夕方", datetime.time(18, 0)),
                                            ("20:00 - 夜", datetime.time(20, 0)),
                                            ("22:00 - 夜", datetime.time(22, 0)),
                                            ("現在の時刻", current_time_for_preset)
                                        ]
                                        
                                        selected_preset = st.selectbox(
                                            "プリセット時間を選択",
                                            options=[opt[0] for opt in preset_times],
                                            key=f"preset_time_{post['id']}"
                                        )
                                        
                                        send_time = next(opt[1] for opt in preset_times if opt[0] == selected_preset)
                                    
                                    else:  # カスタム時間
                                        col_hour, col_minute = st.columns([1, 1])
                                        
                                        with col_hour:
                                            # 時間のプルダウン選択
                                            hour_options = list(range(24))
                                            hour_labels = [f"{h:02d}時" for h in hour_options]
                                            
                                            selected_hour_label = st.selectbox(
                                                "時",
                                                options=hour_labels,
                                                index=original_datetime.hour,
                                                key=f"hour_select_{post['id']}"
                                            )
                                            send_hour = hour_options[hour_labels.index(selected_hour_label)]
                                        
                                        with col_minute:
                                            # 分の入力方法を選択
                                            minute_method = st.radio(
                                                "分の設定",
                                                ["プルダウン", "自由入力"],
                                                key=f"minute_method_{post['id']}",
                                                horizontal=True
                                            )
                                            
                                            if minute_method == "プルダウン":
                                                minute_options = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
                                                minute_labels = [f"{m:02d}分" for m in minute_options]
                                                
                                                # 現在の分に最も近いオプションを選択
                                                closest_minute = min(minute_options, key=lambda x: abs(x - original_datetime.minute))
                                                default_index = minute_options.index(closest_minute)
                                                
                                                selected_minute_label = st.selectbox(
                                                    "分",
                                                    options=minute_labels,
                                                    index=default_index,
                                                    key=f"minute_select_{post['id']}"
                                                )
                                                send_minute = minute_options[minute_labels.index(selected_minute_label)]
                                            
                                            else:  # 自由入力
                                                send_minute = st.number_input(
                                                    "分（0-59）",
                                                    min_value=0,
                                                    max_value=59,
                                                    value=original_datetime.minute,
                                                    key=f"minute_input_{post['id']}"
                                                )
                                        
                                        send_time = datetime.time(send_hour, send_minute)
                                    
                                    scheduled_datetime = datetime.datetime.combine(send_date, send_time)
                                    st.info(f"📅 {send_date.strftime('%Y-%m-%d')} {send_time.strftime('%H:%M')} で送信")
                            
                            with col_action:
                                # 送信先選択
                                destination_options = [
                                    ("📊 Google Sheets", "google_sheets"),
                                    ("🐦 X (Twitter)", "x_api"),
                                    ("📊🐦 両方に送信", "both")
                                ]
                                
                                selected_destination = st.selectbox(
                                    "送信先",
                                    options=[opt[0] for opt in destination_options],
                                    key=f"destination_{post['id']}"
                                )
                                
                                # 選択された送信先に応じてボタンのラベルを変更
                                destination_value = next((opt[1] for opt in destination_options if opt[0] == selected_destination), "google_sheets")
                                button_label = "📤 送信" if destination_value == "both" else selected_destination
                                
                                if st.button(button_label, key=f"send_{post['id']}", type="primary", use_container_width=True):
                                    
                                    # 現在選択中のキャスト名のnameのみを取得
                                    current_cast = next((c for c in casts if c['name'] == selected_cast_name), None)
                                    cast_name_only = current_cast['name'] if current_cast else selected_cast_name
                                    cast_id = current_cast['id'] if current_cast else None
                                    
                                    # 投稿実行時に最新のscheduled_datetimeを再取得
                                    time_option_key = f"time_option_{post['id']}"
                                    if time_option_key in st.session_state:
                                        current_option = st.session_state[time_option_key]
                                        
                                        if current_option == "元の投稿時刻を使用":
                                            final_scheduled_datetime = original_datetime
                                        else:
                                            # カスタム設定の値を取得
                                            date_key = f"date_{post['id']}"
                                            final_send_date = st.session_state.get(date_key, datetime.date.today())
                                            
                                            time_method_key = f"time_method_{post['id']}"
                                            current_time_method = st.session_state.get(time_method_key, "プリセット時間")
                                            
                                            if current_time_method == "プリセット時間":
                                                preset_key = f"preset_time_{post['id']}"
                                                preset_selection = st.session_state.get(preset_key, "07:00 - 朝")
                                                
                                                preset_times = [
                                                    ("07:00 - 朝", datetime.time(7, 0)),
                                                    ("09:00 - 朝", datetime.time(9, 0)),
                                                    ("12:00 - 昼", datetime.time(12, 0)),
                                                    ("15:00 - 午後", datetime.time(15, 0)),
                                                    ("18:00 - 夕方", datetime.time(18, 0)),
                                                    ("20:00 - 夜", datetime.time(20, 0)),
                                                    ("22:00 - 夜", datetime.time(22, 0)),
                                                    ("現在の時刻", original_datetime.time())
                                                ]
                                                final_send_time = next((opt[1] for opt in preset_times if opt[0] == preset_selection), datetime.time(12, 0))
                                            
                                            else:  # カスタム時間
                                                hour_key = f"hour_select_{post['id']}"
                                                final_hour = st.session_state.get(hour_key, "12時")
                                                final_hour_num = int(final_hour.replace("時", ""))
                                                
                                                minute_method_key = f"minute_method_{post['id']}"
                                                minute_method = st.session_state.get(minute_method_key, "プルダウン")
                                                
                                                if minute_method == "プルダウン":
                                                    minute_key = f"minute_select_{post['id']}"
                                                    final_minute_str = st.session_state.get(minute_key, "00分")
                                                    final_minute = int(final_minute_str.replace("分", ""))
                                                else:
                                                    minute_input_key = f"minute_input_{post['id']}"
                                                    final_minute = st.session_state.get(minute_input_key, 0)
                                                
                                                final_send_time = datetime.time(final_hour_num, final_minute)
                                            
                                            final_scheduled_datetime = datetime.datetime.combine(final_send_date, final_send_time)
                                    
                                    else:
                                        # フォールバック: scheduled_datetimeをそのまま使用
                                        final_scheduled_datetime = scheduled_datetime
                                    
                                    # 未来の投稿かどうかをチェック（タイムゾーンを統一）
                                    current_time = datetime.datetime.now(JST)
                                    
                                    # final_scheduled_datetimeがnaiveの場合はJSTタイムゾーンを追加
                                    if final_scheduled_datetime.tzinfo is None:
                                        final_scheduled_datetime = final_scheduled_datetime.replace(tzinfo=JST)
                                    
                                    is_future_post = final_scheduled_datetime > current_time
                                    
                                    if is_future_post:
                                        # 将来の投稿：スケジュール投稿として保存
                                        scheduled_at_str = final_scheduled_datetime.strftime('%Y-%m-%d %H:%M:%S')
                                        execute_query("UPDATE posts SET scheduled_at = ?, sent_status = 'scheduled' WHERE id = ?", 
                                                    (scheduled_at_str, post['id']))
                                        st.session_state.page_status_message = ("success", f"📅 {final_scheduled_datetime.strftime('%Y-%m-%d %H:%M')} にスケジュール投稿を設定しました")
                                    else:
                                        # 即座投稿：従来通りの処理
                                        success, message = send_post_to_destination(cast_name_only, post['content'], final_scheduled_datetime, destination_value, cast_id)
                                        
                                        if success:
                                            # 送信成功時のデータベース更新
                                            sent_at = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                                            execute_query("UPDATE posts SET sent_status = 'sent', sent_at = ? WHERE id = ?", (sent_at, post['id']))
                                            execute_query("INSERT INTO send_history (post_id, destination, sent_at, scheduled_datetime, status) VALUES (?, ?, ?, ?, ?)", 
                                                        (post['id'], destination_value, sent_at, final_scheduled_datetime.strftime('%Y-%m-%d %H:%M:%S'), 'completed'))
                                            st.session_state.page_status_message = ("success", message)
                                        else:
                                            # 送信失敗時のログ記録
                                            failed_at = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                                            execute_query("INSERT INTO send_history (post_id, destination, sent_at, scheduled_datetime, status, error_message) VALUES (?, ?, ?, ?, ?, ?)", 
                                                        (post['id'], destination_value, failed_at, final_scheduled_datetime.strftime('%Y-%m-%d %H:%M:%S'), 'failed', message))
                                            st.session_state.page_status_message = ("error", message)
                                    st.rerun()
                                
                                if st.button("↩️ 投稿案に戻す", key=f"revert_{post['id']}", use_container_width=True):
                                    execute_query("UPDATE posts SET status = 'draft', posted_at = NULL WHERE id = ?", (post['id'],))
                                    st.session_state.page_status_message = ("success", "投稿を「投稿案」に戻しました。"); st.rerun()
                            
                            st.markdown("---")
                else: st.info("承認済みの投稿はまだありません。")

            with tab3:
                # 送信済みタブ
                sent_posts = execute_query("SELECT p.*, sh.destination, sh.sent_at as send_timestamp, sh.scheduled_datetime FROM posts p LEFT JOIN send_history sh ON p.id = sh.post_id WHERE p.cast_id = ? AND p.sent_status = 'sent' ORDER BY p.sent_at DESC", (selected_cast_id,), fetch="all")
                if sent_posts:
                    st.info(f"{len(sent_posts)}件の送信済み投稿があります。")
                    for post in sent_posts:
                        with st.container():
                            col_content, col_info = st.columns([3,1])
                            with col_content:
                                # 実際の生成時刻と投稿予定時刻を表示
                                scheduled_time = datetime.datetime.strptime(post['created_at'], '%Y-%m-%d %H:%M:%S')
                                scheduled_display = scheduled_time.strftime('%H:%M')
                                
                                # スケジュール投稿かどうかを判定
                                is_scheduled_post = post['scheduled_at'] is not None
                                schedule_info = ""
                                
                                if is_scheduled_post:
                                    scheduled_at = datetime.datetime.strptime(post['scheduled_at'], '%Y-%m-%d %H:%M:%S')
                                    schedule_info = f" | 📅 スケジュール実行: {scheduled_at.strftime('%m-%d %H:%M')}"
                                
                                if post['generated_at']:
                                    actual_generated_time = datetime.datetime.strptime(post['generated_at'], '%Y-%m-%d %H:%M:%S')
                                    actual_display = actual_generated_time.strftime('%m-%d %H:%M')
                                    st.caption(f"⏰ 作成: {actual_display} | 🕐 投稿予定: {scheduled_display} | 送信先: {post['destination'] or 'スケジュール投稿'} | 送信日時: {post['send_timestamp'] or post['sent_at']}{schedule_info}")
                                else:
                                    # 古いデータ（generated_atがない場合）
                                    st.caption(f"🕐 生成時刻: {scheduled_display} | 送信先: {post['destination'] or 'スケジュール投稿'} | 送信日時: {post['send_timestamp'] or post['sent_at']}{schedule_info}")
                                
                                # スケジュール投稿の場合は特別なアイコンで表示
                                if is_scheduled_post:
                                    st.success(post['content'], icon="📅")
                                else:
                                    st.info(post['content'], icon="📤")
                                    
                            with col_info:
                                st.write(f"**評価**: {post['evaluation']}")
                                if is_scheduled_post:
                                    st.write(f"**投稿方式**: スケジュール投稿")
                                    st.write(f"**実行時刻**: {post['sent_at']}")
                                else:
                                    st.write(f"**投稿時間**: {post['posted_at']}")
                            st.markdown("---")
                else: 
                    st.info("送信済みの投稿はまだありません。")

            with tab4:
                rejected_posts = execute_query("SELECT * FROM posts WHERE cast_id = ? AND status = 'rejected' ORDER BY created_at DESC", (selected_cast_id,), fetch="all")
                if rejected_posts:
                    st.info(f"{len(rejected_posts)}件の投稿が却下されています。")
                    for post in rejected_posts:
                        full_advice_list = []
                        if post['advice']: full_advice_list.extend(post['advice'].split(','))
                        if post['free_advice']: full_advice_list.append(post['free_advice'])
                        full_advice_str = ", ".join(full_advice_list)
                        # 実際の生成時刻と投稿予定時刻を表示
                        scheduled_time = datetime.datetime.strptime(post['created_at'], '%Y-%m-%d %H:%M:%S')
                        scheduled_display = scheduled_time.strftime('%H:%M')
                        
                        if post['generated_at']:
                            actual_generated_time = datetime.datetime.strptime(post['generated_at'], '%Y-%m-%d %H:%M:%S')
                            actual_display = actual_generated_time.strftime('%Y-%m-%d %H:%M')
                            st.caption(f"⏰ 作成: {actual_display} | 🕐 投稿予定: {scheduled_display} | 評価: {post['evaluation']} | アドバイス: {full_advice_str}")
                        else:
                            # 古いデータ（generated_atがない場合）
                            time_display = scheduled_time.strftime('%Y-%m-%d %H:%M')
                            st.caption(f"🕐 生成時刻: {time_display} | 評価: {post['evaluation']} | アドバイス: {full_advice_str}")
                        st.error(post['content'], icon="✖")
                else: st.info("却下済みの投稿はまだありません。")

            with tab_schedule:
                # スケジュール投稿タブ
                st.markdown("### 📅 スケジュール投稿管理")
                
                # 全てのスケジュール投稿を取得（実行済み・未実行含む）
                all_scheduled_posts = execute_query("""
                    SELECT * FROM posts 
                    WHERE cast_id = ? AND scheduled_at IS NOT NULL 
                    ORDER BY scheduled_at DESC
                """, (selected_cast_id,), fetch="all")
                
                if all_scheduled_posts:
                    # 状態別に分類
                    pending_posts = [p for p in all_scheduled_posts if p['sent_status'] == 'scheduled']
                    completed_posts = [p for p in all_scheduled_posts if p['sent_status'] == 'sent']
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader(f"⏳ 待機中 ({len(pending_posts)}件)")
                        if pending_posts:
                            for post in pending_posts:
                                with st.container():
                                    scheduled_at = datetime.datetime.strptime(post['scheduled_at'], '%Y-%m-%d %H:%M:%S')
                                    current_time = datetime.datetime.now()
                                    
                                    # 実行予定時刻との比較
                                    if scheduled_at <= current_time:
                                        time_status = f"🚨 実行予定時刻経過: {scheduled_at.strftime('%m-%d %H:%M')}"
                                        st.warning(post['content'][:100] + "...")
                                    else:
                                        time_status = f"📅 実行予定: {scheduled_at.strftime('%m-%d %H:%M')}"
                                        st.info(post['content'][:100] + "...")
                                    
                                    st.caption(time_status)
                                    st.markdown("---")
                        else:
                            st.info("待機中のスケジュール投稿はありません")
                    
                    with col2:
                        st.subheader(f"✅ 実行済み ({len(completed_posts)}件)")
                        if completed_posts:
                            for post in completed_posts[:5]:  # 最新5件のみ表示
                                with st.container():
                                    scheduled_at = datetime.datetime.strptime(post['scheduled_at'], '%Y-%m-%d %H:%M:%S')
                                    sent_at = post['sent_at']
                                    
                                    st.success(post['content'][:100] + "...")
                                    st.caption(f"📅 予定: {scheduled_at.strftime('%m-%d %H:%M')} | ✅ 実行: {sent_at}")
                                    st.markdown("---")
                            
                            if len(completed_posts) > 5:
                                st.caption(f"...他 {len(completed_posts) - 5}件の実行済み投稿")
                        else:
                            st.info("実行済みのスケジュール投稿はありません")
                
                else:
                    st.info("スケジュール投稿はまだありません。")
                
                # スケジュール投稿の説明
                st.markdown("---")
                st.markdown("""
                **💡 スケジュール投稿について**
                - 承認済みタブで将来の日時を設定して投稿すると、自動的にスケジュール投稿に登録されます
                - Cloud Functionsが5分間隔で実行時刻をチェックし、自動投稿します
                - 実行済みの投稿は「送信済み」タブでも確認できます
                """)

            with tab_retweet:
                st.markdown("### 🔄 リツイート・引用ツイート予約")
                
                # リツイート設定確認（オプション）
                retweet_config = get_cast_sheets_config(selected_cast_id, 'retweet')
                if retweet_config:
                    st.success(f"✅ Google Sheets設定済み: {retweet_config['sheet_name']}")
                else:
                    st.info("💡 Google Sheets設定は任意です。設定すると送信先オプションが追加されます。")
                    
                # リツイート予約フォーム（Google Sheets設定に関係なく使用可能）
                with st.form("retweet_form"):
                    st.markdown("#### 📝 リツイート予約作成")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        tweet_id = st.text_input(
                            "🆔 ツイートID", 
                            placeholder="1234567890123456789",
                            help="https://twitter.com/user/status/【ここがツイートID】"
                        )
                    
                    with col2:
                        default_dt = datetime.datetime.now(JST) + datetime.timedelta(minutes=10)
                        exec_date = st.date_input(
                            "⏰ 実行日",
                            value=default_dt.date(),
                            help="リツイートを実行する日付"
                        )
                        exec_time = st.time_input(
                            "⏰ 実行時刻",
                            value=default_dt.time(),
                            help="リツイートを実行する時刻"
                        )
                        # JSTタイムゾーン付きのdatetimeオブジェクトを作成
                        execution_datetime = datetime.datetime.combine(exec_date, exec_time).replace(tzinfo=JST)
                    
                    comment = st.text_area(
                        "💬 コメント（引用ツイート用）",
                        placeholder="コメントを入力すると引用ツイートになります。空欄の場合は通常のリツイートです。",
                        help="コメントありの場合は引用ツイート、なしの場合は通常のリツイート"
                    )
                    
                    # 送信先選択オプション（Google Sheets設定により変動）
                    if retweet_config:
                        # Google Sheets設定がある場合は両方のオプション
                        destination = st.radio(
                            "📤 送信先選択",
                            ["Cloud Functions（X API直接・標準）", "Google Sheets（レート制限なし・安定）"],
                            index=0,
                            help="Cloud Functions: X API直接、Free Tier制限50回/24h | Google Sheets: GAS経由、レート制限なし、安定動作"
                        )
                    else:
                        # Google Sheets設定がない場合はCloud Functionsのみ
                        st.info("📤 送信先: Cloud Functions（X API直接）")
                        destination = "Cloud Functions（X API直接・標準）"
                    
                    if st.form_submit_button("📅 リツイート予約を作成", type="primary"):
                        if tweet_id:
                            if retweet_config and destination.startswith("Google Sheets"):
                                # Google Sheets送信（設定がある場合のみ）
                                success, message = send_retweet_to_google_sheets(
                                    selected_cast_id, 
                                    tweet_id, 
                                    comment, 
                                    execution_datetime
                                )
                            else:
                                # Cloud Functions直接送信（標準・常に利用可能）
                                success, message = save_retweet_to_database(
                                    selected_cast_id,
                                    tweet_id,
                                    comment,
                                    execution_datetime
                                )
                            
                            if success:
                                st.success(f"✅ {message}")
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
                        else:
                            st.error("⚠️ ツイートIDを入力してください")
                
                st.markdown("---")
                st.markdown("#### 📋 予約済みリツイート一覧")
                
                # Cloud Functions予約とGoogle Sheets予約を分けて表示
                if retweet_config:
                    # Google Sheets設定がある場合は2列表示
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("##### 🤖 Cloud Functions予約")
                        display_retweet_schedules(selected_cast_id)
                    
                    with col2:
                        st.markdown("##### 📊 Google Sheets予約")
                        st.success("✅ GAS経由でレート制限なし・安定動作中")
                        st.info("実際の予約状況は設定したGoogle Sheetsで確認できます。")
                else:
                    # Google Sheets設定がない場合はCloud Functionsのみ
                    st.markdown("##### 🤖 Cloud Functions予約")
                    display_retweet_schedules(selected_cast_id)
                    st.info("💡 Google Sheets設定を追加すると、レート制限なしの安定した予約オプションが利用できます。")
                
                # Google Sheetsリンク（設定がある場合のみ）
                if retweet_config and st.button("📊 Google Sheetsを開く"):
                    if 'spreadsheet_id' in retweet_config:
                        sheets_url = f"https://docs.google.com/spreadsheets/d/{retweet_config['spreadsheet_id']}"
                        st.markdown(f"[📊 Google Sheetsを開く]({sheets_url})")
                    else:
                        st.error("スプレッドシートIDが設定されていません")

    elif page == "一斉指示":
        st.title("📣 一斉指示（キャンペーン）")
        casts = execute_query("SELECT id, name, nickname FROM casts ORDER BY name", fetch="all")
        if not casts:
            st.warning("キャスト未登録です。「キャスト管理」で作成してください。"); st.stop()
        
        # キャスト表示名を「name（nickname）」形式で作成
        cast_options = {}
        cast_display_options = []
        for cast in casts:
            display_name = f"{cast['name']}（{cast['nickname']}）" if cast['nickname'] else cast['name']
            cast_options[display_name] = cast['id']
            cast_display_options.append(display_name)
        
        selected_cast_names = st.multiselect("対象キャストを選択（複数可）", cast_display_options, default=cast_display_options)
        st.markdown("---")
        with st.form(key="campaign_form"):
            st.subheader("指示内容")
            campaign_placeholder = get_app_setting("campaign_placeholder", "例：「グッチセール」というキーワードと、URL「https://gucci.com/sale」を必ず文末に入れて、セールをお知らせする投稿を作成してください。")
            campaign_instruction = st.text_area("具体的な指示内容*", placeholder=campaign_placeholder)
            default_char_limit = int(get_app_setting("default_char_limit", "140"))
            char_limit = st.number_input("文字数（以内）", min_value=20, max_value=300, value=default_char_limit)
            if st.form_submit_button("選択したキャスト全員に投稿を生成させる", type="primary"):
                if not selected_cast_names:
                    st.error("対象キャストを1名以上選択してください。")
                elif not campaign_instruction:
                    st.error("具体的な指示内容を入力してください。")
                elif st.session_state.get('gemini_model'):
                    total_casts = len(selected_cast_names)
                    progress_bar = st.progress(0, text="生成を開始します...")
                    for i, cast_name in enumerate(selected_cast_names):
                        cast_id = cast_options[cast_name]
                        progress_bar.progress((i + 1) / total_casts, text=f"キャスト「{cast_name}」の投稿を生成中... ({i+1}/{total_casts})")
                        cast_details_row = execute_query(f"SELECT * FROM casts WHERE id = ?", (cast_id,), fetch="one")
                        cast_details = dict(cast_details_row) if cast_details_row else None
                        if cast_details:
                            persona_sheet = format_persona(cast_id, cast_details)
                            prompt = f"""# ペルソナ\n{persona_sheet}\n\n# 特別な指示\n{campaign_instruction}\n\n# ルール\nSNS投稿を**{char_limit}文字以内**で生成。"""
                            try:
                                response = safe_generate_content(st.session_state.gemini_model, prompt)
                                generated_text = clean_generated_content(response.text)
                                created_at = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                                theme = f"一斉指示：{campaign_instruction[:20]}..."
                                execute_query("INSERT INTO posts (cast_id, created_at, content, theme) VALUES (?, ?, ?, ?)", (cast_id, created_at, generated_text, theme))
                                time.sleep(5)
                            except Exception as e:
                                st.warning(f"キャスト「{cast_name}」の生成中にエラーが発生しました: {e}")
                                continue
                    st.success("すべての一斉指示投稿の生成が完了しました！「投稿管理」ページの「投稿案」タブで確認・チューニングしてください。")
                    st.balloons()
                else:
                    st.error("AIモデルの読み込みに失敗しているため、投稿を生成できません。")

    elif page == "キャスト管理":
        st.title("👤 キャスト管理")
        
        # 成功メッセージの表示（全体共通）
        if "cast_import_message" in st.session_state:
            msg_type, msg_content = st.session_state.cast_import_message
            if msg_type == "success":
                st.success(msg_content)
            elif msg_type == "warning":
                st.warning(msg_content)
            elif msg_type == "error":
                st.error(msg_content)
            del st.session_state.cast_import_message
        
        # フィールド管理タブを追加
        individual_tab, csv_tab, field_tab, ai_gen_tab = st.tabs(["👤 個別管理", "📊 CSV管理", "⚙️ フィールド管理", "🤖 AI自動生成"])
        
        with field_tab:
            st.header("キャスト項目の管理")
            st.markdown("キャストプロフィールの項目を動的に追加・削除できます。")
            
            # 新しいフィールドの追加
            with st.expander("🆕 新しい項目を追加", expanded=False):
                with st.form("add_custom_field"):
                    col1, col2 = st.columns(2)
                    new_field_name = col1.text_input("項目ID（英数字のみ）", placeholder="例: favorite_food")
                    new_display_name = col2.text_input("表示名", placeholder="例: 好きな食べ物")
                    
                    col3, col4 = st.columns(2)
                    field_type = col3.selectbox("入力タイプ", ["text", "textarea"], format_func=lambda x: "テキスト入力" if x == "text" else "長文入力")
                    is_required = col4.checkbox("必須項目")
                    
                    placeholder = st.text_input("プレースホルダー", placeholder="例: ラーメン、寿司など")
                    
                    if st.form_submit_button("項目を追加", type="primary"):
                        if new_field_name and new_display_name:
                            # 英数字とアンダースコアのみ許可
                            import re
                            if re.match("^[a-zA-Z0-9_]+$", new_field_name):
                                # カスタムフィールドテーブルに追加
                                max_order = execute_query("SELECT MAX(sort_order) as max_order FROM custom_fields", fetch="one")
                                next_order = (max_order['max_order'] or 0) + 1
                                
                                result = execute_query(
                                    "INSERT INTO custom_fields (field_name, display_name, field_type, placeholder, is_required, sort_order) VALUES (?, ?, ?, ?, ?, ?)",
                                    (new_field_name, new_display_name, field_type, placeholder, 1 if is_required else 0, next_order)
                                )
                                
                                if result is not False:
                                    # castsテーブルに列を追加
                                    if add_column_to_casts_table(new_field_name):
                                        st.success(f"項目「{new_display_name}」を追加しました！")
                                        st.rerun()
                            else:
                                st.error("項目IDは英数字とアンダースコア(_)のみ使用できます。")
                        else:
                            st.error("項目IDと表示名は必須です。")
            
            # 既存フィールドの表示と削除
            st.subheader("登録済み項目一覧")
            
            # デフォルトフィールド
            st.markdown("### 🔒 標準項目（削除不可）")
            default_field_names = {
                "name": "ユーザー名 (@username)", "nickname": "名前 (表示名)", "age": "年齢", "birthday": "誕生日",
                "birthplace": "出身地", "appearance": "外見", "personality": "性格", "strength": "長所",
                "weakness": "短所", "first_person": "一人称", "speech_style": "口調", "catchphrase": "口癖",
                "customer_interaction": "接客スタイル", "occupation": "職業", "hobby": "趣味", "likes": "好きなもの",
                "dislikes": "嫌いなもの", "holiday_activity": "休日の過ごし方", "dream": "夢", "reason_for_job": "仕事の理由",
                "secret": "秘密", "allowed_categories": "許可カテゴリ"
            }
            
            for field, display in default_field_names.items():
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.text(f"📌 {display}")
                col2.text(f"ID: {field}")
                col3.text("🔒 標準")
            
            # カスタムフィールド
            custom_fields = execute_query("SELECT * FROM custom_fields ORDER BY sort_order", fetch="all")
            if custom_fields:
                st.markdown("### ⚙️ カスタム項目")
                for field in custom_fields:
                    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                    col1.text(f"🔧 {field['display_name']}")
                    col2.text(f"ID: {field['field_name']}")
                    col3.text("✅ 必須" if field['is_required'] else "⭕ 任意")
                    
                    if col4.button("🗑️ 削除", key=f"delete_field_{field['id']}"):
                        # カスタムフィールドを削除
                        execute_query("DELETE FROM custom_fields WHERE id = ?", (field['id'],))
                        # テーブルから列を削除
                        if remove_column_from_casts_table(field['field_name']):
                            st.success(f"項目「{field['display_name']}」を削除しました！")
                            st.rerun()
            else:
                st.info("カスタム項目はまだ追加されていません。")
        
        with csv_tab:
            st.subheader("一括管理（CSV）")
            
            with st.expander("CSVでのインポート/エクスポートはこちら", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    uploaded_file = st.file_uploader("CSVファイルをアップロード（1行目:ID、2行目:項目説明、3行目～:データ）", type="csv")
                    if uploaded_file is not None:
                        try:
                            # 動的フィールドを含めた全フィールドを取得
                            all_fields = get_dynamic_persona_fields()
                            
                            # まず1行目（列名）を読み取る
                            uploaded_file.seek(0)  # ファイルポインタをリセット
                            header_df = pandas_lib.read_csv(uploaded_file, nrows=1, dtype=str)
                            column_names = header_df.columns.tolist()
                            
                            # 3行目からデータを読み込み（skiprows=2で1行目と2行目をスキップ、1行目の列名を使用）
                            uploaded_file.seek(0)  # ファイルポインタをリセット
                            df = pandas_lib.read_csv(uploaded_file, skiprows=2, names=column_names, dtype=str, keep_default_na=False).fillna("")
                            
                            if 'id' in df.columns:
                                df = df.drop(columns=['id'])
                            
                            # 不足している列を確認
                            missing_columns = set(all_fields) - set(df.columns)
                            if missing_columns:
                                st.error(f"CSVの列が不足しています。不足している列: {', '.join(missing_columns)}")
                                st.error(f"必要な列: {', '.join(all_fields)}")
                            else:
                                success_count = 0
                                update_count = 0
                                error_rows = []
                                
                                for index, row in df.iterrows():
                                    cast_data = row.to_dict()
                                    name = cast_data.get("name")
                                    if not name:
                                        error_rows.append(f"行{index+3}: キャスト名が空です")
                                        continue
                                    
                                    existing = execute_query("SELECT id FROM casts WHERE name = ?", (name,), fetch="one")
                                    if existing:
                                        set_clause = ", ".join([f"{key} = ?" for key in cast_data.keys() if key != 'name'])
                                        params = tuple(val for key, val in cast_data.items() if key != 'name') + (name,)
                                        result = execute_query(f"UPDATE casts SET {set_clause} WHERE name = ?", params)
                                        if result is not False:
                                            update_count += 1
                                    else:
                                        columns = ', '.join(cast_data.keys())
                                        placeholders = ', '.join(['?'] * len(cast_data))
                                        values = tuple(cast_data.values())
                                        result = execute_query(f"INSERT INTO casts ({columns}) VALUES ({placeholders})", values)
                                        if result is not False:
                                            success_count += 1
                                
                                # 結果の表示
                                total_processed = success_count + update_count
                                if total_processed > 0:
                                    if error_rows:
                                        message = f"{success_count}件の新規キャストを追加、{update_count}件のキャストを更新しました。{len(error_rows)}件のエラーがありました。"
                                        st.warning(message)
                                        st.write("**エラー詳細:**")
                                        for error in error_rows[:5]:  # 最初の5件のエラーを表示
                                            st.write(f"• {error}")
                                    else:
                                        message = f"{success_count}件の新規キャストを追加、{update_count}件のキャストを更新しました。"
                                        st.success(message)
                                    st.info("「一覧表示」タブで結果を確認できます。")
                                elif error_rows:
                                    # 処理されたデータがない場合はエラーメッセージのみ表示
                                    st.error(f"インポートできませんでした。{len(error_rows)}件のエラーがあります。")
                                    for error in error_rows[:3]:  # 最初の3件のエラーのみ表示
                                        st.write(f"• {error}")
                                else:
                                    st.info("処理するデータがありませんでした。")
                                        
                        except Exception as e: 
                            st.error(f"CSVの処理中にエラーが発生しました: {e}")
                with c2:
                    all_casts_data = execute_query("SELECT * FROM casts", fetch="all")
                    if all_casts_data:
                        df = pandas_lib.DataFrame([dict(row) for row in all_casts_data])
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button("既存キャストをCSVでエクスポート", data=csv, file_name='casts_export.csv', mime='text/csv', use_container_width=True)
        
        with individual_tab:
            st.header("キャストの個別管理")
            tab_create, tab_edit, tab_list = st.tabs(["新しいキャストの作成", "既存キャストの編集・削除", "一覧表示"])
        
            cat_rows = execute_query("SELECT name FROM situation_categories ORDER BY name", fetch="all")
            category_options = [row['name'] for row in cat_rows] if cat_rows else []
            
            group_rows = execute_query("SELECT id, name FROM groups ORDER BY name", fetch="all")
            group_options = {row['name']: row['id'] for row in group_rows} if group_rows else {}
            
            # カスタムフィールドを取得
            custom_fields = execute_query("SELECT * FROM custom_fields ORDER BY sort_order", fetch="all")

            with tab_create:
                with st.form(key="new_cast_form"):
                    tab_names = ["1. 基本情報", "2. 性格・話し方", "3. 背景ストーリー", "4. 許可カテゴリ", "5. 所属グループ"]
                    if custom_fields:
                        tab_names.append("6. カスタム項目")
                    form_tabs = st.tabs(tab_names)
                    with form_tabs[0]:
                        c1, c2 = st.columns(2)
                        # プレースホルダーを設定から取得
                        cast_name_ph = get_app_setting("cast_name_placeholder", "@shiori_hoshino")
                        cast_nickname_ph = get_app_setting("cast_nickname_placeholder", "星野 詩織")
                        cast_age_ph = get_app_setting("cast_age_placeholder", "21歳")
                        cast_birthday_ph = get_app_setting("cast_birthday_placeholder", "10月26日")
                        cast_birthplace_ph = get_app_setting("cast_birthplace_placeholder", "神奈川県")
                        cast_appearance_ph = get_app_setting("cast_appearance_placeholder", "黒髪ロングで物静かな雰囲気。古着のワンピースをよく着ている。")
                        
                        new_name = c1.text_input("ユーザー名*", placeholder=cast_name_ph); new_nickname = c2.text_input("名前（表示名）", placeholder=cast_nickname_ph)
                        new_age = c1.text_input("年齢", placeholder=cast_age_ph); new_birthday = c2.text_input("誕生日", placeholder=cast_birthday_ph)
                        new_birthplace = c1.text_input("出身地", placeholder=cast_birthplace_ph); new_appearance = st.text_area("外見の特徴", placeholder=cast_appearance_ph)
                    with form_tabs[1]:
                        c1, c2, c3 = st.columns(3)
                        # プレースホルダーを設定から取得
                        cast_personality_ph = get_app_setting("cast_personality_placeholder", "物静かで穏やかな聞き上手")
                        cast_strength_ph = get_app_setting("cast_strength_placeholder", "人の話に深く共感できる")
                        cast_weakness_ph = get_app_setting("cast_weakness_placeholder", "少し人見知り")
                        cast_first_person_ph = get_app_setting("cast_first_person_placeholder", "私")
                        cast_speech_style_ph = get_app_setting("cast_speech_style_placeholder", "です・ます調の丁寧な言葉遣い")
                        cast_catchphrase_ph = get_app_setting("cast_catchphrase_placeholder", "「なんだか、素敵ですね」")
                        
                        new_personality = c1.text_input("性格（一言で）", placeholder=cast_personality_ph); new_strength = c2.text_input("長所", placeholder=cast_strength_ph)
                        new_weakness = c3.text_input("短所", placeholder=cast_weakness_ph); new_first_person = c1.text_input("一人称", placeholder=cast_first_person_ph)
                        new_speech_style = c2.text_area("口調・語尾", placeholder=cast_speech_style_ph); new_catchphrase = c3.text_input("口癖", placeholder=cast_catchphrase_ph)
                        cast_customer_interaction_ph = get_app_setting("cast_customer_interaction_placeholder", "お客様の心に寄り添うように、静かに話を聞く")
                        new_customer_interaction = st.text_area("お客様への接し方", placeholder=cast_customer_interaction_ph)
                    with form_tabs[2]:
                        c1, c2 = st.columns(2)
                        # プレースホルダーを設定から取得
                        cast_occupation_ph = get_app_setting("cast_occupation_placeholder", "文学部の女子大生")
                        cast_hobby_ph = get_app_setting("cast_hobby_placeholder", "読書、フィルムカメラ、古い喫茶店巡り")
                        
                        new_occupation = c1.text_input("職業／学業", placeholder=cast_occupation_ph); new_hobby = c2.text_area("趣味や特技", placeholder=cast_hobby_ph)
                        # プレースホルダーを設定から取得
                        cast_likes_ph = get_app_setting("cast_likes_placeholder", "雨の日の匂い、万年筆のインク")
                        cast_dislikes_ph = get_app_setting("cast_dislikes_placeholder", "大きな音、人混み")
                        cast_holiday_activity_ph = get_app_setting("cast_holiday_activity_placeholder", "一日中家で本を読んでいるか、目的もなく電車に乗る")
                        cast_dream_ph = get_app_setting("cast_dream_placeholder", "自分の言葉で、誰かの心を動かす物語を紡ぐこと")
                        cast_reason_for_job_ph = get_app_setting("cast_reason_for_job_placeholder", "様々な人の物語に触れたいから")
                        cast_secret_ph = get_app_setting("cast_secret_placeholder", "実は、大のSF小説好き")
                        
                        new_likes = c1.text_area("好きなもの", placeholder=cast_likes_ph); new_dislikes = c2.text_area("嫌いなもの", placeholder=cast_dislikes_ph)
                        new_holiday_activity = st.text_area("休日の過ごし方", placeholder=cast_holiday_activity_ph); new_dream = st.text_area("将来の夢", placeholder=cast_dream_ph)
                        new_reason_for_job = st.text_area("なぜこの仕事をしているのか", placeholder=cast_reason_for_job_ph); new_secret = st.text_area("ちょっとした秘密", placeholder=cast_secret_ph)
                    with form_tabs[3]:
                        st.info("このキャストが投稿を生成する際に使用できるシチュエーションのカテゴリを選択してください。")
                        if not category_options:
                            st.warning("カテゴリが登録されていません。「カテゴリ管理」で先にカテゴリを作成してください。")
                            new_allowed_categories = []
                        else:
                            new_allowed_categories = st.multiselect("許可するカテゴリ", category_options, key="new_cat_select")
                    with form_tabs[4]:
                        st.info("このキャストが所属するグループを選択してください。グループの共通設定がペルソナに追加されます。")
                        new_groups = st.multiselect("所属するグループ", list(group_options.keys()), key="new_group_select")
                
                    # カスタムフィールドのタブを追加
                    if custom_fields:
                        with form_tabs[5]:  # 6番目のタブとして追加
                            st.info("追加されたカスタム項目を入力してください。")
                            for field in custom_fields:
                                if field['field_type'] == 'textarea':
                                    locals()[f"new_{field['field_name']}"] = st.text_area(
                                        field['display_name'] + (" *" if field['is_required'] else ""),
                                        placeholder=field['placeholder']
                                    )
                                else:
                                    locals()[f"new_{field['field_name']}"] = st.text_input(
                                        field['display_name'] + (" *" if field['is_required'] else ""),
                                        placeholder=field['placeholder']
                                    )
                    
                    if st.form_submit_button(label="新しいキャストを作成", type="primary"):
                        if new_name:
                            # 動的フィールドを含む全フィールドでcast_dataを作成
                            all_fields = get_dynamic_persona_fields()
                            form_data = locals(); cast_data = {field: form_data.get(f"new_{field}", "") for field in all_fields}
                            cast_data['allowed_categories'] = ",".join(new_allowed_categories)
                            columns = ', '.join(cast_data.keys()); placeholders = ', '.join(['?'] * len(cast_data)); values = tuple(cast_data.values())
                            new_cast_id = execute_query(f"INSERT INTO casts ({columns}) VALUES ({placeholders})", values)
                            if new_cast_id:
                                for group_name in new_groups:
                                    group_id = group_options.get(group_name)
                                    execute_query("INSERT INTO cast_groups (cast_id, group_id) VALUES (?, ?)", (new_cast_id, group_id))
                                st.session_state.cast_import_message = ("success", f"新しいキャスト「{new_name}」を作成しました！")
                                st.rerun()
                        else: st.error("キャスト名は必須項目です。")

        with tab_edit:
            casts = execute_query("SELECT id, name, nickname FROM casts ORDER BY name", fetch="all")
            if not casts:
                 st.info("編集できるキャストがまだいません。")
            else:
                # キャスト表示名を「name（nickname）」形式で作成
                cast_display_options = []
                cast_name_mapping = {}
                for cast in casts:
                    display_name = f"{cast['name']}（{cast['nickname']}）" if cast['nickname'] else cast['name']
                    cast_display_options.append(display_name)
                    cast_name_mapping[display_name] = cast['name']
                
                selected_cast_display_edit = st.selectbox("編集するキャストを選択", cast_display_options, key="edit_cast_select")
                selected_cast_name_edit = cast_name_mapping[selected_cast_display_edit]
                if selected_cast_name_edit:
                    cast_id_to_edit = next((c['id'] for c in casts if c['name'] == selected_cast_name_edit), None)
                    cast_data_to_edit_row = execute_query(f"SELECT * FROM casts WHERE id = ?", (cast_id_to_edit,), fetch="one")
                    cast_data_to_edit = dict(cast_data_to_edit_row) if cast_data_to_edit_row else None
                    if cast_data_to_edit:
                        with st.form(key="edit_cast_form"):
                            edit_tab_names = ["基本情報", "性格・話し方", "背景ストーリー", "許可カテゴリ", "所属グループ"]
                            if custom_fields:
                                edit_tab_names.append("カスタム項目")
                            edit_tabs = st.tabs(edit_tab_names)
                            t1, t2, t3, t4, t5 = edit_tabs[:5]
                            with t1:
                                c1, c2 = st.columns(2)
                                # プレースホルダーを設定から取得
                                cast_name_ph = get_app_setting("cast_name_placeholder", "星野 詩織")
                                cast_nickname_ph = get_app_setting("cast_nickname_placeholder", "しおりん")
                                cast_age_ph = get_app_setting("cast_age_placeholder", "21歳")
                                cast_appearance_ph = get_app_setting("cast_appearance_placeholder", "黒髪ロングで物静かな雰囲気")
                                cast_birthday_ph = get_app_setting("cast_birthday_placeholder", "10月26日")
                                cast_birthplace_ph = get_app_setting("cast_birthplace_placeholder", "神奈川県")
                                
                                edit_name = c1.text_input("ユーザー名*", value=cast_data_to_edit.get('name', ''), placeholder=cast_name_ph)
                                edit_nickname = c2.text_input("名前（表示名）", value=cast_data_to_edit.get('nickname', ''), placeholder=cast_nickname_ph); edit_age = c1.text_input("年齢", value=cast_data_to_edit.get('age', ''), placeholder=cast_age_ph)
                                edit_appearance = st.text_area("外見の特徴", value=cast_data_to_edit.get('appearance', ''), placeholder=cast_appearance_ph); edit_birthday = c1.text_input("誕生日", value=cast_data_to_edit.get('birthday', ''), placeholder=cast_birthday_ph)
                                edit_birthplace = c2.text_input("出身地", value=cast_data_to_edit.get('birthplace', ''), placeholder=cast_birthplace_ph)
                            with t2:
                                c1, c2, c3 = st.columns(3)
                                # プレースホルダーを設定から取得
                                cast_personality_ph = get_app_setting("cast_personality_placeholder", "物静かで穏やかな聞き上手")
                                cast_strength_ph = get_app_setting("cast_strength_placeholder", "人の話に深く共感できる")
                                cast_weakness_ph = get_app_setting("cast_weakness_placeholder", "少し人見知り")
                                cast_first_person_ph = get_app_setting("cast_first_person_placeholder", "私")
                                cast_speech_style_ph = get_app_setting("cast_speech_style_placeholder", "です・ます調の丁寧な言葉遣い")
                                cast_catchphrase_ph = get_app_setting("cast_catchphrase_placeholder", "「なんだか、素敵ですね」")
                                cast_customer_interaction_ph = get_app_setting("cast_customer_interaction_placeholder", "お客様の心に寄り添うように、静かに話を聞く")
                                
                                edit_personality = c1.text_input("性格（一言で）", value=cast_data_to_edit.get('personality', ''), placeholder=cast_personality_ph); edit_strength = c2.text_input("長所", value=cast_data_to_edit.get('strength', ''), placeholder=cast_strength_ph)
                                edit_weakness = c3.text_input("短所", value=cast_data_to_edit.get('weakness', ''), placeholder=cast_weakness_ph); edit_first_person = c1.text_input("一人称", value=cast_data_to_edit.get('first_person', ''), placeholder=cast_first_person_ph)
                                edit_speech_style = c2.text_area("口調・語尾", value=cast_data_to_edit.get('speech_style', ''), placeholder=cast_speech_style_ph); edit_catchphrase = c3.text_input("口癖", value=cast_data_to_edit.get('catchphrase', ''), placeholder=cast_catchphrase_ph)
                                edit_customer_interaction = st.text_area("お客様への接し方", value=cast_data_to_edit.get('customer_interaction', ''), placeholder=cast_customer_interaction_ph)
                            with t3:
                                c1, c2 = st.columns(2)
                                # プレースホルダーを設定から取得
                                cast_occupation_ph = get_app_setting("cast_occupation_placeholder", "文学部の女子大生")
                                cast_hobby_ph = get_app_setting("cast_hobby_placeholder", "読書、フィルムカメラ、古い喫茶店巡り")
                                cast_likes_ph = get_app_setting("cast_likes_placeholder", "雨の日の匂い、万年筆のインク")
                                cast_dislikes_ph = get_app_setting("cast_dislikes_placeholder", "大きな音、人混み")
                                cast_holiday_activity_ph = get_app_setting("cast_holiday_activity_placeholder", "一日中家で本を読んでいるか、目的もなく電車に乗る")
                                cast_dream_ph = get_app_setting("cast_dream_placeholder", "自分の言葉で、誰かの心を動かす物語を紡ぐこと")
                                cast_reason_for_job_ph = get_app_setting("cast_reason_for_job_placeholder", "様々な人の物語に触れたいから")
                                cast_secret_ph = get_app_setting("cast_secret_placeholder", "実は、大のSF小説好き")
                                
                                edit_occupation = c1.text_input("職業／学業", value=cast_data_to_edit.get('occupation', ''), placeholder=cast_occupation_ph); edit_hobby = c2.text_area("趣味や特技", value=cast_data_to_edit.get('hobby', ''), placeholder=cast_hobby_ph)
                                edit_likes = c1.text_area("好きなもの", value=cast_data_to_edit.get('likes', ''), placeholder=cast_likes_ph); edit_dislikes = c2.text_area("嫌いなもの", value=cast_data_to_edit.get('dislikes', ''), placeholder=cast_dislikes_ph)
                                edit_holiday_activity = st.text_area("休日の過ごし方", value=cast_data_to_edit.get('holiday_activity', ''), placeholder=cast_holiday_activity_ph); edit_dream = st.text_area("将来の夢", value=cast_data_to_edit.get('dream', ''), placeholder=cast_dream_ph)
                                edit_reason_for_job = st.text_area("なぜこの仕事をしているのか", value=cast_data_to_edit.get('reason_for_job', ''), placeholder=cast_reason_for_job_ph); edit_secret = st.text_area("ちょっとした秘密", value=cast_data_to_edit.get('secret', ''), placeholder=cast_secret_ph)
                            with t4:
                                allowed_categories_str = cast_data_to_edit.get('allowed_categories')
                                current_allowed = allowed_categories_str.split(',') if allowed_categories_str else []
                                
                                if not category_options:
                                    st.warning("カテゴリが登録されていません。「カテゴリ管理」で先にカテゴリを作成してください。")
                                    edit_allowed_categories = []
                                else:
                                    # 現在のカテゴリオプションに存在するもののみをデフォルト値として使用
                                    valid_current_allowed = [cat for cat in current_allowed if cat in category_options]
                                    if current_allowed and not valid_current_allowed:
                                        st.warning(f"以前設定されていたカテゴリ「{', '.join(current_allowed)}」が削除されています。新しくカテゴリを選択してください。")
                                    edit_allowed_categories = st.multiselect("許可するカテゴリ", category_options, default=valid_current_allowed)
                            with t5:
                                current_group_rows = execute_query("SELECT g.name FROM groups g JOIN cast_groups cg ON g.id = cg.group_id WHERE cg.cast_id = ?", (cast_id_to_edit,), fetch="all")
                                current_groups = [row['name'] for row in current_group_rows] if current_group_rows else []
                                edit_groups = st.multiselect("所属するグループ", list(group_options.keys()), default=current_groups)
                            
                            # カスタムフィールドの編集タブ
                            if custom_fields and len(edit_tabs) > 5:
                                with edit_tabs[5]:
                                    st.info("カスタム項目を編集してください。")
                                    for field in custom_fields:
                                        current_value = cast_data_to_edit.get(field['field_name'], '')
                                        if field['field_type'] == 'textarea':
                                            locals()[f"edit_{field['field_name']}"] = st.text_area(
                                                field['display_name'] + (" *" if field['is_required'] else ""),
                                                value=current_value,
                                                placeholder=field['placeholder']
                                            )
                                        else:
                                            locals()[f"edit_{field['field_name']}"] = st.text_input(
                                                field['display_name'] + (" *" if field['is_required'] else ""),
                                                value=current_value,
                                                placeholder=field['placeholder']
                                            )
                            
                            if st.form_submit_button(label="この内容に更新する"):
                                if edit_name:
                                    # 動的フィールドを含む全フィールドで更新データを作成
                                    all_fields = get_dynamic_persona_fields()
                                    form_data = locals(); updated_data = {field: form_data.get(f"edit_{field}", "") for field in all_fields}
                                    updated_data['allowed_categories'] = ",".join(edit_allowed_categories)
                                    set_clause = ", ".join([f"{key} = ?" for key in updated_data.keys()]); params = tuple(updated_data.values()) + (cast_id_to_edit,)
                                    execute_query(f"UPDATE casts SET {set_clause} WHERE id = ?", params)
                                    execute_query("DELETE FROM cast_groups WHERE cast_id = ?", (cast_id_to_edit,))
                                    for group_name in edit_groups:
                                        group_id = group_options.get(group_name)
                                        execute_query("INSERT INTO cast_groups (cast_id, group_id) VALUES (?, ?)", (cast_id_to_edit, group_id))
                                    st.success(f"「{selected_cast_name_edit}」のプロフィールを更新しました！"); st.rerun()
                                else: st.error("キャスト名は必須です。")
                        
                        # X API 設定セクション
                        st.markdown("---")
                        st.subheader("🐦 X (Twitter) API 設定")
                        
                        # 現在の認証情報を取得
                        current_credentials = get_cast_x_credentials(cast_id_to_edit)
                        
                        if current_credentials:
                            st.success(f"✅ X API認証情報が設定済みです")
                            col1, col2 = st.columns(2)
                            with col1:
                                twitter_username = current_credentials['twitter_username'] if current_credentials['twitter_username'] else '未取得'
                                st.info(f"🔗 Twitterアカウント: @{twitter_username}")
                            with col2:
                                updated_at = current_credentials['updated_at'] if current_credentials['updated_at'] else '不明'
                                st.info(f"📅 最終更新: {updated_at}")
                            
                            # 認証テストボタン
                            if st.button("🔍 認証状況を確認", key=f"test_auth_{cast_id_to_edit}"):
                                with st.spinner("認証情報を確認中..."):
                                    try:
                                        # キャッシュされたクライアントを削除して再認証
                                        if cast_id_to_edit in x_poster.cast_clients:
                                            del x_poster.cast_clients[cast_id_to_edit]
                                        
                                        success, message, user_data = x_poster.setup_cast_credentials(
                                            cast_id_to_edit,
                                            current_credentials['api_key'],
                                            current_credentials['api_secret'], 
                                            current_credentials['bearer_token'],
                                            current_credentials['access_token'],
                                            current_credentials['access_token_secret']
                                        )
                                        
                                        if success:
                                            st.success(message)
                                            if user_data:
                                                # アカウント情報を更新
                                                save_cast_x_credentials(
                                                    cast_id_to_edit,
                                                    current_credentials['api_key'],
                                                    current_credentials['api_secret'],
                                                    current_credentials['bearer_token'], 
                                                    current_credentials['access_token'],
                                                    current_credentials['access_token_secret'],
                                                    user_data.username,
                                                    str(user_data.id)
                                                )
                                                st.info(f"✨ アカウント情報を更新: @{user_data.username} ({user_data.name})")
                                        else:
                                            st.error(message)
                                    except Exception as e:
                                        st.error(f"認証確認中にエラーが発生しました: {e}")
                        
                        # 認証情報設定/編集フォーム
                        with st.expander("🔧 X API認証情報の設定/編集", expanded=not bool(current_credentials)):
                            st.info("""
                            **設定手順:**
                            1. [X Developer Portal](https://developer.twitter.com) でアプリを作成
                            2. Read and Write権限を設定
                            3. 以下のキーを取得して入力
                            """)
                            
                            with st.form(f"x_api_form_{cast_id_to_edit}"):
                                x_api_key = st.text_input(
                                    "API Key", 
                                    value=current_credentials.get('api_key', '') if current_credentials else '',
                                    type="password",
                                    help="Consumer Key とも呼ばれます"
                                )
                                x_api_secret = st.text_input(
                                    "API Secret", 
                                    value=current_credentials.get('api_secret', '') if current_credentials else '',
                                    type="password",
                                    help="Consumer Secret とも呼ばれます"
                                )
                                x_bearer_token = st.text_input(
                                    "Bearer Token", 
                                    value=current_credentials.get('bearer_token', '') if current_credentials else '',
                                    type="password"
                                )
                                x_access_token = st.text_input(
                                    "Access Token", 
                                    value=current_credentials.get('access_token', '') if current_credentials else '',
                                    type="password"
                                )
                                x_access_token_secret = st.text_input(
                                    "Access Token Secret", 
                                    value=current_credentials.get('access_token_secret', '') if current_credentials else '',
                                    type="password"
                                )
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.form_submit_button("💾 認証情報を保存", type="primary"):
                                        if all([x_api_key, x_api_secret, x_bearer_token, x_access_token, x_access_token_secret]):
                                            with st.spinner("認証情報を検証中..."):
                                                try:
                                                    # 認証テスト
                                                    success, message, user_data = x_poster.setup_cast_credentials(
                                                        cast_id_to_edit, x_api_key, x_api_secret, x_bearer_token, x_access_token, x_access_token_secret
                                                    )
                                                    
                                                    if success:
                                                        # データベースに保存
                                                        if save_cast_x_credentials(
                                                            cast_id_to_edit, x_api_key, x_api_secret, x_bearer_token, x_access_token, x_access_token_secret,
                                                            user_data.username if user_data else None,
                                                            str(user_data.id) if user_data else None
                                                        ):
                                                            st.success(f"✅ 認証情報を保存しました！")
                                                            if user_data:
                                                                st.info(f"🔗 連携アカウント: @{user_data.username} ({user_data.name})")
                                                            st.rerun()
                                                        else:
                                                            st.error("認証情報の保存に失敗しました")
                                                    else:
                                                        st.error(f"認証に失敗しました: {message}")
                                                except Exception as e:
                                                    st.error(f"認証確認中にエラーが発生しました: {e}")
                                        else:
                                            st.error("すべての項目を入力してください")
                                
                                with col2:
                                    if current_credentials and st.form_submit_button("🗑️ 認証情報を削除", type="secondary"):
                                        if delete_cast_x_credentials(cast_id_to_edit):
                                            st.success("認証情報を削除しました")
                                            st.rerun()
                                        else:
                                            st.error("認証情報の削除に失敗しました")
                        
                        # Google Sheets 設定セクション
                        st.markdown("---")
                        st.subheader("📊 Google Sheets 設定")
                        
                        # 現在のGoogle Sheets設定を取得
                        current_sheets_config = get_cast_sheets_config(cast_id_to_edit)
                        
                        if current_sheets_config:
                            st.success(f"✅ Google Sheets設定が設定済みです")
                            col1, col2 = st.columns(2)
                            with col1:
                                sheets_id = current_sheets_config['spreadsheet_id']
                                display_id = f"{sheets_id[:15]}..." if len(sheets_id) > 15 else sheets_id
                                st.info(f"📋 スプレッドシートID: {display_id}")
                            with col2:
                                updated_at = current_sheets_config['updated_at'] if current_sheets_config['updated_at'] else '不明'
                                st.info(f"📅 最終更新: {updated_at}")
                        else:
                            st.info("⚠️ Google Sheets設定が未設定です")
                        
                        with st.expander("� Google Sheets設定（シンプル版）", expanded=not bool(current_sheets_config)):
                            with st.form(f"sheets_config_form_{cast_id_to_edit}"):
                                st.markdown("""
                                **📊 シンプルGoogle Sheets設定:**
                                - 共通のGoogle認証を使用（`credentials/credentials.json`）
                                - キャスト毎に異なるスプレッドシート・シートを設定可能
                                - 認証は1回のみ、設定は簡単！
                                """)
                                
                                # スプレッドシートID
                                sheets_spreadsheet_id = st.text_input(
                                    "📊 スプレッドシートID", 
                                    value=current_sheets_config['spreadsheet_id'] if current_sheets_config else '',
                                    placeholder="1VPSyQOp0p2U9bPHghP4JZiyePsev2Uoq3nVbbC26VAo",
                                    help="Google SheetsのURLから取得: https://docs.google.com/spreadsheets/d/【ここがID】/edit"
                                )
                                
                                # シート名
                                sheets_sheet_name = st.text_input(
                                    "📄 シート名", 
                                    value=current_sheets_config['sheet_name'] if current_sheets_config else 'Sheet1',
                                    placeholder="投稿メッセージリスト"
                                )
                                
                                st.markdown("""
                                **📝 設定手順:**
                                1. Google Sheetsでスプレッドシートを作成
                                2. URLからスプレッドシートIDをコピー
                                3. シート名を確認（デフォルト: Sheet1）
                                4. 認証は共通ファイル `credentials/credentials.json` を使用
                                
                                **� 利点:**
                                - 認証ファイル設定不要！
                                - 同一Googleアカウントで複数スプレッドシート管理
                                - シンプルで分かりやすい設定
                                """)
                                
                                st.markdown("---")
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.form_submit_button("💾 Google Sheets設定を保存", type="primary"):
                                        if sheets_spreadsheet_id:
                                            if save_cast_sheets_config(
                                                cast_id_to_edit, 
                                                sheets_spreadsheet_id, 
                                                sheets_sheet_name
                                            ):
                                                st.success("✅ Google Sheets設定を保存しました！")
                                                st.rerun()
                                            else:
                                                st.error("❌ 設定の保存に失敗しました")
                                        else:
                                            st.error("⚠️ スプレッドシートIDを入力してください")
                                
                                with col2:
                                    if current_sheets_config and st.form_submit_button("🗑️ Google Sheets設定を削除", type="secondary"):
                                        if delete_cast_sheets_config(cast_id_to_edit):
                                            st.success("✅ Google Sheets設定を削除しました")
                                            st.rerun()
                                        else:
                                            st.error("❌ 設定の削除に失敗しました")
                        
                        # アクション別設定セクション（フォーム外）
                        st.markdown("---")
                        st.markdown("### 🎯 アクション別シート設定")
                        
                        action_types = ['post', 'retweet']
                        action_labels = {
                            'post': '📝 通常投稿',
                            'retweet': '🔄 リツイート・引用ツイート'
                        }
                        
                        for action_type in action_types:
                            with st.expander(f"{action_labels[action_type]} 設定", expanded=False):
                                current_action_config = get_cast_sheets_config(cast_id_to_edit, action_type)
                                
                                # 各アクションごとに独立したフォームを作成
                                with st.form(key=f"form_{action_type}_config"):
                                    col_a1, col_a2 = st.columns(2)
                                    with col_a1:
                                        action_spreadsheet_id = st.text_input(
                                            f"📊 {action_labels[action_type]} スプレッドシートID",
                                            value=current_action_config['spreadsheet_id'] if current_action_config else '',
                                            placeholder="1VPSyQOp0p2U9bPHghP4JZiyePsev2Uoq3nVbbC26VAo"
                                        )
                                    
                                    with col_a2:
                                        action_sheet_name = st.text_input(
                                            f"📄 {action_labels[action_type]} シート名",
                                            value=current_action_config['sheet_name'] if current_action_config else f"{action_type}_sheet",
                                            placeholder=f"{action_type}_sheet"
                                        )
                                    
                                    if st.form_submit_button(f"💾 {action_labels[action_type]}設定を保存", type="secondary"):
                                        if action_spreadsheet_id:
                                            if save_cast_action_sheets_config(
                                                cast_id_to_edit, 
                                                action_type,
                                                action_spreadsheet_id, 
                                                action_sheet_name
                                            ):
                                                st.success(f"✅ {action_labels[action_type]}設定を保存しました！")
                                                st.rerun()
                                            else:
                                                st.error("❌ 設定の保存に失敗しました")
                                        else:
                                            st.error("⚠️ スプレッドシートIDを入力してください")
                        
                        with st.expander("🚨 Danger Zone: キャストの削除", expanded=False):
                            st.warning(f"**警告:** キャスト「{selected_cast_name_edit}」を削除すると、関連するすべての投稿も永久に削除され、元に戻すことはできません。")
                            delete_confirmation = st.text_input(f"削除を確定するには、キャスト名「{selected_cast_name_edit}」を以下に入力してください。")
                            if st.button("このキャストを完全に削除する", type="primary"):
                                if delete_confirmation == selected_cast_name_edit:
                                    execute_query("DELETE FROM posts WHERE cast_id = ?", (cast_id_to_edit,))
                                    execute_query("DELETE FROM cast_groups WHERE cast_id = ?", (cast_id_to_edit,))
                                    execute_query("DELETE FROM casts WHERE id = ?", (cast_id_to_edit,))
                                    st.success(f"キャスト「{selected_cast_name_edit}」を削除しました。"); st.rerun()
                                else: st.error("入力されたキャスト名が一致しません。")
        
        with tab_list:
            st.header("登録済みキャスト一覧")
            all_casts = execute_query("SELECT * FROM casts ORDER BY name", fetch="all")
            if all_casts:
                st.info(f"登録済みキャスト数: {len(all_casts)}件")
                for cast in all_casts:
                    display_name = f"{cast['name']}（{cast['nickname']}）" if cast['nickname'] else cast['name']
                    with st.expander(f"👤 {display_name}", expanded=False):
                        cast_dict = dict(cast)
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**基本情報**")
                            st.write(f"• 名前: {cast_dict.get('name', '')}")
                            st.write(f"• ニックネーム: {cast_dict.get('nickname', '')}")
                            st.write(f"• 年齢: {cast_dict.get('age', '')}")
                            st.write(f"• 誕生日: {cast_dict.get('birthday', '')}")
                            st.write(f"• 出身地: {cast_dict.get('birthplace', '')}")
                            st.write(f"• 外見: {cast_dict.get('appearance', '')}")
                            
                            st.write("**性格・話し方**")
                            st.write(f"• 性格: {cast_dict.get('personality', '')}")
                            st.write(f"• 長所: {cast_dict.get('strength', '')}")
                            st.write(f"• 短所: {cast_dict.get('weakness', '')}")
                            st.write(f"• 一人称: {cast_dict.get('first_person', '')}")
                            st.write(f"• 口調: {cast_dict.get('speech_style', '')}")
                            st.write(f"• 口癖: {cast_dict.get('catchphrase', '')}")
                            st.write(f"• 接客スタイル: {cast_dict.get('customer_interaction', '')}")
                        
                        with col2:
                            st.write("**背景ストーリー**")
                            st.write(f"• 職業: {cast_dict.get('occupation', '')}")
                            st.write(f"• 趣味: {cast_dict.get('hobby', '')}")
                            st.write(f"• 好きなもの: {cast_dict.get('likes', '')}")
                            st.write(f"• 嫌いなもの: {cast_dict.get('dislikes', '')}")
                            st.write(f"• 休日の過ごし方: {cast_dict.get('holiday_activity', '')}")
                            st.write(f"• 夢: {cast_dict.get('dream', '')}")
                            st.write(f"• 仕事の理由: {cast_dict.get('reason_for_job', '')}")
                            st.write(f"• 秘密: {cast_dict.get('secret', '')}")
                            st.write(f"• 許可カテゴリ: {cast_dict.get('allowed_categories', '')}")
                            
                            # カスタムフィールドがある場合は表示
                            custom_fields = execute_query("SELECT * FROM custom_fields ORDER BY sort_order", fetch="all")
                            if custom_fields:
                                st.write("**カスタム項目**")
                                for field in custom_fields:
                                    field_value = cast_dict.get(field['field_name'], '')
                                    st.write(f"• {field['display_name']}: {field_value}")
            else:
                st.info("登録済みのキャストはまだありません。")
        
        with ai_gen_tab:
            st.header("🤖 AIキャスト自動生成")
            st.markdown("AIを使って複数のキャストプロフィールを自動生成し、一括でCSV登録できます。")
            
            # 成功メッセージの表示
            if "ai_gen_message" in st.session_state:
                msg_type, msg_content = st.session_state.ai_gen_message
                if msg_type == "success":
                    st.success(msg_content)
                elif msg_type == "warning":
                    st.warning(msg_content)
                elif msg_type == "error":
                    st.error(msg_content)
                del st.session_state.ai_gen_message
            
            with st.form("ai_cast_generation"):
                st.subheader("🎯 生成設定")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    gen_count = st.number_input("生成するキャスト数", min_value=1, max_value=20, value=5)
                    gen_instruction = st.text_area(
                        "簡単な指示文（任意）", 
                        placeholder="例：アニメ風の可愛いキャラクター、ファンタジー世界の住人、現代の学生など",
                        height=100
                    )
                
                with col2:
                    st.subheader("🔧 事前登録項目")
                    name_pairs_placeholder = get_app_setting("name_pairs_placeholder", "例：\n@hanao_tanaka,田中 花音\n@misaki_sato,佐藤 美咲\n@aina_suzuki,鈴木 愛菜")
                    gen_names = st.text_area(
                        "ユーザー名,名前 のペアリスト（必須）\n※1行に1ペアずつ入力",
                        placeholder=name_pairs_placeholder,
                        height=100
                    )
                    gen_gender_ratio = st.selectbox(
                        "性別比率",
                        ["ランダム", "全て女性", "全て男性", "女性多め", "男性多め"]
                    )
                
                # 許可カテゴリの選択
                st.subheader("📚 許可するシチュエーションカテゴリ")
                cat_rows = execute_query("SELECT name FROM situation_categories ORDER BY name", fetch="all")
                category_options = [row['name'] for row in cat_rows] if cat_rows else []
                
                if category_options:
                    gen_categories = st.multiselect(
                        "生成されたキャストに許可するカテゴリ（複数選択可）",
                        category_options,
                        default=category_options[:3]  # 最初の3つをデフォルト選択
                    )
                else:
                    st.warning("カテゴリが登録されていません。「カテゴリ管理」で先にカテゴリを作成してください。")
                    gen_categories = []
                
                # 所属グループの選択
                group_rows = execute_query("SELECT id, name FROM groups ORDER BY name", fetch="all")
                group_options = {row['name']: row['id'] for row in group_rows} if group_rows else {}
                
                if group_options:
                    gen_groups = st.multiselect(
                        "所属グループ（任意）",
                        list(group_options.keys())
                    )
                else:
                    gen_groups = []
                
                generate_button = st.form_submit_button("🚀 キャストを自動生成", type="primary")
            
            # フォーム外での生成処理
            if generate_button:
                    if not gen_names.strip():
                        st.error("ユーザー名,名前のペアリストは必須です。1行に1ペアずつ入力してください。")
                    elif not gen_categories:
                        st.error("最低1つのカテゴリを選択してください。")
                    elif not st.session_state.get('gemini_model'):
                        st.error("AIモデルが利用できません。")
                    else:
                        # ユーザー名,名前ペアリストを処理
                        name_pairs = []
                        for line in gen_names.strip().split('\n'):
                            line = line.strip()
                            if line and ',' in line:
                                username, display_name = [part.strip() for part in line.split(',', 1)]
                                if username and display_name:
                                    name_pairs.append((username, display_name))
                        
                        actual_count = min(gen_count, len(name_pairs))
                        
                        if actual_count == 0:
                            st.error("有効なユーザー名,名前のペアが入力されていません。正しい形式：@username,表示名")
                        else:
                            # 性別比率の設定
                            gender_weights = {
                                "ランダム": {"女性": 0.5, "男性": 0.5},
                                "全て女性": {"女性": 1.0, "男性": 0.0},
                                "全て男性": {"女性": 0.0, "男性": 1.0},
                                "女性多め": {"女性": 0.7, "男性": 0.3},
                                "男性多め": {"女性": 0.3, "男性": 0.7}
                            }
                            
                            generated_casts = []
                            progress_bar = st.progress(0, text="AIキャストを生成中...")
                            
                            for i in range(actual_count):
                                progress_bar.progress((i + 1) / actual_count, text=f"キャスト {i+1}/{actual_count} を生成中...")
                                
                                username, display_name = name_pairs[i]
                                
                                # 性別を決定
                                weights = gender_weights[gen_gender_ratio]
                                gender = random.choices(["女性", "男性"], weights=[weights["女性"], weights["男性"]])[0]
                                
                                # AIプロンプトを作成
                                default_instruction = get_app_setting("ai_generation_instruction", "魅力的で個性豊かなキャラクター")
                                base_instruction = gen_instruction if gen_instruction.strip() else default_instruction
                                
                                prompt = f"""以下の指示に従って、キャラクターのプロフィールを生成してください。

# 基本設定
- ユーザー名: {username}
- 名前（表示名）: {display_name}
- 性別: {gender}
- 追加指示: {base_instruction}

# 出力形式
以下の項目を必ず含めて、自然で魅力的なキャラクタープロフィールを作成してください：

**基本情報**
- ニックネーム: （親しみやすい呼び方）
- 年齢: （具体的な年齢）
- 誕生日: （月日）
- 出身地: （都道府県）
- 外見の特徴: （髪型、服装、特徴的な部分など）

**性格・話し方**
- 性格: （一言で表現）
- 長所: （魅力的な点）
- 短所: （親しみやすい欠点）
- 一人称: （私、僕、俺など）
- 口調・語尾: （話し方の特徴）
- 口癖: （「」で囲んで）
- お客様への接し方: （接客スタイル）

**背景ストーリー**
- 職業／学業: （現在の所属）
- 趣味や特技: （興味のあること）
- 好きなもの: （具体的に）
- 嫌いなもの: （具体的に）
- 休日の過ごし方: （日常の様子）
- 将来の夢: （目標や憧れ）
- なぜこの仕事をしているのか: （動機）
- ちょっとした秘密: （親しみやすい秘密）

# ルール
- 各項目は簡潔で具体的に
- キャラクターに一貫性を持たせる
- 親しみやすく魅力的な設定にする
- 性別に合った自然な設定にする"""

                                try:
                                    response = safe_generate_content(st.session_state.gemini_model, prompt)
                                    ai_profile = response.text
                                    
                                    # AI出力を解析してフィールドに分割
                                    cast_data = parse_ai_profile(ai_profile, username, display_name, gen_categories)
                                    generated_casts.append(cast_data)
                                    
                                    time.sleep(2)  # API制限を考慮
                                    
                                except Exception as e:
                                    st.warning(f"キャスト「{display_name}（{username}）」の生成中にエラーが発生しました: {e}")
                                    continue
                            
                            if generated_casts:
                                # CSV形式でダウンロード用データを作成
                                df = pandas_lib.DataFrame(generated_casts)
                                csv_data = df.to_csv(index=False).encode('utf-8')
                                
                                # セッション状態に保存
                                st.session_state.generated_casts_data = csv_data
                                st.session_state.generated_casts_list = generated_casts
                                st.session_state.ai_gen_message = ("success", f"{len(generated_casts)}件のキャストプロフィールを生成しました！")
                            else:
                                st.session_state.ai_gen_message = ("error", "キャストの生成に失敗しました。")
                            
                            st.rerun()
            
            # 生成完了後のダウンロードボタン表示（フォーム外）
            if 'generated_casts_data' in st.session_state:
                st.subheader("🎉 生成完了")
                st.info(f"{len(st.session_state.generated_casts_list)}件のキャストが生成されました。以下からCSVをダウンロードして、「CSV管理」タブからインポートしてください。")
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.download_button(
                        "📥 生成されたキャストをCSVでダウンロード",
                        data=st.session_state.generated_casts_data,
                        file_name=f'ai_generated_casts_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                        mime='text/csv',
                        use_container_width=True
                    )
                with col2:
                    if st.button("🗑️ 生成結果をクリア", use_container_width=True):
                        if 'generated_casts_data' in st.session_state:
                            del st.session_state.generated_casts_data
                        if 'generated_casts_list' in st.session_state:
                            del st.session_state.generated_casts_list
                        st.rerun()
                
                # プレビュー表示
                with st.expander("生成されたキャストのプレビュー", expanded=True):
                    for i, cast in enumerate(st.session_state.generated_casts_list[:3]):  # 最初の3件のみ表示
                        st.write(f"**{i+1}. {cast['name']}**")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"• ニックネーム: {cast.get('nickname', '')}")
                            st.write(f"• 年齢: {cast.get('age', '')}")
                            st.write(f"• 性格: {cast.get('personality', '')}")
                        with col2:
                            st.write(f"• 職業: {cast.get('occupation', '')}")
                            st.write(f"• 趣味: {cast.get('hobby', '')}")
                            st.write(f"• 口癖: {cast.get('catchphrase', '')}")
                        if i < len(st.session_state.generated_casts_list) - 1:
                            st.markdown("---")
                    
                    if len(st.session_state.generated_casts_list) > 3:
                        st.info(f"他 {len(st.session_state.generated_casts_list) - 3} 件のキャストも生成されました。CSVファイルで全て確認できます。")
            
            st.markdown("---")
            st.subheader("💡 使い方")
            st.markdown("""
            1. **生成設定**：作りたいキャスト数と簡単な指示を入力
            2. **基本情報**：名前リストと性別比率を設定
            3. **カテゴリ選択**：生成されたキャストが使用できるシチュエーションを選択
            4. **自動生成**：AIが各キャストの詳細プロフィールを生成
            5. **CSV保存**：生成結果をCSVでダウンロード
            6. **一括登録**：「CSV管理」タブからインポートして一括登録
            7. **チューニング**：「個別管理」タブで各キャストを編集・調整
            """)

    elif page == "グループ管理":
        st.title("🏢 グループ管理"); st.markdown("キャストに共通のプロフィール（職場や所属など）を設定します。")
        st.header("新しいグループの作成")
        with st.form(key="new_group_form", clear_on_submit=True):
            new_name = st.text_input("グループ名", placeholder="例：喫茶アルタイル")
            new_content = st.text_area("内容（共通プロフィール）", placeholder="あなたは銀座の路地裏にある、星をテーマにした小さな喫茶店「アルタイル」の店員です。")
            if st.form_submit_button("作成する"):
                if new_name and new_content:
                    if execute_query("INSERT INTO groups (name, content) VALUES (?, ?)", (new_name, new_content)) is not False: st.success("新しいグループを作成しました！")
                else: st.warning("グループ名と内容の両方を入力してください。")
        st.markdown("---")
        st.header("登録済みグループ一覧")
        all_groups = execute_query("SELECT id, name, content FROM groups ORDER BY id DESC", fetch="all")
        if all_groups:
            for group in all_groups:
                with st.expander(f"🏢 {group['name']}", expanded=False):
                    with st.form(key=f"edit_group_{group['id']}"):
                        # 編集フィールド
                        new_name = st.text_input("グループ名", value=group['name'])
                        new_content = st.text_area("内容（共通プロフィール）", value=group['content'], height=100)
                        
                        # ボタン
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        update_btn = col_btn1.form_submit_button("更新", type="primary")
                        delete_btn = col_btn2.form_submit_button("削除")
                        cancel_btn = col_btn3.form_submit_button("キャンセル")
                        
                        if update_btn:
                            if new_name and new_content:
                                if execute_query("UPDATE groups SET name = ?, content = ? WHERE id = ?", 
                                               (new_name, new_content, group['id'])) is not False:
                                    st.success("グループを更新しました！")
                                    st.rerun()
                            else:
                                st.warning("グループ名と内容の両方を入力してください。")
                        
                        if delete_btn:
                            execute_query("DELETE FROM cast_groups WHERE group_id = ?", (group['id'],))
                            if execute_query("DELETE FROM groups WHERE id = ?", (group['id'],)) is not False:
                                st.success("グループを削除しました。")
                                st.rerun()
        else: 
            st.info("登録済みのグループはありません。")

    elif page == "カテゴリ管理":
        st.title("📚 カテゴリ管理"); st.markdown("シチュエーションを分類するためのカテゴリを管理します。")
        st.header("新しいカテゴリの追加")
        with st.form(key="new_category_form", clear_on_submit=True):
            new_name = st.text_input("カテゴリ名", placeholder="例：日常")
            if st.form_submit_button("追加する"):
                if new_name:
                    if execute_query("INSERT INTO situation_categories (name) VALUES (?)", (new_name,)) is not False: st.success("新しいカテゴリを追加しました！")
                else: st.warning("カテゴリ名を入力してください。")
        st.markdown("---")
        st.header("登録済みカテゴリ一覧")
        all_categories = execute_query("SELECT id, name FROM situation_categories ORDER BY id DESC", fetch="all")
        if all_categories:
            for cat in all_categories:
                with st.expander(f"📚 {cat['name']}", expanded=False):
                    with st.form(key=f"edit_category_{cat['id']}"):
                        # 編集フィールド
                        new_name = st.text_input("カテゴリ名", value=cat['name'])
                        
                        # ボタン
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        update_btn = col_btn1.form_submit_button("更新", type="primary")
                        delete_btn = col_btn2.form_submit_button("削除")
                        cancel_btn = col_btn3.form_submit_button("キャンセル")
                        
                        if update_btn:
                            if new_name:
                                if execute_query("UPDATE situation_categories SET name = ? WHERE id = ?", 
                                               (new_name, cat['id'])) is not False:
                                    st.success("カテゴリを更新しました！")
                                    st.rerun()
                            else:
                                st.warning("カテゴリ名を入力してください。")
                        
                        if delete_btn:
                            st.warning(f"カテゴリ「{cat['name']}」を削除すると、関連するシチュエーションもすべて削除されます。")
                            if st.form_submit_button("はい, 削除します", key=f"confirm_delete_{cat['id']}"):
                                execute_query("DELETE FROM situations WHERE category_id = ?", (cat['id'],))
                                if execute_query("DELETE FROM situation_categories WHERE id = ?", (cat['id'],)) is not False:
                                    st.success("カテゴリを削除しました。")
                                    st.rerun()
        else: 
            st.info("登録済みのカテゴリはありません。")

    elif page == "シチュエーション管理":
        st.title("🎭 シチュエーション管理"); st.markdown("キャラクターが「今、何をしているか」を定義し、投稿の多様性を生み出します。")
        
        # インポート成功メッセージの表示
        if "situation_import_message" in st.session_state:
            msg_type, msg_content = st.session_state.situation_import_message
            if msg_type == "success":
                st.success(msg_content)
            elif msg_type == "warning":
                st.warning(msg_content)
            elif msg_type == "error":
                st.error(msg_content)
            del st.session_state.situation_import_message
        
        st.subheader("一括管理（CSV）")
        with st.expander("CSVでのインポート/エクスポートはこちら", expanded=False):
            c1, c2 = st.columns(2)
            uploaded_file = c1.file_uploader("CSVファイル（1行目:ID、2行目:項目説明、3行目～:データ）", type="csv", key="sit_csv_up")
            if uploaded_file:
                try:
                    # ファイルポインタをリセット
                    uploaded_file.seek(0)
                    
                    # まず全体を読み込んで行数を確認
                    all_lines = uploaded_file.read().decode('utf-8').strip().split('\n')
                    uploaded_file.seek(0)
                    
                    if len(all_lines) < 3:
                        st.error("CSVファイルには最低3行（ヘッダー行、説明行、データ行）が必要です。")
                        st.info("現在のファイル構造：")
                        for i, line in enumerate(all_lines, 1):
                            st.text(f"{i}行目: {line}")
                    else:
                        # 正しい形式で読み込み：1行目をヘッダーとして使用し、2行目をスキップ
                        df = pandas_lib.read_csv(uploaded_file, skiprows=[1], dtype=str).fillna("")
                        
                        # 必要な列の存在チェック
                        required_columns = ['content', 'time_slot', 'category']
                        missing_columns = [col for col in required_columns if col not in df.columns]
                        
                        if missing_columns:
                            st.error(f"CSVに必要な列が不足しています: {', '.join(missing_columns)}")
                            st.info("必要な列: content (シチュエーション内容), time_slot (時間帯), category (カテゴリ名)")
                        else:
                            cat_rows = execute_query("SELECT id, name FROM situation_categories", fetch="all")
                            cat_map = {row['name']: row['id'] for row in cat_rows}
                            
                            success_count = 0
                            error_rows = []
                            
                            for index, row in df.iterrows():
                                content = row.get('content', '').strip()
                                time_slot = row.get('time_slot', 'いつでも').strip()
                                category_name = row.get('category', '').strip()
                                
                                if not content:
                                    error_rows.append(f"行{index+3}: シチュエーション内容が空です")
                                    continue
                                    
                                if not category_name:
                                    error_rows.append(f"行{index+3}: カテゴリが空です")
                                    continue
                                    
                                cat_id = cat_map.get(category_name)
                                if not cat_id:
                                    error_rows.append(f"行{index+3}: カテゴリ「{category_name}」が存在しません")
                                    continue
                                
                                # time_slotの値をチェック
                                valid_time_slots = ["いつでも", "朝", "昼", "夜"]
                                if time_slot not in valid_time_slots:
                                    time_slot = "いつでも"  # デフォルト値に設定
                                
                                # 重複チェック
                                existing = execute_query("SELECT id FROM situations WHERE content = ?", (content,), fetch="one")
                                if existing:
                                    error_rows.append(f"行{index+3}: シチュエーション「{content}」は既に存在します")
                                    continue
                                
                                result = execute_query("INSERT INTO situations (content, time_slot, category_id) VALUES (?, ?, ?)", 
                                                    (content, time_slot, cat_id))
                                if result is not False:
                                    success_count += 1
                            
                            # 結果の表示とリロード処理
                            if success_count > 0:
                                if error_rows:
                                    error_summary = f"{success_count}件のシチュエーションをインポートしました。{len(error_rows)}件のエラーがありました。"
                                    st.session_state.situation_import_message = ("warning", error_summary)
                                else:
                                    st.session_state.situation_import_message = ("success", f"{success_count}件のシチュエーションをインポートしました。")
                                # 必ずリロードを実行
                                st.rerun()
                            elif error_rows:
                                # 追加されたデータがない場合はエラーメッセージのみ表示
                                st.error(f"インポートできませんでした。{len(error_rows)}件のエラーがあります。")
                                for error in error_rows[:3]:  # 最初の3件のエラーのみ表示
                                    st.write(f"• {error}")
                            
                except Exception as e:
                    st.error(f"CSVの処理中にエラーが発生しました: {e}")
                    st.info("CSVファイルの形式を確認してください。1行目: 列名、2行目: 説明、3行目以降: データ")
            
            all_sits_for_export = execute_query("SELECT s.content, s.time_slot, sc.name as category FROM situations s LEFT JOIN situation_categories sc ON s.category_id = sc.id", fetch="all")
            if all_sits_for_export:
                df = pandas_lib.DataFrame([dict(r) for r in all_sits_for_export])
                c2.download_button("CSVエクスポート", df.to_csv(index=False).encode('utf-8'), "situations.csv", "text/csv", use_container_width=True)
        st.markdown("---")
        st.header("個別管理")
        with st.form(key="new_situation_form", clear_on_submit=True):
            situation_placeholder = get_app_setting("situation_placeholder", "例：お気に入りの喫茶店で読書中")
            new_content = st.text_area("シチュエーション内容", placeholder=situation_placeholder)
            c1, c2 = st.columns(2)
            time_slot = c1.selectbox("時間帯", ["いつでも", "朝", "昼", "夜"])
            cat_rows = execute_query("SELECT id, name FROM situation_categories ORDER BY name", fetch="all")
            category_options = [row['name'] for row in cat_rows] if cat_rows else []
            selected_category_name = c2.selectbox("カテゴリ", category_options)
            if st.form_submit_button("追加する"):
                if new_content and selected_category_name:
                    category_id = next((c['id'] for c in cat_rows if c['name'] == selected_category_name), None)
                    if execute_query("INSERT INTO situations (content, time_slot, category_id) VALUES (?, ?, ?)", (new_content, time_slot, category_id)) is not False: 
                        st.session_state.situation_import_message = ("success", "新しいシチュエーションを追加しました！")
                        st.rerun()
                else: st.warning("内容とカテゴリの両方を入力・選択してください。")
        st.header("登録済みシチュエーション一覧")
        all_situations = execute_query("SELECT s.id, s.content, s.time_slot, sc.name as category_name, s.category_id FROM situations s LEFT JOIN situation_categories sc ON s.category_id = sc.id ORDER BY s.id DESC", fetch="all")
        if all_situations:
            cat_rows = execute_query("SELECT id, name FROM situation_categories ORDER BY name", fetch="all")
            category_options = [row['name'] for row in cat_rows] if cat_rows else []
            time_slot_options = ["いつでも", "朝", "昼", "夜"]
            
            for sit in all_situations:
                with st.expander(f"📝 {sit['content'][:50]}{'...' if len(sit['content']) > 50 else ''}", expanded=False):
                    with st.form(key=f"edit_situation_{sit['id']}"):
                        col1, col2 = st.columns(2)
                        
                        # 編集フィールド
                        new_content = st.text_area("シチュエーション内容", value=sit['content'], height=100)
                        current_time_slot_index = time_slot_options.index(sit['time_slot']) if sit['time_slot'] in time_slot_options else 0
                        new_time_slot = col1.selectbox("時間帯", time_slot_options, index=current_time_slot_index, key=f"time_{sit['id']}")
                        current_category_index = next((i for i, cat in enumerate(category_options) if cat == sit['category_name']), 0)
                        new_category_name = col2.selectbox("カテゴリ", category_options, index=current_category_index, key=f"cat_{sit['id']}")
                        
                        # ボタン
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        update_btn = col_btn1.form_submit_button("更新", type="primary")
                        delete_btn = col_btn2.form_submit_button("削除")
                        cancel_btn = col_btn3.form_submit_button("キャンセル")
                        
                        if update_btn:
                            if new_content and new_category_name:
                                new_category_id = next((c['id'] for c in cat_rows if c['name'] == new_category_name), None)
                                if execute_query("UPDATE situations SET content = ?, time_slot = ?, category_id = ? WHERE id = ?", 
                                               (new_content, new_time_slot, new_category_id, sit['id'])) is not False:
                                    st.success("シチュエーションを更新しました！")
                                    st.rerun()
                            else:
                                st.warning("内容とカテゴリの両方を入力・選択してください。")
                        
                        if delete_btn:
                            if execute_query("DELETE FROM situations WHERE id = ?", (sit['id'],)) is not False:
                                st.success("シチュエーションを削除しました。")
                                st.rerun()
        else: 
            st.info("登録済みのシチュエーションはありません。")
    
    elif page == "アドバイス管理":
        st.title("💡 アドバイス管理"); st.markdown("投稿に対するフィードバックの選択肢（アドバイス）を管理します。")
        st.subheader("一括管理（CSV）")
        with st.expander("CSVでのインポート/エクスポートはこちら", expanded=False):
            c1, c2 = st.columns(2)
            uploaded_file = c1.file_uploader("CSVファイル（1行目:ID、2行目:項目説明、3行目～:データ）", type="csv", key="adv_csv_up")
            if uploaded_file:
                try:
                    # まず1行目（列名）を読み取る
                    uploaded_file.seek(0)  # ファイルポインタをリセット
                    header_df = pandas_lib.read_csv(uploaded_file, nrows=1, dtype=str)
                    column_names = header_df.columns.tolist()
                    
                    # 3行目からデータを読み込み（skiprows=2で1行目と2行目をスキップ、1行目の列名を使用）
                    uploaded_file.seek(0)  # ファイルポインタをリセット
                    df = pandas_lib.read_csv(uploaded_file, skiprows=2, names=column_names, dtype=str, keep_default_na=False).fillna("")
                    
                    # content列の存在確認
                    if 'content' not in df.columns:
                        st.error("CSVに 'content' 列が見つかりません。アドバイス内容を含む列名を 'content' としてください。")
                    else:
                        success_count = 0
                        duplicate_count = 0
                        
                        for _, row in df.iterrows():
                            content = row['content'].strip()
                            if content:  # 空でない場合のみ処理
                                # 既存チェック
                                existing = execute_query("SELECT id FROM advice_master WHERE content = ?", (content,), fetch="one")
                                if existing:
                                    duplicate_count += 1
                                else:
                                    if execute_query("INSERT INTO advice_master (content) VALUES (?)", (content,)) is not False:
                                        success_count += 1
                        
                        # 結果メッセージの表示
                        if success_count > 0:
                            if duplicate_count > 0:
                                st.success(f"{success_count}件の新しいアドバイスを追加しました。{duplicate_count}件は既に存在するため重複を回避しました。")
                            else:
                                st.success(f"{success_count}件のアドバイスを追加しました。")
                        elif duplicate_count > 0:
                            st.warning(f"{duplicate_count}件のアドバイスは既に存在するため、追加されませんでした。")
                        else:
                            st.info("有効なアドバイスデータが見つかりませんでした。")
                            
                except Exception as e:
                    st.error(f"CSVの処理中にエラーが発生しました: {e}")
                    
            all_advs = execute_query("SELECT content FROM advice_master", fetch="all")
            if all_advs:
                df = pandas_lib.DataFrame([dict(r) for r in all_advs])
                c2.download_button("CSVエクスポート", df.to_csv(index=False).encode('utf-8'), "advice.csv", "text/csv", use_container_width=True)
        st.markdown("---")
        st.header("個別管理")
        with st.form(key="new_advice_form", clear_on_submit=True):
            new_content = st.text_input("アドバイス内容", placeholder="例：もっと可愛く")
            if st.form_submit_button("追加する"):
                if new_content:
                    if execute_query("INSERT INTO advice_master (content) VALUES (?)", (new_content,)) is not False: st.success("新しいアドバイスを追加しました！")
                else: st.warning("内容を入力してください。")
        st.header("登録済みアドバイス一覧")
        all_advice = execute_query("SELECT id, content FROM advice_master ORDER BY id DESC", fetch="all")
        if all_advice:
            for adv in all_advice:
                with st.expander(f"💡 {adv['content']}", expanded=False):
                    with st.form(key=f"edit_advice_{adv['id']}"):
                        # 編集フィールド
                        new_content = st.text_input("アドバイス内容", value=adv['content'])
                        
                        # ボタン
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        update_btn = col_btn1.form_submit_button("更新", type="primary")
                        delete_btn = col_btn2.form_submit_button("削除")
                        cancel_btn = col_btn3.form_submit_button("キャンセル")
                        
                        if update_btn:
                            if new_content:
                                if execute_query("UPDATE advice_master SET content = ? WHERE id = ?", 
                                               (new_content, adv['id'])) is not False:
                                    st.success("アドバイスを更新しました！")
                                    st.rerun()
                            else:
                                st.warning("アドバイス内容を入力してください。")
                        
                        if delete_btn:
                            if execute_query("DELETE FROM advice_master WHERE id = ?", (adv['id'],)) is not False:
                                st.success("アドバイスを削除しました。")
                                st.rerun()
        else: 
            st.info("登録済みのアドバイスはありません。")
    
    elif page == "指針アドバイス":
        st.title("📋 指針アドバイス管理")
        st.markdown("すべての投稿生成時に参考にするグローバルアドバイスと、カテゴリ別の個別アドバイスを管理します。")
        
        # タブ作成
        global_tab, category_tab = st.tabs(["🌐 グローバル指針", "📂 カテゴリ別指針"])
        
        with global_tab:
            st.subheader("🌐 グローバル指針アドバイス")
            st.markdown("すべての投稿生成時に自動的に参考にされる指針です。キャストの性格や投稿の基本方針を設定してください。")
            
            # グローバルアドバイス一覧表示
            global_advices = execute_query("SELECT * FROM global_advice ORDER BY sort_order, created_at", fetch="all")
            
            # 新規追加フォーム
            with st.expander("➕ 新しいグローバル指針を追加", expanded=not global_advices):
                with st.form("add_global_advice"):
                    col1, col2 = st.columns([3, 1])
                    new_title = col1.text_input("指針タイトル", placeholder="例：投稿の基本方針")
                    new_sort_order = col2.number_input("表示順", min_value=0, max_value=100, value=0)
                    new_content = st.text_area(
                        "指針内容", 
                        placeholder="例：フォロワーの心に寄り添う内容を心がけ、共感を呼ぶ投稿を作成してください。",
                        height=120
                    )
                    
                    if st.form_submit_button("📝 グローバル指針を追加", type="primary"):
                        if new_title and new_content:
                            try:
                                execute_query(
                                    "INSERT INTO global_advice (title, content, sort_order) VALUES (?, ?, ?)",
                                    (new_title, new_content, new_sort_order)
                                )
                                st.success("✅ グローバル指針を追加しました！")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 追加中にエラーが発生しました: {e}")
                        else:
                            st.warning("タイトルと内容を入力してください。")
            
            # 既存のグローバルアドバイス表示・編集
            if global_advices:
                st.markdown("### 📝 登録済みグローバル指針")
                for advice in global_advices:
                    with st.expander(f"{'🟢' if advice['is_active'] else '🔴'} {advice['title']}", expanded=False):
                        with st.form(f"edit_global_{advice['id']}"):
                            col1, col2, col3 = st.columns([2, 1, 1])
                            edit_title = col1.text_input("タイトル", value=advice['title'], key=f"title_g_{advice['id']}")
                            edit_sort_order = col2.number_input("表示順", min_value=0, max_value=100, value=advice['sort_order'], key=f"sort_g_{advice['id']}")
                            edit_active = col3.checkbox("有効", value=bool(advice['is_active']), key=f"active_g_{advice['id']}")
                            
                            edit_content = st.text_area(
                                "指針内容", 
                                value=advice['content'], 
                                height=100,
                                key=f"content_g_{advice['id']}"
                            )
                            
                            col_a, col_b = st.columns(2)
                            if col_a.form_submit_button("💾 更新", type="primary"):
                                try:
                                    execute_query(
                                        "UPDATE global_advice SET title=?, content=?, is_active=?, sort_order=? WHERE id=?",
                                        (edit_title, edit_content, int(edit_active), edit_sort_order, advice['id'])
                                    )
                                    st.success("✅ グローバル指針を更新しました！")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 更新中にエラーが発生しました: {e}")
                            
                            if col_b.form_submit_button("🗑️ 削除", type="secondary"):
                                try:
                                    execute_query("DELETE FROM global_advice WHERE id=?", (advice['id'],))
                                    st.success("✅ グローバル指針を削除しました！")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 削除中にエラーが発生しました: {e}")
            else:
                st.info("📝 グローバル指針がまだ登録されていません。上記のフォームから追加してください。")
        
        with category_tab:
            st.subheader("📂 カテゴリ別指針アドバイス")
            st.markdown("特定のカテゴリの投稿生成時にのみ参考にされる指針です。カテゴリ固有の注意点や方針を設定してください。")
            
            # カテゴリ選択
            categories = execute_query("SELECT * FROM situation_categories ORDER BY name", fetch="all")
            if not categories:
                st.warning("⚠️ カテゴリが登録されていません。「カテゴリ管理」で先にカテゴリを作成してください。")
            else:
                category_options = {cat['name']: cat['id'] for cat in categories}
                selected_category_name = st.selectbox("カテゴリを選択", list(category_options.keys()))
                selected_category_id = category_options[selected_category_name]
                
                # 選択されたカテゴリのアドバイス一覧
                category_advices = execute_query(
                    "SELECT * FROM category_advice WHERE category_id=? ORDER BY sort_order, created_at",
                    (selected_category_id,),
                    fetch="all"
                )
                
                # 新規追加フォーム
                with st.expander(f"➕ 「{selected_category_name}」カテゴリの指針を追加", expanded=not category_advices):
                    with st.form(f"add_category_advice_{selected_category_id}"):
                        col1, col2 = st.columns([3, 1])
                        new_title = col1.text_input("指針タイトル", placeholder="例：恋愛投稿の注意点")
                        new_sort_order = col2.number_input("表示順", min_value=0, max_value=100, value=0)
                        new_content = st.text_area(
                            "指針内容",
                            placeholder=f"例：{selected_category_name}カテゴリ特有の投稿方針や注意点を記述してください。",
                            height=120
                        )
                        
                        if st.form_submit_button("📝 カテゴリ指針を追加", type="primary"):
                            if new_title and new_content:
                                try:
                                    execute_query(
                                        "INSERT INTO category_advice (category_id, title, content, sort_order) VALUES (?, ?, ?, ?)",
                                        (selected_category_id, new_title, new_content, new_sort_order)
                                    )
                                    st.success(f"✅ 「{selected_category_name}」カテゴリの指針を追加しました！")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 追加中にエラーが発生しました: {e}")
                            else:
                                st.warning("タイトルと内容を入力してください。")
                
                # 既存のカテゴリアドバイス表示・編集
                if category_advices:
                    st.markdown(f"### 📝 「{selected_category_name}」カテゴリの指針")
                    for advice in category_advices:
                        with st.expander(f"{'🟢' if advice['is_active'] else '🔴'} {advice['title']}", expanded=False):
                            with st.form(f"edit_category_{advice['id']}"):
                                col1, col2, col3 = st.columns([2, 1, 1])
                                edit_title = col1.text_input("タイトル", value=advice['title'], key=f"title_c_{advice['id']}")
                                edit_sort_order = col2.number_input("表示順", min_value=0, max_value=100, value=advice['sort_order'], key=f"sort_c_{advice['id']}")
                                edit_active = col3.checkbox("有効", value=bool(advice['is_active']), key=f"active_c_{advice['id']}")
                                
                                edit_content = st.text_area(
                                    "指針内容",
                                    value=advice['content'],
                                    height=100,
                                    key=f"content_c_{advice['id']}"
                                )
                                
                                col_a, col_b = st.columns(2)
                                if col_a.form_submit_button("💾 更新", type="primary"):
                                    try:
                                        execute_query(
                                            "UPDATE category_advice SET title=?, content=?, is_active=?, sort_order=? WHERE id=?",
                                            (edit_title, edit_content, int(edit_active), edit_sort_order, advice['id'])
                                        )
                                        st.success("✅ カテゴリ指針を更新しました！")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ 更新中にエラーが発生しました: {e}")
                                
                                if col_b.form_submit_button("🗑️ 削除", type="secondary"):
                                    try:
                                        execute_query("DELETE FROM category_advice WHERE id=?", (advice['id'],))
                                        st.success("✅ カテゴリ指針を削除しました！")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ 削除中にエラーが発生しました: {e}")
                else:
                    st.info(f"📝 「{selected_category_name}」カテゴリの指針がまだ登録されていません。上記のフォームから追加してください。")

    elif page == "システム設定":
        st.title("⚙️ システム設定")
        st.markdown("アプリケーションの各種設定を管理します。")
        
        # タブ作成
        auth_tab, sheets_tab, app_settings_tab = st.tabs(["🔐 Google Cloud認証", "🗃️ Google Sheets連携", "🔧 アプリ設定"])
        
        with auth_tab:
            st.subheader("🔐 Google Cloud Application Default Credentials")
            st.markdown("Google Cloud認証を設定します。通常はコマンドライン `gcloud auth application-default login --no-launch-browser` で行う処理をGUIで実行できます。")
            
            # 現在の認証状況確認
            adc_file = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
            
            # リアルタイム認証テスト
            auth_test_result = None
            try:
                import vertexai
                # APIバージョンを動的に決定
                try:
                    from vertexai.generative_models import GenerativeModel
                    test_models = ["gemini-2.5-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash-001"]
                except ImportError:
                    from vertexai.preview.generative_models import GenerativeModel
                    test_models = ["gemini-2.5-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash-001"]
                
                vertexai.init(project="aicast-472807", location="us-central1")
                
                # 最初の利用可能なモデルでテスト
                model = GenerativeModel(test_models[0])
                auth_test_result = "active"
            except Exception as e:
                auth_test_result = f"error: {str(e)}"
            
            if os.path.exists(adc_file) and "error" not in auth_test_result:
                st.success("✅ Google Cloud Application Default Credentials が設定済み＆有効です")
                
                # 認証情報の詳細表示
                try:
                    with open(adc_file, 'r') as f:
                        import json
                        creds = json.load(f)
                        if 'client_id' in creds:
                            masked_client_id = creds['client_id'][:20] + "..." if len(creds['client_id']) > 20 else creds['client_id']
                            st.info(f"📋 クライアントID: {masked_client_id}")
                        if 'type' in creds:
                            st.info(f"📋 認証タイプ: {creds['type']}")
                except Exception as e:
                    st.warning(f"認証情報の読み取り中にエラーが発生しました: {e}")
                # 認証管理ボタン
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🔄 認証を更新", type="primary", use_container_width=True):
                        st.info("**認証更新方法:**")
                        st.code("gcloud auth application-default login --no-launch-browser", language="bash")
                        st.markdown("上記コマンドを実行して認証コードを取得し、下記フォームに入力してください。")
                
                with col2:
                    if st.button("🗑️ 認証をリセット", use_container_width=True):
                        try:
                            if os.path.exists(adc_file):
                                os.remove(adc_file)
                            # セッション状態もクリア
                            if 'auth_done' in st.session_state:
                                del st.session_state['auth_done']
                            if 'gemini_model' in st.session_state:
                                del st.session_state['gemini_model']
                            st.success("✅ 認証情報をリセットしました。ページを更新してください。")
                            st.rerun()
                        except Exception as e:
                            st.error(f"認証リセット中にエラーが発生しました: {e}")
                
                with col3:
                    if st.button("🔍 認証テスト", use_container_width=True):
                        st.rerun()
                
            elif os.path.exists(adc_file):
                st.warning("⚠️ 認証ファイルは存在しますが、認証が無効です（期限切れの可能性）")
                st.error(f"認証テスト結果: {auth_test_result}")
                
                # 認証エラー時の管理オプション
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🔄 認証を更新", type="primary", use_container_width=True):
                        st.info("**認証更新方法:**")
                        st.code("gcloud auth application-default login --no-launch-browser", language="bash")
                        st.markdown("上記コマンドを実行して認証を更新してください。")
                
                with col2:
                    if st.button("🗑️ 認証をリセット", use_container_width=True):
                        try:
                            os.remove(adc_file)
                            # セッション状態もクリア
                            if 'auth_done' in st.session_state:
                                del st.session_state['auth_done']
                            if 'gemini_model' in st.session_state:
                                del st.session_state['gemini_model']
                            st.success("✅ 認証情報をリセットしました。ページを更新してください。")
                            st.rerun()
                        except Exception as e:
                            st.error(f"認証リセット中にエラーが発生しました: {e}")
                
                with col3:
                    if st.button("🔍 再テスト", use_container_width=True):
                        st.rerun()
            else:
                st.error("❌ Google Cloud Application Default Credentials が設定されていません")
                
                st.markdown("""
                **設定方法:**
                1. 下記のフォームに認証情報を入力
                2. または、コマンドラインで以下を実行:
                ```bash
                gcloud auth application-default login --no-launch-browser
                ```
                """)
                
                with st.form("gcloud_auth_form"):
                    st.markdown("**手動認証設定（上級者向け）:**")
                    auth_json = st.text_area(
                        "Application Default Credentials JSON",
                        height=200,
                        placeholder='''{
  "client_id": "your-client-id.googleusercontent.com",
  "client_secret": "your-client-secret",
  "refresh_token": "your-refresh-token",
  "type": "authorized_user"
}'''
                    )
                    
                    if st.form_submit_button("🔐 認証情報を保存", type="primary"):
                        if auth_json.strip():
                            try:
                                import json
                                auth_data = json.loads(auth_json)
                                
                                # 必要なフィールドの確認
                                required_fields = ["client_id", "client_secret", "refresh_token", "type"]
                                missing_fields = [field for field in required_fields if field not in auth_data]
                                
                                if missing_fields:
                                    st.error(f"必要なフィールドが不足しています: {', '.join(missing_fields)}")
                                else:
                                    # ディレクトリ作成
                                    os.makedirs(os.path.dirname(adc_file), exist_ok=True)
                                    
                                    # 認証ファイル保存
                                    with open(adc_file, 'w', encoding='utf-8') as f:
                                        json.dump(auth_data, f, indent=2, ensure_ascii=False)
                                    
                                    st.success("✅ Google Cloud認証情報を保存しました！ページを更新してください。")
                                    st.rerun()
                                    
                            except json.JSONDecodeError as e:
                                st.error(f"JSONの解析に失敗しました: {e}")
                            except Exception as e:
                                st.error(f"認証情報の保存中にエラーが発生しました: {e}")
                        else:
                            st.warning("認証情報のJSONを入力してください。")
                            
                st.markdown("---")
                
                # 認証の推奨方法
                st.subheader("🔄 認証の設定方法")
                st.markdown("**推奨:** 下記のコマンドラインツールを使用してください。")
                
                st.code("gcloud auth application-default login --no-launch-browser", language="bash")
                
                st.markdown("""
                **手順:**
                1. 上記のコマンドをターミナルで実行
                2. 表示されるURLをブラウザで開く
                3. Googleアカウントでログイン
                4. 認証コードをコピーしてターミナルに貼り付け
                5. このページを更新して認証状況を確認
                """)
                
                # 認証ファイルの場所を表示
                with st.expander("📁 認証ファイル情報", expanded=False):
                    st.code(f"認証ファイル保存先: {adc_file}")
                    st.markdown("このファイルに認証情報が保存されます。")
                
                # 手動確認用
                st.markdown("---")
                col1, col2 = st.columns(2)
                if col1.button("🔍 認証状況を再確認", key="recheck_auth"):
                    st.rerun()
                    
                if col2.button("📖 詳細ガイド", key="auth_guide"):
                    st.info("""
                    **詳細な認証手順:**
                    
                    1. **Google Cloud SDK インストール確認:**
                       ```bash
                       gcloud --version
                       ```
                    
                    2. **プロジェクト設定:**
                       ```bash
                       gcloud config set project aicast-472807
                       ```
                    
                    3. **認証実行:**
                       ```bash
                       gcloud auth application-default login --no-launch-browser
                       ```
                    
                    4. **認証確認:**
                       ```bash
                       gcloud auth application-default print-access-token
                       ```
                    """)
                
                st.markdown("---")
                st.markdown("**💡 ヒント:** 通常は `gcloud` コマンドラインツールを使用することを推奨します。")
        
        with sheets_tab:
            st.subheader("🗃️ Google Sheets 連携設定")
            st.markdown("Google Sheets APIを使用して投稿を送信するための認証設定を行います。")
        
        with st.expander("OAuth認証情報の設定", expanded=True):
            st.markdown("""
            **設定手順:**
            1. [Google Cloud Console](https://console.cloud.google.com/)でOAuth 2.0クライアントIDを作成
            2. クライアントタイプは"デスクトップアプリケーション"を選択
            3. 作成したクライアントIDのJSONファイルをダウンロード
            4. 下記のテキストエリアにJSONの内容を貼り付けて保存
            """)
            
            # 現在の認証情報の状態確認
            credentials_path = "credentials/credentials.json"
            if os.path.exists(credentials_path):
                st.success("✅ OAuth認証情報が設定済みです")
                if st.button("認証情報を削除"):
                    try:
                        os.remove(credentials_path)
                        # トークンファイルも削除
                        token_path = "credentials/token.pickle"
                        if os.path.exists(token_path):
                            os.remove(token_path)
                        st.success("認証情報を削除しました。ページを更新してください。")
                        st.rerun()
                    except Exception as e:
                        st.error(f"認証情報の削除中にエラーが発生しました: {e}")
            else:
                st.warning("⚠️ OAuth認証情報が設定されていません")
                
                # JSON入力フォーム
                with st.form("oauth_credentials_form"):
                    st.markdown("**OAuth認証情報JSON:**")
                    json_content = st.text_area(
                        "GoogleクライアントIDのJSONファイルの内容を貼り付けてください",
                        height=200,
                        placeholder='{\n  "installed": {\n    "client_id": "...",\n    "client_secret": "...",\n    ...\n  }\n}'
                    )
                    
                    submit_btn = st.form_submit_button("認証情報を保存", type="primary")
                    
                    if submit_btn:
                        if json_content.strip():
                            try:
                                # JSONの妥当性をチェック
                                import json
                                credentials_data = json.loads(json_content)
                                
                                # 必要なフィールドの存在確認
                                if "installed" in credentials_data:
                                    required_fields = ["client_id", "client_secret", "auth_uri", "token_uri"]
                                    missing_fields = []
                                    for field in required_fields:
                                        if field not in credentials_data["installed"]:
                                            missing_fields.append(field)
                                    
                                    if missing_fields:
                                        st.error(f"必要なフィールドが不足しています: {', '.join(missing_fields)}")
                                    else:
                                        # credentialsディレクトリが存在しない場合は作成
                                        os.makedirs("credentials", exist_ok=True)
                                        
                                        # JSONファイルを保存
                                        with open(credentials_path, 'w', encoding='utf-8') as f:
                                            json.dump(credentials_data, f, indent=2, ensure_ascii=False)
                                        
                                        st.success("✅ OAuth認証情報を保存しました！ページを更新してください。")
                                        st.rerun()
                                else:
                                    st.error("無効なJSONフォーマットです。'installed'フィールドが見つかりません。")
                                    
                            except json.JSONDecodeError as e:
                                st.error(f"JSONの解析に失敗しました: {e}")
                            except Exception as e:
                                st.error(f"認証情報の保存中にエラーが発生しました: {e}")
                        else:
                            st.warning("JSON内容を入力してください。")
        
        # 認証コード入力セクション（認証情報が設定済みの場合のみ表示）
        if os.path.exists(credentials_path):
            token_path = "credentials/token.pickle"
            if not os.path.exists(token_path):
                st.markdown("---")
                st.subheader("🔑 認証コード入力")
                st.markdown("""
                **認証手順:**
                1. OAuth認証情報が保存されました
                2. 下記のリンクをクリックしてGoogleアカウントで認証
                3. 認証後に表示されるコードを下記に入力
                """)
                
                # 認証URLを生成して表示
                try:
                    import json
                    with open(credentials_path, 'r', encoding='utf-8') as f:
                        creds_data = json.load(f)
                    
                    if "installed" in creds_data:
                        client_id = creds_data["installed"]["client_id"]
                        auth_uri = creds_data["installed"]["auth_uri"]
                        redirect_uri = creds_data["installed"]["redirect_uris"][0] if "redirect_uris" in creds_data["installed"] else "urn:ietf:wg:oauth:2.0:oob"
                        
                        # 必要なスコープを設定（URLエンコード）
                        import urllib.parse
                        scopes = [
                            "https://www.googleapis.com/auth/spreadsheets",
                            "https://www.googleapis.com/auth/drive"
                        ]
                        scope = urllib.parse.quote(" ".join(scopes))
                        auth_url = f"{auth_uri}?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&response_type=code&access_type=offline"
                        
                        st.markdown(f"🔗 **[Googleで認証する]({auth_url})**")
                        
                        # 認証コード入力フォーム
                        with st.form("auth_code_input"):
                            st.markdown("**認証コードを入力してください:**")
                            auth_code = st.text_input(
                                "認証コード", 
                                placeholder="4/0AVGzR1Aqe0m2U88_owDGYgSOmCIsJqmpRu4dQp-gcJbg64BC-DGLnPtp27aHoGfe4B_e5Q",
                                help="上記のリンクで認証後に表示されるコードを入力してください"
                            )
                            
                            if st.form_submit_button("認証を完了", type="primary"):
                                if auth_code.strip():
                                    try:
                                        # Google OAuth2 トークン交換
                                        import requests
                                        
                                        token_url = creds_data["installed"]["token_uri"]
                                        client_secret = creds_data["installed"]["client_secret"]
                                        
                                        payload = {
                                            'code': auth_code.strip(),
                                            'client_id': client_id,
                                            'client_secret': client_secret,
                                            'redirect_uri': redirect_uri,
                                            'grant_type': 'authorization_code'
                                        }
                                        
                                        response = requests.post(token_url, data=payload)
                                        
                                        if response.status_code == 200:
                                            token_data = response.json()
                                            
                                            # Credentialsオブジェクトを作成
                                            from google.oauth2.credentials import Credentials
                                            
                                            creds = Credentials(
                                                token=token_data.get('access_token'),
                                                refresh_token=token_data.get('refresh_token'),
                                                token_uri=creds_data["installed"]["token_uri"],
                                                client_id=client_id,
                                                client_secret=client_secret,
                                                scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
                                            )
                                            
                                            # トークンをファイルに保存
                                            import pickle
                                            with open(token_path, 'wb') as token_file:
                                                pickle.dump(creds, token_file)
                                            
                                            st.success("✅ Google Sheets認証が完了しました！ページを更新してください。")
                                            st.balloons()
                                            st.rerun()
                                        else:
                                            st.error(f"認証に失敗しました: {response.text}")
                                            
                                    except Exception as e:
                                        st.error(f"認証処理中にエラーが発生しました: {e}")
                                else:
                                    st.warning("認証コードを入力してください。")
                        
                except Exception as e:
                    st.error(f"認証URL生成中にエラーが発生しました: {e}")
            else:
                st.success("✅ Google Sheets認証完了済み")
                
                # 認証状態の詳細表示
                try:
                    import pickle
                    with open(token_path, 'rb') as token_file:
                        saved_creds = pickle.load(token_file)
                    
                    if hasattr(saved_creds, 'scopes'):
                        st.info(f"認証済みスコープ: {', '.join(saved_creds.scopes) if saved_creds.scopes else '不明'}")
                    else:
                        st.warning("スコープ情報が取得できません。認証をリセットすることをお勧めします。")
                
                except Exception as e:
                    st.warning(f"認証情報の確認中にエラー: {e}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("認証をリセット"):
                        try:
                            os.remove(token_path)
                            st.success("認証をリセットしました。ページを更新してください。")
                            st.rerun()
                        except Exception as e:
                            st.error(f"認証リセット中にエラーが発生しました: {e}")
                
                with col2:
                    if st.button("認証をテスト"):
                        try:
                            import pickle
                            with open(token_path, 'rb') as token_file:
                                test_creds = pickle.load(token_file)
                            
                            # 辞書形式の場合はCredentialsオブジェクトに変換
                            if isinstance(test_creds, dict):
                                from google.oauth2.credentials import Credentials
                                test_creds = Credentials(
                                    token=test_creds.get('access_token'),
                                    refresh_token=test_creds.get('refresh_token'),
                                    token_uri=test_creds.get('token_uri'),
                                    client_id=test_creds.get('client_id'),
                                    client_secret=test_creds.get('client_secret'),
                                    scopes=test_creds.get('scopes', ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
                                )
                            
                            import gspread
                            client = gspread.authorize(test_creds)
                            # テスト用スプレッドシート作成試行
                            test_sheet = client.create("aicast_auth_test")
                            test_sheet.del_worksheet(test_sheet.sheet1)  # 作成後すぐ削除
                            st.success("✅ 認証テスト成功！Google Sheetsアクセス可能です。")
                            
                        except Exception as e:
                            st.error(f"❌ 認証テスト失敗: {e}")
                            st.info("認証をリセットして再設定してください。")
        
        with app_settings_tab:
            st.subheader("🔧 アプリケーション設定")
            
            # 設定をカテゴリ別に取得
        all_settings = execute_query("SELECT * FROM app_settings ORDER BY category, key", fetch="all")
        if all_settings:
            settings_by_category = {}
            for setting in all_settings:
                category = setting['category']
                if category not in settings_by_category:
                    settings_by_category[category] = []
                settings_by_category[category].append(setting)
            
            # カテゴリごとにタブを作成
            tab_names = list(settings_by_category.keys())
            tabs = st.tabs([f"📊 {cat}" for cat in tab_names])
            
            for i, (category, settings) in enumerate(settings_by_category.items()):
                with tabs[i]:
                    st.markdown(f"### {category}設定")
                    
                    with st.form(f"settings_form_{category}"):
                        updated_values = {}
                        
                        for setting in settings:
                            key = setting['key']
                            current_value = setting['value']
                            description = setting['description']
                            
                            if key.endswith('_placeholder'):
                                # プレースホルダー設定は大きなテキストエリア
                                updated_values[key] = st.text_area(
                                    f"📝 {description}",
                                    value=current_value,
                                    height=100,
                                    key=f"setting_{key}"
                                )
                            elif key.endswith('_limit') or key.endswith('_count'):
                                # 数値設定
                                try:
                                    current_int = int(current_value)
                                    updated_values[key] = str(st.number_input(
                                        f"🔢 {description}",
                                        min_value=1,
                                        max_value=500,
                                        value=current_int,
                                        key=f"setting_{key}"
                                    ))
                                except ValueError:
                                    updated_values[key] = st.text_input(
                                        f"📝 {description}",
                                        value=current_value,
                                        key=f"setting_{key}"
                                    )
                            else:
                                # その他は通常のテキスト入力
                                updated_values[key] = st.text_input(
                                    f"📝 {description}",
                                    value=current_value,
                                    key=f"setting_{key}"
                                )
                        
                        if st.form_submit_button(f"💾 {category}設定を保存", type="primary"):
                            try:
                                for key, value in updated_values.items():
                                    update_app_setting(key, value)
                                st.success(f"✅ {category}設定を保存しました！")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 設定の保存中にエラーが発生しました: {e}")
                
        else:
            st.info("設定項目がありません。初期化中...")
            st.rerun()
        
        st.markdown("---")
        st.subheader("🐦 X (Twitter) API設定")
        
        with st.expander("X API認証設定", expanded=False):
            st.markdown("""
            **X API認証の設定手順:**
            1. [X Developer Portal](https://developer.twitter.com) にアクセス
            2. アプリケーションを作成（Read and Write権限必要）
            3. 認証キーを取得
            4. 下記のファイルを作成してアップロード
            """)
            
            # X API認証状況確認
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔍 X API認証状況確認", use_container_width=True):
                    success, message = x_poster.setup_credentials()
                    if success:
                        st.success(f"✅ {message}")
                        # アカウント情報を取得して表示
                        account_info, info_message = x_poster.get_account_info()
                        if account_info:
                            st.info(f"🐦 連携アカウント: @{account_info['username']} ({account_info['name']})")
                    else:
                        st.error(f"❌ {message}")
                
                # 詳細権限確認ボタンを追加
                if st.button("🔧 詳細権限確認", use_container_width=True):
                    with st.spinner("権限を詳細確認中..."):
                        perm_success, perm_data = x_poster.check_permissions_detailed()
                        
                        if perm_success:
                            st.success(f"✅ 詳細確認完了: {perm_data['account_type']}")
                            st.info(f"🐦 @{perm_data['username']} ({perm_data['name']})")
                            
                            # 権限テスト結果を表示
                            st.markdown("**権限テスト結果:**")
                            
                            # 読み取り権限
                            if perm_data['tests']['read_permission'] == True:
                                st.success("✅ 読み取り権限: OK")
                            else:
                                st.error(f"❌ 読み取り権限: {perm_data['tests']['read_permission']}")
                            
                            # 投稿権限
                            if perm_data['tests']['write_permission'] == True:
                                st.success("✅ 投稿権限: OK")
                            else:
                                st.error(f"❌ 投稿権限: {perm_data['tests']['write_permission']}")
                            
                            # いいね権限
                            like_perm = perm_data['tests']['like_permission']
                            if "テスト可能" in str(like_perm):
                                st.success(f"✅ いいね権限: {like_perm}")
                                
                                # いいね権限の実テストボタンを表示
                                if 'latest_tweet_id' in perm_data['tests']:
                                    latest_tweet_id = perm_data['tests']['latest_tweet_id']
                                    if st.button(f"🧪 いいね権限実テスト (投稿ID: {latest_tweet_id})", use_container_width=True):
                                        # 自分の投稿にいいね→すぐ取り消し
                                        like_success, like_msg = x_poster.like_tweet(latest_tweet_id)
                                        if like_success:
                                            st.success(f"✅ いいね権限テスト成功!")
                                            # すぐに取り消し
                                            unlike_success, unlike_msg = x_poster.unlike_tweet(latest_tweet_id)
                                            if unlike_success:
                                                st.info("ℹ️ テスト後にいいねを取り消しました")
                                            else:
                                                st.warning(f"⚠️ いいね取り消し失敗: {unlike_msg}")
                                        else:
                                            st.error(f"❌ いいね権限テスト失敗: {like_msg}")
                                            
                                            # エラー解決ガイドを表示
                                            with st.expander("💡 いいね権限エラーの解決方法", expanded=True):
                                                st.markdown("""
                                                **よくあるいいね権限エラーと対策:**
                                                
                                                1. **OAuth 2.0スコープ設定不足**
                                                   - X Developer Portalの「User authentication settings」を確認
                                                   - 以下のスコープが有効になっているか確認:
                                                     - ✅ `tweet.read`
                                                     - ✅ `tweet.write`
                                                     - ✅ `like.read` 
                                                     - ✅ `like.write` ← **重要！**
                                                     - ✅ `users.read`
                                                
                                                2. **アプリがプロジェクトに紐付いていない**
                                                   - 「Standalone App」ではなく「Project内のApp」である必要
                                                   - 新規プロジェクト作成 → その中でアプリ作成
                                                
                                                3. **API Key/Token の更新が必要**
                                                   - スコープ変更後は新しいトークンを発行
                                                   - Bearer Token、Access Token/Secret を再発行
                                                   - 認証情報をAIcast Roomで更新
                                                
                                                4. **App permissions が Read and Write になっているか**
                                                   - アプリの「Settings」→「App permissions」を確認
                                                   - 「Read and Write」に設定
                                                """)
                            else:
                                st.error(f"❌ いいね権限: {like_perm}")
                                
                        else:
                            st.error(f"❌ 詳細確認失敗: {perm_data}")
            
            with col2:
                # 設定ファイル作成支援
                st.markdown("**認証ファイル作成:**")
                st.code('''
# credentials/x_api_credentials.json
{
    "api_key": "YOUR_API_KEY",
    "api_secret": "YOUR_API_SECRET", 
    "bearer_token": "YOUR_BEARER_TOKEN",
    "access_token": "YOUR_ACCESS_TOKEN",
    "access_token_secret": "YOUR_ACCESS_TOKEN_SECRET"
}
                ''', language='json')
        
        # X API いいね機能テスト
        with st.expander("👍 X API いいね機能テスト", expanded=False):
            st.warning("""
            ⚠️ **X API プラン制限について**
            
            **FREEプラン**: いいね機能は**利用不可**
            **BASICプラン ($100/月)**: いいね 200回/24時間
            **PROプラン ($5,000/月)**: いいね 1000回/24時間
            
            💡 FREEプランでも利用可能: いいね履歴確認 (1回/15分)
            """)
            
            st.markdown("""
            **X API「いいね」機能の使用方法:**
            - 任意の投稿にいいね・いいね取り消しが可能 (BASIC以上)
            - グローバル認証またはキャスト別認証で実行
            - いいね履歴の取得は全プランで可能
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🧪 グローバル認証でテスト**")
                tweet_id_global = st.text_input(
                    "投稿ID", 
                    placeholder="例: 1234567890123456789",
                    key="global_tweet_id",
                    help="XのURLの末尾にある数字です"
                )
                
                col1_1, col1_2 = st.columns(2)
                with col1_1:
                    if st.button("👍 いいね", key="global_like", use_container_width=True):
                        if tweet_id_global:
                            success, message = x_poster.like_tweet(tweet_id_global)
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                        else:
                            st.warning("投稿IDを入力してください")
                
                with col1_2:
                    if st.button("💔 いいね取消", key="global_unlike", use_container_width=True):
                        if tweet_id_global:
                            success, message = x_poster.unlike_tweet(tweet_id_global)
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                        else:
                            st.warning("投稿IDを入力してください")
                
                if st.button("📋 いいね履歴", key="global_liked_tweets", use_container_width=True):
                    success, data = x_poster.get_liked_tweets(max_results=5)
                    if success:
                        st.success(f"✅ いいね履歴取得成功 ({data['count']}件)")
                        if data['tweets']:
                            for i, tweet in enumerate(data['tweets'], 1):
                                with st.container():
                                    st.write(f"**{i}.** ID: `{tweet['id']}`")
                                    st.write(f"📝 {tweet['text'][:100]}...")
                                    st.write(f"📅 {tweet['created_at']}")
                                    st.divider()
                    else:
                        st.error(data)
            
            with col2:
                st.markdown("**🎭 キャスト認証でテスト**")
                
                # キャスト選択
                cast_options = execute_query("""
                    SELECT c.id, c.name, cx.twitter_username 
                    FROM casts c 
                    JOIN cast_x_credentials cx ON c.id = cx.cast_id 
                    WHERE cx.is_active = 1
                """, fetch="all")
                
                if cast_options:
                    cast_names = [f"{cast['name']} (@{cast['twitter_username']})" for cast in cast_options]
                    cast_ids = [cast['id'] for cast in cast_options]
                    
                    selected_cast_idx = st.selectbox(
                        "テスト対象キャスト", 
                        range(len(cast_names)),
                        format_func=lambda x: cast_names[x],
                        key="cast_like_selection"
                    )
                    selected_cast_id = cast_ids[selected_cast_idx]
                    
                    tweet_id_cast = st.text_input(
                        "投稿ID", 
                        placeholder="例: 1234567890123456789",
                        key="cast_tweet_id"
                    )
                    
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        if st.button("👍 いいね", key="cast_like", use_container_width=True):
                            if tweet_id_cast:
                                # キャスト認証を設定
                                cast_creds = get_cast_x_credentials(selected_cast_id)
                                if cast_creds:
                                    x_poster.setup_cast_credentials(
                                        selected_cast_id,
                                        cast_creds['api_key'],
                                        cast_creds['api_secret'], 
                                        cast_creds['bearer_token'],
                                        cast_creds['access_token'],
                                        cast_creds['access_token_secret']
                                    )
                                    success, message = x_poster.like_tweet(tweet_id_cast, cast_id=selected_cast_id)
                                    if success:
                                        st.success(message)
                                    else:
                                        st.error(message)
                                else:
                                    st.error("キャストの認証情報が見つかりません")
                            else:
                                st.warning("投稿IDを入力してください")
                    
                    with col2_2:
                        if st.button("💔 いいね取消", key="cast_unlike", use_container_width=True):
                            if tweet_id_cast:
                                cast_creds = get_cast_x_credentials(selected_cast_id)
                                if cast_creds:
                                    x_poster.setup_cast_credentials(
                                        selected_cast_id,
                                        cast_creds['api_key'],
                                        cast_creds['api_secret'],
                                        cast_creds['bearer_token'], 
                                        cast_creds['access_token'],
                                        cast_creds['access_token_secret']
                                    )
                                    success, message = x_poster.unlike_tweet(tweet_id_cast, cast_id=selected_cast_id)
                                    if success:
                                        st.success(message)
                                    else:
                                        st.error(message)
                                else:
                                    st.error("キャストの認証情報が見つかりません")
                            else:
                                st.warning("投稿IDを入力してください")
                    
                    if st.button("📋 いいね履歴", key="cast_liked_tweets", use_container_width=True):
                        cast_creds = get_cast_x_credentials(selected_cast_id)
                        if cast_creds:
                            x_poster.setup_cast_credentials(
                                selected_cast_id,
                                cast_creds['api_key'],
                                cast_creds['api_secret'],
                                cast_creds['bearer_token'],
                                cast_creds['access_token'], 
                                cast_creds['access_token_secret']
                            )
                            success, data = x_poster.get_liked_tweets(cast_id=selected_cast_id, max_results=3)
                            if success:
                                st.success(f"✅ {data['account_type']} いいね履歴 ({data['count']}件)")
                                if data['tweets']:
                                    for i, tweet in enumerate(data['tweets'], 1):
                                        with st.container():
                                            st.write(f"**{i}.** ID: `{tweet['id']}`")
                                            st.write(f"📝 {tweet['text'][:80]}...")
                                            st.write(f"📅 {tweet['created_at']}")
                                            st.divider()
                            else:
                                st.error(data)
                        else:
                            st.error("キャストの認証情報が見つかりません")
                else:
                    st.info("X API認証が設定されたキャストがありません")
        
        # X API リツイート機能テスト
        with st.expander("🔄 X API リツイート機能テスト", expanded=False):
            st.success("""
            ✅ **FREEプランでもリツイート機能は利用可能！**
            
            **FREEプラン制限**: リツイート 1回/15分、リツイート取り消し 1回/15分
            **BASICプラン ($100/月)**: リツイート 5回/15分、リツイート取り消し 5回/15分
            **PROプラン ($5,000/月)**: リツイート 50回/15分、リツイート取り消し 50回/15分
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🧪 グローバル認証でテスト**")
                tweet_id_rt_global = st.text_input(
                    "投稿ID", 
                    placeholder="例: 1234567890123456789",
                    key="global_rt_tweet_id",
                    help="リツイートしたい投稿のIDを入力"
                )
                
                col1_1, col1_2 = st.columns(2)
                with col1_1:
                    if st.button("🔄 リツイート", key="global_retweet", use_container_width=True):
                        if tweet_id_rt_global:
                            success, message = x_poster.retweet(tweet_id_rt_global)
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                        else:
                            st.warning("投稿IDを入力してください")
                
                with col1_2:
                    if st.button("❌ RT取消", key="global_unretweet", use_container_width=True):
                        if tweet_id_rt_global:
                            success, message = x_poster.unretweet(tweet_id_rt_global)
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                        else:
                            st.warning("投稿IDを入力してください")
            
            with col2:
                st.markdown("**🎭 キャスト認証でテスト**")
                
                # キャスト選択（リツイート用）
                if cast_options:
                    selected_cast_idx_rt = st.selectbox(
                        "テスト対象キャスト", 
                        range(len(cast_names)),
                        format_func=lambda x: cast_names[x],
                        key="cast_rt_selection"
                    )
                    selected_cast_id_rt = cast_ids[selected_cast_idx_rt]
                    
                    tweet_id_rt_cast = st.text_input(
                        "投稿ID", 
                        placeholder="例: 1234567890123456789",
                        key="cast_rt_tweet_id"
                    )
                    
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        if st.button("🔄 リツイート", key="cast_retweet", use_container_width=True):
                            if tweet_id_rt_cast:
                                cast_creds = get_cast_x_credentials(selected_cast_id_rt)
                                if cast_creds:
                                    x_poster.setup_cast_credentials(
                                        selected_cast_id_rt,
                                        cast_creds['api_key'],
                                        cast_creds['api_secret'],
                                        cast_creds['bearer_token'],
                                        cast_creds['access_token'], 
                                        cast_creds['access_token_secret']
                                    )
                                    success, message = x_poster.retweet(tweet_id_rt_cast, cast_id=selected_cast_id_rt)
                                    if success:
                                        st.success(message)
                                    else:
                                        st.error(message)
                                else:
                                    st.error("キャストの認証情報が見つかりません")
                            else:
                                st.warning("投稿IDを入力してください")
                    
                    with col2_2:
                        if st.button("❌ RT取消", key="cast_unretweet", use_container_width=True):
                            if tweet_id_rt_cast:
                                cast_creds = get_cast_x_credentials(selected_cast_id_rt)
                                if cast_creds:
                                    x_poster.setup_cast_credentials(
                                        selected_cast_id_rt,
                                        cast_creds['api_key'],
                                        cast_creds['api_secret'],
                                        cast_creds['bearer_token'],
                                        cast_creds['access_token'],
                                        cast_creds['access_token_secret']
                                    )
                                    success, message = x_poster.unretweet(tweet_id_rt_cast, cast_id=selected_cast_id_rt)
                                    if success:
                                        st.success(message)
                                    else:
                                        st.error(message)
                                else:
                                    st.error("キャストの認証情報が見つかりません")
                            else:
                                st.warning("投稿IDを入力してください")
                else:
                    st.info("X API認証が設定されたキャストがありません")
        
        # X API コメント入りリツイート機能テスト
        with st.expander("💬 X API コメント入りリツイート機能テスト", expanded=False):
            st.success("""
            ✅ **FREEプランでもコメント入りリツイート（引用ツイート）が利用可能！**
            
            **制限**: 通常の投稿制限と同じ
            - **FREEプラン**: 17回/24時間
            - **BASICプラン ($100/月)**: 1,667回/24時間  
            - **PROプラン ($5,000/月)**: 10,000回/24時間
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🧪 グローバル認証でテスト**")
                tweet_id_quote_global = st.text_input(
                    "引用したい投稿ID", 
                    placeholder="例: 1234567890123456789",
                    key="global_quote_tweet_id",
                    help="コメント付きでリツイートしたい投稿のID"
                )
                
                comment_global = st.text_area(
                    "コメント内容",
                    placeholder="引用ツイートに追加するコメントを入力...",
                    key="global_quote_comment",
                    max_chars=280,
                    help="280文字以内でコメントを入力"
                )
                
                if st.button("💬 コメント入りリツイート", key="global_quote_tweet", use_container_width=True):
                    if tweet_id_quote_global and comment_global:
                        success, message = x_poster.quote_tweet(tweet_id_quote_global, comment_global)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.warning("投稿IDとコメント内容を入力してください")
            
            with col2:
                st.markdown("**🎭 キャスト認証でテスト**")
                
                # キャスト選択（コメント入りリツイート用）
                if cast_options:
                    selected_cast_idx_quote = st.selectbox(
                        "テスト対象キャスト", 
                        range(len(cast_names)),
                        format_func=lambda x: cast_names[x],
                        key="cast_quote_selection"
                    )
                    selected_cast_id_quote = cast_ids[selected_cast_idx_quote]
                    
                    tweet_id_quote_cast = st.text_input(
                        "引用したい投稿ID", 
                        placeholder="例: 1234567890123456789",
                        key="cast_quote_tweet_id"
                    )
                    
                    comment_cast = st.text_area(
                        "コメント内容",
                        placeholder="キャストのコメントを入力...",
                        key="cast_quote_comment",
                        max_chars=280
                    )
                    
                    if st.button("💬 コメント入りリツイート", key="cast_quote_tweet", use_container_width=True):
                        if tweet_id_quote_cast and comment_cast:
                            cast_creds = get_cast_x_credentials(selected_cast_id_quote)
                            if cast_creds:
                                x_poster.setup_cast_credentials(
                                    selected_cast_id_quote,
                                    cast_creds['api_key'],
                                    cast_creds['api_secret'],
                                    cast_creds['bearer_token'],
                                    cast_creds['access_token'], 
                                    cast_creds['access_token_secret']
                                )
                                success, message = x_poster.quote_tweet(
                                    tweet_id_quote_cast, 
                                    comment_cast, 
                                    cast_id=selected_cast_id_quote
                                )
                                if success:
                                    st.success(message)
                                else:
                                    st.error(message)
                            else:
                                st.error("キャストの認証情報が見つかりません")
                        else:
                            st.warning("投稿IDとコメント内容を入力してください")
                else:
                    st.info("X API認証が設定されたキャストがありません")
        
        st.markdown("---")
        st.subheader("⚙️ 設定の追加")
        with st.expander("新しい設定項目を追加", expanded=False):
                with st.form("add_setting_form"):
                    col1, col2 = st.columns(2)
                    new_key = col1.text_input("設定キー", placeholder="例：default_timeout")
                    new_category = col2.selectbox("カテゴリ", ["投稿生成", "UI設定", "AI設定", "その他"])
                    new_description = st.text_input("説明", placeholder="例：タイムアウト時間（秒）")
                    new_value = st.text_input("初期値", placeholder="例：30")
                    
                    if st.form_submit_button("➕ 設定を追加"):
                        if new_key and new_value and new_description:
                            try:
                                update_app_setting(new_key, new_value, new_description, new_category)
                                st.success("✅ 新しい設定を追加しました！")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 設定の追加中にエラーが発生しました: {e}")
                        else:
                            st.warning("すべての項目を入力してください。")

if __name__ == "__main__":
    main()

