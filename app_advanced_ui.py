"""
AIcast Room - Advanced UI Version
高度な機能とUIを実装した完全版

🎖️ MCF Integration: Mission-Critical Functions included
🌟 Features: Advanced UI, Multi-panel layout, Enhanced workflow
📊 Analytics: Real-time statistics and monitoring
🔄 Automation: Scheduling and batch operations
"""

import streamlit as st
import pandas as pd
import datetime
import time
import random
import sqlite3
import vertexai
from vertexai.preview.generative_models import GenerativeModel
import os
import io
import re
import gspread
from google.oauth2.service_account import Credentials
import pickle
import json
from config import Config
from x_api_poster import post_to_x_simple, test_x_api_connection

# pandasの参照を保護
pandas_lib = pd

# JST timezone
JST = datetime.timezone(datetime.timedelta(hours=9))

# --- 設定 ---
project_id = os.environ.get("GCP_PROJECT")
if not project_id:
    project_id = os.environ.get("DEVSHELL_PROJECT_ID", "aicast-472807")
location = "asia-northeast1"
DB_FILE = "casting_office.db"

# --- データベースの列定義 ---
PERSONA_FIELDS = [
    "name", "nickname", "age", "birthday", "birthplace", "appearance",
    "personality", "strength", "weakness", "first_person", "speech_style", 
    "catchphrase", "customer_interaction", "occupation", "hobby", "likes", 
    "dislikes", "holiday_activity", "dream", "reason_for_job", "secret",
    "allowed_categories"
]

# --- Advanced UI Configuration ---
UI_THEMES = {
    "classic": {"primary": "#FF6B6B", "secondary": "#4ECDC4", "accent": "#45B7D1"},
    "dark": {"primary": "#BB86FC", "secondary": "#03DAC6", "accent": "#CF6679"},
    "professional": {"primary": "#1976D2", "secondary": "#388E3C", "accent": "#F57C00"}
}

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
            return dict(result) if result else None
        elif fetch == "all":
            results = cursor.fetchall()
            return [dict(row) for row in results] if results else []
        else:
            conn.commit()
            return cursor.lastrowid if cursor.lastrowid else None
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
    
    # Core tables
    casts_table_query = f"CREATE TABLE IF NOT EXISTS casts (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, {persona_columns})"
    posts_table_query = """CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY, 
        cast_id INTEGER, 
        created_at TEXT, 
        content TEXT, 
        theme TEXT, 
        evaluation TEXT, 
        advice TEXT, 
        free_advice TEXT, 
        status TEXT DEFAULT 'draft', 
        posted_at TEXT, 
        sent_status TEXT DEFAULT 'not_sent', 
        sent_at TEXT,
        scheduled_at TEXT,
        priority INTEGER DEFAULT 1,
        tags TEXT,
        word_count INTEGER,
        engagement_prediction REAL,
        FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE
    )"""
    
    situations_table_query = """CREATE TABLE IF NOT EXISTS situations (
        id INTEGER PRIMARY KEY, 
        content TEXT NOT NULL UNIQUE, 
        time_slot TEXT DEFAULT 'いつでも', 
        category_id INTEGER,
        usage_count INTEGER DEFAULT 0,
        last_used TEXT,
        effectiveness_score REAL DEFAULT 0.0,
        FOREIGN KEY(category_id) REFERENCES situation_categories(id) ON DELETE CASCADE
    )"""
    
    categories_table_query = """CREATE TABLE IF NOT EXISTS situation_categories (
        id INTEGER PRIMARY KEY, 
        name TEXT NOT NULL UNIQUE, 
        description TEXT,
        color TEXT DEFAULT '#4ECDC4',
        icon TEXT DEFAULT '📁'
    )"""
    
    # MCF関連テーブル
    cast_x_credentials_table_query = """CREATE TABLE IF NOT EXISTS cast_x_credentials (
        id INTEGER PRIMARY KEY, 
        cast_id INTEGER UNIQUE, 
        api_key TEXT, 
        api_secret TEXT, 
        bearer_token TEXT, 
        access_token TEXT, 
        access_token_secret TEXT, 
        created_at TEXT DEFAULT CURRENT_TIMESTAMP, 
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_post_at TEXT,
        total_posts INTEGER DEFAULT 0,
        success_rate REAL DEFAULT 0.0,
        FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE
    )"""
    
    retweet_schedules_table_query = """CREATE TABLE IF NOT EXISTS retweet_schedules (
        id INTEGER PRIMARY KEY, 
        cast_id INTEGER, 
        target_url TEXT NOT NULL, 
        scheduled_at TEXT NOT NULL, 
        status TEXT DEFAULT 'pending', 
        comment TEXT, 
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        executed_at TEXT,
        retry_count INTEGER DEFAULT 0,
        FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE
    )"""
    
    send_history_table_query = """CREATE TABLE IF NOT EXISTS send_history (
        id INTEGER PRIMARY KEY, 
        post_id INTEGER, 
        destination TEXT, 
        sent_at TEXT, 
        status TEXT, 
        response_details TEXT,
        response_time REAL,
        FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE
    )"""
    
    # Analytics tables
    analytics_table_query = """CREATE TABLE IF NOT EXISTS analytics (
        id INTEGER PRIMARY KEY,
        cast_id INTEGER,
        date TEXT,
        posts_created INTEGER DEFAULT 0,
        posts_approved INTEGER DEFAULT 0,
        posts_sent INTEGER DEFAULT 0,
        avg_word_count REAL DEFAULT 0.0,
        engagement_score REAL DEFAULT 0.0,
        FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE
    )"""
    
    tables = [
        casts_table_query, posts_table_query, situations_table_query, 
        categories_table_query, cast_x_credentials_table_query, 
        retweet_schedules_table_query, send_history_table_query,
        analytics_table_query
    ]
    
    for table in tables:
        execute_query(table)

