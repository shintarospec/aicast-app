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
try:
    from google.cloud import secretmanager_v1 as secretmanager
except ImportError:
    secretmanager = None
import pickle

# 🔐 認証システムのインポート
from auth_system import check_password, show_auth_status, save_current_page, get_current_page

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

# AI画像投稿機能 (MCF機能と完全分離)
try:
    from ai_image_db import (
        init_image_db, execute_image_query, save_img_post, 
        update_img_post_status, get_img_post, get_img_posts_by_status,
        get_img_setting, set_img_setting
    )
    from ai_image_generator import (
        generate_ai_image, get_auto_caption, check_daily_limits,
        ai_image_generator
    )
    AI_IMAGE_AVAILABLE = True
except ImportError as e:
    AI_IMAGE_AVAILABLE = False
    print(f"AI画像投稿機能が利用できません: {e}")

# 安全な日時パースヘルパー関数
def safe_datetime_parse(date_str, default_format='%Y-%m-%d %H:%M:%S'):
    """
    安全に日時をパースする汎用関数
    データベースの不正な値に対して柔軟に対応
    """
    if not date_str:
        return None
    
    # 複数のフォーマットを試行
    formats_to_try = [
        default_format,            # 標準: '2024-01-01 12:00:00'
        '%H:%M:%S',               # 時刻のみ: '17:00:00'
        '%Y-%m-%d',               # 日付のみ: '2024-01-01'
        '%Y-%m-%d %H:%M',         # 秒なし: '2024-01-01 12:00'
        '%d/%m/%Y %H:%M:%S',      # 欧州形式
        '%d-%m-%Y %H:%M:%S',      # 欧州形式（ハイフン）
    ]
    
    for fmt in formats_to_try:
        try:
            parsed_dt = datetime.datetime.strptime(date_str, fmt)
            
            # 時刻のみの場合は今日の日付を追加
            if fmt == '%H:%M:%S':
                today = datetime.date.today()
                parsed_dt = datetime.datetime.combine(today, parsed_dt.time())
            
            return parsed_dt
        except ValueError:
            continue
    
    # すべて失敗した場合は None を返す
    print(f"⚠️ 日時パースエラー: '{date_str}' - 対応していないフォーマットです")
    return None

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
# 必須3項目（新プロンプト構造のコア）
PERSONA_REQUIRED_FIELDS = ["name", "nickname", "age"]

# オプション項目（キャラクター設定タブで管理）
PERSONA_OPTIONAL_FIELDS = [
    "birthday", "personality", "strength", "weakness", 
    "first_person", "speech_style", "catchphrase",
    "occupation", "hobby", "likes", "dislikes", "dream", "secret"
]

# 全項目（互換性維持用、段階的移行のため残す）
PERSONA_FIELDS = PERSONA_REQUIRED_FIELDS + PERSONA_OPTIONAL_FIELDS

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
    posts_table_query = "CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, cast_id INTEGER, created_at TEXT, content TEXT, theme TEXT, evaluation TEXT, advice TEXT, free_advice TEXT, status TEXT DEFAULT 'draft', posted_at TEXT, sent_status TEXT DEFAULT 'not_sent', sent_at TEXT, generated_at TEXT, scheduled_at TEXT, FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE)"
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
    
    # 新しいプロンプト構造用テーブル（柔軟な設計 - 将来の変更に対応）
    account_mission_table_query = "CREATE TABLE IF NOT EXISTS account_mission (id INTEGER PRIMARY KEY, cast_id INTEGER UNIQUE, mission TEXT, persona_design TEXT, content_strategy TEXT, final_goal TEXT, additional_notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE)"
    persona_detailed_table_query = "CREATE TABLE IF NOT EXISTS persona_detailed (id INTEGER PRIMARY KEY, cast_id INTEGER UNIQUE, archetype TEXT, occupation TEXT, residence TEXT, family_structure TEXT, symbolic_quote TEXT, x_usage_purpose TEXT, behavior_pattern TEXT, interested_topics TEXT, platform_pain_points TEXT, brand_relationship TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE)"
    sample_profiles_table_query = "CREATE TABLE IF NOT EXISTS sample_profiles (id INTEGER PRIMARY KEY, cast_id INTEGER UNIQUE, profile_text TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE)"
    sample_posts_table_query = "CREATE TABLE IF NOT EXISTS sample_posts (id INTEGER PRIMARY KEY, cast_id INTEGER, category TEXT, post_content TEXT NOT NULL, sort_order INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE)"

    queries = [casts_table_query, posts_table_query, situations_table_query, categories_table_query, advice_table_query, groups_table_query, cast_groups_table_query, tuning_history_table_query, custom_fields_table_query, send_history_table_query, app_settings_table_query, global_advice_table_query, category_advice_table_query, cast_x_credentials_table_query, cast_sheets_config_table_query, account_mission_table_query, persona_detailed_table_query, sample_profiles_table_query, sample_posts_table_query]
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
# キャラクター設定シート：{(cast_data['name'] if cast_data and 'name' in cast_data else '')}
## 1. 基本情報
- 名前: {(cast_data['name'] if cast_data and 'name' in cast_data else '')}, ニックネーム: {(cast_data['nickname'] if cast_data and 'nickname' in cast_data else '')}, 年齢: {(cast_data['age'] if cast_data and 'age' in cast_data else '')}, 誕生日: {(cast_data['birthday'] if cast_data and 'birthday' in cast_data else '')}, 出身地: {(cast_data['birthplace'] if cast_data and 'birthplace' in cast_data else '')}, 外見の特徴: {(cast_data['appearance'] if cast_data and 'appearance' in cast_data else '')}
## 2. 性格・話し方
- 性格: {(cast_data['personality'] if cast_data and 'personality' in cast_data else '')}, 長所: {(cast_data['strength'] if cast_data and 'strength' in cast_data else '')}, 短所: {(cast_data['weakness'] if cast_data and 'weakness' in cast_data else '')}, 一人称: {(cast_data['first_person'] if cast_data and 'first_person' in cast_data else '')}, 口調・語尾: {(cast_data['speech_style'] if cast_data and 'speech_style' in cast_data else '')}, 口癖: {(cast_data['catchphrase'] if cast_data and 'catchphrase' in cast_data else '')}, お客様への接し方: {(cast_data['customer_interaction'] if cast_data and 'customer_interaction' in cast_data else '')}
## 3. 背景ストーリー
- 職業／学業: {(cast_data['occupation'] if cast_data and 'occupation' in cast_data else '')}, 趣味や特技: {(cast_data['hobby'] if cast_data and 'hobby' in cast_data else '')}, 好きなもの: {(cast_data['likes'] if cast_data and 'likes' in cast_data else '')}, 嫌いなもの: {(cast_data['dislikes'] if cast_data and 'dislikes' in cast_data else '')}, 休日の過ごし方: {(cast_data['holiday_activity'] if cast_data and 'holiday_activity' in cast_data else '')}, 将来の夢: {(cast_data['dream'] if cast_data and 'dream' in cast_data else '')}, なぜこの仕事をしているのか: {(cast_data['reason_for_job'] if cast_data and 'reason_for_job' in cast_data else '')}, ちょっとした秘密: {(cast_data['secret'] if cast_data and 'secret' in cast_data else '')}
{group_text}
"""

# =========================================
# 新プロンプト生成関数（柔軟性・拡張性重視）
# =========================================

def get_account_mission_prompt(cast_id):
    """アカウント運営指針を取得してMarkdown形式で返す"""
    mission_data = execute_query(
        "SELECT mission, persona_design, content_strategy, final_goal, additional_notes FROM account_mission WHERE cast_id = ?",
        (cast_id,),
        fetch="one"
    )
    
    if not mission_data:
        return ""  # 設定なしの場合は空文字列
    
    sections = []
    
    if mission_data and mission_data['mission']:
        sections.append(f"## アカウント運営指針\n{mission_data['mission']}")
    
    if mission_data and mission_data['persona_design']:
        sections.append(f"## ペルソナ設計\n{mission_data['persona_design']}")
    
    if mission_data and mission_data['content_strategy']:
        sections.append(f"## コンテンツ戦略\n{mission_data['content_strategy']}")
    
    if mission_data and mission_data['final_goal']:
        sections.append(f"## 最終ゴール\n{mission_data['final_goal']}")
    
    if mission_data and mission_data['additional_notes']:
        sections.append(f"## 補足事項\n{mission_data['additional_notes']}")
    
    return "\n\n".join(sections)


def get_detailed_persona_prompt(cast_id):
    """詳細ペルソナを取得してCSV形式で返す"""
    persona_data = execute_query(
        """SELECT archetype, occupation, residence, family_structure, symbolic_quote, 
                  x_usage_purpose, behavior_pattern, interested_topics, platform_pain_points, brand_relationship
           FROM persona_detailed WHERE cast_id = ?""",
        (cast_id,),
        fetch="one"
    )
    
    if not persona_data:
        return ""  # 設定なしの場合は空文字列
    
    # CSV形式で構造化
    lines = []
    
    if persona_data and persona_data['archetype']:
        lines.append(f"アーキタイプ: {persona_data['archetype']}")
    
    if persona_data and persona_data['occupation']:
        lines.append(f"職業: {persona_data['occupation']}")
    
    if persona_data and persona_data['residence']:
        lines.append(f"居住地: {persona_data['residence']}")
    
    if persona_data and persona_data['family_structure']:
        lines.append(f"家族構成: {persona_data['family_structure']}")
    
    if persona_data and persona_data['symbolic_quote']:
        lines.append(f"象徴的な一言: {persona_data['symbolic_quote']}")
    
    if persona_data and persona_data['x_usage_purpose']:
        lines.append(f"X利用目的: {persona_data['x_usage_purpose']}")
    
    if persona_data and persona_data['behavior_pattern']:
        lines.append(f"行動パターン: {persona_data['behavior_pattern']}")
    
    if persona_data and persona_data['interested_topics']:
        lines.append(f"関心トピック: {persona_data['interested_topics']}")
    
    if persona_data and persona_data['platform_pain_points']:
        lines.append(f"プラットフォーム不満: {persona_data['platform_pain_points']}")
    
    if persona_data and persona_data['brand_relationship']:
        lines.append(f"ブランド関係: {persona_data['brand_relationship']}")
    
    if lines:
        return "## 詳細ペルソナ\n" + "\n".join(lines)
    else:
        return ""


def get_sample_profile_prompt(cast_id):
    """サンプルプロフィールを取得"""
    profile_data = execute_query(
        "SELECT profile_text FROM sample_profiles WHERE cast_id = ?",
        (cast_id,),
        fetch="one"
    )
    
    if not profile_data or not (profile_data and profile_data['profile_text']):
        return ""
    
    return f"## サンプルプロフィール\n{profile_data['profile_text']}"


def get_sample_posts_prompt(cast_id, category=None, limit=100):
    """サンプル投稿を取得してプロンプト形式で返す
    
    Args:
        cast_id: キャストID
        category: カテゴリ指定（Noneの場合は全カテゴリ、文字列の場合はそのカテゴリのみ）
        limit: 取得件数上限
    
    Returns:
        プロンプト文字列（カテゴリごとに整理）
    """
    if category:
        # 特定カテゴリのみ取得
        posts = execute_query(
            "SELECT category, post_content FROM sample_posts WHERE cast_id = ? AND category = ? ORDER BY sort_order, id LIMIT ?",
            (cast_id, category, limit),
            fetch="all"
        )
    else:
        # 全カテゴリ取得
        posts = execute_query(
            "SELECT category, post_content FROM sample_posts WHERE cast_id = ? ORDER BY sort_order, id LIMIT ?",
            (cast_id, limit),
            fetch="all"
        )
    
    if not posts:
        return ""
    
    # カテゴリごとに整理
    category_posts = {}
    for post in posts:
        cat = post['category'] or "その他"
        if cat not in category_posts:
            category_posts[cat] = []
        category_posts[cat].append(post['post_content'])
    
    # プロンプト生成
    sections = ["## サンプル投稿"]
    for cat, post_list in category_posts.items():
        sections.append(f"\n### {cat}")
        for i, content in enumerate(post_list, 1):
            sections.append(f"{i}. {content}")
    
    return "\n".join(sections)


def build_full_prompt(cast_id, situation_or_instruction, char_limit=140, is_custom_instruction=False):
    """フルプロンプトを構築（新プロンプト構造専用）
    
    新プロンプト構造：
    1. 基本ペルソナ（必須3項目：name, nickname, age）
    2. アカウント運営指針（オプション）
    3. 詳細ペルソナ（オプション）
    4. サンプルプロフィール（オプション）
    5. サンプル投稿（オプション）
    6. シチュエーションまたは指示
    7. 生成ルール
    
    Args:
        cast_id: キャストID
        situation_or_instruction: シチュエーション文字列または指示文字列
        char_limit: 文字数上限
        is_custom_instruction: カスタム指示かどうか
    
    Returns:
        完全なプロンプト文字列
    """
    sections = []
    
    # 1. 基本ペルソナ（必須3項目）
    cast_data = execute_query("SELECT name, nickname, age FROM casts WHERE id = ?", (cast_id,), fetch="one")
    if cast_data:
        basic_info = f"# キャラクター：{cast_data['name']}（{cast_data['nickname']}）\n年齢: {cast_data['age']}歳"
        sections.append(basic_info)
    
    # 2. アカウント運営指針（オプション）
    account_mission = get_account_mission_prompt(cast_id)
    if account_mission:
        sections.append(account_mission)
    
    # 3. 詳細ペルソナ（オプション）
    detailed_persona = get_detailed_persona_prompt(cast_id)
    if detailed_persona:
        sections.append(detailed_persona)
    
    # 4. サンプルプロフィール（オプション）
    sample_profile = get_sample_profile_prompt(cast_id)
    if sample_profile:
        sections.append(sample_profile)
    
    # 5. サンプル投稿（オプション）
    sample_posts = get_sample_posts_prompt(cast_id)
    if sample_posts:
        sections.append(sample_posts)
    
    # 6. シチュエーションまたは指示
    if is_custom_instruction:
        sections.append(f"## 投稿生成の指示\n{situation_or_instruction}")
    else:
        sections.append(f"## シチュエーション\n{situation_or_instruction}")
    
    # 7. 生成ルール
    generation_rules = f"""
