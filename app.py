import streamlit as st
import pandas as pd
import datetime
import time
import random
import sqlite3
import vertexai
from vertexai.preview.generative_models import GenerativeModel
import os

# --- 設定 ---
project_id = os.environ.get("GCP_PROJECT")
if not project_id:
    project_id = os.environ.get("DEVSHELL_PROJECT_ID", "aicast-472807")
location = "asia-northeast1"
DB_FILE = "casting_office.db"

# --- データベース関数 ---
def execute_query(query, params=(), fetch=None):
    """データベース接続、クエリ実行、接続切断を安全に行う"""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch == "one":
            result = cursor.fetchone()
        elif fetch == "all":
            result = cursor.fetchall()
        else:
            conn.commit()
            result = None
        return result
    except sqlite3.Error as e:
        # UNIQUE制約違反は特定のエラーメッセージを出す
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
    queries = [
        'CREATE TABLE IF NOT EXISTS casts (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, persona TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, cast_id INTEGER, timestamp TEXT, content TEXT, theme TEXT, FOREIGN KEY(cast_id) REFERENCES casts(id))',
        'CREATE TABLE IF NOT EXISTS situations (id INTEGER PRIMARY KEY, content TEXT NOT NULL UNIQUE)'
    ]
    for query in queries:
        execute_query(query)
    
    # --- デフォルトキャストの追加 ---
    existing_cast = execute_query("SELECT id FROM casts WHERE name = ?", ("星野 詩織",), fetch="one")
    if not existing_cast:
        default_persona = "あなたは「星野 詩織」という名の21歳の文学部女子大生です。物静かで穏やかな聞き上手で、丁寧な言葉を使います。趣味は読書、フィルムカメラ、古い喫茶店巡りです。"
        execute_query("INSERT INTO casts (name, persona) VALUES (?, ?)", ("星野 詩織", default_persona))

    # --- デフォルトシチュエーションの追加 ---
    situation_count = execute_query("SELECT COUNT(*) as count FROM situations", fetch="one")['count']
    if situation_count == 0:
        default_situations = [
            ("静かな雨が降る夜",),
            ("気持ちの良い秋晴れの昼下がり",),
            ("お気に入りの喫茶店で読書中",),
            ("フィルムカメラ片手に散歩中",),
            ("少しセンチメンタルな気分",),
            ("新しいことを始めたくなるワクワク感",)
        ]
        for sit in default_situations:
            execute_query("INSERT INTO situations (content) VALUES (?)", sit)

