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

# pandasの参照を保護
pandas_lib = pd

# 認証エラー用のヘルパー関数
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
location = "asia-northeast1"
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
    posts_table_query = "CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, cast_id INTEGER, created_at TEXT, content TEXT, theme TEXT, evaluation TEXT, advice TEXT, free_advice TEXT, status TEXT DEFAULT 'draft', posted_at TEXT, sent_status TEXT DEFAULT 'not_sent', sent_at TEXT, FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE)"
    situations_table_query = "CREATE TABLE IF NOT EXISTS situations (id INTEGER PRIMARY KEY, content TEXT NOT NULL UNIQUE, time_slot TEXT DEFAULT 'いつでも', category_id INTEGER, FOREIGN KEY(category_id) REFERENCES situation_categories(id) ON DELETE CASCADE)"
    categories_table_query = "CREATE TABLE IF NOT EXISTS situation_categories (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT)"
    # MCF関連テーブル
    cast_x_credentials_table_query = "CREATE TABLE IF NOT EXISTS cast_x_credentials (id INTEGER PRIMARY KEY, cast_id INTEGER UNIQUE, api_key TEXT, api_secret TEXT, bearer_token TEXT, access_token TEXT, access_token_secret TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE)"
    retweet_schedules_table_query = "CREATE TABLE IF NOT EXISTS retweet_schedules (id INTEGER PRIMARY KEY, cast_id INTEGER, target_url TEXT NOT NULL, scheduled_at TEXT NOT NULL, status TEXT DEFAULT 'pending', comment TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE)"
    send_history_table_query = "CREATE TABLE IF NOT EXISTS send_history (id INTEGER PRIMARY KEY, post_id INTEGER, destination TEXT, sent_at TEXT, status TEXT, response_details TEXT, FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE)"
    
    tables = [casts_table_query, posts_table_query, situations_table_query, categories_table_query, cast_x_credentials_table_query, retweet_schedules_table_query, send_history_table_query]
    for table in tables:
        execute_query(table)

def format_persona(cast_id, cast_details):
    """キャストの詳細情報をプロンプト用に整形"""
    formatted = f"名前: {cast_details['name']}"
    if cast_details['nickname']:
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
        if cast_details[field]:
            formatted += f"{label}: {cast_details[field]}\n"
    
    return formatted.strip()

def set_editing_post(post_id):
    """編集対象の投稿をセッション状態に設定"""
    st.session_state.editing_post_id = post_id

def quick_approve(post_id):
    """投稿を迅速承認"""
    execute_query("UPDATE posts SET status = 'approved' WHERE id = ?", (post_id,))
    st.success("投稿を承認しました！")
    time.sleep(1)
    st.rerun()

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
            
            from google_auth_oauthlib.flow import Flow
            from google.auth.transport.requests import Request
            
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            flow = Flow.from_client_secrets_file(credentials_path, SCOPES)
            flow.redirect_uri = 'http://localhost:8080'
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            return False, f"初回認証が必要です。認証URL: {auth_url}"
        
        gc = gspread.authorize(creds)
        spreadsheet_url = "https://docs.google.com/spreadsheets/d/1EHR8WKMXwvMkUlR8wQXuPYLQLqtJQa_N2VYvQ4Kp8RA"
        sheet = gc.open_by_url(spreadsheet_url).sheet1
        
        timestamp = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
        sheet.append_row([timestamp, cast_name, post_content, context])
        
        return True, "Google Sheetsに送信完了"
    
    except Exception as e:
        return False, f"送信エラー: {str(e)}"