## 生成ルール
- 上記のキャラクター設定・運営指針・サンプルに基づいて投稿を生成してください
- 文字数は{char_limit}文字以内に収めてください
- サンプル投稿がある場合は、同じような雰囲気・トーン・スタイルで書いてください
- 改行は適切に使用し、読みやすさを重視してください
- 投稿内容のみを生成し、説明や前置きは不要です
"""
    sections.append(generation_rules)
    
    return "\n\n".join(sections)


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

def setup_vertex_ai_oauth_simple():
    """Vertex AI用OAuth認証（Streamlit Secrets対応）"""
    try:
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        import pickle
        import json
        
        # Vertex AI に必要なスコープ
        SCOPES = [
            'https://www.googleapis.com/auth/cloud-platform',
            'https://www.googleapis.com/auth/cloud-platform.read-only'
        ]
        
        token_path = "credentials/vertex_ai_token.pickle"
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
                # OAuth設定を取得（Streamlit Secrets優先）
                oauth_config = None
                
                if Config.is_production_environment() and "google_oauth" in st.secrets:
                    # Streamlit Secrets から OAuth設定を取得
                    oauth_config = dict(st.secrets["google_oauth"])
                    oauth_config = {"installed": oauth_config}
                else:
                    # ローカル環境：ファイルから読み込み
                    credentials_path = "credentials/client_secret_909115239455-fauih26mvj1g6hksfq9pub4okse90acg.apps.googleusercontent.com.json"
                    if os.path.exists(credentials_path):
                        with open(credentials_path, 'r') as f:
                            oauth_config = json.load(f)
                
                if not oauth_config:
                    return None, "OAuth認証設定が見つかりません"
                
                # ブラウザ認証（Google Sheetsと同じパターン）
                flow = InstalledAppFlow.from_client_config(oauth_config, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # トークンを保存
            os.makedirs("credentials", exist_ok=True)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds, "Vertex AI認証成功"
    except Exception as e:
        return None, f"Vertex AI OAuth認証エラー: {str(e)}"

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

def send_image_to_cloud_functions(cast_id, image_path, tweet_content):
    """AI画像投稿をCloud Functions経由でX APIに送信"""
    try:
        # キャスト認証情報を取得
        cast_credentials = get_cast_x_credentials(cast_id)
        if not cast_credentials:
            return False, "キャストのX API認証情報が見つかりません"
        
        # キャスト名を取得
        cast_info = execute_query(
            "SELECT name, nickname FROM casts WHERE id = ?",
            (cast_id,), fetch="one"
        )
        cast_name = f"{cast_info['name']}（{cast_info['nickname']}）" if cast_info else f"Cast_{cast_id}"
        
        # 画像最適化を実行
        from image_optimizer import optimize_image_for_upload, get_image_info
        
        # 元画像の情報を取得
        original_info = get_image_info(image_path)
        print(f"元画像情報: {original_info}")
        
        # 画像を最適化（Cloud Functions用に小さくする）
        optimized_path, success, message = optimize_image_for_upload(
            image_path,
            max_size=(1024, 1024),  # Twitter推奨サイズ
            quality=80,  # 品質を少し下げる
            max_file_size_mb=3  # 3MB以下に制限
        )
        
        if not success:
            return False, f"画像最適化エラー: {message}"
        
        print(f"画像最適化完了: {message}")
        
        # 最適化された画像をbase64エンコード
        import base64
        try:
            with open(optimized_path, 'rb') as img_file:
                image_data = img_file.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                
            print(f"Base64エンコード完了: {len(image_base64)} 文字")
            
        except Exception as e:
            return False, f"画像読み込みエラー: {str(e)}"
        
        # Cloud Functions用ペイロード
        payload = {
            "action": "post_with_image",
            "text": tweet_content,
            "image_data": image_base64,
            "image_filename": os.path.basename(optimized_path),
            "cast_credentials": {
                "api_key": cast_credentials['api_key'],
                "api_secret": cast_credentials['api_secret'],
                "access_token": cast_credentials['access_token'],
                "access_token_secret": cast_credentials['access_token_secret']
            }
        }
        
        # Cloud Functions URL（環境変数から取得またはデフォルト）
        cloud_functions_url = os.environ.get(
            'X_POSTER_CLOUD_FUNCTIONS_URL',
            'https://asia-northeast1-aicast-472807.cloudfunctions.net/x-poster'
        )
        
        print(f"Cloud Functions URL: {cloud_functions_url}")
        print(f"ペイロードサイズ: {len(str(payload))} 文字")
        
        # Cloud Functionsに送信（リトライ機能付き）
        import time
        for attempt in range(3):
            try:
                print(f"送信試行 {attempt + 1}/3...")
                response = requests.post(
                    cloud_functions_url,
                    json=payload,
                    timeout=60,  # タイムアウトを延長
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'AIcast-ImagePoster/1.0'
                    }
                )
                
                print(f"レスポンスコード: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('status') == 'success':
                        tweet_id = result.get('tweet_id')
                        # 最適化された一時ファイルを削除
                        try:
                            if optimized_path != image_path and os.path.exists(optimized_path):
                                os.remove(optimized_path)
                        except:
                            pass
                        return True, f"✅ {cast_name}として画像投稿完了！Tweet ID: {tweet_id}"
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        return False, f"❌ Cloud Functions投稿エラー: {error_msg}"
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    if attempt < 2:  # 最後の試行でない場合
                        print(f"リトライします: {error_msg}")
                        time.sleep(2 ** attempt)  # 指数バックオフ
                        continue
                    return False, f"❌ Cloud Functions接続エラー: {error_msg}"
                    
            except requests.exceptions.SSLError as e:
                error_msg = f"SSL接続エラー: {str(e)}"
                if attempt < 2:
                    print(f"SSL エラー、リトライします: {error_msg}")
                    time.sleep(2 ** attempt)
                    continue
                return False, f"❌ {error_msg}"
                
            except requests.exceptions.ConnectionError as e:
                error_msg = f"接続エラー: {str(e)}"
                if attempt < 2:
                    print(f"接続エラー、リトライします: {error_msg}")
                    time.sleep(2 ** attempt)
                    continue
                return False, f"❌ {error_msg}"
                
            except requests.exceptions.Timeout as e:
                error_msg = f"タイムアウトエラー: {str(e)}"
                if attempt < 2:
                    print(f"タイムアウト、リトライします: {error_msg}")
                    time.sleep(2 ** attempt)
                    continue
                return False, f"❌ {error_msg}"
        
        # 最適化された一時ファイルを削除
        try:
            if optimized_path != image_path and os.path.exists(optimized_path):
                os.remove(optimized_path)
        except:
            pass
            
        return False, "❌ 3回の試行後も送信に失敗しました"
            
    except Exception as e:
        return False, f"❌ 画像投稿送信エラー: {str(e)}"

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

def sync_to_secret_manager(twitter_username, api_key, api_secret, bearer_token, access_token, access_token_secret):
    """データベースからSecret Managerに認証情報を自動同期"""
    try:
        # Secret Managerが利用できない場合はスキップ
        if secretmanager is None:
            return False, "Secret Manager SDKがインストールされていません"
        
        # GCPプロジェクトID取得
        project_id = os.environ.get('GCP_PROJECT', 'aicast-472807')
        
        # Secret Managerクライアント初期化
        client = secretmanager.SecretManagerServiceClient()
        
        # Secret名（既存アカウント形式に統一）
        secret_id = f"x-api-{twitter_username}"
        parent = f"projects/{project_id}"
        secret_path = f"{parent}/secrets/{secret_id}"
        
        # 認証情報をJSON形式で準備（既存アカウントと同じフィールド名）
        credentials_data = {
            "consumer_key": api_key,
            "consumer_secret": api_secret,
            "bearer_token": bearer_token,
            "access_token": access_token,
            "access_token_secret": access_token_secret
        }
        credentials_json = json.dumps(credentials_data)
        
        # Secretが存在するか確認
        try:
            client.get_secret(request={"name": secret_path})
            secret_exists = True
        except Exception:
            secret_exists = False
        
        # Secretが存在しない場合は作成
        if not secret_exists:
            client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}}
                }
            )
        
        # 新しいバージョンとして認証情報を追加
        client.add_secret_version(
            request={
                "parent": secret_path,
                "payload": {"data": credentials_json.encode("UTF-8")}
            }
        )
        
        return True, f"Secret Manager同期成功: {secret_id}"
        
    except Exception as e:
        error_msg = f"Secret Manager同期エラー: {str(e)}"
        print(error_msg)  # ログに出力
        return False, error_msg

def save_cast_x_credentials(cast_id, api_key, api_secret, bearer_token, access_token, access_token_secret, twitter_username=None, twitter_user_id=None):
    """キャストのX API認証情報を保存（Secret Manager自動同期付き）"""
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
        
        # 🔄 Secret Managerに自動同期（twitter_usernameが設定されている場合のみ）
        if twitter_username:
            success, message = sync_to_secret_manager(
                twitter_username, api_key, api_secret, bearer_token, 
                access_token, access_token_secret
            )
            if success:
                st.success(f"✅ {message}")
            else:
                st.warning(f"⚠️ データベースに保存されましたが、Secret Manager同期に失敗しました: {message}")
        
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
    """クイック承認（承認日を今日に設定）"""
    created_at_row = execute_query("SELECT created_at FROM posts WHERE id = ?", (post_id,), fetch="one")
    if created_at_row:
        created_at = created_at_row['created_at']
        # 承認日をJST（日本時間）で取得
        approval_date_jst = datetime.datetime.now(JST).date()
        # created_atから時刻部分を抽出
        if ' ' in created_at:
            time_part = created_at.split(' ')[1]
        else:
            time_part = created_at
        # 承認日（JST）+ 設定時刻で完全なdatetimeを作成
        posted_at_full = f"{approval_date_jst.strftime('%Y-%m-%d')} {time_part}"
        execute_query("UPDATE posts SET evaluation = '◎', status = 'approved', posted_at = ?, scheduled_at = ? WHERE id = ?", (posted_at_full, posted_at_full, post_id))
        st.session_state.page_status_message = ("success", f"投稿をクイック承認しました！（承認日: {approval_date_jst}）")
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
            elif Config.is_production_environment():
                # Streamlit Cloud環境でサービスアカウントが使用できない場合、OAuth認証を試行
                try:
                    oauth_creds, oauth_message = setup_vertex_ai_oauth_simple()
                    if oauth_creds:
                        vertexai.init(project=project_id, location=location, credentials=oauth_creds)
                        st.sidebar.success("🔐 OAuth認証完了（Vertex AI）")
                    else:
                        raise Exception(f"OAuth認証失敗: {oauth_message}")
                except Exception as oauth_error:
                    raise Exception(f"OAuth認証も失敗: {oauth_error}")
            else:
                # Local development or default authentication (変更なし！)
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
    menu_options = ["📊 ダッシュボード", "投稿管理", "🎨 AI画像投稿", "キャスト管理", "グループ管理", "アドバイス管理", "指針アドバイス", "システム設定"]
    
    # 保存されたページを取得（リロード後の復帰用）
    saved_page = get_current_page()
    
    # リダイレクト機能
    if st.session_state.get('redirect_to_settings'):
        page = "システム設定"
        default_index = menu_options.index("システム設定")
        st.session_state.redirect_to_settings = False  # リセット
        save_current_page("システム設定")  # ページ状態を保存
    elif st.session_state.get('dashboard_redirect'):
        page = st.session_state.dashboard_redirect
        default_index = menu_options.index(page) if page in menu_options else 1  # 投稿管理のインデックス
        save_current_page(page)  # ページ状態を保存
        # リダイレクト情報は後で削除する
    elif saved_page and saved_page in menu_options:
        # 保存されたページがある場合はそれを使用
        default_index = menu_options.index(saved_page)
        page = saved_page
    else:
        default_index = 0  # デフォルトはダッシュボード
        page = "📊 ダッシュボード"
        save_current_page("📊 ダッシュボード")
        
    # サイドバーメニューを常に表示
    selected_page = st.sidebar.radio("メニュー", menu_options, index=default_index, key="main_navigation")
    
    # ページ変更時の処理
    if selected_page != page:
        page = selected_page
        save_current_page(page)  # 新しいページ状態を保存
        st.rerun()  # ページ変更を反映
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
            
            # ウィジェットの安全な初期化（重複回避）
            content_key = f"content_{post_id}"
            eval_key = f"eval_{post_id}"
            
            # セッション状態の安全な初期化
            if content_key not in st.session_state:
                st.session_state[content_key] = post['content']
            
            # データベースと同期（ただし、ユーザー編集中は上書きしない）
            if not hasattr(st.session_state, f"{content_key}_user_modified"):
                if st.session_state.get(content_key) != post['content']:
                    st.session_state[content_key] = post['content']
            
            st.text_area("投稿内容", height=150, key=content_key)
            
            eval_options = ['未評価', '◎', '◯', '△', '✕']
            current_eval = post['evaluation'] if post['evaluation'] in eval_options else '未評価'
            st.selectbox("評価", eval_options, index=eval_options.index(current_eval), key=eval_key)

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
            
            # デバッグ: ボタンの状態確認
            print(f"🔗 投稿ID {post_id}: ボタン状態 - 承認:{do_approve}, 保存:{do_save}, 却下:{do_reject}, 再生成:{do_regenerate}")

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
                            
                            # セッション状態の安全な更新
                            new_content = clean_generated_content(response.text)
                            content_key = f"content_{post_id}"
                            
                            # ウィジェット状態を安全に更新
                            try:
                                # 既存のキーをクリア
                                if content_key in st.session_state:
                                    del st.session_state[content_key]
                                # 新しい値を設定
                                st.session_state[content_key] = new_content
                                # 修正フラグをクリア
                                if f"{content_key}_user_modified" in st.session_state:
                                    del st.session_state[f"{content_key}_user_modified"]
                                
                                print(f"🔄 投稿ID {post_id}: セッション状態更新完了: {new_content[:50]}...")
                            except Exception as widget_error:
                                print(f"⚠️ ウィジェット状態更新エラー（無視可能）: {widget_error}")
                            
                            # デバッグ情報
                            print(f"🔄 投稿ID {post_id}: データベース更新完了")
                            
                            # --- 再生成後にウィジェットのセッションキーをクリア ---
                            for k in [f"advice_{post_id}", f"free_advice_{post_id}", f"regen_char_limit_{post_id}"]:
                                if k in st.session_state:
                                    del st.session_state[k]
                            
                            # 再生成後の選択項目のリセット
                            st.session_state[f"advice_{post_id}"] = []  # アドバイスをクリア
                            st.session_state[f"free_advice_{post_id}"] = ""  # 追加アドバイスをクリア
                            st.session_state[f"regen_char_limit_{post_id}"] = 140  # 文字数を初期値に
                            
                            st.session_state.edit_status_message = ("success", "✅ 投稿を再生成しました！")
                            # ページを即座にリロードしてウィジェット競合を回避
                            st.rerun()
                        except Exception as e:
                            # ウィジェット競合エラーの特別処理
                            if "cannot be modified after the widget" in str(e):
                                print(f"⚠️ ウィジェット競合エラー（無視可能）: {str(e)}")
                                st.session_state.edit_status_message = ("success", "✅ 投稿を再生成しました！（表示を更新中...）")
                                st.rerun()
                            # 認証エラーの可能性をチェック
                            elif any(keyword.lower() in str(e).lower() for keyword in ["credential", "authentication", "unauthorized", "permission", "quota", "token"]):
                                st.session_state.edit_status_message = ("auth_error", str(e))
                            else:
                                st.session_state.edit_status_message = ("error", f"再生成中にエラーが発生しました: {str(e)}")
                st.rerun()

            if do_approve:
                print("=" * 50)
                print("🚨🚨🚨 個別承認ボタンが押されました！ 🚨🚨🚨")
                print("=" * 50)
                content = st.session_state.get(f"content_{post_id}", "")
                evaluation = st.session_state.get(f"eval_{post_id}", "未評価")
                advice = ",".join(st.session_state.get(f"advice_{post_id}", []))
                free_advice = st.session_state.get(f"free_advice_{post_id}", "")
                
                print(f"🔍 個別承認開始: 投稿ID {post_id}")
                print(f"🔍 取得データ: content長={len(content)}, evaluation={evaluation}")
                
                try:
                    # 一括承認と同じロジックを使用
                    approval_date_jst = datetime.datetime.now(JST).date()
                    print(f"🔍 Step 1: approval_date_jst: {approval_date_jst}")
                    
                    created_at_row = execute_query("SELECT created_at FROM posts WHERE id = ?", (post_id,), fetch="one")
                    print(f"🔍 Step 2: created_at_row: {created_at_row}")
                    
                    if created_at_row:
                        created_at = created_at_row['created_at']
                        print(f"🔍 Step 3: created_at: {created_at}")
                        
                        # created_atから時刻部分を抽出
                        if ' ' in created_at:
                            time_part = created_at.split(' ')[1]  # 例: '2025-10-07 14:30:00' → '14:30:00'
                        else:
                            time_part = created_at  # 時刻のみの場合（例: '14:30:00'）
                        print(f"🔍 Step 4: time_part: {time_part}")
                        
                        # 承認日（JST）+ 設定時刻で完全なdatetimeを作成（承認日を強制更新）
                        posted_at_full = f"{approval_date_jst.strftime('%Y-%m-%d')} {time_part}"
                        print(f"🔍 Step 5: posted_at_full: {posted_at_full}")
                        
                        # データベース更新
                        print(f"🔍 Step 6: データベース更新開始")
                        execute_query("UPDATE posts SET content = ?, evaluation = ?, advice = ?, free_advice = ?, status = 'approved', posted_at = ?, scheduled_at = ? WHERE id = ?", 
                                    (content, evaluation, advice, free_advice, posted_at_full, posted_at_full, post_id))
                        print(f"📅 個別承認: 投稿ID {post_id} の投稿時刻を {posted_at_full} に設定（承認日【{approval_date_jst}】+設定時刻【{time_part}】）")
                        print(f"📅 個別承認: scheduled_atも {posted_at_full} に設定")
                    else:
                        # created_at取得失敗時は承認日+現在時刻
                        print(f"🔍 created_at取得失敗: フォールバック処理")
                        current_time_jst = datetime.datetime.now(JST)
                        posted_at_full = current_time_jst.strftime('%Y-%m-%d %H:%M:%S')
                        print(f"🔍 フォールバック posted_at_full: {posted_at_full}")
                        execute_query("UPDATE posts SET content = ?, evaluation = ?, advice = ?, free_advice = ?, status = 'approved', posted_at = ?, scheduled_at = ? WHERE id = ?", 
                                    (content, evaluation, advice, free_advice, posted_at_full, posted_at_full, post_id))
                        print(f"⚠️ 個別承認: 投稿ID {post_id} のcreated_atが見つからないため承認日時 {posted_at_full} を使用")
                        print(f"⚠️ 個別承認: scheduled_atも {posted_at_full} に設定")

                    # セッション状態をクリア
                    print(f"🔍 Step 7: セッション状態クリア開始")
                    for key in list(st.session_state.keys()):
                        if key.startswith(f"content_{post_id}") or key.startswith(f"eval_{post_id}") or key.startswith(f"advice_{post_id}"):
                            del st.session_state[key]

                    # 成功メッセージと画面更新
                    print(f"🔍 Step 8: 成功処理開始")
                    st.session_state.page_status_message = ("success", f"✅ 投稿ID {post_id} を承認しました！承認日【{approval_date_jst}】+設定時刻で投稿予定日時を更新しました。")
                    clear_editing_post()
                    print(f"🔍 個別承認完了: 投稿ID {post_id}")
                    st.rerun()
                except Exception as e:
                    import traceback
                    error_traceback = traceback.format_exc()
                    print(f"❌ 個別承認エラー詳細: 投稿ID {post_id}")
                    print(f"❌ エラー内容: {str(e)}")
                    print(f"❌ スタックトレース:\n{error_traceback}")
                    st.session_state.edit_status_message = ("error", f"個別承認エラー: {str(e)}")
                    st.rerun()

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
                                        # まず sample_posts を優先してプロンプト指示を決定（新構造）。なければ既存のシチュエーションを使用
                                        sample_posts_rows = execute_query(
                                            "SELECT category, post_content FROM sample_posts WHERE cast_id = ? ORDER BY sort_order, id",
                                            (selected_cast_id,),
                                            fetch="all"
                                        )
                                        if sample_posts_rows:
                                            # sample_posts がある場合はランダムで1件を指示に使う
                                            selected_sample = random.choice(sample_posts_rows)
                                            instruction_text = selected_sample['post_content'] if selected_sample else ''
                                        else:
                                            instruction_text = selected_situation['content'] if selected_situation else ''

                                        # 新しいフルプロンプトを組み立て（フォールバックは build_full_prompt 内で実施）
                                        prompt_template = build_full_prompt(selected_cast_id, instruction_text, char_limit=char_limit, is_custom_instruction=False)
                                        
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
                                        
                                        # 直接指示用プロンプト（新プロンプト構造を利用）
                                        instruction_text = custom_instruction.strip() + variation_instruction
                                        custom_prompt = build_full_prompt(selected_cast_id, instruction_text, char_limit=custom_char_limit, is_custom_instruction=True)

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
                                    
                                    # 承認日をJST（日本時間）で取得
                                    approval_date_jst = datetime.datetime.now(JST).date()
                                    
                                    for post_key in selected_posts:
                                        post_id = post_key.replace('select_draft_', '')
                                        
                                        # 投稿の既存のcreated_atから時刻部分を取得して保持
                                        created_at_row = execute_query("SELECT created_at FROM posts WHERE id = ?", (post_id,), fetch="one")
                                        if created_at_row:
                                            created_at = created_at_row['created_at']
                                            # created_atから時刻部分を抽出
                                            if ' ' in created_at:
                                                time_part = created_at.split(' ')[1]  # 例: '2025-10-07 14:30:00' → '14:30:00'
                                            else:
                                                time_part = created_at  # 時刻のみの場合（例: '14:30:00'）
                                            
                                            # 承認日（JST）+ 設定時刻で完全なdatetimeを作成（承認日を強制更新）
                                            posted_at_full = f"{approval_date_jst.strftime('%Y-%m-%d')} {time_part}"
                                            execute_query("UPDATE posts SET status = 'approved', posted_at = ?, scheduled_at = ? WHERE id = ?", 
                                                        (posted_at_full, posted_at_full, post_id))
                                            print(f"📅 一括承認: 投稿ID {post_id} の投稿時刻を {posted_at_full} に設定（承認日【{approval_date_jst}】+設定時刻【{time_part}】）")
                                            print(f"📅 一括承認: scheduled_atも {posted_at_full} に設定")
                                        else:
                                            # フォールバック: created_atが取得できない場合は承認日+現在時刻を使用
                                            current_time_jst = datetime.datetime.now(JST)
                                            posted_at_full = current_time_jst.strftime('%Y-%m-%d %H:%M:%S')
                                            execute_query("UPDATE posts SET status = 'approved', posted_at = ?, scheduled_at = ? WHERE id = ?", 
                                                        (posted_at_full, posted_at_full, post_id))
                                            print(f"⚠️ 一括承認: 投稿ID {post_id} のcreated_atが見つからないため承認日時 {posted_at_full} を使用")
                                            print(f"⚠️ 一括承認: scheduled_atも {posted_at_full} に設定")
                                        
                                        approved_count += 1
                                        # チェックボックスの状態をクリア
                                        st.session_state[post_key] = False
                                    
                                    st.session_state.page_status_message = ("success", f"✅ {approved_count}件の投稿を一括承認しました！承認日【{approval_date_jst}】+設定時刻で投稿予定日時を更新しました。")
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
                        
                        # アドバイス選択UI（advice_listの有無に関わらず表示）
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
                                        
                                        # build_full_prompt を使って改善プロンプトを構築（フォールバック含む）
                                        instruction_text = f"元の投稿:\n{original_post['content']}\n\n改善指示:\n- {instructions_text}"
                                        improvement_prompt = build_full_prompt(original_post['cast_id'], instruction_text, char_limit=140, is_custom_instruction=True)

                                        # AI で改善
                                        response = safe_generate_content(st.session_state.gemini_model, improvement_prompt)
                                        improved_content = clean_generated_content(response.text)
                                        
                                        # チューニング履歴に記録（個別チューニングと同じ形式で比較表示）
                                        timestamp = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                                        combined_advice = ",".join(selected_advice) if selected_advice else ""
                                        # 前回の投稿と新しい投稿の比較形式で保存
                                        comparison_content = f"<span style='color: #888888'>前回の投稿:</span>\n<span style='color: #888888'>{original_post['content']}</span>\n\n**新しい投稿:**\n{improved_content}"
                                        execute_query("INSERT INTO tuning_history (post_id, timestamp, previous_content, advice_used) VALUES (?, ?, ?, ?)", 
                                                    (post_id, timestamp, comparison_content, instructions_text))
                                        
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
                                    st.session_state.page_status_message = ("success", f"🎯 {improved_count}件の投稿を改善しました！")
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
                
                approved_posts = execute_query("SELECT * FROM posts WHERE cast_id = ? AND status = 'approved' AND (sent_status = 'not_sent' OR sent_status IS NULL) ORDER BY posted_at DESC", (selected_cast_id,), fetch="all")
                if approved_posts:
                    st.info(f"{len(approved_posts)}件の承認済み投稿があります。")
                    
                    # 一括予約パネル
                    with st.expander("� 一括予約", expanded=False):
                        st.subheader("� 選択した投稿を一括予約")
                        
                        # 送信先選択
                        bulk_destination_options = [
                            ("📊 Google Sheets", "google_sheets"),
                            ("🐦 X (Twitter)", "x_api"),
                            ("📊🐦 両方に送信", "both")
                        ]
                        
                        bulk_destination = st.selectbox(
                            "一括予約先",
                            options=[opt[0] for opt in bulk_destination_options],
                            index=1,  # デフォルトで"🐦 X (Twitter)"を選択
                            key="bulk_destination"
                        )
                        
                        bulk_destination_value = next((opt[1] for opt in bulk_destination_options if opt[0] == bulk_destination), "x_api")
                        
                        st.info(f"選択した投稿を設定された時刻で{bulk_destination}に一括予約します。")
                        
                        # 一括予約実行
                        if st.button("� 選択した投稿を一括予約", type="primary", use_container_width=True):
                            selected_posts = [post_id for post_id, selected in st.session_state.items() 
                                            if post_id.startswith('select_approved_') and selected]
                            
                            if selected_posts:
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                scheduled_count = 0
                                total_posts = len(selected_posts)
                                
                                # キャスト名とIDを取得
                                current_cast = next((c for c in casts if c['name'] == selected_cast_name), None)
                                cast_name_only = current_cast['name'] if current_cast else selected_cast_name
                                cast_id = current_cast['id'] if current_cast else None
                                
                                for i, post_key in enumerate(selected_posts):
                                    try:
                                        post_id = post_key.replace('select_approved_', '')
                                        status_text.text(f"投稿ID {post_id} を予約中... ({i+1}/{total_posts})")
                                        
                                        # 投稿データを取得
                                        post_data = next((p for p in approved_posts if str(p['id']) == post_id), None)
                                        if not post_data:
                                            continue
                                        
                                        # 時刻の優先順位: scheduled_at > posted_at > created_at
                                        target_datetime = None
                                        today = datetime.date.today()
                                        
                                        if post_data['scheduled_at']:
                                            # 既にスケジュール時刻が設定されている場合
                                            target_datetime = safe_datetime_parse(post_data['scheduled_at'])
                                        elif post_data['posted_at']:
                                            # 承認時刻を使用（今日の日付で適用）
                                            posted_at_raw = post_data['posted_at']
                                            if len(posted_at_raw) > 10:  # 日付部分が含まれている場合
                                                target_datetime = safe_datetime_parse(posted_at_raw)
                                            else:
                                                # 時刻のみの場合は今日の日付を追加
                                                target_datetime = safe_datetime_parse(f"{today} {posted_at_raw}")
                                                # 今日の過去時刻の場合は明日に設定
                                                if target_datetime and target_datetime <= datetime.datetime.now():
                                                    tomorrow = today + datetime.timedelta(days=1)
                                                    target_datetime = datetime.datetime.combine(tomorrow, target_datetime.time())
                                                    print(f"📅 投稿ID {post_id}: 承認時刻が過去のため明日に調整: {target_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                                        else:
                                            # フォールバック: 作成時刻を使用
                                            target_datetime = safe_datetime_parse(post_data['created_at'])
                                        
                                        if not target_datetime:
                                            continue
                                        
                                        # 現在時刻と比較して過去の場合は自動調整
                                        now = datetime.datetime.now()
                                        
                                        if target_datetime <= now:
                                            # 過去の時刻の場合
                                            if target_datetime.date() == now.date():
                                                # 今日の過去時刻の場合は明日の同時刻に設定
                                                tomorrow = now.date() + datetime.timedelta(days=1)
                                                target_datetime = datetime.datetime.combine(tomorrow, target_datetime.time())
                                                print(f"📅 投稿ID {post_id}: 今日の過去時刻 → 明日の同時刻に自動調整: {target_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                                            else:
                                                # 過去の日付の場合は明日の同時刻に設定
                                                tomorrow = now.date() + datetime.timedelta(days=1)
                                                target_datetime = datetime.datetime.combine(tomorrow, target_datetime.time())
                                                print(f"📅 投稿ID {post_id}: 過去日付 → 明日の同時刻に自動調整: {target_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                                        else:
                                            print(f"📅 投稿ID {post_id}: 未来時刻のため調整なし: {target_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                                        
                                        # スケジュール予約として保存
                                        scheduled_at_str = target_datetime.strftime('%Y-%m-%d %H:%M:%S')
                                        execute_query("UPDATE posts SET scheduled_at = ?, sent_status = 'scheduled' WHERE id = ?", 
                                                    (scheduled_at_str, post_id))
                                        
                                        # 予約履歴を記録
                                        scheduled_at_log = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                                        execute_query("INSERT INTO send_history (post_id, destination, sent_at, scheduled_datetime, status) VALUES (?, ?, ?, ?, ?)", 
                                                    (post_id, bulk_destination_value, scheduled_at_log, scheduled_at_str, 'scheduled'))
                                        
                                        scheduled_count += 1
                                        progress_bar.progress((i + 1) / total_posts)
                                        time.sleep(0.1)  # 高速処理
                                        
                                    except Exception as e:
                                        st.error(f"投稿ID {post_id} の予約中にエラーが発生しました: {str(e)}")
                                        continue
                                
                                progress_bar.empty()
                                status_text.empty()
                                
                                if scheduled_count > 0:
                                    st.session_state.page_status_message = ("success", f"� {scheduled_count}件の投稿を一括予約しました！スケジュール投稿タブで確認できます。")
                                    st.success(f"✅ 処理完了: {scheduled_count}件の投稿を一括予約しました")
                                    
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
                                    st.image(img, caption=f"画像{i+1}: {img.name}", use_container_width=True)
                        
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
                                    actual_generated_time = safe_datetime_parse(post['generated_at'])
                                    if actual_generated_time:
                                        actual_display = actual_generated_time.strftime('%m-%d %H:%M')
                                        # 承認日時から日付のみを取得
                                        approval_date_only = safe_datetime_parse(post['posted_at']).strftime('%Y-%m-%d') if post['posted_at'] else "不明"
                                        st.caption(f"⏰ 作成: {actual_display} | 🕐 投稿予定: {scheduled_display} | 承認日: {approval_date_only} | 評価: {post['evaluation']} | アドバイス: {full_advice_str}{status_info}")
                                    else:
                                        # 承認日時から日付のみを取得
                                        approval_date_only = safe_datetime_parse(post['posted_at']).strftime('%Y-%m-%d') if post['posted_at'] else "不明"
                                        st.caption(f"⏰ 作成: エラー | 🕐 投稿予定: {scheduled_display} | 承認日: {approval_date_only} | 評価: {post['evaluation']} | アドバイス: {full_advice_str}{status_info}")
                                else:
                                    # 古いデータ（generated_atがない場合）
                                    # 承認日時から日付のみを取得
                                    approval_date_only = safe_datetime_parse(post['posted_at']).strftime('%Y-%m-%d') if post['posted_at'] else "不明"
                                    st.caption(f"🕐 生成時刻: {scheduled_display} | 承認日: {approval_date_only} | 評価: {post['evaluation']} | アドバイス: {full_advice_str}{status_info}")
                                
                                # スケジュール状態に応じたアイコン表示
                                if post['sent_status'] == 'scheduled':
                                    st.info(post['content'], icon="📅")
                                else:
                                    st.success(post['content'], icon="✔")
                            
                            with col_datetime:
                                # 投稿時刻の取得（スケジュール投稿がある場合は scheduled_at を優先）
                                if post['scheduled_at'] and post['sent_status'] == 'scheduled':
                                    # スケジュール投稿として保存されている場合
                                    current_scheduled_datetime = safe_datetime_parse(post['scheduled_at'])
                                    original_datetime = current_scheduled_datetime
                                    created_at_dt = safe_datetime_parse(post['created_at'])
                                    created_at_str = created_at_dt.strftime('%H:%M') if created_at_dt else 'N/A'
                                    st.caption(f"📅 スケジュール時刻: {current_scheduled_datetime.strftime('%m-%d %H:%M')} | 🕒 元の投稿時刻: {created_at_str}")
                                else:
                                    # 通常の投稿または未スケジュール
                                    original_datetime = safe_datetime_parse(post['created_at'])
                                    st.caption(f"🕒 元の投稿時刻: {original_datetime.strftime('%H:%M')}")
                                
                                # シンプルな時刻設定UI
                                
                                # 現在時刻の取得と適切な初期値設定
                                now = datetime.datetime.now(JST)
                                today = datetime.date.today()
                                
                                # 時刻取得の優先順位（scheduled_at > posted_at > created_at）
                                # 安全な日時取得（優先順位: scheduled_at > posted_at > created_at）
                                
                                if post['scheduled_at']:
                                    parsed_dt = safe_datetime_parse(post['scheduled_at'])
                                    if parsed_dt:
                                        current_datetime = parsed_dt
                                        st.info("📅 保存済み予約時刻を表示中")
                                elif post['posted_at']:
                                    parsed_dt = safe_datetime_parse(post['posted_at'])
                                    if parsed_dt:
                                        current_datetime = parsed_dt
                                        st.info("🕐 承認時刻を表示中")
                                else:
                                    parsed_dt = safe_datetime_parse(post['created_at'])
                                    if parsed_dt:
                                        current_datetime = parsed_dt
                                        st.info("� 作成時刻を表示中")
                                
                                # パースに失敗した場合は現在時刻 + 10分を初期値に
                                if not current_datetime:
                                    current_datetime = datetime.datetime.now() + datetime.timedelta(minutes=10)
                                    st.warning("⚠️ 保存済み時刻の取得に失敗しました。現在時刻を初期値にします。")
                                
                                # 過去の投稿の場合は現在時刻を初期値に
                                if current_datetime.date() < today:
                                    initial_date = today
                                    initial_hour = now.hour
                                    initial_minute = now.minute
                                    st.warning("⚠️ 過去の投稿のため、現在時刻を初期値として設定しています")
                                else:
                                    initial_date = current_datetime.date()
                                    initial_hour = current_datetime.hour
                                    initial_minute = current_datetime.minute
                                
                                # 日付選択
                                send_date = st.date_input(
                                    "📅 送信日",
                                    value=initial_date,
                                    min_value=today,
                                    key=f"send_date_{post['id']}"
                                )
                                
                                # 時刻入力方式の選択
                                time_input_method = st.radio(
                                    "時刻入力方式",
                                    ["🔢 数値入力（1分単位）", "📋 プルダウン選択（5分刻み）"],
                                    key=f"time_method_{post['id']}",
                                    horizontal=True
                                )
                                
                                if time_input_method == "🔢 数値入力（1分単位）":
                                    # 数値入力による1分単位設定
                                    col_hour, col_min = st.columns(2)
                                    with col_hour:
                                        send_hour = st.number_input(
                                            "時（0-23）",
                                            min_value=0,
                                            max_value=23,
                                            value=initial_hour,
                                            key=f"hour_num_{post['id']}"
                                        )
                                    with col_min:
                                        send_minute = st.number_input(
                                            "分（0-59）",
                                            min_value=0,
                                            max_value=59,
                                            value=initial_minute,
                                            key=f"minute_num_{post['id']}"
                                        )
                                else:
                                    # プルダウン選択による5分刻み設定
                                    col_hour, col_min = st.columns(2)
                                    with col_hour:
                                        hour_options = list(range(24))
                                        hour_labels = [f"{h:02d}時" for h in hour_options]
                                        selected_hour_label = st.selectbox(
                                            "時",
                                            options=hour_labels,
                                            index=initial_hour,
                                            key=f"hour_select_{post['id']}"
                                        )
                                        send_hour = hour_options[hour_labels.index(selected_hour_label)]
                                    
                                    with col_min:
                                        minute_options = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
                                        minute_labels = [f"{m:02d}分" for m in minute_options]
                                        closest_minute = min(minute_options, key=lambda x: abs(x - initial_minute))
                                        default_index = minute_options.index(closest_minute)
                                        selected_minute_label = st.selectbox(
                                            "分",
                                            options=minute_labels,
                                            index=default_index,
                                            key=f"minute_select_{post['id']}"
                                        )
                                        send_minute = minute_options[minute_labels.index(selected_minute_label)]
                                
                                # 送信時刻の表示と時間差計算
                                send_time = datetime.time(send_hour, send_minute)
                                scheduled_datetime = datetime.datetime.combine(send_date, send_time)
                                
                                # 現在時刻との差を計算
                                time_diff = scheduled_datetime - now.replace(tzinfo=None)
                                if time_diff.total_seconds() > 0:
                                    hours = int(time_diff.total_seconds() // 3600)
                                    minutes = int((time_diff.total_seconds() % 3600) // 60)
                                    st.success(f"📅 {scheduled_datetime.strftime('%Y-%m-%d %H:%M')} に送信予定（{hours}時間{minutes}分後）")
                                else:
                                    st.error("⚠️ 過去の時刻が選択されています")
                                
                                # 時刻保存ボタン
                                if st.button("💾 時刻を保存", key=f"save_time_{post['id']}", use_container_width=True):
                                    try:
                                        execute_query(
                                            "UPDATE posts SET scheduled_at = ? WHERE id = ?",
                                            (scheduled_datetime.strftime('%Y-%m-%d %H:%M:%S'), post['id'])
                                        )
                                        st.session_state.page_status_message = ("success", f"💾 投稿ID {post['id']} の時刻を {scheduled_datetime.strftime('%Y-%m-%d %H:%M')} で保存しました")
                                        st.rerun()
                                    except Exception as e:
                                        st.session_state.page_status_message = ("error", f"時刻保存エラー: {str(e)}")
                                        st.rerun()
                                    
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
                                    index=1,  # デフォルトで"🐦 X (Twitter)"を選択
                                    key=f"destination_{post['id']}"
                                )
                                
                                # 選択された送信先に応じてボタンのラベルを変更
                                destination_value = next((opt[1] for opt in destination_options if opt[0] == selected_destination), "x_api")
                                button_label = "📤 送信" if destination_value == "both" else selected_destination
                                
                                if st.button(button_label, key=f"send_{post['id']}", type="primary", use_container_width=True):
                                    
                                    # 現在選択中のキャスト名のnameのみを取得
                                    current_cast = next((c for c in casts if c['name'] == selected_cast_name), None)
                                    cast_name_only = current_cast['name'] if current_cast else selected_cast_name
                                    cast_id = current_cast['id'] if current_cast else None
                                    
                                    # 送信時刻の決定（保存済み時刻を最優先）
                                    if post['scheduled_at']:
                                        # 保存済みの予約時刻を使用
                                        final_scheduled_datetime = datetime.datetime.strptime(post['scheduled_at'], '%Y-%m-%d %H:%M:%S')
                                        st.info(f"📅 保存済み予約時刻 {final_scheduled_datetime.strftime('%Y-%m-%d %H:%M')} で送信")
                                    else:
                                        # UIで設定中の時刻を使用
                                        final_scheduled_datetime = scheduled_datetime
                                        st.info(f"📅 設定中の時刻 {final_scheduled_datetime.strftime('%Y-%m-%d %H:%M')} で送信")
                                    
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
                                    col_content, col_action = st.columns([3, 1])
                                    
                                    with col_content:
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
                                    
                                    with col_action:
                                        if st.button("↩️ 承認済みに戻す", key=f"return_approved_{post['id']}", use_container_width=True):
                                            try:
                                                execute_query(
                                                    "UPDATE posts SET sent_status = 'not_sent' WHERE id = ?",
                                                    (post['id'],)
                                                )
                                                print(f"🔄 投稿ID {post['id']} を承認済み一覧に戻しました")
                                                print(f"   - 承認時間: {post.get('posted_at', 'N/A')}")
                                                print(f"   - 作成時間: {post.get('created_at', 'N/A')}")
                                                print(f"   - スケジュール: {post.get('scheduled_at', 'N/A')}")
                                                print(f"   - 送信状態: {post.get('sent_status', 'N/A')} → not_sent")
                                                
                                                st.session_state.page_status_message = ("success", f"↩️ 投稿ID {post['id']} を承認済み一覧に戻しました")
                                                st.rerun()
                                            except Exception as e:
                                                st.session_state.page_status_message = ("error", f"承認済みに戻すエラー: {str(e)}")
                                                st.rerun()
                                    
                                    st.markdown("---")
                        else:
                            st.info("待機中のスケジュール投稿はありません")
                    
                    with col2:
                        st.subheader(f"✅ 実行済み ({len(completed_posts)}件)")
                        if completed_posts:
                            for post in completed_posts[:5]:  # 最新5件のみ表示
                                with st.container():
                                    scheduled_at = safe_datetime_parse(post['scheduled_at'])
                                    sent_at_raw = post['sent_at']
                                    
                                    # sent_atをJSTに変換
                                    if sent_at_raw:
                                        try:
                                            # ISO形式の場合（例：2025-10-07T14:50:02.514261）
                                            if 'T' in sent_at_raw:
                                                sent_at_dt = datetime.datetime.fromisoformat(sent_at_raw.replace('Z', '+00:00'))
                                                # UTCからJSTに変換（+9時間）
                                                sent_at_jst = sent_at_dt + datetime.timedelta(hours=9)
                                                sent_at_display = sent_at_jst.strftime('%m-%d %H:%M:%S')
                                            else:
                                                # 既にローカル形式の場合
                                                sent_at_dt = safe_datetime_parse(sent_at_raw)
                                                sent_at_display = sent_at_dt.strftime('%m-%d %H:%M:%S') if sent_at_dt else sent_at_raw
                                        except:
                                            sent_at_display = sent_at_raw
                                    else:
                                        sent_at_display = "不明"
                                    
                                    st.success(post['content'][:100] + "...")
                                    if scheduled_at:
                                        st.caption(f"📅 予定: {scheduled_at.strftime('%m-%d %H:%M')} | ✅ 実行: {sent_at_display}")
                                    else:
                                        st.caption(f"📅 予定: 不明 | ✅ 実行: {sent_at_display}")
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

    elif page == "🎨 AI画像投稿":
        if not AI_IMAGE_AVAILABLE:
            st.error("🚫 AI画像投稿機能が利用できません")
            st.info("必要なモジュールがインストールされていない可能性があります")
            with st.expander("📋 解決方法"):
                st.markdown("""
                **必要なパッケージをインストール:**
                ```bash
                pip install google-cloud-aiplatform
                ```
                """)
            st.stop()
        
        # 認証状況をチェック
        try:
            adc_file = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
            if not os.path.exists(adc_file):
                st.error("🔐 Google Cloud認証が設定されていません")
                st.markdown("""
                **📋 認証設定方法:**
                1. 左サイドバーの「システム設定」をクリック
                2. 「🔐 Google Cloud認証」タブを開く
                3. 認証情報を設定してください
                """)
                if st.button("🔧 認証設定に移動", type="primary"):
                    st.session_state['redirect_to_settings'] = True
                    st.rerun()
                st.stop()
            else:
                # 認証ファイルの基本情報を表示
                stat = os.stat(adc_file)
                st.success(f"✅ Google Cloud認証設定済み (更新: {datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')})")
                
        except Exception as e:
            st.error(f"認証チェックエラー: {e}")
            st.stop()
        
        # 画像投稿専用DBを初期化
        init_image_db()
        
        # Geminiモデルの初期化（投稿管理と同じ処理）
        if 'gemini_model' not in st.session_state:
            try:
                # APIインポートを動的に決定
                try:
                    from vertexai.generative_models import GenerativeModel
                    api_version = "stable"
                except ImportError:
                    from vertexai.preview.generative_models import GenerativeModel
                    api_version = "preview"
                
                # シンプルモデル選択
                selected_model = st.session_state.get('selected_model_name', 'gemini-2.5-flash')
                
                if not selected_model or selected_model.strip() == "":
                    selected_model = 'gemini-2.5-flash'  # デフォルト
                
                try:
                    st.session_state.gemini_model = GenerativeModel(selected_model)
                    print(f"✅ AI画像投稿: Geminiモデル初期化完了 ({selected_model})")
                except Exception as model_error:
                    print(f"❌ AI画像投稿: Geminiモデル初期化失敗: {model_error}")
                    st.session_state.gemini_model = None
                    
            except Exception as e:
                print(f"❌ AI画像投稿: Gemini初期化エラー: {e}")
                st.session_state.gemini_model = None
        
        st.title("🎨 AI画像投稿")
        st.markdown("---")
        
        # キャスト一覧を取得（MCF DBから）
        casts = execute_query("SELECT id, name, nickname FROM casts ORDER BY name", fetch="all")
        if not casts:
            st.warning("⚠️ キャストが登録されていません")
            st.info("「キャスト管理」でキャストを作成してください")
            st.stop()
        
        # タブメニュー
        tab1, tab2, tab3 = st.tabs(["🎨 新規作成", "📋 投稿履歴", "📊 統計"])
        
        with tab1:
            st.subheader("🎨 新規画像投稿")
            
            # キャスト選択
            cast_options = [f"{cast['name']} ({cast['nickname']})" for cast in casts]
            selected_cast_index = st.selectbox(
                "投稿するキャスト",
                range(len(cast_options)),
                format_func=lambda x: cast_options[x],
                key="ai_image_cast_selector"
            )
            
            selected_cast = casts[selected_cast_index]
            cast_id = selected_cast['id']
            cast_name = selected_cast['name']
            
            # 投稿管理スタイルのレイアウト
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # 画像の取得方法を選択（一時的にアップロードのみ）
                st.info("💡 現在は画像アップロード機能のみ利用可能です")
                image_method = "📁 ファイルアップロード"
                
                st.markdown("---")
                
                # ファイルアップロードセクション
                st.subheader("📁 画像ファイルアップロード")
                
                # 画像アップロードセクション
                uploaded_file = st.file_uploader(
                    "画像ファイルを選択",
                    type=['png', 'jpg', 'jpeg', 'gif', 'webp'],
                    help="対応形式: PNG, JPG, JPEG, GIF, WebP（最大10MB）",
                    key=f"ai_image_uploader_{st.session_state.get('uploader_reset_counter', 0)}"
                )
                
                if uploaded_file is not None:
                    # ファイルサイズチェック
                    if uploaded_file.size > 10 * 1024 * 1024:  # 10MB
                        st.error("ファイルサイズが10MBを超えています")
                    else:
                        # 画像を表示
                        st.image(uploaded_file, caption="アップロードされた画像", use_container_width=True)
                        
                        # アップロードボタン
                        if st.button("📁 画像を保存", key="save_uploaded_image", type="primary"):
                            try:
                                # temp_imagesディレクトリを作成
                                os.makedirs("temp_images", exist_ok=True)
                                
                                # ファイルを保存
                                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                                file_extension = uploaded_file.name.split('.')[-1]
                                saved_filename = f"uploaded_{timestamp}_{cast_name}.{file_extension}"
                                saved_path = f"temp_images/{saved_filename}"
                                
                                with open(saved_path, "wb") as f:
                                    f.write(uploaded_file.getbuffer())
                                
                                # セッション状態に保存
                                st.session_state.generated_image_path = saved_path
                                st.session_state.generated_prompt = f"アップロード画像: {uploaded_file.name}"
                                
                                # アップロード画像の場合は、ファイル名を基本プロンプトとして設定
                                st.session_state.original_image_prompt = f"アップロード画像: {uploaded_file.name}"
                                
                                st.session_state.selected_cast_id = cast_id
                                st.session_state.selected_cast_name = cast_name
                                st.session_state.image_source = "uploaded"
                                
                                st.success("✅ 画像が保存されました！")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"画像の保存に失敗しました: {e}")
            
            with col2:
                # サイドパネル：投稿設定
                if (st.session_state.get('generated_image_path') and 
                    os.path.exists(st.session_state.generated_image_path) and
                    st.session_state.get('selected_cast_id') and
                    st.session_state.get('image_source')):
                    st.markdown("### 📤 投稿設定")
                    
                    # 画像のソースを表示
                    source_text = "AI生成" if st.session_state.get('image_source') == "ai_generated" else "アップロード"
                    st.caption(f"画像ソース: {source_text}")
                    
                    # 小さく画像を再表示
                    st.image(st.session_state.generated_image_path, caption=f"{source_text}画像", width=200)
                    
                    # コメント生成指示（投稿管理スタイル）
                    user_instruction = st.text_area(
                        "💬 コメント指示",
                        placeholder="例: 可愛らしい感じで、猫好きアピールを入れて",
                        help="AIがコメントを生成する際の特別な指示",
                        key="ai_comment_instruction_main",
                        height=80
                    )
                    
                    # AIコメント生成ボタン
                    if st.button("🤖 AIコメント生成", key="generate_comment", type="secondary"):
                        with st.spinner("AIコメントを生成中..."):
                            # 投稿管理と同じ方法でコメント生成
                            cast_id = st.session_state.get('selected_cast_id')
                            cast_name = st.session_state.get('selected_cast_name', '')
                            
                            # 適切なプロンプトを決定
                            original_prompt = st.session_state.get('original_image_prompt', '')
                            
                            # プロンプトの優先順位を改善
                            if user_instruction and user_instruction.strip():
                                # ユーザー指示が最優先
                                image_context = user_instruction.strip()
                            elif original_prompt and not original_prompt.startswith('アップロード画像:'):
                                # AI生成のオリジナルプロンプト
                                image_context = original_prompt
                            else:
                                # アップロード画像の場合は汎用的な指示
                                image_context = "アップロードされた画像"
                            
                            # 投稿管理と同じGeminiモデルチェック
                            if st.session_state.get('gemini_model'):
                                try:
                                    # キャスト情報を取得
                                    if cast_id:
                                        cast_details = execute_query(
                                            "SELECT * FROM casts WHERE id = ?", 
                                            (cast_id,)
                                        )
                                        if cast_details:
                                            cast_row = execute_query("SELECT name, nickname, age FROM casts WHERE id = ?", (cast_details[0],), fetch="one")
                                            if cast_row:
                                                persona_sheet = f"# キャラクター：{cast_row.get('name','')}（{cast_row.get('nickname','')}）\n年齢: {cast_row.get('age','')}歳"
                                            else:
                                                persona_sheet = f"キャスト名: {cast_name}"
                                        else:
                                            persona_sheet = f"キャスト名: {cast_name}"
                                    else:
                                        persona_sheet = f"キャスト名: {cast_name}"
                                    
                                    # 投稿管理と完全に同じプロンプト形式
                                    caption_prompt = f"""# ペルソナ
{persona_sheet}

