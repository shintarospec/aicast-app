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
    categories_table_query = "CREATE TABLE IF NOT EXISTS situation_categories (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)"
    advice_table_query = 'CREATE TABLE IF NOT EXISTS advice_master (id INTEGER PRIMARY KEY, content TEXT NOT NULL UNIQUE)'
    groups_table_query = "CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, content TEXT NOT NULL)"
    cast_groups_table_query = "CREATE TABLE IF NOT EXISTS cast_groups (cast_id INTEGER, group_id INTEGER, PRIMARY KEY (cast_id, group_id), FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE, FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE)"
    tuning_history_table_query = "CREATE TABLE IF NOT EXISTS tuning_history (id INTEGER PRIMARY KEY, post_id INTEGER, timestamp TEXT, previous_content TEXT, advice_used TEXT, FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE)"
    custom_fields_table_query = "CREATE TABLE IF NOT EXISTS custom_fields (id INTEGER PRIMARY KEY, field_name TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL, field_type TEXT DEFAULT 'text', placeholder TEXT DEFAULT '', is_required INTEGER DEFAULT 0, sort_order INTEGER DEFAULT 0)"
    send_history_table_query = "CREATE TABLE IF NOT EXISTS send_history (id INTEGER PRIMARY KEY, post_id INTEGER, destination TEXT, sent_at TEXT, scheduled_datetime TEXT, status TEXT DEFAULT 'pending', error_message TEXT, FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE)"
    app_settings_table_query = "CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, description TEXT DEFAULT '', category TEXT DEFAULT 'general')"

    queries = [casts_table_query, posts_table_query, situations_table_query, categories_table_query, advice_table_query, groups_table_query, cast_groups_table_query, tuning_history_table_query, custom_fields_table_query, send_history_table_query, app_settings_table_query]
    for query in queries: execute_query(query)
    
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
        ]
        for setting in default_settings:
            execute_query("INSERT INTO app_settings (key, value, description, category) VALUES (?, ?, ?, ?)", setting)
    
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

def setup_google_sheets_oauth():
    """Google Sheets OAuth認証の初期設定"""
    try:
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        import pickle
        
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        
        creds = None
        token_path = "credentials/token.pickle"
        credentials_path = "credentials/credentials.json"
        
        # 既存のトークンを確認
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # 認証が必要な場合
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_path):
                    return None, "OAuth認証ファイルが見つかりません。設定が必要です。"
                
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # トークンを保存
            os.makedirs("credentials", exist_ok=True)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds, "認証成功"
    except Exception as e:
        return None, f"OAuth認証エラー: {str(e)}"