# --- UI Helper Functions ---
def show_auth_error_guidance(error_msg, context="AI生成"):
    """認証エラー時の案内を表示する共通関数"""
    st.error(f"🔐 **Google Cloud認証エラー ({context})**")
    
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

def display_cast_card(cast, show_details=False):
    """キャスト情報をカード形式で表示"""
    with st.container():
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            st.markdown("### 🎭")
        
        with col2:
            display_name = f"{cast['name']}"
            if cast.get('nickname'):
                display_name += f" ({cast['nickname']})"
            st.markdown(f"### {display_name}")
            
            if show_details:
                if cast.get('age'):
                    st.caption(f"年齢: {cast['age']}")
                if cast.get('personality'):
                    st.caption(f"性格: {cast['personality'][:50]}...")
        
        with col3:
            x_creds = execute_query(
                "SELECT COUNT(*) as count FROM cast_x_credentials WHERE cast_id = ?",
                (cast['id'],),
                fetch="one"
            )
            if x_creds and x_creds['count'] > 0:
                st.success("🔗 X API")
            else:
                st.info("⚪ 未設定")

def display_post_card(post, cast_name="", show_actions=True):
    """投稿をカード形式で表示"""
    status_colors = {
        'draft': '🟡',
        'approved': '🟢', 
        'rejected': '🔴',
        'sent': '✅'
    }
    
    with st.expander(f"{status_colors.get(post['status'], '⚪')} {post['theme']} - {cast_name}", expanded=False):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.write(post['content'])
            st.caption(f"作成: {post['created_at']}")
            
            if post.get('word_count'):
                st.caption(f"文字数: {post['word_count']}")
            
            if post.get('tags'):
                tags = post['tags'].split(',') if post['tags'] else []
                for tag in tags:
                    st.badge(tag.strip())
        
        with col2:
            if show_actions and post['status'] == 'draft':
                if st.button("✅ 承認", key=f"approve_{post['id']}", use_container_width=True):
                    execute_query("UPDATE posts SET status = 'approved' WHERE id = ?", (post['id'],))
                    st.rerun()
                
                if st.button("❌ 却下", key=f"reject_{post['id']}", use_container_width=True):
                    execute_query("UPDATE posts SET status = 'rejected' WHERE id = ?", (post['id'],))
                    st.rerun()