# 投稿指示
{image_context}

# ルール
上記の指示に従って、このキャラクターらしいSNS投稿を**140文字以内**で生成してください。キャラクターの個性、口調、趣味嗜好を反映させてください。"""
                                    
                                    # 投稿管理と同じsafe_generate_content使用
                                    auto_caption = safe_generate_content(st.session_state.gemini_model, caption_prompt)
                                    
                                    if auto_caption and hasattr(auto_caption, 'text') and auto_caption.text.strip():
                                        auto_caption_text = clean_generated_content(auto_caption.text)
                                        
                                        # 文字数制限チェック（140文字）
                                        if len(auto_caption_text) > 140:
                                            auto_caption_text = auto_caption_text[:137] + "..."
                                        
                                        st.session_state.auto_caption = auto_caption_text
                                        st.success("✅ コメント生成完了！")
                                    else:
                                        # auto_captionが空またはNoneの場合
                                        raise ValueError("生成されたコンテンツが空です")
                                    
                                except Exception as e:
                                    # シンプルなフォールバック
                                    if image_context and image_context.strip():
                                        hashtag = image_context.replace(' ', '').replace('　', '')[:10]
                                        auto_caption = f"素晴らしい画像ですね！ #{hashtag}" if hashtag else "素晴らしい画像ですね！"
                                    else:
                                        auto_caption = "素晴らしい画像ですね！"
                                    
                                    st.session_state.auto_caption = auto_caption
                                    st.error(f"⚠️ AI生成に失敗しました: {str(e)}")
                                    st.info("💡 フォールバック処理でコメントを生成しました。")
                            else:
                                # Geminiモデルが利用できない場合
                                auto_caption = f"画像を投稿しました！"
                                st.session_state.auto_caption = auto_caption
                                st.info("💡 Geminiモデルが利用できないため、フォールバック処理でコメントを生成しました。")
                            
                            st.rerun()
                    
                    # === 生成されたコメントのチューニング機能 ===
                    if st.session_state.get('auto_caption'):
                        st.markdown("### 🎯 コメントチューニング")
                        
                        # チューニングオプション
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # 感情・トーン調整
                            tone_options = {
                                "そのまま": "",
                                "もっと楽しく": "より楽しく明るい表現に",
                                "もっと丁寧に": "より丁寧で上品な表現に", 
                                "もっとカジュアルに": "よりカジュアルでフレンドリーな表現に",
                                "もっと専門的に": "より専門的で詳しい表現に",
                                "もっと簡潔に": "より簡潔で短い表現に"
                            }
                            
                            selected_tone = st.selectbox(
                                "🎭 トーン調整",
                                options=list(tone_options.keys()),
                                help="生成されたコメントのトーンを調整できます"
                            )
                        
                        with col2:
                            # 追加要素
                            add_elements = st.multiselect(
                                "➕ 追加要素",
                                ["絵文字を追加", "ハッシュタグを追加", "質問を追加", "感想を追加", "おすすめポイントを追加"],
                                help="コメントに追加したい要素を選択"
                            )
                        
                        # 自由記述でのチューニング指示
                        custom_tuning = st.text_area(
                            "✏️ 自由チューニング指示",
                            placeholder="例: もっと親しみやすく、猫好きアピールを強めて、関西弁で",
                            help="具体的なチューニング指示を入力してください",
                            height=60
                        )
                        
                        # チューニング実行ボタン
                        col_tune, col_restore = st.columns([2, 1])
                        with col_tune:
                            if st.button("🔄 コメントを再生成", key="tune_comment"):
                                if selected_tone != "そのまま" or add_elements or custom_tuning.strip():
                                    with st.spinner("コメントを再調整中..."):
                                        # チューニング指示を組み立て
                                        tuning_instructions = []
                                        
                                        if selected_tone != "そのまま":
                                            tuning_instructions.append(tone_options[selected_tone])
                                        
                                        if add_elements:
                                            for element in add_elements:
                                                if element == "絵文字を追加":
                                                    tuning_instructions.append("適切な絵文字を追加")
                                                elif element == "ハッシュタグを追加":
                                                    tuning_instructions.append("関連するハッシュタグを追加")
                                                elif element == "質問を追加":
                                                    tuning_instructions.append("読者への質問を追加")
                                                elif element == "感想を追加":
                                                    tuning_instructions.append("個人的な感想を追加")
                                                elif element == "おすすめポイントを追加":
                                                    tuning_instructions.append("おすすめポイントを追加")
                                        
                                        if custom_tuning.strip():
                                            tuning_instructions.append(custom_tuning.strip())
                                        
                                        # 元のコメントを基にしたチューニングプロンプト
                                        try:
                                            cast_id = st.session_state.get('selected_cast_id')
                                            if cast_id:
                                                cast_details = execute_query("SELECT * FROM casts WHERE id = ?", (cast_id,))
                                                if cast_details:
                                                    cast_row = execute_query("SELECT name, nickname, age FROM casts WHERE id = ?", (cast_details[0],), fetch="one")
                                                    if cast_row:
                                                        persona_sheet = f"# キャラクター：{cast_row.get('name','')}（{cast_row.get('nickname','')}）\n年齢: {cast_row.get('age','')}歳"
                                                    else:
                                                        persona_sheet = f"キャスト名: {st.session_state.get('selected_cast_name', '')}"
                                                else:
                                                    persona_sheet = f"キャスト名: {st.session_state.get('selected_cast_name', '')}"
                                            else:
                                                persona_sheet = f"キャスト名: {st.session_state.get('selected_cast_name', '')}"
                                            
                                            original_comment = st.session_state.get('auto_caption', '')
                                            tuning_prompt = f"""# ペルソナ
{persona_sheet}