def main():
    st.set_page_config(page_title="AIcast Room", page_icon="🎭", layout="wide")
    
    # CSSファイルの読み込み
    try:
        with open("style.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass
    
    init_db()
    
    # リダイレクトチェック
    if st.session_state.get('redirect_to_settings'):
        st.session_state['redirect_to_settings'] = False
        st.session_state['selected_page'] = 'システム設定'
    
    # サイドバーでページ選択
    with st.sidebar:
        st.title("🎭 AIcast Room")
        selected_page = st.selectbox(
            "ページを選択",
            ["投稿管理", "キャスト管理", "シチュエーション管理", "システム設定"],
            key="selected_page"
        )
    
    # Vertex AI初期化
    if 'gemini_model' not in st.session_state:
        vertex_ok, vertex_msg = load_vertex_ai()
        if vertex_ok:
            try:
                model_name = "gemini-1.5-flash"
                st.session_state.gemini_model = GenerativeModel(model_name)
            except Exception as e:
                st.session_state.gemini_model = None
                st.sidebar.error(f"Geminiモデル読み込みエラー: {str(e)}")
        else:
            st.session_state.gemini_model = None
            st.sidebar.error(f"Vertex AI初期化失敗: {vertex_msg}")
    
    if selected_page == "投稿管理":
        st.title("🎭 AIcast Room - 投稿管理")
        
        # キャスト選択
        casts = execute_query("SELECT * FROM casts ORDER BY name", fetch="all")
        if not casts:
            st.warning("キャストが登録されていません。まず「キャスト管理」でキャストを登録してください。")
            return
        
        cast_options = [f"{cast['name']}（{cast['nickname']}）" if cast['nickname'] else cast['name'] for cast in casts]
        selected_cast_display = st.selectbox("キャストを選択", cast_options)
        selected_cast_name = selected_cast_display.split('（')[0]
        selected_cast_id = next(cast['id'] for cast in casts if cast['name'] == selected_cast_name)
        selected_cast_details = next(cast for cast in casts if cast['name'] == selected_cast_name)
        
        # 投稿生成セクション
        st.subheader("新しい投稿を生成")
        
        # シチュエーション取得
        cast_categories = selected_cast_details['allowed_categories']
        if cast_categories:
            category_ids = [int(cat_id.strip()) for cat_id in cast_categories.split(',') if cat_id.strip().isdigit()]
            if category_ids:
                placeholders = ','.join(['?'] * len(category_ids))
                situations_rows = execute_query(f"SELECT * FROM situations WHERE category_id IN ({placeholders})", category_ids, fetch="all")
            else:
                situations_rows = execute_query("SELECT * FROM situations", fetch="all")
        else:
            situations_rows = execute_query("SELECT * FROM situations", fetch="all")
        
        if not situations_rows:
            st.warning("利用可能なシチュエーションがありません。")
            return
        
        # 投稿生成フォーム
        with st.form("generate_posts_form"):
            col1, col2 = st.columns(2)
            with col1:
                num_posts = st.number_input("生成する投稿数", min_value=1, max_value=10, value=1)
            with col2:
                char_limit = st.number_input("文字数制限", min_value=50, max_value=500, value=140)
            
            generate_button = st.form_submit_button("投稿を生成", type="primary")
            
            if generate_button:
                if st.session_state.gemini_model:
                    with st.spinner("投稿を生成中です..."):
                        persona_sheet = format_persona(selected_cast_id, selected_cast_details)
                        for i in range(num_posts):
                            try:
                                selected_situation = random.choice(situations_rows)
                                prompt_template = f"""# ペルソナ\n{persona_sheet}\n\n# シチュエーション\n{selected_situation['content']}\n\n# ルール\nSNS投稿を**{char_limit}文字以内**で生成。"""
                                response = st.session_state.gemini_model.generate_content(prompt_template)
                                generated_text = response.text
                                
                                time_slot_map = {"朝": (7, 11), "昼": (12, 17), "夜": (18, 23)}
                                hour_range = time_slot_map.get(selected_situation['time_slot'], (0, 23))
                                random_hour = random.randint(hour_range[0], hour_range[1])
                                random_minute = random.randint(0, 59)
                                created_at = datetime.datetime.now(JST).replace(hour=random_hour, minute=random_minute, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
                                
                                execute_query("INSERT INTO posts (cast_id, created_at, content, theme) VALUES (?, ?, ?, ?)", 
                                            (selected_cast_id, created_at, generated_text, selected_situation['content']))
                                time.sleep(2)
                            except Exception as e:
                                st.error(f"投稿生成中にエラーが発生しました: {e}")
                                continue
                    
                    st.success(f"{num_posts}件の投稿案をデータベースに保存しました！")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("AIモデルの読み込みに失敗しているため、投稿を生成できません。")
        
        st.markdown("---")
        
        # 選択されたキャストの表示名を作成
        current_cast = next((c for c in casts if c['name'] == selected_cast_name), None)
        cast_display_name = f"{current_cast['name']}（{current_cast['nickname']}）" if current_cast and current_cast['nickname'] else selected_cast_name
        st.header(f"「{cast_display_name}」の投稿一覧")
        
        # 6タブ構成
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["投稿案 (Drafts)", "承認済み (Approved)", "送信済み (Sent)", "却下済み (Rejected)", "📅 スケジュール投稿", "🔄 リツイート予約"])
        
        with tab1:
            draft_posts = execute_query("SELECT * FROM posts WHERE cast_id = ? AND status = 'draft' ORDER BY created_at DESC", (selected_cast_id,), fetch="all")
            if draft_posts:
                st.info(f"{len(draft_posts)}件の投稿案があります。")
                for post in draft_posts:
                    post_id = post['id']
                    with st.container():
                        col1, col2, col3 = st.columns([6,1,1])
                        with col1:
                            st.caption(f"作成: {post['created_at']} | テーマ: {post['theme']}")
                            st.write(post['content'])
                        with col2:
                            st.button("チューニング", key=f"edit_{post_id}", on_click=set_editing_post, args=(post_id,), use_container_width=True)
                        with col3:
                            st.button("承認", type="primary", key=f"quick_approve_{post_id}", on_click=quick_approve, args=(post_id,), use_container_width=True)
                        st.markdown("---")
            else:
                st.info("チューニング対象の投稿案はありません。")
        
        with tab2:
            # Google Sheets連携設定状況表示
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
2. APIs & Services > Credentials でOAuth 2.0 Client IDを作成
3. ダウンロードしたJSONファイルを `credentials/credentials.json` として保存
4. 初回送信時にブラウザでGoogle認証を完了

設定完了後、このメッセージは自動的に消えます。""")
            
            approved_posts = execute_query("SELECT * FROM posts WHERE cast_id = ? AND status = 'approved' ORDER BY created_at DESC", (selected_cast_id,), fetch="all")
            if approved_posts:
                st.info(f"{len(approved_posts)}件の承認済み投稿があります。")
                for post in approved_posts:
                    with st.container():
                        col1, col2 = st.columns([5, 1])
                        with col1:
                            st.caption(f"作成: {post['created_at']} | テーマ: {post['theme']}")
                            st.write(post['content'])
                            
                            # 送信状況表示
                            if post['sent_status'] == 'sent':
                                st.success(f"✅ 送信済み ({post['sent_at']})")
                            elif post['sent_status'] == 'sending':
                                st.info("📤 送信中...")
                            else:
                                st.warning("📋 未送信")
                        
                        with col2:
                            if post['sent_status'] != 'sent':
                                if st.button("Google Sheetsに送信", key=f"send_{post['id']}", use_container_width=True):
                                    with st.spinner("Google Sheetsに送信中..."):
                                        # 送信状況を更新
                                        execute_query("UPDATE posts SET sent_status = 'sending' WHERE id = ?", (post['id'],))
                                        
                                        # 実際の送信処理
                                        success, message = send_to_google_sheets(post['content'], selected_cast_name, "承認済み投稿")
                                        
                                        if success:
                                            # 送信成功時の処理
                                            sent_time = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                                            execute_query("UPDATE posts SET sent_status = 'sent', sent_at = ? WHERE id = ?", (sent_time, post['id']))
                                            execute_query("INSERT INTO send_history (post_id, destination, sent_at, status, response_details) VALUES (?, ?, ?, ?, ?)", 
                                                        (post['id'], 'google_sheets', sent_time, 'success', message))
                                            st.success("✅ Google Sheetsに送信完了！")
                                        else:
                                            # 送信失敗時の処理
                                            execute_query("UPDATE posts SET sent_status = 'failed' WHERE id = ?", (post['id'],))
                                            execute_query("INSERT INTO send_history (post_id, destination, sent_at, status, response_details) VALUES (?, ?, ?, ?, ?)", 
                                                        (post['id'], 'google_sheets', datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S'), 'failed', message))
                                            st.error(f"❌ 送信失敗: {message}")
                                        
                                        time.sleep(1)
                                        st.rerun()
                        st.markdown("---")
            else:
                st.info("承認済みの投稿はありません。")
        
        with tab3:
            sent_posts = execute_query("SELECT * FROM posts WHERE cast_id = ? AND status = 'approved' AND sent_status = 'sent' ORDER BY sent_at DESC", (selected_cast_id,), fetch="all")
            if sent_posts:
                st.info(f"{len(sent_posts)}件の送信済み投稿があります。")
                for post in sent_posts:
                    with st.container():
                        st.caption(f"作成: {post['created_at']} | 送信: {post['sent_at']} | テーマ: {post['theme']}")
                        st.write(post['content'])
                        st.markdown("---")
            else:
                st.info("送信済みの投稿はありません。")
        
        with tab4:
            rejected_posts = execute_query("SELECT * FROM posts WHERE cast_id = ? AND status = 'rejected' ORDER BY created_at DESC", (selected_cast_id,), fetch="all")
            if rejected_posts:
                st.info(f"{len(rejected_posts)}件の却下済み投稿があります。")
                for post in rejected_posts:
                    with st.container():
                        st.caption(f"作成: {post['created_at']} | テーマ: {post['theme']}")
                        st.write(post['content'])
                        st.markdown("---")
            else:
                st.info("却下済みの投稿はありません。")
        
        with tab5:
            st.subheader("📅 スケジュール投稿管理")
            
            # 新規スケジュール投稿の作成
            with st.expander("新しいスケジュール投稿を作成", expanded=False):
                with st.form("schedule_post_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        schedule_date = st.date_input("投稿日", min_value=datetime.date.today())
                    with col2:
                        schedule_time = st.time_input("投稿時刻", value=datetime.time(9, 0))
                    
                    schedule_content = st.text_area("投稿内容", height=100, placeholder="スケジュール投稿の内容を入力してください...")
                    
                    if st.form_submit_button("スケジュール投稿を作成", type="primary"):
                        if schedule_content.strip():
                            schedule_datetime = datetime.datetime.combine(schedule_date, schedule_time)
                            schedule_datetime = JST.localize(schedule_datetime)
                            
                            # データベースに保存（postsテーブルを拡張して使用）
                            execute_query("INSERT INTO posts (cast_id, created_at, content, theme, status) VALUES (?, ?, ?, ?, ?)", 
                                        (selected_cast_id, schedule_datetime.strftime('%Y-%m-%d %H:%M:%S'), schedule_content, "スケジュール投稿", "scheduled"))
                            st.success(f"スケジュール投稿を作成しました。予定日時: {schedule_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("投稿内容を入力してください。")
            
            # 既存のスケジュール投稿表示
            st.subheader("スケジュール投稿一覧")
            scheduled_posts = execute_query("SELECT * FROM posts WHERE cast_id = ? AND status = 'scheduled' ORDER BY created_at ASC", (selected_cast_id,), fetch="all")
            if scheduled_posts:
                for post in scheduled_posts:
                    with st.container():
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.caption(f"予定日時: {post['created_at']}")
                            st.write(post['content'])
                        with col2:
                            if st.button("削除", key=f"delete_schedule_{post['id']}", use_container_width=True):
                                execute_query("DELETE FROM posts WHERE id = ?", (post['id'],))
                                st.success("スケジュール投稿を削除しました。")
                                time.sleep(1)
                                st.rerun()
                        st.markdown("---")
            else:
                st.info("スケジュール投稿はありません。")
        
        with tab6:
            st.subheader("🔄 リツイート予約管理")
            
            # 新規リツイート予約の作成
            with st.expander("新しいリツイート予約を作成", expanded=False):
                with st.form("retweet_reservation_form"):
                    target_url = st.text_input("リツイート対象URL", placeholder="https://twitter.com/username/status/1234567890")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        retweet_date = st.date_input("実行日", min_value=datetime.date.today())
                    with col2:
                        retweet_time = st.time_input("実行時刻", value=datetime.time(12, 0))
                    
                    quote_comment = st.text_area("引用コメント（オプション）", height=80, placeholder="引用リツイートする場合のコメントを入力...")
                    
                    if st.form_submit_button("リツイート予約を作成", type="primary"):
                        if target_url.strip():
                            retweet_datetime = datetime.datetime.combine(retweet_date, retweet_time)
                            retweet_datetime = JST.localize(retweet_datetime)
                            
                            # リツイート予約をデータベースに保存
                            execute_query("""INSERT INTO retweet_schedules (cast_id, target_url, scheduled_at, comment) 
                                           VALUES (?, ?, ?, ?)""", 
                                        (selected_cast_id, target_url, retweet_datetime.strftime('%Y-%m-%d %H:%M:%S'), quote_comment or None))
                            st.success(f"リツイート予約を作成しました。実行予定: {retweet_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("リツイート対象URLを入力してください。")
            
            # 既存のリツイート予約表示
            st.subheader("リツイート予約一覧")
            retweet_schedules = execute_query("SELECT * FROM retweet_schedules WHERE cast_id = ? ORDER BY scheduled_at ASC", (selected_cast_id,), fetch="all")
            if retweet_schedules:
                for schedule in retweet_schedules:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 2, 1])
                        with col1:
                            try:
                                st.caption(f"実行予定: {schedule['scheduled_at']}")
                                st.write(f"対象URL: {schedule['target_url']}")
                                if 'comment' in schedule.keys() and schedule['comment']:
                                    st.write(f"コメント: {schedule['comment']}")
                            except (KeyError, IndexError) as e:
                                st.error(f"データエラー: {e}")
                        with col2:
                            try:
                                status_color = {"pending": "🟡", "completed": "🟢", "failed": "🔴"}.get(schedule['status'], "⚪")
                                st.write(f"状態: {status_color} {schedule['status']}")
                            except (KeyError, IndexError):
                                st.write("状態: ⚪ 不明")
                        with col3:
                            try:
                                if schedule['status'] == 'pending':
                                    if st.button("削除", key=f"delete_retweet_{schedule['id']}", use_container_width=True):
                                        execute_query("DELETE FROM retweet_schedules WHERE id = ?", (schedule['id'],))
                                        st.success("リツイート予約を削除しました。")
                                        time.sleep(1)
                                        st.rerun()
                            except (KeyError, IndexError):
                                pass
                        st.markdown("---")
            else:
                st.info("リツイート予約はありません。")
    
    elif selected_page == "キャスト管理":
        st.title("🎭 キャスト管理")
        
        # 一括投稿生成機能
        st.subheader("複数キャストの一括投稿生成")
        casts = execute_query("SELECT * FROM casts ORDER BY name", fetch="all")
        if casts:
            cast_options = [f"{cast['name']}（{cast['nickname']}）" if cast['nickname'] else cast['name'] for cast in casts]
            selected_casts = st.multiselect("投稿を生成するキャストを選択", cast_options)
            
            with st.form("bulk_generate_form"):
                col1, col2 = st.columns(2)
                with col1:
                    bulk_num_posts = st.number_input("各キャストの投稿数", min_value=1, max_value=5, value=1)
                with col2:
                    bulk_char_limit = st.number_input("文字数制限", min_value=50, max_value=500, value=140)
                
                if st.form_submit_button("選択したキャスト全員に投稿を生成させる", type="primary"):
                    if selected_casts and st.session_state.gemini_model:
                        total_casts = len(selected_casts)
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for i, cast_display in enumerate(selected_casts):
                            cast_name = cast_display.split('（')[0]
                            cast_id = next(cast['id'] for cast in casts if cast['name'] == cast_name)
                            cast_details = next(cast for cast in casts if cast['name'] == cast_name)
                            
                            progress_bar.progress((i + 1) / total_casts, text=f"キャスト「{cast_name}」の投稿を生成中... ({i+1}/{total_casts})")
                            
                            # シチュエーション取得
                            cast_categories = cast_details['allowed_categories']
                            if cast_categories:
                                category_ids = [int(cat_id.strip()) for cat_id in cast_categories.split(',') if cat_id.strip().isdigit()]
                                if category_ids:
                                    placeholders = ','.join(['?'] * len(category_ids))
                                    situations_rows = execute_query(f"SELECT * FROM situations WHERE category_id IN ({placeholders})", category_ids, fetch="all")
                                else:
                                    situations_rows = execute_query("SELECT * FROM situations", fetch="all")
                            else:
                                situations_rows = execute_query("SELECT * FROM situations", fetch="all")
                            
                            if situations_rows:
                                persona_sheet = format_persona(cast_id, cast_details)
                                for j in range(bulk_num_posts):
                                    try:
                                        selected_situation = random.choice(situations_rows)
                                        prompt_template = f"""# ペルソナ\n{persona_sheet}\n\n# シチュエーション\n{selected_situation['content']}\n\n# ルール\nSNS投稿を**{bulk_char_limit}文字以内**で生成。"""
                                        response = st.session_state.gemini_model.generate_content(prompt_template)
                                        generated_text = response.text
                                        
                                        created_at = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                                        execute_query("INSERT INTO posts (cast_id, created_at, content, theme) VALUES (?, ?, ?, ?)", 
                                                    (cast_id, created_at, generated_text, selected_situation['content']))
                                        time.sleep(1)
                                    except Exception as e:
                                        st.error(f"キャスト{cast_name}の投稿生成中にエラー: {e}")
                                        continue
                        
                        progress_bar.progress(1.0, text="一括投稿生成完了！")
                        st.success(f"{len(selected_casts)}人のキャストに対して投稿を生成しました！")
                        time.sleep(2)
                        st.rerun()
                    elif not selected_casts:
                        st.error("キャストを選択してください。")
                    else:
                        st.error("AIモデルの読み込みに失敗しているため、投稿を生成できません。")
        
        st.markdown("---")
        
        # キャスト管理セクション
        st.subheader("キャスト一覧・編集")
        
        casts = execute_query("SELECT * FROM casts ORDER BY name", fetch="all")
        if casts:
            for cast in casts:
                with st.expander(f"👤 {cast['name']}（{cast['nickname']}）" if cast['nickname'] else f"👤 {cast['name']}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        # 基本情報表示
                        st.write(f"**名前:** {cast['name']}")
                        if cast['nickname']:
                            st.write(f"**愛称:** {cast['nickname']}")
                        if cast['age']:
                            st.write(f"**年齢:** {cast['age']}")
                        if cast['personality']:
                            st.write(f"**性格:** {cast['personality']}")
                        if cast['speech_style']:
                            st.write(f"**話し方:** {cast['speech_style']}")
                        
                        # X API設定情報
                        x_creds = execute_query("SELECT * FROM cast_x_credentials WHERE cast_id = ?", (cast['id'],), fetch="one")
                        if x_creds:
                            st.success("✅ X API設定済み")
                        else:
                            st.info("📋 X API未設定")
                    
                    with col2:
                        if st.button("編集", key=f"edit_cast_{cast['id']}", use_container_width=True):
                            st.session_state[f'editing_cast_{cast["id"]}'] = True
                        
                        if st.button("削除", key=f"delete_cast_{cast['id']}", use_container_width=True):
                            execute_query("DELETE FROM casts WHERE id = ?", (cast['id'],))
                            st.success(f"キャスト「{cast['name']}」を削除しました。")
                            time.sleep(1)
                            st.rerun()
                    
                    # 編集フォーム
                    if st.session_state.get(f'editing_cast_{cast["id"]}'):
                        st.markdown("### 編集フォーム")
                        with st.form(f"edit_cast_form_{cast['id']}"):
                            # 基本情報
                            new_name = st.text_input("名前", value=cast['name'])
                            new_nickname = st.text_input("愛称", value=cast['nickname'] or "")
                            new_age = st.text_input("年齢", value=cast['age'] or "")
                            new_personality = st.text_area("性格", value=cast['personality'] or "")
                            new_speech_style = st.text_area("話し方", value=cast['speech_style'] or "")
                            
                            # X API設定
                            st.markdown("#### X API設定")
                            x_creds = execute_query("SELECT * FROM cast_x_credentials WHERE cast_id = ?", (cast['id'],), fetch="one")
                            
                            api_key = st.text_input("API Key", value=x_creds['api_key'] if x_creds else "", type="password")
                            api_secret = st.text_input("API Secret", value=x_creds['api_secret'] if x_creds else "", type="password")
                            bearer_token = st.text_input("Bearer Token", value=x_creds['bearer_token'] if x_creds else "", type="password")
                            access_token = st.text_input("Access Token", value=x_creds['access_token'] if x_creds else "", type="password")
                            access_token_secret = st.text_input("Access Token Secret", value=x_creds['access_token_secret'] if x_creds else "", type="password")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("更新", type="primary"):
                                    # キャスト情報更新
                                    execute_query("UPDATE casts SET name = ?, nickname = ?, age = ?, personality = ?, speech_style = ? WHERE id = ?", 
                                                (new_name, new_nickname, new_age, new_personality, new_speech_style, cast['id']))
                                    
                                    # X API認証情報更新
                                    if any([api_key, api_secret, bearer_token, access_token, access_token_secret]):
                                        if x_creds:
                                            execute_query("""UPDATE cast_x_credentials 
                                                           SET api_key = ?, api_secret = ?, bearer_token = ?, access_token = ?, access_token_secret = ?, updated_at = CURRENT_TIMESTAMP 
                                                           WHERE cast_id = ?""",
                                                         (api_key, api_secret, bearer_token, access_token, access_token_secret, cast['id']))
                                        else:
                                            execute_query("""INSERT INTO cast_x_credentials (cast_id, api_key, api_secret, bearer_token, access_token, access_token_secret) 
                                                           VALUES (?, ?, ?, ?, ?, ?)""",
                                                         (cast['id'], api_key, api_secret, bearer_token, access_token, access_token_secret))
                                    
                                    st.success("キャスト情報を更新しました！")
                                    st.session_state[f'editing_cast_{cast["id"]}'] = False
                                    time.sleep(1)
                                    st.rerun()
                            
                            with col2:
                                if st.form_submit_button("キャンセル"):
                                    st.session_state[f'editing_cast_{cast["id"]}'] = False
                                    st.rerun()
        else:
            st.info("登録されているキャストがありません。")
        
        st.markdown("---")
        
        # 新キャスト登録
        st.subheader("新しいキャストを登録")
        with st.form("new_cast_form"):
            # 基本情報
            cast_name = st.text_input("名前（必須）")
            cast_nickname = st.text_input("愛称")
            cast_age = st.text_input("年齢")
            cast_personality = st.text_area("性格")
            cast_speech_style = st.text_area("話し方")
            
            # X API設定
            st.markdown("#### X API設定（オプション）")
            new_api_key = st.text_input("API Key", type="password")
            new_api_secret = st.text_input("API Secret", type="password")
            new_bearer_token = st.text_input("Bearer Token", type="password")
            new_access_token = st.text_input("Access Token", type="password")
            new_access_token_secret = st.text_input("Access Token Secret", type="password")
            
            # カテゴリ選択
            categories = execute_query("SELECT * FROM situation_categories ORDER BY name", fetch="all")
            if categories:
                st.info("このキャストが投稿を生成する際に使用できるシチュエーションのカテゴリを選択してください。")
                selected_categories = st.multiselect(
                    "利用可能カテゴリ",
                    options=[cat['id'] for cat in categories],
                    format_func=lambda x: next(cat['name'] for cat in categories if cat['id'] == x)
                )
            
            if st.form_submit_button("キャストを登録", type="primary"):
                if cast_name.strip():
                    # カテゴリIDを文字列として保存
                    allowed_categories = ','.join(map(str, selected_categories)) if categories and selected_categories else None
                    
                    cast_id = execute_query("INSERT INTO casts (name, nickname, age, personality, speech_style, allowed_categories) VALUES (?, ?, ?, ?, ?, ?)", 
                                          (cast_name, cast_nickname, cast_age, cast_personality, cast_speech_style, allowed_categories))
                    
                    if cast_id:
                        # X API認証情報が提供されている場合は保存
                        if any([new_api_key, new_api_secret, new_bearer_token, new_access_token, new_access_token_secret]):
                            execute_query("""INSERT INTO cast_x_credentials (cast_id, api_key, api_secret, bearer_token, access_token, access_token_secret) 
                                           VALUES (?, ?, ?, ?, ?, ?)""",
                                         (cast_id, new_api_key, new_api_secret, new_bearer_token, new_access_token, new_access_token_secret))
                        
                        st.success(f"キャスト「{cast_name}」を登録しました！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("キャスト登録に失敗しました。")
                else:
                    st.error("名前は必須です。")
    
    elif selected_page == "シチュエーション管理":
        st.title("🎬 シチュエーション管理")
        
        # カテゴリ管理
        st.subheader("カテゴリ管理")
        categories = execute_query("SELECT * FROM situation_categories ORDER BY name", fetch="all")
        
        if categories:
            for category in categories:
                with st.expander(f"📁 {category['name']}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**説明:** {category['description'] or '説明なし'}")
                    with col2:
                        if st.button("削除", key=f"delete_cat_{category['id']}", use_container_width=True):
                            execute_query("DELETE FROM situation_categories WHERE id = ?", (category['id'],))
                            st.success(f"カテゴリ「{category['name']}」を削除しました。")
                            time.sleep(1)
                            st.rerun()
        else:
            st.info("カテゴリが登録されていません。")
        
        # 新カテゴリ登録
        with st.form("new_category_form"):
            st.markdown("### 新しいカテゴリを追加")
            new_cat_name = st.text_input("カテゴリ名")
            new_cat_desc = st.text_area("説明")
            
            if st.form_submit_button("カテゴリを追加", type="primary"):
                if new_cat_name.strip():
                    execute_query("INSERT INTO situation_categories (name, description) VALUES (?, ?)", (new_cat_name, new_cat_desc))
                    st.success(f"カテゴリ「{new_cat_name}」を追加しました！")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("カテゴリ名は必須です。")
        
        st.markdown("---")
        
        # シチュエーション管理
        st.subheader("シチュエーション管理")
        situations = execute_query("""SELECT s.*, c.name as category_name 
                                    FROM situations s 
                                    LEFT JOIN situation_categories c ON s.category_id = c.id 
                                    ORDER BY c.name, s.content""", fetch="all")
        
        if situations:
            for situation in situations:
                with st.expander(f"🎭 {situation['content'][:50]}...", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**シチュエーション:** {situation['content']}")
                        st.write(f"**カテゴリ:** {situation['category_name'] or '未分類'}")
                        st.write(f"**時間帯:** {situation['time_slot']}")
                    with col2:
                        if st.button("削除", key=f"delete_sit_{situation['id']}", use_container_width=True):
                            execute_query("DELETE FROM situations WHERE id = ?", (situation['id'],))
                            st.success("シチュエーションを削除しました。")
                            time.sleep(1)
                            st.rerun()
        else:
            st.info("シチュエーションが登録されていません。")
        
        # 新シチュエーション登録
        with st.form("new_situation_form"):
            st.markdown("### 新しいシチュエーションを追加")
            new_content = st.text_area("シチュエーション内容")
            
            col1, col2 = st.columns(2)
            with col1:
                time_slot = st.selectbox("時間帯", ["朝", "昼", "夜", "いつでも"])
            with col2:
                categories = execute_query("SELECT * FROM situation_categories ORDER BY name", fetch="all")
                if categories:
                    category_options = {cat['id']: cat['name'] for cat in categories}
                    selected_category = st.selectbox("カテゴリ", options=list(category_options.keys()), format_func=lambda x: category_options[x])
                else:
                    st.warning("カテゴリを先に作成してください。")
                    selected_category = None
            
            if st.form_submit_button("シチュエーションを追加", type="primary"):
                if new_content.strip() and selected_category:
                    execute_query("INSERT INTO situations (content, time_slot, category_id) VALUES (?, ?, ?)", 
                                (new_content, time_slot, selected_category))
                    st.success("シチュエーションを追加しました！")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("シチュエーション内容とカテゴリは必須です。")
    
    elif selected_page == "システム設定":
        st.title("⚙️ システム設定")
        
        tab1, tab2, tab3 = st.tabs(["🔐 Google Cloud認証", "📊 システム状況", "🔧 データベース管理"])
        
        with tab1:
            st.subheader("Google Cloud認証設定")
            
            # 認証状況チェック
            auth_ok, creds_or_error, project_or_error = check_google_auth()
            
            if auth_ok:
                st.success("✅ Google Cloud認証成功")
                st.info(f"プロジェクトID: {project_or_error}")
                
                # Vertex AI接続テスト
                if st.button("Vertex AI接続テスト", type="secondary"):
                    with st.spinner("Vertex AI接続をテストしています..."):
                        vertex_ok, vertex_msg = load_vertex_ai()
                        if vertex_ok:
                            st.success("✅ Vertex AI接続成功")
                        else:
                            st.error(f"❌ Vertex AI接続失敗: {vertex_msg}")
            else:
                st.error("❌ Google Cloud認証失敗")
                st.error(f"エラー詳細: {project_or_error}")
                
                st.markdown("""
                ### 認証設定手順
                1. ターミナルで以下のコマンドを実行:
                ```bash
                gcloud auth application-default login --no-launch-browser
                ```
                2. 表示されたURLをブラウザで開く
                3. 認証コードをターミナルに貼り付け
                4. このページを再読み込み
                """)
        
        with tab2:
            st.subheader("システム状況")
            
            # データベース統計
            cast_count = execute_query("SELECT COUNT(*) as count FROM casts", fetch="one")['count']
            post_count = execute_query("SELECT COUNT(*) as count FROM posts", fetch="one")['count']
            situation_count = execute_query("SELECT COUNT(*) as count FROM situations", fetch="one")['count']
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("登録キャスト数", cast_count)
            with col2:
                st.metric("投稿総数", post_count)
            with col3:
                st.metric("シチュエーション数", situation_count)
            
            # MCF機能統計
            st.markdown("### MCF機能統計")
            x_creds_count = execute_query("SELECT COUNT(*) as count FROM cast_x_credentials", fetch="one")['count']
            retweet_count = execute_query("SELECT COUNT(*) as count FROM retweet_schedules", fetch="one")['count']
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("X API設定済みキャスト", x_creds_count)
            with col2:
                st.metric("リツイート予約数", retweet_count)
        
        with tab3:
            st.subheader("データベース管理")
            
            if st.button("データベース初期化", type="secondary"):
                init_db()
                st.success("データベースを初期化しました。")

if __name__ == "__main__":
    main()