def display_analytics_dashboard():
    """アナリティクスダッシュボードを表示"""
    st.subheader("📊 システム分析")
    
    # 全体統計
    total_casts = execute_query("SELECT COUNT(*) as count FROM casts", fetch="one")['count']
    total_posts = execute_query("SELECT COUNT(*) as count FROM posts", fetch="one")['count']
    approved_posts = execute_query("SELECT COUNT(*) as count FROM posts WHERE status = 'approved'", fetch="one")['count']
    sent_posts = execute_query("SELECT COUNT(*) as count FROM posts WHERE sent_status = 'sent'", fetch="one")['count']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("登録キャスト", total_casts, help="システムに登録されているキャスト数")
    
    with col2:
        st.metric("総投稿数", total_posts, help="作成された投稿の総数")
    
    with col3:
        approval_rate = (approved_posts / total_posts * 100) if total_posts > 0 else 0
        st.metric("承認率", f"{approval_rate:.1f}%", help="承認された投稿の割合")
    
    with col4:
        send_rate = (sent_posts / approved_posts * 100) if approved_posts > 0 else 0
        st.metric("送信率", f"{send_rate:.1f}%", help="送信された投稿の割合")
    
    # 最近の活動
    st.markdown("### 📈 最近の活動")
    recent_posts = execute_query("""
        SELECT p.*, c.name as cast_name 
        FROM posts p 
        JOIN casts c ON p.cast_id = c.id 
        ORDER BY p.created_at DESC 
        LIMIT 5
    """, fetch="all")
    
    if recent_posts:
        for post in recent_posts:
            display_post_card(post, post['cast_name'], show_actions=False)
    else:
        st.info("まだ投稿がありません")

def format_persona(cast_id, cast_details):
    """キャストの詳細情報をプロンプト用に整形"""
    formatted = f"名前: {cast_details['name']}"
    if cast_details.get('nickname'):
        formatted += f" (愛称: {cast_details['nickname']})"
    formatted += "\n"
    
    field_labels = {
        "age": "年齢", "birthday": "誕生日", "birthplace": "出身地", "appearance": "外見",
        "personality": "性格", "strength": "強み", "weakness": "弱点", "first_person": "一人称",
        "speech_style": "話し方", "catchphrase": "決め台詞", "customer_interaction": "お客様との接し方",
        "occupation": "職業", "hobby": "趣味", "likes": "好きなもの", "dislikes": "苦手なもの",
        "holiday_activity": "休日の過ごし方", "dream": "夢・目標", "reason_for_job": "この仕事をする理由", "secret": "秘密"
    }
    
    for field, label in field_labels.items():
        if cast_details.get(field):
            formatted += f"{label}: {cast_details[field]}\n"
    
    return formatted.strip()

# --- Authentication Functions ---
def check_google_auth():
    """Google Cloud認証状況をチェック"""
    try:
        import google.auth
        credentials, project = google.auth.default()
        return True, credentials, project
    except Exception as e:
        return False, None, str(e)

def load_vertex_ai():
    """Vertex AIを安全に初期化"""
    try:
        auth_ok, creds, project_or_error = check_google_auth()
        if not auth_ok:
            return False, f"Google Cloud認証エラー: {project_or_error}"
        
        vertexai.init(project=project_id, location=location)
        return True, "Vertex AI初期化成功"
    except Exception as e:
        return False, f"Vertex AI初期化エラー: {str(e)}"

# --- AI Content Generation ---
def generate_post_content(cast_details, theme, situation=""):
    """AIを使用して投稿内容を生成"""
    try:
        vertex_ok, vertex_msg = load_vertex_ai()
        if not vertex_ok:
            show_auth_error_guidance(vertex_msg, "投稿生成")
            return None, vertex_msg
        
        model = GenerativeModel("gemini-1.5-flash")
        
        persona_text = format_persona(cast_details['id'], cast_details)
        
        prompt = f"""
以下のキャラクター設定に基づいて、SNS投稿（X/Twitter）を作成してください。

{persona_text}

テーマ: {theme}
{f"シチュエーション: {situation}" if situation else ""}

条件:
- 文字数は280文字以内
- キャラクターの口調と性格を忠実に再現
- 自然で親しみやすい内容
- ハッシュタグを1-2個含める
- 絵文字を適度に使用

投稿内容のみを出力してください:
"""
        
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # 文字数チェック
        word_count = len(content)
        if word_count > 280:
            st.warning(f"⚠️ 文字数オーバー: {word_count}文字（280文字制限）")
        
        return content, None
        
    except Exception as e:
        error_msg = f"AI生成エラー: {str(e)}"
        show_auth_error_guidance(str(e), "投稿生成")
        return None, error_msg

# --- Sending Functions ---
def send_to_google_sheets(post_content, cast_name="不明", context="投稿"):
    """Google Sheetsに投稿を送信"""
    try:
        credentials_path = "credentials/credentials.json"
        token_path = "credentials/token.pickle"
        
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        else:
            if not os.path.exists(credentials_path):
                return False, "OAuth認証ファイルが見つかりません"
            
            return False, "初回認証が必要です"
        
        gc = gspread.authorize(creds)
        spreadsheet_url = "https://docs.google.com/spreadsheets/d/1EHR8WKMXwvMkUlR8wQXuPYLQLqtJQa_N2VYvQ4Kp8RA"
        sheet = gc.open_by_url(spreadsheet_url).sheet1
        
        timestamp = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
        sheet.append_row([timestamp, cast_name, post_content, context])
        
        return True, "Google Sheetsに送信完了"
    
    except Exception as e:
        return False, f"送信エラー: {str(e)}"