# 元のコメント
{original_comment}

# チューニング指示
以下の指示に従って、元のコメントを調整してください：
{' / '.join(tuning_instructions)}

# ルール
- 元のコメントの良い部分は残しつつ、指示に従って調整してください
- このキャラクターらしさを保ってください
- **140文字以内**で調整してください
- 自然で魅力的な投稿にしてください"""
                                            
                                            if st.session_state.get('gemini_model'):
                                                tuned_comment = safe_generate_content(st.session_state.gemini_model, tuning_prompt)
                                                if tuned_comment and hasattr(tuned_comment, 'text') and tuned_comment.text.strip():
                                                    tuned_text = clean_generated_content(tuned_comment.text)
                                                    if len(tuned_text) > 140:
                                                        tuned_text = tuned_text[:137] + "..."
                                                    st.session_state.auto_caption = tuned_text
                                                    st.success("✅ コメントを再調整しました！")
                                                    st.rerun()
                                                else:
                                                    st.error("チューニングに失敗しました")
                                            else:
                                                st.error("Geminiモデルが利用できません")
                                        except Exception as e:
                                            st.error(f"チューニングエラー: {str(e)}")
                                else:
                                    st.warning("チューニング指示を選択または入力してください")
                        
                        with col_restore:
                            if st.button("🔙 元に戻す", key="restore_original"):
                                if 'original_auto_caption' in st.session_state:
                                    st.session_state.auto_caption = st.session_state.original_auto_caption
                                    st.success("元のコメントに戻しました")
                                    st.rerun()
                                else:
                                    st.warning("元のコメントが見つかりません")
                        
                        # 元のコメントを保存（初回のみ）
                        if 'original_auto_caption' not in st.session_state and st.session_state.get('auto_caption'):
                            st.session_state.original_auto_caption = st.session_state.auto_caption
                        
                        st.divider()
                    
                    # ツイート内容の編集
                    # セッション状態から値を取得し、ウィジェットキーに直接設定
                    if 'tweet_content_for_image' not in st.session_state:
                        st.session_state.tweet_content_for_image = st.session_state.get('auto_caption', '')
                    elif st.session_state.get('auto_caption') and st.session_state.tweet_content_for_image != st.session_state.auto_caption:
                        # auto_captionが更新されたら、tweet_contentも更新
                        st.session_state.tweet_content_for_image = st.session_state.auto_caption
                    
                    tweet_content = st.text_area(
                        "ツイート内容",
                        max_chars=280,
                        help="画像と一緒に投稿するテキスト（280文字以内）",
                        key="tweet_content_for_image",
                        height=120
                    )
                    
                    # 文字数表示
                    char_count = len(tweet_content)
                    if char_count > 280:
                        st.error(f"文字数オーバー: {char_count}/280")
                    else:
                        st.info(f"文字数: {char_count}/280")
                    
                    # 投稿ボタン
                    col_post, col_reset = st.columns([2, 1])
                    with col_post:
                        post_button = st.button("📤 X投稿", key="post_ai_image", type="primary")
                    with col_reset:
                        if st.button("🔄", key="reset_image", help="リセット"):
                            # セッション状態をクリア
                            image_path_to_cleanup = st.session_state.get('generated_image_path')
                            
                            # すべての関連セッション状態を削除
                            all_keys_to_clear = [
                                'generated_image_path', 'generated_prompt', 'original_image_prompt',
                                'selected_cast_id', 'selected_cast_name', 'auto_caption', 
                                'image_source', 'user_instruction', 'original_auto_caption'
                            ]
                            for key in all_keys_to_clear:
                                if key in st.session_state:
                                    del st.session_state[key]
                            
                            # ファイルアップローダーをリセット
                            st.session_state.uploader_reset_counter = st.session_state.get('uploader_reset_counter', 0) + 1
                            
                            # 一時画像ファイルを削除
                            if image_path_to_cleanup and os.path.exists(image_path_to_cleanup):
                                try:
                                    os.remove(image_path_to_cleanup)
                                except Exception as e:
                                    pass  # エラーは無視
                            
                            st.success("リセットしました")
                            time.sleep(0.5)
                            st.rerun()
                    
                    if post_button:
                        # キャスト情報の確認
                        if not st.session_state.get('selected_cast_id'):
                            st.error("❌ キャストが選択されていません")
                            st.info("💡 まず画像を生成またはアップロードしてキャストを選択してください")
                            st.stop()
                        
                        if not st.session_state.get('selected_cast_name'):
                            st.error("❌ キャスト名が設定されていません")
                            st.stop()
                        
                        # 投稿処理を実行
                        cast_credentials = get_cast_x_credentials(st.session_state.selected_cast_id)
                        
                        if not cast_credentials:
                            st.error(f"❌ {st.session_state.selected_cast_name} のX API認証情報が設定されていません")
                            st.info("「キャスト管理」でX API認証情報を設定してください")
                        else:
                            # 画像投稿データをDBに保存
                            img_post_id = save_img_post(
                                prompt=st.session_state.generated_prompt,
                                cast_id=st.session_state.selected_cast_id,
                                cast_name=st.session_state.selected_cast_name,
                                tweet_content=tweet_content
                            )
                            
                            if img_post_id:
                                # 画像パスを更新
                                update_img_post_status(
                                    img_post_id, 
                                    "ready",
                                    generated_image_path=st.session_state.generated_image_path
                                )
                                
                                # Cloud Functions経由で投稿
                                try:
                                    success, result_message = send_image_to_cloud_functions(
                                        cast_id=st.session_state.selected_cast_id,
                                        image_path=st.session_state.generated_image_path,
                                        tweet_content=tweet_content
                                    )
                                    
                                    if success:
                                        st.success(result_message)
                                        
                                        # 投稿成功の場合、DBステータスを更新
                                        update_img_post_status(
                                            img_post_id, 
                                            "posted",
                                            posted_at=datetime.datetime.now().isoformat(),
                                            tweet_id=result_message.split("Tweet ID: ")[-1] if "Tweet ID:" in result_message else None
                                        )
                                        
                                        # セッション状態をクリア
                                        image_path_to_cleanup = st.session_state.get('generated_image_path')
                                        
                                        # すべての関連セッション状態を削除
                                        all_keys_to_clear = [
                                            'generated_image_path', 'generated_prompt', 'original_image_prompt',
                                            'selected_cast_id', 'selected_cast_name', 'auto_caption',
                                            'image_source', 'user_instruction', 'original_auto_caption'
                                        ]
                                        for key in all_keys_to_clear:
                                            if key in st.session_state:
                                                del st.session_state[key]
                                        
                                        # ファイルアップローダーをリセット
                                        st.session_state.uploader_reset_counter = st.session_state.get('uploader_reset_counter', 0) + 1
                                        
                                        # 一時画像ファイルを削除
                                        if image_path_to_cleanup and os.path.exists(image_path_to_cleanup):
                                            try:
                                                os.remove(image_path_to_cleanup)
                                            except Exception as e:
                                                pass  # エラーは無視
                                        
                                        # 明示的にページの状態をリセット
                                        st.success("✅ 投稿完了！ページをリセットします...")
                                        time.sleep(1)  # 1秒待機してユーザーにメッセージを見せる
                                        st.rerun()
                                    else:
                                        st.error(result_message)
                                        update_img_post_status(img_post_id, "failed", error_message=result_message)
                                    
                                except Exception as e:
                                    error_msg = f"投稿に失敗しました: {e}"
                                    st.error(f"❌ {error_msg}")
                                    update_img_post_status(img_post_id, "failed", error_message=error_msg)
                            else:
                                st.error("データベース保存に失敗しました")
                else:
                    st.markdown("### 📋 手順")
                    st.markdown("""
                    1. **キャスト選択**: 投稿するキャラクターを選択
                    2. **画像準備**: AI生成またはファイルアップロード
                    3. **コメント指示**: AIがコメント生成する際の指示
                    4. **コメント生成**: キャラクターの個性を活かしたコメント作成
                    5. **投稿実行**: X（旧Twitter）への投稿
                    """)
                    
                    st.markdown("### ⚙️ 設定")
                    # 高度な設定をサイドパネルに移動
                    with st.expander("画像生成設定"):
                        aspect_ratio = st.selectbox(
                            "アスペクト比",
                            ["1:1", "16:9", "9:16", "4:3", "3:4"],
                            index=0,
                            help="1:1はSNS投稿に最適"
                        )
                        
                        image_size = st.selectbox(
                            "画像サイズ",
                            ["1024x1024", "512x512"],
                            index=0
                        )
        
        with tab2:
            st.subheader("📋 投稿履歴")
            
            # フィルタオプション
            col1, col2 = st.columns([1, 1])
            with col1:
                status_filter = st.selectbox(
                    "ステータスフィルタ",
                    ["すべて", "draft", "ready", "posted", "failed"],
                    key="history_status_filter"
                )
            
            with col2:
                cast_filter = st.selectbox(
                    "キャストフィルタ",
                    ["すべて"] + [f"{cast['name']}" for cast in casts],
                    key="history_cast_filter"
                )
            
            # 履歴取得
            status = None if status_filter == "すべて" else status_filter
            cast_id_filter = None
            if cast_filter != "すべて":
                cast_id_filter = next(cast['id'] for cast in casts if cast['name'] == cast_filter)
            
            history = get_img_posts_by_status(status=status, cast_id=cast_id_filter, limit=20)
            
            if history:
                for post in history:
                    with st.expander(f"🎨 {post['prompt'][:50]}... - {post['cast_name']} ({post['status']})"):
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.write(f"**プロンプト:** {post['prompt']}")
                            st.write(f"**キャスト:** {post['cast_name']}")
                            st.write(f"**ステータス:** {post['status']}")
                            st.write(f"**作成日時:** {post['created_at']}")
                            
                            if post['tweet_content']:
                                st.write(f"**ツイート内容:** {post['tweet_content']}")
                            
                            if post['tweet_id']:
                                st.write(f"**Tweet ID:** {post['tweet_id']}")
                            
                            if post['error_message']:
                                st.error(f"エラー: {post['error_message']}")
                        
                        with col2:
                            if post['generated_image_path'] and os.path.exists(post['generated_image_path']):
                                st.image(post['generated_image_path'], caption="生成画像")
                            else:
                                st.info("画像ファイルが見つかりません")
            else:
                st.info("投稿履歴がありません")
        
        with tab3:
            st.subheader("📊 生成統計")
            
            # 統計期間選択
            period = st.selectbox("期間", ["7日間", "30日間", "90日間"], key="stats_period")
            period_days = {"7日間": 7, "30日間": 30, "90日間": 90}[period]
            
            # 全体統計
            all_stats = ai_image_generator.get_generation_stats(days=period_days)
            
            if all_stats:
                # グラフ表示用のデータ準備
                dates = [stat['generation_date'] for stat in all_stats]
                total_counts = [stat['total_generations'] for stat in all_stats]
                success_counts = [stat['successful_generations'] for stat in all_stats]
                
                # 統計表示
                col1, col2, col3 = st.columns(3)
                with col1:
                    total_generations = sum(total_counts)
                    st.metric("総生成数", total_generations)
                
                with col2:
                    total_success = sum(success_counts)
                    success_rate = (total_success / total_generations * 100) if total_generations > 0 else 0
                    st.metric("成功率", f"{success_rate:.1f}%")
                
                with col3:
                    avg_time = sum(stat['avg_generation_time'] or 0 for stat in all_stats) / len(all_stats)
                    st.metric("平均生成時間", f"{avg_time:.2f}秒")
                
                # 日別生成数グラフ（簡易版）
                st.subheader("📈 日別生成数")
                chart_data = pd.DataFrame({
                    "日付": dates,
                    "生成数": total_counts,
                    "成功数": success_counts
                })
                st.line_chart(chart_data.set_index("日付"))
            else:
                st.info("統計データがありません")

    elif page == "キャスト管理":
        st.title("👤 キャスト管理")
        
        # 成功メッセージの表示
        if "cast_import_message" in st.session_state:
            msg_type, msg_content = st.session_state.cast_import_message
            if msg_type == "success":
                st.success(msg_content)
            elif msg_type == "warning":
                st.warning(msg_content)
            elif msg_type == "error":
                st.error(msg_content)
            del st.session_state.cast_import_message
        
        # セッションステート初期化
        if 'selected_cast_for_edit' not in st.session_state:
            st.session_state.selected_cast_for_edit = None
        
        # 3タブ構成（編集、一覧、CSV管理）
        tab_edit, tab_list, tab_csv = st.tabs([
            "✏️ 編集",
            "👥 キャスト一覧", 
            "📥 CSV管理"
        ])
        
        # ==================== タブ1: 編集 ====================
        with tab_edit:
            st.header("既存キャストの編集・削除")
            
            casts = execute_query("SELECT id, name, nickname FROM casts ORDER BY name", fetch="all")
            
            if not casts:
                st.info("編集できるキャストがまだいません。CSV管理タブからインポートしてください。")
            else:
                # 選択状態の表示
                if st.session_state.selected_cast_for_edit:
                    selected_cast = execute_query(
                        "SELECT name, nickname FROM casts WHERE id = ?",
                        (st.session_state.selected_cast_for_edit,),
                        fetch="one"
                    )
                    if selected_cast:
                        display = f"{selected_cast['name']}（{selected_cast['nickname']}）" if selected_cast['nickname'] else selected_cast['name']
                        st.success(f"✅ 編集対象: {display}")
                
                # キャスト選択
                cast_options = {f"{c['name']}（{c['nickname']}）" if c['nickname'] else c['name']: c['id'] for c in casts}
                
                default_index = 0
                if st.session_state.selected_cast_for_edit:
                    for idx, (display, cid) in enumerate(cast_options.items()):
                        if cid == st.session_state.selected_cast_for_edit:
                            default_index = idx
                            break
                
                selected_display = st.selectbox(
                    "編集するキャストを選択",
                    list(cast_options.keys()),
                    index=default_index,
                    key="edit_cast_selector"
                )
                selected_cast_id = cast_options[selected_display]
                
                if st.session_state.selected_cast_for_edit != selected_cast_id:
                    st.session_state.selected_cast_for_edit = selected_cast_id
                
                # キャスト情報取得
                cast_data = execute_query("SELECT * FROM casts WHERE id = ?", (selected_cast_id,), fetch="one")
                persona_data = execute_query("SELECT * FROM persona_detailed WHERE cast_id = ?", (selected_cast_id,), fetch="one")
                mission_data = execute_query("SELECT * FROM account_mission WHERE cast_id = ?", (selected_cast_id,), fetch="one")
                profile_data = execute_query("SELECT * FROM sample_profiles WHERE cast_id = ?", (selected_cast_id,), fetch="one")
                x_creds = get_cast_x_credentials(selected_cast_id)
                
                if cast_data:
                    # 編集用サブタブ（5つ）
                    persona_edit_tab, mission_edit_tab, character_edit_tab, xapi_edit_tab, sample_post_edit_tab = st.tabs([
                        "👤 ペルソナ管理",
                        "📋 運営指針", 
                        "🎭 キャラクター設定",
                        "🔐 X API設定",
                        "📝 サンプル投稿"
                    ])
                    
                    with persona_edit_tab:
                        st.markdown("### 📌 必須項目")
                        col1, col2, col3 = st.columns(3)
                        edit_name = col1.text_input("ユーザー名*", value=cast_data['name'] or '', key=f"edit_name_{selected_cast_id}")
                        edit_nickname = col2.text_input("名前*", value=cast_data['nickname'] or '', key=f"edit_nickname_{selected_cast_id}")
                        
                        # 年齢：抽出データがあれば優先
                        age_val = st.session_state.get(f'parsed_age_{selected_cast_id}', str(cast_data['age']) if cast_data['age'] else '')
                        edit_age = col3.text_input("年齢*", value=age_val, key=f"edit_age_{selected_cast_id}")
                        
                        st.markdown("### 🔍 詳細ペルソナ")
                        st.info("💡 運営指針タブの「テキスト一括インポート」で抽出したデータがある場合、自動反映されます")
                        
                        with st.expander("詳細ペルソナを編集", expanded=True):
                            col1, col2 = st.columns(2)
                            
                            # 各フィールド：抽出データがあれば優先、なければDB値
                            archetype_val = st.session_state.get(f'parsed_archetype_{selected_cast_id}', persona_data['archetype'] if persona_data and persona_data['archetype'] else '')
                            occupation_val = st.session_state.get(f'parsed_occupation_{selected_cast_id}', persona_data['occupation'] if persona_data and persona_data['occupation'] else '')
                            residence_val = st.session_state.get(f'parsed_residence_{selected_cast_id}', persona_data['residence'] if persona_data and persona_data['residence'] else '')
                            family_val = st.session_state.get(f'parsed_family_{selected_cast_id}', persona_data['family_structure'] if persona_data and persona_data['family_structure'] else '')
                            quote_val = st.session_state.get(f'parsed_quote_{selected_cast_id}', persona_data['symbolic_quote'] if persona_data and persona_data['symbolic_quote'] else '')
                            x_purpose_val = st.session_state.get(f'parsed_x_purpose_{selected_cast_id}', persona_data['x_usage_purpose'] if persona_data and persona_data['x_usage_purpose'] else '')
                            behavior_val = st.session_state.get(f'parsed_behavior_{selected_cast_id}', persona_data['behavior_pattern'] if persona_data and persona_data['behavior_pattern'] else '')
                            topics_val = st.session_state.get(f'parsed_topics_{selected_cast_id}', persona_data['interested_topics'] if persona_data and persona_data['interested_topics'] else '')
                            pain_val = st.session_state.get(f'parsed_pain_{selected_cast_id}', persona_data['platform_pain_points'] if persona_data and persona_data['platform_pain_points'] else '')
                            brand_val = st.session_state.get(f'parsed_brand_{selected_cast_id}', persona_data['brand_relationship'] if persona_data and persona_data['brand_relationship'] else '')
                            
                            edit_archetype = col1.text_input("アーキタイプ", value=archetype_val, key=f"edit_archetype_{selected_cast_id}")
                            edit_occupation = col2.text_input("職業", value=occupation_val, key=f"edit_occupation_{selected_cast_id}")
                            edit_residence = col1.text_input("居住地", value=residence_val, key=f"edit_residence_{selected_cast_id}")
                            edit_family = col2.text_input("家族構成", value=family_val, key=f"edit_family_{selected_cast_id}")
                            edit_quote = st.text_input("象徴的な一言", value=quote_val, key=f"edit_quote_{selected_cast_id}")
                            edit_x_purpose = st.text_input("X利用目的", value=x_purpose_val, key=f"edit_x_purpose_{selected_cast_id}")
                            edit_behavior = st.text_area("行動パターン", value=behavior_val, key=f"edit_behavior_{selected_cast_id}")
                            edit_topics = st.text_input("関心トピック", value=topics_val, key=f"edit_topics_{selected_cast_id}")
                            edit_pain = st.text_input("プラットフォーム不満", value=pain_val, key=f"edit_pain_{selected_cast_id}")
                            edit_brand = st.text_input("ブランド関係", value=brand_val, key=f"edit_brand_{selected_cast_id}")
                    
                    with mission_edit_tab:
                        st.markdown("### 📋 テキスト一括インポート")
                        st.info("💡 アカウント運営指針のドキュメント全文を貼り付けると、該当項目を自動抽出してフォームに反映します")
                        
                        with st.expander("📝 テキスト一括インポートフォーム", expanded=False):
                            bulk_text = st.text_area(
                                "アカウント運営指針ドキュメントをコピペ",
                                placeholder="## **アカウント運営指針**\n\nから始まるドキュメント全文を貼り付けてください",
                                height=300,
                                key=f"bulk_import_{selected_cast_id}"
                            )
                            
                            if st.button("🔄 テキストから自動抽出して反映", key=f"parse_bulk_{selected_cast_id}"):
                                if bulk_text:
                                    try:
                                        import re
                                        extraction_results = []
                                        
                                        # ペルソナ設定から詳細ペルソナを抽出（CSV形式）
                                        persona_csv_match = re.search(r'ID,名前,年齢.*?\n(\d+,.+?)(?=\n\n|---)', bulk_text, re.DOTALL)
                                        if persona_csv_match:
                                            csv_line = persona_csv_match.group(1).strip()
                                            # CSVパース（引用符内のカンマを考慮）
                                            import csv
                                            from io import StringIO
                                            reader = csv.reader(StringIO(csv_line))
                                            parts = next(reader)
                                            
                                            if len(parts) >= 14:
                                                # セッションステートに値を保存
                                                st.session_state[f'parsed_age_{selected_cast_id}'] = parts[2].strip()
                                                st.session_state[f'parsed_archetype_{selected_cast_id}'] = parts[3].strip()
                                                st.session_state[f'parsed_occupation_{selected_cast_id}'] = parts[4].strip()
                                                st.session_state[f'parsed_residence_{selected_cast_id}'] = parts[5].strip()
                                                st.session_state[f'parsed_family_{selected_cast_id}'] = parts[6].strip()
                                                st.session_state[f'parsed_quote_{selected_cast_id}'] = parts[7].strip()
                                                st.session_state[f'parsed_x_purpose_{selected_cast_id}'] = parts[8].strip()
                                                st.session_state[f'parsed_behavior_{selected_cast_id}'] = parts[9].strip()
                                                st.session_state[f'parsed_topics_{selected_cast_id}'] = parts[10].strip()
                                                # parts[11]は主なフォロー対象（スキップ）
                                                st.session_state[f'parsed_pain_{selected_cast_id}'] = parts[12].strip() if len(parts) > 12 else ''
                                                st.session_state[f'parsed_brand_{selected_cast_id}'] = parts[13].strip() if len(parts) > 13 else ''
                                                extraction_results.append("✅ ペルソナ情報を抽出")
                                        
                                        # サンプルプロフィールを抽出（複数パターンに対応）
                                        # パターン1: プロフィール:\n
                                        profile_match = re.search(r'プロフィール:\s*\n(.+?)(?=\n\n|---|\Z)', bulk_text, re.DOTALL)
                                        if profile_match:
                                            st.session_state[f'parsed_profile_{selected_cast_id}'] = profile_match.group(1).strip()
                                            extraction_results.append("✅ サンプルプロフィールを抽出")
                                        
                                        # サンプル投稿をCSV形式から抽出（ダブルクオート対応）
                                        posts_csv_match = re.search(r'Category,Post[_\s]Content\s*\n((?:.+\n?)+?)(?=\n\n---|\Z)', bulk_text, re.DOTALL)
                                        if posts_csv_match:
                                            csv_content = posts_csv_match.group(1).strip()
                                            # 抽出した投稿数をカウント
                                            post_lines = [l for l in csv_content.split('\n') if l.strip()]
                                            st.session_state[f'parsed_posts_csv_{selected_cast_id}'] = csv_content
                                            extraction_results.append(f"✅ サンプル投稿を抽出 ({len(post_lines)}件)")
                                        
                                        if extraction_results:
                                            st.success("✅ テキストから情報を抽出しました！")
                                            for result in extraction_results:
                                                st.write(result)
                                            st.info("💡 下のフォームで内容を確認し、サンプル投稿は「📥 一括インポート」ボタンでDBに登録してください")
                                        else:
                                            st.warning("⚠️ 抽出できる情報が見つかりませんでした。テキストの形式を確認してください。")
                                        
                                        st.rerun()
                                        
                                    except Exception as e:
                                        st.error(f"❌ 抽出エラー: {str(e)}")
                                        st.info("テキストの形式を確認してください")
                                        import traceback
                                        with st.expander("詳細エラー"):
                                            st.code(traceback.format_exc())
                                else:
                                    st.warning("テキストを入力してください")
                        
                        st.markdown("---")
                        st.markdown("### 📝 アカウント運営指針（個別編集）")
                        
                        # 抽出データがあれば反映
                        mission_val = mission_data['mission'] if mission_data and mission_data['mission'] else ''
                        persona_design_val = mission_data['persona_design'] if mission_data and mission_data['persona_design'] else ''
                        content_val = mission_data['content_strategy'] if mission_data and mission_data['content_strategy'] else ''
                        goal_val = mission_data['final_goal'] if mission_data and mission_data['final_goal'] else ''
                        notes_val = mission_data['additional_notes'] if mission_data and mission_data['additional_notes'] else ''
                        profile_val = st.session_state.get(f'parsed_profile_{selected_cast_id}', profile_data['profile_text'] if profile_data and profile_data['profile_text'] else '')
                        
                        edit_mission = st.text_area("運営ミッション", value=mission_val, key=f"edit_mission_{selected_cast_id}", height=100)
                        edit_persona_design = st.text_area("ペルソナ設計意図", value=persona_design_val, key=f"edit_persona_design_{selected_cast_id}", height=100)
                        edit_content = st.text_area("コンテンツ戦略", value=content_val, key=f"edit_content_{selected_cast_id}", height=100)
                        edit_goal = st.text_area("最終目標", value=goal_val, key=f"edit_goal_{selected_cast_id}", height=100)
                        edit_notes = st.text_area("補足事項", value=notes_val, key=f"edit_notes_{selected_cast_id}", height=100)
                        
                        st.markdown("### サンプルプロフィール")
                        edit_profile = st.text_area("サンプルプロフィール", value=profile_val, key=f"edit_profile_{selected_cast_id}", height=100)
                        
                        # サンプル投稿一括インポート機能
                        if f'parsed_posts_csv_{selected_cast_id}' in st.session_state:
                            st.markdown("---")
                            st.markdown("### 📊 抽出されたサンプル投稿")
                            csv_content = st.session_state[f'parsed_posts_csv_{selected_cast_id}']
                            
                            # プレビュー表示を改善
                            lines = [l for l in csv_content.strip().split('\n') if l.strip()]
                            st.info(f"📋 抽出件数: **{len(lines)}件** のサンプル投稿が見つかりました")
                            
                            # カテゴリごとに整理してプレビュー
                            with st.expander("📝 抽出内容プレビュー", expanded=True):
                                preview_data = []
                                try:
                                    import csv
                                    from io import StringIO
                                    csv_reader = csv.reader(StringIO(csv_content))
                                    
                                    for idx, row in enumerate(csv_reader):
                                        if idx >= 10:  # 最初の10件のみ
                                            break
                                        if len(row) >= 2:
                                            category = row[0].strip()
                                            content = row[1].strip()
                                            preview_data.append({
                                                "カテゴリ": category, 
                                                "投稿内容": content[:50] + "..." if len(content) > 50 else content
                                            })
                                except Exception as e:
                                    st.error(f"プレビューエラー: {str(e)}")
                                
                                if preview_data:
                                    import pandas as pd
                                    df = pd.DataFrame(preview_data)
                                    st.dataframe(df, use_container_width=True)
                                    
                                    if len(lines) > 10:
                                        st.caption(f"...他 {len(lines) - 10}件")
                                else:
                                    st.warning("プレビューできるデータがありません")
                            
                            # 詳細CSV表示
                            with st.expander("🔍 CSVデータ全文", expanded=False):
                                st.text_area("抽出されたCSV", value=csv_content, height=200, disabled=True, key=f"preview_posts_{selected_cast_id}")
                            
                            col1, col2 = st.columns([2, 1])
                            
                            if col1.button("📥 サンプル投稿を一括インポート", type="primary", key=f"import_posts_{selected_cast_id}"):
                                try:
                                    import csv
                                    from io import StringIO
                                    
                                    imported_count = 0
                                    errors = []
                                    
                                    # 既存のサンプル投稿を削除
                                    execute_query("DELETE FROM sample_posts WHERE cast_id = ?", (selected_cast_id,))
                                    
                                    # CSVとして正しくパース（引用符内のカンマを考慮）
                                    csv_reader = csv.reader(StringIO(csv_content))
                                    
                                    for idx, row in enumerate(csv_reader, 1):
                                        try:
                                            if len(row) >= 2:
                                                category = row[0].strip()
                                                content = row[1].strip()
                                                
                                                if category and content:
                                                    execute_query(
                                                        "INSERT INTO sample_posts (cast_id, category, post_content, sort_order) VALUES (?, ?, ?, ?)",
                                                        (selected_cast_id, category, content, imported_count)
                                                    )
                                                    imported_count += 1
                                                else:
                                                    errors.append(f"行{idx}: カテゴリまたは内容が空")
                                            else:
                                                errors.append(f"行{idx}: フォーマットエラー（列数不足）")
                                        except Exception as row_error:
                                            errors.append(f"行{idx}: {str(row_error)}")
                                    
                                    # セッションステートをクリア
                                    del st.session_state[f'parsed_posts_csv_{selected_cast_id}']
                                    
                                    if errors:
                                        st.warning(f"⚠️ {len(errors)}件のエラーがありました")
                                        with st.expander("エラー詳細"):
                                            for err in errors[:10]:
                                                st.text(err)
                                            if len(errors) > 10:
                                                st.text(f"...他 {len(errors) - 10}件")
                                    
                                    st.success(f"✅ {imported_count}件のサンプル投稿をインポートしました！")
                                    st.balloons()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ インポートエラー: {str(e)}")
                                    import traceback
                                    with st.expander("エラー詳細"):
                                        st.code(traceback.format_exc())
                            
                            if col2.button("❌ キャンセル", key=f"cancel_posts_{selected_cast_id}"):
                                del st.session_state[f'parsed_posts_csv_{selected_cast_id}']
                                st.info("インポートをキャンセルしました")
                                st.rerun()
                    
                    with character_edit_tab:
                        st.markdown("### キャラクター詳細設定")
                        col1, col2 = st.columns(2)
                        edit_birthday = col1.text_input("誕生日", value=cast_data['birthday'] or '', key=f"edit_birthday_{selected_cast_id}")
                        edit_birthplace = col2.text_input("出身地", value=cast_data['birthplace'] or '', key=f"edit_birthplace_{selected_cast_id}")
                        edit_appearance = st.text_area("外見", value=cast_data['appearance'] or '', key=f"edit_appearance_{selected_cast_id}")
                        edit_interaction = st.text_area("顧客対応", value=cast_data['customer_interaction'] or '', key=f"edit_interaction_{selected_cast_id}")
                        col1, col2 = st.columns(2)
                        edit_hobby = col1.text_input("趣味", value=cast_data['hobby'] or '', key=f"edit_hobby_{selected_cast_id}")
                        edit_holiday = col2.text_input("休日の過ごし方", value=cast_data['holiday_activity'] or '', key=f"edit_holiday_{selected_cast_id}")
                        edit_reason = st.text_area("この仕事を選んだ理由", value=cast_data['reason_for_job'] or '', key=f"edit_reason_{selected_cast_id}")
                    
                    with xapi_edit_tab:
                        st.markdown("### X API認証情報")
                        st.info("キャスト専用のX APIキーを設定できます。")
                        edit_api_key = st.text_input("API Key", value=x_creds['api_key'] if x_creds and x_creds['api_key'] else '', type="password", key=f"edit_api_key_{selected_cast_id}")
                        edit_api_secret = st.text_input("API Secret", value=x_creds['api_secret'] if x_creds and x_creds['api_secret'] else '', type="password", key=f"edit_api_secret_{selected_cast_id}")
                        edit_bearer = st.text_input("Bearer Token", value=x_creds['bearer_token'] if x_creds and x_creds['bearer_token'] else '', type="password", key=f"edit_bearer_{selected_cast_id}")
                        edit_access = st.text_input("Access Token", value=x_creds['access_token'] if x_creds and x_creds['access_token'] else '', type="password", key=f"edit_access_{selected_cast_id}")
                        edit_access_secret = st.text_input("Access Token Secret", value=x_creds['access_token_secret'] if x_creds and x_creds['access_token_secret'] else '', type="password", key=f"edit_access_secret_{selected_cast_id}")
                        col1, col2 = st.columns(2)
                        edit_username = col1.text_input("Twitterユーザー名", value=x_creds['twitter_username'] if x_creds and x_creds['twitter_username'] else '', key=f"edit_username_{selected_cast_id}")
                        edit_user_id = col2.text_input("TwitterユーザーID", value=x_creds['twitter_user_id'] if x_creds and x_creds['twitter_user_id'] else '', key=f"edit_user_id_{selected_cast_id}")
                    
                    # --- サブタブ3-5: サンプル投稿 ---
                    with sample_post_edit_tab:
                        st.markdown("### 📝 サンプル投稿管理")
                        st.info("このキャスト専用のサンプル投稿を追加・編集できます。")
                        
                        # 既存のサンプル投稿を取得
                        sample_posts = execute_query(
                            "SELECT id, category, post_content FROM sample_posts WHERE cast_id = ? ORDER BY sort_order, id",
                            (selected_cast_id,), fetch="all"
                        )
                        
                        if sample_posts:
                            st.write(f"**登録済みサンプル投稿: {len(sample_posts)}件**")
                            for idx, post in enumerate(sample_posts):
                                with st.expander(f"📄 {post['category']} - {post['post_content'][:30]}..."):
                                    st.text_area("投稿内容", value=post['post_content'], key=f"sample_view_{post['id']}", disabled=True, height=100)
                                    if st.button("🗑️ 削除", key=f"delete_sample_{post['id']}"):
                                        execute_query("DELETE FROM sample_posts WHERE id = ?", (post['id'],))
                                        st.success("削除しました")
                                        st.rerun()
                        else:
                            st.info("サンプル投稿がまだ登録されていません。")
                        
                        # 新規追加フォーム
                        st.markdown("---")
                        st.markdown("#### ➕ 新規サンプル投稿")
                        new_category = st.text_input("カテゴリ", placeholder="例: 日常", key=f"new_sample_cat_{selected_cast_id}")
                        new_content = st.text_area("投稿内容", placeholder="サンプル投稿の内容を入力", key=f"new_sample_content_{selected_cast_id}", height=150)
                        
                        if st.button("➕ サンプル投稿を追加", key=f"add_sample_{selected_cast_id}"):
                            if new_category and new_content:
                                max_order = execute_query(
                                    "SELECT COALESCE(MAX(sort_order), 0) as max_order FROM sample_posts WHERE cast_id = ?",
                                    (selected_cast_id,), fetch="one"
                                )
                                next_order = (max_order['max_order'] or 0) + 1
                                execute_query(
                                    "INSERT INTO sample_posts (cast_id, category, post_content, sort_order) VALUES (?, ?, ?, ?)",
                                    (selected_cast_id, new_category, new_content, next_order)
                                )
                                st.success("サンプル投稿を追加しました！")
                                st.rerun()
                            else:
                                st.error("カテゴリと投稿内容を入力してください")
                    
                    # 更新・削除ボタン
                    st.markdown("---")
                    col_update, col_delete = st.columns([3, 1])
                    
                    if col_update.button("💾 更新", type="primary", key=f"update_{selected_cast_id}"):
                        if edit_name and edit_nickname and edit_age:
                            try:
                                # casts更新
                                execute_query(
                                    """UPDATE casts SET name = ?, nickname = ?, age = ?, birthday = ?, birthplace = ?, 
                                    appearance = ?, customer_interaction = ?, hobby = ?, holiday_activity = ?, reason_for_job = ?
                                    WHERE id = ?""",
                                    (edit_name, edit_nickname, edit_age, edit_birthday, edit_birthplace,
                                     edit_appearance, edit_interaction, edit_hobby, edit_holiday, edit_reason, selected_cast_id)
                                )
                                
                                # persona_detailed更新または挿入
                                if any([edit_archetype, edit_occupation, edit_residence, edit_family, edit_quote,
                                       edit_x_purpose, edit_behavior, edit_topics, edit_pain, edit_brand]):
                                    if persona_data:
                                        execute_query(
                                            """UPDATE persona_detailed SET archetype = ?, occupation = ?, residence = ?, 
                                            family_structure = ?, symbolic_quote = ?, x_usage_purpose = ?, behavior_pattern = ?, 
                                            interested_topics = ?, platform_pain_points = ?, brand_relationship = ? WHERE cast_id = ?""",
                                            (edit_archetype, edit_occupation, edit_residence, edit_family, edit_quote,
                                             edit_x_purpose, edit_behavior, edit_topics, edit_pain, edit_brand, selected_cast_id)
                                        )
                                    else:
                                        execute_query(
                                            """INSERT INTO persona_detailed (cast_id, archetype, occupation, residence, family_structure, 
                                            symbolic_quote, x_usage_purpose, behavior_pattern, interested_topics, platform_pain_points, 
                                            brand_relationship) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                            (selected_cast_id, edit_archetype, edit_occupation, edit_residence, edit_family,
                                             edit_quote, edit_x_purpose, edit_behavior, edit_topics, edit_pain, edit_brand)
                                        )
                                
                                # account_mission更新または挿入
                                if any([edit_mission, edit_persona_design, edit_content, edit_goal, edit_notes]):
                                    if mission_data:
                                        execute_query(
                                            """UPDATE account_mission SET mission = ?, persona_design = ?, content_strategy = ?, 
                                            final_goal = ?, additional_notes = ? WHERE cast_id = ?""",
                                            (edit_mission, edit_persona_design, edit_content, edit_goal, edit_notes, selected_cast_id)
                                        )
                                    else:
                                        execute_query(
                                            """INSERT INTO account_mission (cast_id, mission, persona_design, content_strategy, 
                                            final_goal, additional_notes) VALUES (?, ?, ?, ?, ?, ?)""",
                                            (selected_cast_id, edit_mission, edit_persona_design, edit_content, edit_goal, edit_notes)
                                        )
                                
                                # sample_profiles更新または挿入
                                if edit_profile:
                                    if profile_data:
                                        execute_query("UPDATE sample_profiles SET profile_text = ? WHERE cast_id = ?", (edit_profile, selected_cast_id))
                                    else:
                                        execute_query("INSERT INTO sample_profiles (cast_id, profile_text) VALUES (?, ?)", (selected_cast_id, edit_profile))
                                
                                # X API認証情報更新
                                if edit_api_key:
                                    save_cast_x_credentials(selected_cast_id, edit_api_key, edit_api_secret, edit_bearer,
                                                          edit_access, edit_access_secret, edit_username, edit_user_id)
                                
                                # セッションステートのクリア（抽出データ）
                                keys_to_clear = [
                                    f'parsed_age_{selected_cast_id}',
                                    f'parsed_archetype_{selected_cast_id}',
                                    f'parsed_occupation_{selected_cast_id}',
                                    f'parsed_residence_{selected_cast_id}',
                                    f'parsed_family_{selected_cast_id}',
                                    f'parsed_quote_{selected_cast_id}',
                                    f'parsed_x_purpose_{selected_cast_id}',
                                    f'parsed_behavior_{selected_cast_id}',
                                    f'parsed_topics_{selected_cast_id}',
                                    f'parsed_pain_{selected_cast_id}',
                                    f'parsed_brand_{selected_cast_id}',
                                    f'parsed_profile_{selected_cast_id}',
                                    f'parsed_posts_csv_{selected_cast_id}'
                                ]
                                for key in keys_to_clear:
                                    if key in st.session_state:
                                        del st.session_state[key]
                                
                                st.session_state.cast_import_message = ("success", f"✅ キャスト「{edit_name}（{edit_nickname}）」を更新しました！")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 更新エラー: {e}")
                        else:
                            st.error("❌ 必須項目を入力してください")
                    
                    if col_delete.button("🗑️ 削除", type="secondary", key=f"delete_{selected_cast_id}"):
                        try:
                            execute_query("DELETE FROM casts WHERE id = ?", (selected_cast_id,))
                            st.session_state.cast_import_message = ("success", f"🗑️ キャスト「{cast_data['name']}」を削除しました")
                            st.session_state.selected_cast_for_edit = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 削除エラー: {e}")
        
        # ==================== タブ2: キャスト一覧 ====================
        with tab_list:
            st.header("キャスト一覧")
            casts = execute_query("SELECT c.id, c.name, c.nickname, c.age FROM casts c ORDER BY c.name", fetch="all")
            
            if not casts:
                st.info("登録されているキャストがいません。")
            else:
                st.write(f"**登録キャスト数: {len(casts)}件**")
                
                for cast in casts:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                        display_name = f"{cast['name']}（{cast['nickname']}）" if cast['nickname'] else cast['name']
                        col1.markdown(f"### {display_name}")
                        col2.text(f"年齢: {cast['age']}歳")
                        
                        persona_exists = execute_query("SELECT COUNT(*) as count FROM persona_detailed WHERE cast_id = ?", (cast['id'],), fetch="one")
                        if persona_exists and persona_exists['count'] > 0:
                            col3.success("✅ 詳細有")
                        else:
                            col3.info("➖ 詳細無")
                        
                        # 選択ボタン
                        is_selected = st.session_state.selected_cast_for_edit == cast['id']
                        if col4.button("✅ 選択中" if is_selected else "📝 選択", key=f"select_cast_{cast['id']}", disabled=is_selected):
                            st.session_state.selected_cast_for_edit = cast['id']
                            st.session_state.cast_import_message = ("success", f"✅ {display_name}を選択しました！編集タブに移動してください。")
                            st.rerun()
                        
                        st.markdown("---")
        
        # ==================== タブ3: CSV管理 ====================
        with tab_csv:
            st.header("📥 CSV一括管理")
            st.info("キャスト基本情報（38項目）とサンプル投稿（4項目）をCSVで一括管理できます。")
            
            csv_import_tab, csv_export_tab, csv_sample_posts_tab = st.tabs(["📥 インポート", "📤 エクスポート", "📝 サンプル投稿CSV"])
            
            # ===== インポートタブ =====
            with csv_import_tab:
                st.markdown("### キャスト基本情報のインポート")
                st.info("""
**CSVフォーマット:**
- 必須項目: name, nickname, age
- 詳細ペルソナ: archetype, occupation, residence等9項目
- キャラクター設定: birthday, personality等13項目
- 運営指針: mission, persona_design等5項目
- サンプルプロフィール: sample_profile
- X API情報: x_api_key, x_api_secret等7項目

**合計: 38項目（nameのみ必須、他はオプション）**
""")
                
                uploaded_file = st.file_uploader("キャスト基本情報CSV", type="csv", key="cast_master_csv")
                
                if uploaded_file:
                    try:
                        import pandas as pd
                        df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False).fillna("")
                        
                        st.write(f"**読み込んだデータ: {len(df)}件**")
                        st.dataframe(df.head())
                        
                        if st.button("💾 インポート実行", type="primary"):
                            success_count = 0
                            error_count = 0
                            
                            for idx, row in df.iterrows():
                                try:
                                    if not row.get('name'):
                                        st.warning(f"行{idx+1}: nameが必須です")
                                        error_count += 1
                                        continue
                                    
                                    # キャスト存在確認
                                    existing_cast = execute_query("SELECT id FROM casts WHERE name = ?", (row['name'],), fetch="one")
                                    
                                    # キャスト基本情報
                                    if existing_cast:
                                        cast_id = existing_cast['id']
                                        execute_query(
                                            """UPDATE casts SET nickname = ?, age = ?, birthday = ?, personality = ?, 
                                            strength = ?, weakness = ?, first_person = ?, speech_style = ?, catchphrase = ?, 
                                            occupation = ?, hobby = ?, likes = ?, dislikes = ?, dream = ?, secret = ?
                                            WHERE id = ?""",
                                            (row.get('nickname', ''), row.get('age', ''), row.get('birthday', ''),
                                             row.get('personality', ''), row.get('strength', ''), row.get('weakness', ''),
                                             row.get('first_person', ''), row.get('speech_style', ''), row.get('catchphrase', ''),
                                             row.get('occupation', ''), row.get('hobby', ''), row.get('likes', ''),
                                             row.get('dislikes', ''), row.get('dream', ''), row.get('secret', ''), cast_id)
                                        )
                                    else:
                                        execute_query(
                                            """INSERT INTO casts (name, nickname, age, birthday, personality, strength, weakness, 
                                            first_person, speech_style, catchphrase, occupation, hobby, likes, dislikes, dream, secret)
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                            (row['name'], row.get('nickname', ''), row.get('age', ''), row.get('birthday', ''),
                                             row.get('personality', ''), row.get('strength', ''), row.get('weakness', ''),
                                             row.get('first_person', ''), row.get('speech_style', ''), row.get('catchphrase', ''),
                                             row.get('occupation', ''), row.get('hobby', ''), row.get('likes', ''),
                                             row.get('dislikes', ''), row.get('dream', ''), row.get('secret', ''))
                                        )
                                        cast_id = execute_query("SELECT id FROM casts WHERE name = ?", (row['name'],), fetch="one")['id']
                                    
                                    # 詳細ペルソナ
                                    if any([row.get('archetype'), row.get('residence'), row.get('family_structure')]):
                                        persona_exists = execute_query("SELECT COUNT(*) as count FROM persona_detailed WHERE cast_id = ?", (cast_id,), fetch="one")
                                        if persona_exists['count'] > 0:
                                            execute_query(
                                                """UPDATE persona_detailed SET archetype = ?, occupation = ?, residence = ?, 
                                                family_structure = ?, symbolic_quote = ?, x_usage_purpose = ?, behavior_pattern = ?, 
                                                interested_topics = ?, platform_pain_points = ?, brand_relationship = ?, 
                                                updated_at = CURRENT_TIMESTAMP WHERE cast_id = ?""",
                                                (row.get('archetype', ''), row.get('occupation', ''), row.get('residence', ''),
                                                 row.get('family_structure', ''), row.get('symbolic_quote', ''), row.get('x_usage_purpose', ''),
                                                 row.get('behavior_pattern', ''), row.get('interested_topics', ''),
                                                 row.get('platform_pain_points', ''), row.get('brand_relationship', ''), cast_id)
                                            )
                                        else:
                                            execute_query(
                                                """INSERT INTO persona_detailed (cast_id, archetype, occupation, residence, family_structure, 
                                                symbolic_quote, x_usage_purpose, behavior_pattern, interested_topics, platform_pain_points, brand_relationship)
                                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                                (cast_id, row.get('archetype', ''), row.get('occupation', ''), row.get('residence', ''),
                                                 row.get('family_structure', ''), row.get('symbolic_quote', ''), row.get('x_usage_purpose', ''),
                                                 row.get('behavior_pattern', ''), row.get('interested_topics', ''),
                                                 row.get('platform_pain_points', ''), row.get('brand_relationship', ''))
                                            )
                                    
                                    # 運営指針
                                    if any([row.get('mission'), row.get('persona_design')]):
                                        mission_exists = execute_query("SELECT COUNT(*) as count FROM account_mission WHERE cast_id = ?", (cast_id,), fetch="one")
                                        if mission_exists['count'] > 0:
                                            execute_query(
                                                """UPDATE account_mission SET mission = ?, persona_design = ?, content_strategy = ?, 
                                                final_goal = ?, additional_notes = ?, updated_at = CURRENT_TIMESTAMP WHERE cast_id = ?""",
                                                (row.get('mission', ''), row.get('persona_design', ''), row.get('content_strategy', ''),
                                                 row.get('final_goal', ''), row.get('additional_notes', ''), cast_id)
                                            )
                                        else:
                                            execute_query(
                                                """INSERT INTO account_mission (cast_id, mission, persona_design, content_strategy, final_goal, additional_notes)
                                                VALUES (?, ?, ?, ?, ?, ?)""",
                                                (cast_id, row.get('mission', ''), row.get('persona_design', ''),
                                                 row.get('content_strategy', ''), row.get('final_goal', ''), row.get('additional_notes', ''))
                                            )
                                    
                                    # サンプルプロフィール
                                    if row.get('sample_profile'):
                                        profile_exists = execute_query("SELECT COUNT(*) as count FROM sample_profiles WHERE cast_id = ?", (cast_id,), fetch="one")
                                        if profile_exists['count'] > 0:
                                            execute_query("UPDATE sample_profiles SET profile_text = ?, updated_at = CURRENT_TIMESTAMP WHERE cast_id = ?",
                                                        (row['sample_profile'], cast_id))
                                        else:
                                            execute_query("INSERT INTO sample_profiles (cast_id, profile_text) VALUES (?, ?)",
                                                        (cast_id, row['sample_profile']))
                                    
                                    # X API認証情報
                                    if row.get('x_api_key'):
                                        save_cast_x_credentials(cast_id, row.get('x_api_key', ''), row.get('x_api_secret', ''),
                                                              row.get('x_bearer_token', ''), row.get('x_access_token', ''),
                                                              row.get('x_access_token_secret', ''), row.get('x_twitter_username'),
                                                              row.get('x_twitter_user_id'))
                                    
                                    success_count += 1
                                except Exception as e:
                                    st.error(f"行{idx+1}: {e}")
                                    error_count += 1
                            
                            st.success(f"✅ インポート完了: 成功 {success_count}件、エラー {error_count}件")
                            st.rerun()
                    except Exception as e:
                        st.error(f"CSVの読み込みエラー: {e}")
            
            # ===== エクスポートタブ =====
            with csv_export_tab:
                st.markdown("### キャスト基本情報のエクスポート")
                
                if st.button("📤 CSVをダウンロード"):
                    try:
                        import pandas as pd
                        import io
                        
                        casts = execute_query("SELECT * FROM casts", fetch="all")
                        export_data = []
                        
                        for cast in casts:
                            persona = execute_query("SELECT * FROM persona_detailed WHERE cast_id = ?", (cast['id'],), fetch="one")
                            mission = execute_query("SELECT * FROM account_mission WHERE cast_id = ?", (cast['id'],), fetch="one")
                            profile = execute_query("SELECT profile_text FROM sample_profiles WHERE cast_id = ?", (cast['id'],), fetch="one")
                            x_creds = get_cast_x_credentials(cast['id'])
                            
                            row_data = {
                                'name': cast['name'],
                                'nickname': cast['nickname'] or '',
                                'age': cast['age'] or '',
                                'birthday': cast['birthday'] or '',
                                'personality': cast['personality'] or '',
                                'strength': cast['strength'] or '',
                                'weakness': cast['weakness'] or '',
                                'first_person': cast['first_person'] or '',
                                'speech_style': cast['speech_style'] or '',
                                'catchphrase': cast['catchphrase'] or '',
                                'occupation': cast['occupation'] or '',
                                'hobby': cast['hobby'] or '',
                                'likes': cast['likes'] or '',
                                'dislikes': cast['dislikes'] or '',
                                'dream': cast['dream'] or '',
                                'secret': cast['secret'] or '',
                                'archetype': persona['archetype'] if persona else '',
                                'residence': persona['residence'] if persona else '',
                                'family_structure': persona['family_structure'] if persona else '',
                                'symbolic_quote': persona['symbolic_quote'] if persona else '',
                                'x_usage_purpose': persona['x_usage_purpose'] if persona else '',
                                'behavior_pattern': persona['behavior_pattern'] if persona else '',
                                'interested_topics': persona['interested_topics'] if persona else '',
                                'platform_pain_points': persona['platform_pain_points'] if persona else '',
                                'brand_relationship': persona['brand_relationship'] if persona else '',
                                'mission': mission['mission'] if mission else '',
                                'persona_design': mission['persona_design'] if mission else '',
                                'content_strategy': mission['content_strategy'] if mission else '',
                                'final_goal': mission['final_goal'] if mission else '',
                                'additional_notes': mission['additional_notes'] if mission else '',
                                'sample_profile': profile['profile_text'] if profile else '',
                                'x_api_key': x_creds['api_key'] if x_creds else '',
                                'x_api_secret': x_creds['api_secret'] if x_creds else '',
                                'x_bearer_token': x_creds['bearer_token'] if x_creds else '',
                                'x_access_token': x_creds['access_token'] if x_creds else '',
                                'x_access_token_secret': x_creds['access_token_secret'] if x_creds else '',
                                'x_twitter_username': x_creds['twitter_username'] if x_creds else '',
                                'x_twitter_user_id': x_creds['twitter_user_id'] if x_creds else ''
                            }
                            export_data.append(row_data)
                        
                        df = pd.DataFrame(export_data)
                        csv_buffer = io.StringIO()
                        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                        
                        st.download_button(
                            label="💾 cast_master.csv をダウンロード",
                            data=csv_buffer.getvalue(),
                            file_name="cast_master.csv",
                            mime="text/csv"
                        )
                        st.success(f"✅ {len(export_data)}件のキャストをエクスポートしました")
                    except Exception as e:
                        st.error(f"エクスポートエラー: {e}")
            
            # ===== サンプル投稿CSVタブ =====
            with csv_sample_posts_tab:
                st.markdown("### サンプル投稿のCSV管理")
                st.info("""
**CSVフォーマット:**
- username: キャスト名（紐付け用）
- category: カテゴリ名
- post_content: 投稿内容
- sort_order: 表示順（オプション）
""")
                
                # インポート
                st.markdown("#### 📥 インポート")
                uploaded_posts = st.file_uploader("サンプル投稿CSV", type="csv", key="sample_posts_csv")
                
                if uploaded_posts:
                    try:
                        import pandas as pd
                        df = pd.read_csv(uploaded_posts, dtype=str, keep_default_na=False).fillna("")
                        
                        st.write(f"**読み込んだデータ: {len(df)}件**")
                        st.dataframe(df.head())
                        
                        if st.button("💾 サンプル投稿をインポート", type="primary", key="import_sample_posts"):
                            success_count = 0
                            error_count = 0
                            
                            for idx, row in df.iterrows():
                                try:
                                    if not row.get('username') or not row.get('post_content'):
                                        error_count += 1
                                        continue
                                    
                                    cast = execute_query("SELECT id FROM casts WHERE name = ?", (row['username'],), fetch="one")
                                    if not cast:
                                        st.warning(f"行{idx+1}: キャスト '{row['username']}' が見つかりません")
                                        error_count += 1
                                        continue
                                    
                                    execute_query(
                                        """INSERT INTO sample_posts (cast_id, category, post_content, sort_order)
                                        VALUES (?, ?, ?, ?)""",
                                        (cast['id'], row.get('category', ''), row['post_content'],
                                         int(row.get('sort_order', 0)) if row.get('sort_order') else 0)
                                    )
                                    success_count += 1
                                except Exception as e:
                                    st.error(f"行{idx+1}: {e}")
                                    error_count += 1
                            
                            st.success(f"✅ インポート完了: 成功 {success_count}件、エラー {error_count}件")
                            st.rerun()
                    except Exception as e:
                        st.error(f"CSVの読み込みエラー: {e}")
                
                # エクスポート
                st.markdown("#### 📤 エクスポート")
                if st.button("📤 サンプル投稿CSVをダウンロード", key="export_sample_posts"):
                    try:
                        import pandas as pd
                        import io
                        
                        posts = execute_query(
                            """SELECT c.name as username, sp.category, sp.post_content, sp.sort_order
                            FROM sample_posts sp
                            JOIN casts c ON sp.cast_id = c.id
                            ORDER BY c.name, sp.category, sp.sort_order""",
                            fetch="all"
                        )
                        
                        export_data = [dict(p) for p in posts]
                        df = pd.DataFrame(export_data)
                        
                        csv_buffer = io.StringIO()
                        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                        
                        st.download_button(
                            label="💾 sample_posts.csv をダウンロード",
                            data=csv_buffer.getvalue(),
                            file_name="sample_posts.csv",
                            mime="text/csv"
                        )
                        st.success(f"✅ {len(export_data)}件のサンプル投稿をエクスポートしました")
                    except Exception as e:
                        st.error(f"エクスポートエラー: {e}")


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