# --- Streamlitアプリ本体 ---
def main():
    st.set_page_config(layout="wide")
    init_db()

    # --- 認証処理 ---
    try:
        if 'auth_done' not in st.session_state:
            vertexai.init(project=project_id, location=location)
            st.session_state.auth_done = True
        st.sidebar.success("✅ Googleサービス認証完了")
    except Exception as e:
        st.sidebar.error(f"認証に失敗しました: {e}")
        st.stop()

    # --- Geminiモデルの準備 ---
    if 'gemini_model' not in st.session_state:
        try:
            model_name = "gemini-1.5-pro"
            st.session_state.gemini_model = GenerativeModel(model_name)
        except Exception as e:
            st.error(f"Geminiモデルのロードに失敗しました: {e}")
            st.session_state.gemini_model = None

    # --- サイドバー ---
    st.sidebar.title("AIキャスト控室")
    page = st.sidebar.radio("メニュー", ["投稿管理", "シチュエーション管理", "キャスト管理"])

    # ==========================================================================
    # ページ1：投稿管理
    # ==========================================================================
    if page == "投稿管理":
        st.title("📝 投稿管理")
        
        casts = execute_query("SELECT * FROM casts ORDER BY name", fetch="all")
        if not casts:
            st.warning("キャスト未登録です。「キャスト管理」で作成してください。")
            st.stop()
            
        cast_names = [cast['name'] for cast in casts]
        selected_cast_name = st.selectbox("キャストを選択", cast_names)
        
        if selected_cast_name:
            selected_cast = next((cast for cast in casts if cast['name'] == selected_cast_name), None)
            
            st.header("投稿案を生成する")
            num_posts = st.number_input("生成する数", min_value=1, max_value=50, value=5, key="post_num")

            if st.button("生成開始", type="primary"):
                if st.session_state.get('gemini_model'):
                    with st.spinner("投稿を生成中です..."):
                        gemini_model = st.session_state.gemini_model
                        situations_rows = execute_query("SELECT content FROM situations", fetch="all")
                        if not situations_rows:
                            st.error("シチュエーションが1件も登録されていません。「シチュエーション管理」で追加してください。")
                            st.stop()
                        
                        situations = [row['content'] for row in situations_rows]
                        
                        prompt_template = f"""# ペルソナ\n{selected_cast['persona']}\n\n# シチュエーション\n{{situation}}\n\n# ルール\n上記のペルソナになりきり、与えられたシチュエーションに沿ったSNS投稿を80～120字で一つだけ生成してください。AIであることは隠し、ハッシュタグは含めないでください。"""

                        for i in range(num_posts):
                            selected_situation = random.choice(situations)
                            final_prompt = prompt_template.format(situation=selected_situation)
                            
                            try:
                                response = gemini_model.generate_content(final_prompt)
                                generated_text = response.text
                            except Exception as e:
                                st.error(f"AIからの応答生成中にエラーが発生しました: {e}")
                                continue
                            
                            today = datetime.date.today()
                            random_hour = random.randint(9, 23)
                            random_minute = random.randint(0, 59)
                            timestamp = datetime.datetime.combine(today, datetime.time(random_hour, random_minute))
                            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')

                            execute_query("INSERT INTO posts (cast_id, timestamp, content, theme) VALUES (?, ?, ?, ?)", (selected_cast['id'], timestamp_str, generated_text, selected_situation))
                            # --- MODIFIED: 待機時間を2秒に延長 ---
                            time.sleep(2)
                        
                        st.success(f"{num_posts}件の投稿案をデータベースに保存しました！")
                        st.balloons()
                else:
                    st.error("AIモデルの読み込みに失敗しているため、投稿を生成できません。")
            
            st.header(f"「{selected_cast_name}」の投稿一覧")
            all_posts = execute_query("SELECT timestamp, content, theme FROM posts WHERE cast_id = ? ORDER BY timestamp DESC", (selected_cast['id'],), fetch="all")
            if all_posts:
                df = pd.DataFrame(all_posts, columns=['投稿日時', '投稿内容', 'テーマ（シチュエーション）'])
                st.dataframe(df, use_container_width=True)
            else:
                st.info("このキャストの投稿はまだありません。")

    # ==========================================================================
    # ページ2：シチュエーション管理
    # ==========================================================================
    elif page == "シチュエーション管理":
        st.title("🎭 シチュエーション管理")
        st.markdown("キャラクターが「今、何をしているか」を定義し、投稿の多様性を生み出します。")

        st.header("新しいシチュエーションの追加")
        with st.form(key="new_situation_form", clear_on_submit=True):
            new_content = st.text_area("シチュエーション内容", placeholder="例：お気に入りの喫茶店で読書中")
            if st.form_submit_button("追加する"):
                if new_content:
                    if execute_query("INSERT INTO situations (content) VALUES (?)", (new_content,)):
                        st.success("新しいシチュエーションを追加しました！")
                else:
                    st.warning("内容を入力してください。")
        
        st.markdown("---")
        
        st.header("登録済みシチュエーション一覧")
        all_situations = execute_query("SELECT id, content FROM situations ORDER BY id DESC", fetch="all")
        if all_situations:
            for sit in all_situations:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.info(sit['content'])
                with col2:
                    if st.button("削除", key=f"delete_sit_{sit['id']}"):
                        execute_query("DELETE FROM situations WHERE id = ?", (sit['id'],))
                        st.rerun()
        else:
            st.info("登録済みのシチュエーションはありません。")


    # ==========================================================================
    # ページ3：キャスト管理
    # ==========================================================================
    elif page == "キャスト管理":
        st.title("👤 キャスト管理")

        st.header("新しいキャストの作成")
        with st.form(key="new_cast_form"):
            new_cast_name = st.text_input("新しいキャスト名")
            new_persona = st.text_area("ペルソナ（キャラクター設定）", height=200, placeholder="例：あなたは「〇〇」という名の…")
            if st.form_submit_button(label="新しいキャストを作成"):
                if new_cast_name and new_persona:
                    execute_query("INSERT INTO casts (name, persona) VALUES (?, ?)", (new_cast_name, new_persona))
                    st.success(f"新しいキャスト「{new_cast_name}」を作成しました！")
                    st.rerun()
                else:
                    st.error("キャスト名とペルソナの両方を入力してください。")

        st.markdown("---")

        st.header("既存キャストの編集")
        casts = execute_query("SELECT * FROM casts ORDER BY name", fetch="all")
        if not casts:
             st.info("編集できるキャストがまだいません。")
        else:
            cast_names = [cast['name'] for cast in casts]
            selected_cast_name_edit = st.selectbox("編集するキャストを選択", cast_names, key="edit_cast_select")
            selected_cast_to_edit = next((cast for cast in casts if cast['name'] == selected_cast_name_edit), None)

            if selected_cast_to_edit:
                 with st.form(key="edit_cast_form"):
                     st.text_input("キャスト名", value=selected_cast_to_edit['name'], disabled=True)
                     persona_to_edit = st.text_area("ペルソナを編集", value=selected_cast_to_edit['persona'], height=200)
                     if st.form_submit_button(label="この内容に更新する"):
                         execute_query("UPDATE casts SET persona = ? WHERE id = ?", (persona_to_edit, selected_cast_to_edit['id']))
                         st.success(f"「{selected_cast_to_edit['name']}」のプロフィールを更新しました！")
                         st.rerun()

# --- アプリの実行 ---
if __name__ == "__main__":
    main()