def send_to_google_sheets(cast_name, post_content, scheduled_datetime):
    """Google Sheetsにデータを送信する（キャスト名付き）"""
    try:
        os.makedirs("credentials", exist_ok=True)
        credentials_path = "credentials/credentials.json"
        
        # OAuth認証ファイルの確認
        if not os.path.exists(credentials_path):
            setup_message = """Google Sheets連携の設定が必要です。

【OAuth認証設定手順】
1. [Google Cloud Console](https://console.cloud.google.com) にアクセス
2. 新しいプロジェクトを作成または既存プロジェクト選択
3. 「APIとサービス」> 「ライブラリ」で以下を有効化：
   - Google Sheets API
   - Google Drive API
4. 「APIとサービス」> 「認証情報」> 「認証情報を作成」> 「OAuthクライアントID」
5. アプリケーションの種類：「デスクトップアプリケーション」
6. 作成されたクライアントIDの右側の「ダウンロード」ボタンをクリック
7. ダウンロードしたJSONファイルを `credentials/credentials.json` として保存
8. アプリを再起動して送信を試行（ブラウザでの認証が開始されます）

設定完了後、再度送信をお試しください。"""
            return False, setup_message
        
        # OAuth認証を実行
        creds, auth_message = setup_google_sheets_oauth()
        if not creds:
            return False, auth_message
        
        client = gspread.authorize(creds)
        
        # スプレッドシートを開く（存在しない場合は作成）
        try:
            sheet = client.open("aicast_post").sheet1
        except gspread.SpreadsheetNotFound:
            # スプレッドシートが存在しない場合は作成
            spreadsheet = client.create("aicast_post")
            sheet = spreadsheet.sheet1
            # ヘッダー行を追加
            sheet.append_row(["datetime", "content", "name"])
        
        # データを追加（日時, 投稿内容, name の順）
        formatted_datetime = scheduled_datetime.strftime('%Y-%m-%d %H:%M:%S')
        sheet.append_row([formatted_datetime, post_content, cast_name])
        
        return True, "Google Sheetsに送信しました。"
        
    except Exception as e:
        return False, f"Google Sheets送信エラー: {str(e)}"

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

    try:
        if 'auth_done' not in st.session_state:
            vertexai.init(project=project_id, location=location)
            st.session_state.auth_done = True
        st.sidebar.success("✅ Googleサービス認証完了")
    except Exception as e:
        st.sidebar.error(f"認証に失敗しました: {e}"); st.stop()

    if 'gemini_model' not in st.session_state:
        try:
            model_name = "gemini-1.5-pro"
            st.session_state.gemini_model = GenerativeModel(model_name)
        except Exception as e:
            st.error(f"Geminiモデルのロードに失敗しました: {e}"); st.session_state.gemini_model = None

    st.sidebar.title("AIcast room")
    page = st.sidebar.radio("メニュー", ["投稿管理", "一斉指示", "キャスト管理", "シチュエーション管理", "カテゴリ管理", "グループ管理", "アドバイス管理", "システム設定"])
    if page == "投稿管理":
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
                del st.session_state.edit_status_message
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
                            response = st.session_state.gemini_model.generate_content(regeneration_prompt)
                            # 履歴に保存：前の投稿内容とアドバイス、そして新しい投稿内容
                            execute_query("INSERT INTO tuning_history (post_id, timestamp, previous_content, advice_used) VALUES (?, ?, ?, ?)", 
                                      (post_id, history_ts, f"<span style='color: #888888'>前回の投稿:</span>\n<span style='color: #888888'>{post['content']}</span>\n\n**新しい投稿:**\n{response.text}", final_advice_str))
                            execute_query("UPDATE posts SET content = ?, evaluation = '未評価', advice = '', free_advice = '' WHERE id = ?", (response.text, post_id))
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
                num_posts = col1.number_input("生成する数", min_value=1, max_value=50, value=default_post_count, key="post_num")
                default_char_limit = int(get_app_setting("default_char_limit", "140"))
                char_limit = col2.number_input("文字数（以内）", min_value=20, max_value=300, value=default_char_limit, key="char_limit")

                if st.button("生成開始", type="primary"):
                    if st.session_state.get('gemini_model'):
                        if not situations_rows:
                            st.error("キャストに許可されたカテゴリに属するシチュエーションがありません。"); st.stop()
                        with top_status_placeholder:
                            with st.spinner("投稿を生成中です..."):
                                persona_sheet = format_persona(selected_cast_id, selected_cast_details)
                                for i in range(num_posts):
                                    selected_situation = random.choice(situations_rows)
                                    prompt_template = f"""# ペルソナ\n{persona_sheet}\n\n# シチュエーション\n{selected_situation['content']}\n\n# ルール\nSNS投稿を**{char_limit}文字以内**で生成。"""
                                    try:
                                        response = st.session_state.gemini_model.generate_content(prompt_template)
                                        generated_text = response.text
                                    except Exception as e:
                                        st.error(f"AIからの応答生成中にエラーが発生しました: {e}"); continue
                                    time_slot_map = {"朝": (7, 11), "昼": (12, 17), "夜": (18, 23)}
                                    hour_range = time_slot_map.get(selected_situation['time_slot'], (0, 23))
                                    random_hour = random.randint(hour_range[0], hour_range[1]); random_minute = random.randint(0, 59)
                                    created_at = datetime.datetime.now(JST).replace(hour=random_hour, minute=random_minute, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
                                    execute_query("INSERT INTO posts (cast_id, created_at, content, theme) VALUES (?, ?, ?, ?)", (selected_cast_id, created_at, generated_text, selected_situation['content']))
                                    time.sleep(5)
                        top_status_placeholder.success(f"{num_posts}件の投稿案をデータベースに保存しました！")
                        st.balloons(); time.sleep(2); top_status_placeholder.empty(); st.rerun()
                    else: 
                        top_status_placeholder.error("AIモデルの読み込みに失敗しているため、投稿を生成できません。")

            st.markdown("---")
            # 選択されたキャストの表示名を作成
            current_cast = next((c for c in casts if c['name'] == selected_cast_name), None)
            cast_display_name = f"{current_cast['name']}（{current_cast['nickname']}）" if current_cast and current_cast['nickname'] else selected_cast_name
            st.header(f"「{cast_display_name}」の投稿一覧")
            tab1, tab2, tab3, tab4 = st.tabs(["投稿案 (Drafts)", "承認済み (Approved)", "送信済み (Sent)", "却下済み (Rejected)"])

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
                else: st.info("チューニング対象の投稿案はありません。")

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
                    for post in approved_posts:
                        with st.container():
                            col_content, col_datetime, col_action = st.columns([3,1,1])
                            with col_content:
                                full_advice_list = []; 
                                if post['advice']: full_advice_list.extend(post['advice'].split(','))
                                if post['free_advice']: full_advice_list.append(post['free_advice'])
                                full_advice_str = ", ".join(full_advice_list)
                                st.caption(f"投稿時間: {post['posted_at']} | 評価: {post['evaluation']} | アドバイス: {full_advice_str}")
                                st.success(post['content'], icon="✔")
                            
                            with col_datetime:
                                # 投稿の元の時刻を取得
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
                                    # カスタム送信日（時刻は元の投稿時刻を使用）
                                    send_date = st.date_input("送信日", key=f"date_{post['id']}", min_value=datetime.date.today())
                                    # 元の投稿時刻を使用
                                    original_time = original_datetime.time()
                                    scheduled_datetime = datetime.datetime.combine(send_date, original_time)
                                    st.info(f"📅 {send_date.strftime('%Y-%m-%d')} {original_time.strftime('%H:%M')} で送信")
                            
                            with col_action:
                                if st.button("📊 Sheets送信", key=f"send_sheets_{post['id']}", type="primary", use_container_width=True):
                                    
                                    # Google Sheetsに送信（キャスト名付き）
                                    # 現在選択中のキャスト名を取得
                                    current_cast = next((c for c in casts if c['name'] == selected_cast_name), None)
                                    display_cast_name = f"{current_cast['name']}（{current_cast['nickname']}）" if current_cast and current_cast['nickname'] else selected_cast_name
                                    success, message = send_to_google_sheets(display_cast_name, post['content'], scheduled_datetime)
                                    
                                    if success:
                                        # 送信成功時のデータベース更新
                                        sent_at = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                                        execute_query("UPDATE posts SET sent_status = 'sent', sent_at = ? WHERE id = ?", (sent_at, post['id']))
                                        execute_query("INSERT INTO send_history (post_id, destination, sent_at, scheduled_datetime, status) VALUES (?, ?, ?, ?, ?)", 
                                                    (post['id'], 'google_sheets', sent_at, scheduled_datetime.strftime('%Y-%m-%d %H:%M:%S'), 'completed'))
                                        st.session_state.page_status_message = ("success", f"Google Sheetsに送信しました！")
                                    else:
                                        # 送信失敗時のログ記録
                                        failed_at = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                                        execute_query("INSERT INTO send_history (post_id, destination, sent_at, scheduled_datetime, status, error_message) VALUES (?, ?, ?, ?, ?, ?)", 
                                                    (post['id'], 'google_sheets', failed_at, scheduled_datetime.strftime('%Y-%m-%d %H:%M:%S'), 'failed', message))
                                        st.session_state.page_status_message = ("error", message)
                                    st.rerun()
                                
                                if st.button("↩️ 投稿案に戻す", key=f"revert_{post['id']}", use_container_width=True):
                                    execute_query("UPDATE posts SET status = 'draft', posted_at = NULL WHERE id = ?", (post['id'],))
                                    st.session_state.page_status_message = ("success", "投稿を「投稿案」に戻しました。"); st.rerun()
                            
                            st.markdown("---")
                else: st.info("承認済みの投稿はまだありません。")

            with tab3:
                # 送信済みタブ
                sent_posts = execute_query("SELECT p.*, sh.destination, sh.sent_at as send_timestamp, sh.scheduled_datetime FROM posts p LEFT JOIN send_history sh ON p.id = sh.post_id WHERE p.cast_id = ? AND p.sent_status = 'sent' ORDER BY sh.sent_at DESC", (selected_cast_id,), fetch="all")
                if sent_posts:
                    st.info(f"{len(sent_posts)}件の送信済み投稿があります。")
                    for post in sent_posts:
                        with st.container():
                            col_content, col_info = st.columns([3,1])
                            with col_content:
                                st.caption(f"送信先: {post['destination']} | 送信日時: {post['send_timestamp']} | 予定日時: {post['scheduled_datetime']}")
                                st.info(post['content'], icon="📤")
                            with col_info:
                                st.write(f"**評価**: {post['evaluation']}")
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
                        st.caption(f"作成日時: {post['created_at']} | 評価: {post['evaluation']} | アドバイス: {full_advice_str}")
                        st.error(post['content'], icon="✖")
                else: st.info("却下済みの投稿はまだありません。")

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
                                response = st.session_state.gemini_model.generate_content(prompt)
                                generated_text = response.text
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
                        new_name = c1.text_input("ユーザー名*", placeholder="@shiori_hoshino"); new_nickname = c2.text_input("名前（表示名）", placeholder="星野 詩織")
                        new_age = c1.text_input("年齢", placeholder="21歳"); new_birthday = c2.text_input("誕生日", placeholder="10月26日")
                        new_birthplace = c1.text_input("出身地", placeholder="神奈川県"); new_appearance = st.text_area("外見の特徴", placeholder="黒髪ロングで物静かな雰囲気...")
                    with form_tabs[1]:
                        c1, c2, c3 = st.columns(3)
                        new_personality = c1.text_input("性格（一言で）", placeholder="物静かで穏やかな聞き上手"); new_strength = c2.text_input("長所", placeholder="人の話に深く共感できる")
                        new_weakness = c3.text_input("短所", placeholder="少し人見知り"); new_first_person = c1.text_input("一人称", placeholder="私")
                        new_speech_style = c2.text_area("口調・語尾", placeholder="です・ます調の丁寧な言葉遣い"); new_catchphrase = c3.text_input("口癖", placeholder="「なんだか、素敵ですね」")
                        new_customer_interaction = st.text_area("お客様への接し方", placeholder="お客様の心に寄り添うように...")
                    with form_tabs[2]:
                        c1, c2 = st.columns(2)
                        new_occupation = c1.text_input("職業／学業", placeholder="文学部の女子大生"); new_hobby = c2.text_area("趣味や特技", placeholder="読書、フィルムカメラ...")
                        new_likes = c1.text_area("好きなもの", placeholder="雨の日の匂い、万年筆のインク"); new_dislikes = c2.text_area("嫌いなもの", placeholder="大きな音、人混み")
                        new_holiday_activity = st.text_area("休日の過ごし方", placeholder="一日中家で本を読んでいるか..."); new_dream = st.text_area("将来の夢", placeholder="自分の言葉で物語を紡ぐこと")
                        new_reason_for_job = st.text_area("なぜこの仕事をしているのか", placeholder="様々な人の物語に触れたいから"); new_secret = st.text_area("ちょっとした秘密", placeholder="実は、大のSF小説好き")
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
                                edit_name = c1.text_input("ユーザー名*", value=cast_data_to_edit.get('name', ''))
                                edit_nickname = c2.text_input("名前（表示名）", value=cast_data_to_edit.get('nickname', '')); edit_age = c1.text_input("年齢", value=cast_data_to_edit.get('age', ''))
                                edit_appearance = st.text_area("外見の特徴", value=cast_data_to_edit.get('appearance', '')); edit_birthday = c1.text_input("誕生日", value=cast_data_to_edit.get('birthday', ''))
                                edit_birthplace = c2.text_input("出身地", value=cast_data_to_edit.get('birthplace', ''))
                            with t2:
                                c1, c2, c3 = st.columns(3)
                                edit_personality = c1.text_input("性格（一言で）", value=cast_data_to_edit.get('personality', '')); edit_strength = c2.text_input("長所", value=cast_data_to_edit.get('strength', ''))
                                edit_weakness = c3.text_input("短所", value=cast_data_to_edit.get('weakness', '')); edit_first_person = c1.text_input("一人称", value=cast_data_to_edit.get('first_person', ''))
                                edit_speech_style = c2.text_area("口調・語尾", value=cast_data_to_edit.get('speech_style', '')); edit_catchphrase = c3.text_input("口癖", value=cast_data_to_edit.get('catchphrase', ''))
                                edit_customer_interaction = st.text_area("お客様への接し方", value=cast_data_to_edit.get('customer_interaction', ''))
                            with t3:
                                c1, c2 = st.columns(2)
                                edit_occupation = c1.text_input("職業／学業", value=cast_data_to_edit.get('occupation', '')); edit_hobby = c2.text_area("趣味や特技", value=cast_data_to_edit.get('hobby', ''))
                                edit_likes = c1.text_area("好きなもの", value=cast_data_to_edit.get('likes', '')); edit_dislikes = c2.text_area("嫌いなもの", value=cast_data_to_edit.get('dislikes', ''))
                                edit_holiday_activity = st.text_area("休日の過ごし方", value=cast_data_to_edit.get('holiday_activity', '')); edit_dream = st.text_area("将来の夢", value=cast_data_to_edit.get('dream', ''))
                                edit_reason_for_job = st.text_area("なぜこの仕事をしているのか", value=cast_data_to_edit.get('reason_for_job', '')); edit_secret = st.text_area("ちょっとした秘密", value=cast_data_to_edit.get('secret', ''))
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
                        
                        with st.expander(" Danger Zone: キャストの削除", expanded=False):
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
                                    response = st.session_state.gemini_model.generate_content(prompt)
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
    
    elif page == "システム設定":
        st.title("⚙️ システム設定")
        st.markdown("アプリケーションの各種設定を管理します。")
        
        st.subheader("🗃️ Google Sheets 連携設定")
        st.markdown("Google Sheets APIを使用して投稿を送信するための認証設定を行います。")
        
        with st.expander("OAuth認証情報の設定", expanded=True):
            st.markdown("""
            **設定手順:**
            1. [Google Cloud Console](https://console.cloud.google.com/)でOAuth 2.0クライアントIDを作成
            2. クライアントタイプは「デスクトップアプリケーション」を選択
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