def send_to_x_api(post_content, cast_id, cast_name):
    """X APIに投稿を送信"""
    try:
        # Get credentials
        credentials = execute_query(
            "SELECT * FROM cast_x_credentials WHERE cast_id = ?",
            (cast_id,),
            fetch="one"
        )
        
        if not credentials:
            return False, "X API認証情報が設定されていません"
        
        # Prepare credentials dict
        creds_dict = {
            'api_key': credentials['api_key'],
            'api_secret': credentials['api_secret'],
            'bearer_token': credentials['bearer_token'],
            'access_token': credentials['access_token'],
            'access_token_secret': credentials['access_token_secret']
        }
        
        # Post using MCF system
        result = post_to_x_simple(post_content, creds_dict, cast_name)
        
        if result['success']:
            # Update statistics
            execute_query("""
                UPDATE cast_x_credentials 
                SET last_post_at = ?, total_posts = total_posts + 1 
                WHERE cast_id = ?
            """, (datetime.datetime.now(JST).isoformat(), cast_id))
            
            return True, "X API投稿成功"
        else:
            return False, result['message']
    
    except Exception as e:
        return False, f"X API投稿エラー: {str(e)}"

# --- Main Application ---
def main():
    st.set_page_config(
        page_title="AIcast Room - Advanced", 
        page_icon="🎭", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Load custom CSS
    try:
        with open("style.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass
    
    # Initialize database
    init_db()
    
    # Sidebar navigation
    with st.sidebar:
        st.title("🎭 AIcast Room")
        st.markdown("**Advanced UI Version**")
        
        # MCF System Status
        st.markdown("---")
        st.markdown("### 🎖️ MCF System Status")
        
        mcf_errors = Config.validate_mcf_settings()
        if mcf_errors:
            st.error("⚠️ MCF Configuration Issues")
            for error in mcf_errors:
                st.caption(error)
        else:
            st.success("✅ MCF System Ready")
        
        # Navigation
        st.markdown("---")
        selected_page = st.selectbox(
            "ページを選択",
            [
                "🏠 ダッシュボード",
                "✍️ 投稿管理", 
                "🎭 キャスト管理", 
                "🎬 シチュエーション管理",
                "📊 アナリティクス",
                "⚙️ システム設定"
            ],
            key="selected_page"
        )
    
    # Main content area
    if selected_page == "🏠 ダッシュボード":
        st.title("🏠 AIcast Room ダッシュボード")
        display_analytics_dashboard()
        
        # Quick actions
        st.markdown("---")
        st.subheader("🚀 クイックアクション")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("➕ 新規投稿作成", use_container_width=True):
                st.session_state.selected_page = "✍️ 投稿管理"
                st.rerun()
        
        with col2:
            if st.button("🎭 キャスト追加", use_container_width=True):
                st.session_state.selected_page = "🎭 キャスト管理"
                st.rerun()
        
        with col3:
            if st.button("📊 詳細分析", use_container_width=True):
                st.session_state.selected_page = "📊 アナリティクス"
                st.rerun()
    
    elif selected_page == "✍️ 投稿管理":
        st.title("✍️ 投稿管理")
        
        # Cast selection
        casts = execute_query("SELECT * FROM casts ORDER BY name", fetch="all")
        if not casts:
            st.warning("⚠️ キャストが登録されていません。まずキャストを追加してください。")
            return
        
        cast_options = [f"{cast['name']} ({cast['nickname']})" if cast['nickname'] else cast['name'] for cast in casts]
        selected_cast_idx = st.selectbox("キャストを選択", range(len(cast_options)), format_func=lambda x: cast_options[x])
        selected_cast = casts[selected_cast_idx]
        
        # Content generation
        st.markdown("### 📝 投稿生成")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            theme = st.text_input("テーマ", placeholder="例：今日の気分、おすすめ商品など")
            
            # Situation selection
            situations = execute_query("SELECT * FROM situations ORDER BY content", fetch="all")
            situation_options = ["なし"] + [sit['content'] for sit in situations]
            selected_situation = st.selectbox("シチュエーション（任意）", situation_options)
            
            if st.button("🤖 AI生成", type="primary"):
                if theme:
                    situation_text = selected_situation if selected_situation != "なし" else ""
                    
                    with st.spinner("AI生成中..."):
                        content, error = generate_post_content(selected_cast, theme, situation_text)
                    
                    if content:
                        # Save to database
                        word_count = len(content)
                        post_id = execute_query("""
                            INSERT INTO posts (cast_id, created_at, content, theme, status, word_count)
                            VALUES (?, ?, ?, ?, 'draft', ?)
                        """, (
                            selected_cast['id'],
                            datetime.datetime.now(JST).isoformat(),
                            content,
                            theme,
                            word_count
                        ))
                        
                        if post_id:
                            st.success("投稿を生成しました！")
                            st.rerun()
                        else:
                            st.error("投稿の保存に失敗しました")
                    else:
                        st.error(f"生成失敗: {error}")
                else:
                    st.warning("テーマを入力してください")
        
        with col2:
            display_cast_card(selected_cast, show_details=True)
        
        # Posts management with tabs
        st.markdown("---")
        st.subheader(f"📋 {selected_cast['name']} の投稿一覧")
        
        tab1, tab2, tab3, tab4 = st.tabs(["🟡 下書き", "🟢 承認済み", "✅ 送信済み", "🔴 却下済み"])
        
        with tab1:
            draft_posts = execute_query(
                "SELECT * FROM posts WHERE cast_id = ? AND status = 'draft' ORDER BY created_at DESC",
                (selected_cast['id'],),
                fetch="all"
            )
            
            if draft_posts:
                for post in draft_posts:
                    display_post_card(post, selected_cast['name'])
            else:
                st.info("下書きはありません")
        
        with tab2:
            approved_posts = execute_query(
                "SELECT * FROM posts WHERE cast_id = ? AND status = 'approved' ORDER BY created_at DESC",
                (selected_cast['id'],),
                fetch="all"
            )
            
            if approved_posts:
                for post in approved_posts:
                    with st.expander(f"✅ {post['theme']}", expanded=False):
                        st.write(post['content'])
                        st.caption(f"承認日: {post['created_at']}")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button("📤 Google Sheets送信", key=f"sheets_{post['id']}"):
                                success, message = send_to_google_sheets(
                                    post['content'], 
                                    selected_cast['name'], 
                                    "AIcast投稿"
                                )
                                if success:
                                    execute_query(
                                        "UPDATE posts SET sent_status = 'sent', sent_at = ? WHERE id = ?",
                                        (datetime.datetime.now(JST).isoformat(), post['id'])
                                    )
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
                        
                        with col2:
                            if st.button("🐦 X API送信", key=f"x_{post['id']}"):
                                success, message = send_to_x_api(
                                    post['content'],
                                    selected_cast['id'],
                                    selected_cast['name']
                                )
                                if success:
                                    execute_query(
                                        "UPDATE posts SET sent_status = 'sent', sent_at = ? WHERE id = ?",
                                        (datetime.datetime.now(JST).isoformat(), post['id'])
                                    )
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
                        
                        with col3:
                            if st.button("🗑️ 削除", key=f"delete_{post['id']}"):
                                execute_query("DELETE FROM posts WHERE id = ?", (post['id'],))
                                st.success("投稿を削除しました")
                                st.rerun()
            else:
                st.info("承認済み投稿はありません")
        
        with tab3:
            sent_posts = execute_query(
                "SELECT * FROM posts WHERE cast_id = ? AND sent_status = 'sent' ORDER BY sent_at DESC",
                (selected_cast['id'],),
                fetch="all"
            )
            
            if sent_posts:
                for post in sent_posts:
                    with st.expander(f"📤 {post['theme']} (送信済み)", expanded=False):
                        st.write(post['content'])
                        st.success(f"送信日時: {post['sent_at']}")
            else:
                st.info("送信済み投稿はありません")
        
        with tab4:
            rejected_posts = execute_query(
                "SELECT * FROM posts WHERE cast_id = ? AND status = 'rejected' ORDER BY created_at DESC",
                (selected_cast['id'],),
                fetch="all"
            )
            
            if rejected_posts:
                for post in rejected_posts:
                    display_post_card(post, selected_cast['name'], show_actions=False)
            else:
                st.info("却下された投稿はありません")
    
    elif selected_page == "🎭 キャスト管理":
        st.title("🎭 キャスト管理")
        
        # キャスト一覧表示
        casts = execute_query("SELECT * FROM casts ORDER BY name", fetch="all")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("登録済みキャスト")
            
            if casts:
                for cast in casts:
                    display_cast_card(cast, show_details=True)
            else:
                st.info("まだキャストが登録されていません")
        
        with col2:
            st.subheader("新しいキャストを追加")
            
            with st.form("add_cast_form"):
                name = st.text_input("名前 *", placeholder="田中花子")
                nickname = st.text_input("愛称", placeholder="はなちゃん")
                age = st.text_input("年齢", placeholder="25")
                personality = st.text_area("性格", placeholder="明るく元気で、いつも笑顔...")
                
                if st.form_submit_button("💾 キャスト追加", type="primary"):
                    if name:
                        persona_values = [name]
                        persona_values.extend([nickname, age, "", "", "", personality, "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
                        
                        placeholders = ", ".join(["?" for _ in PERSONA_FIELDS])
                        query = f"INSERT INTO casts ({', '.join(PERSONA_FIELDS)}) VALUES ({placeholders})"
                        
                        if execute_query(query, persona_values):
                            st.success(f"キャスト「{name}」を追加しました！")
                            st.rerun()
                        else:
                            st.error("キャストの追加に失敗しました")
                    else:
                        st.warning("名前は必須です")
    
    elif selected_page == "📊 アナリティクス":
        st.title("📊 詳細アナリティクス")
        display_analytics_dashboard()
        
        # Additional analytics here
        st.markdown("### 📈 投稿トレンド")
        
        # Recent posts chart
        recent_posts = execute_query("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM posts 
            WHERE created_at >= date('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        """, fetch="all")
        
        if recent_posts:
            df = pd.DataFrame(recent_posts)
            df['date'] = pd.to_datetime(df['date'])
            st.line_chart(df.set_index('date'))
        else:
            st.info("表示できるデータがありません")
    
    elif selected_page == "⚙️ システム設定":
        st.title("⚙️ システム設定")
        
        tab1, tab2, tab3 = st.tabs(["🔐 認証設定", "🎖️ MCF設定", "📊 システム情報"])
        
        with tab1:
            st.subheader("Google Cloud認証")
            
            auth_ok, creds, project_or_error = check_google_auth()
            
            if auth_ok:
                st.success("✅ Google Cloud認証: 正常")
                st.info(f"プロジェクト: {project_or_error}")
                
                # Test Vertex AI
                vertex_ok, vertex_msg = load_vertex_ai()
                if vertex_ok:
                    st.success("✅ Vertex AI: 接続正常")
                else:
                    st.error(f"❌ Vertex AI: {vertex_msg}")
            else:
                st.error("❌ Google Cloud認証: エラー")
                st.error(project_or_error)
        
        with tab2:
            st.subheader("Mission-Critical Functions (MCF)")
            
            # MCF validation
            mcf_errors = Config.validate_mcf_settings()
            
            if mcf_errors:
                st.error("⚠️ MCF Configuration Issues")
                for error in mcf_errors:
                    st.error(error)
            else:
                st.success("✅ All MCF validations passed")
            
            # MCF settings display
            st.markdown("### 📋 MCF Configuration")
            st.code(f"""
Cloud Functions URL: {Config.get_cloud_functions_url()}
Test Account ID: {Config.get_test_account_id()}
Production Environment: {Config.is_production_environment()}
            """)
            
            # Test X API connection
            if st.button("🧪 Test X API Connection"):
                with st.spinner("Testing connection..."):
                    result = test_x_api_connection()
                
                if result['success']:
                    st.success("✅ X API Connection: OK")
                else:
                    st.error(f"❌ X API Connection: {result['message']}")
        
        with tab3:
            st.subheader("システム情報")
            
            # Database stats
            stats = {
                "キャスト数": execute_query("SELECT COUNT(*) as count FROM casts", fetch="one")['count'],
                "投稿数": execute_query("SELECT COUNT(*) as count FROM posts", fetch="one")['count'],
                "X API設定済み": execute_query("SELECT COUNT(*) as count FROM cast_x_credentials", fetch="one")['count'],
                "シチュエーション数": execute_query("SELECT COUNT(*) as count FROM situations", fetch="one")['count']
            }
            
            for key, value in stats.items():
                st.metric(key, value)
            
            # Database management
            st.markdown("---")
            st.subheader("データベース管理")
            
            if st.button("🔄 データベース初期化", type="secondary"):
                init_db()
                st.success("データベースを初期化しました")

if __name__ == "__main__":
    main()