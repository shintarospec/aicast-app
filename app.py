import streamlit as st
import pandas as pd
import datetime
import time
import random
import sqlite3
import vertexai
from vertexai.preview.generative_models import GenerativeModel
import os

# （この部分は変更なし）
# ...

# --- Streamlitアプリ本体 ---
def main():
    st.set_page_config(layout="wide")
    
    # --- DEBUG MESSAGES ADDED ---
    st.info("ステップ1：アプリ開始")
    
    init_db()
    st.info("ステップ2：データベース初期化完了")

    # --- 認証処理 ---
    try:
        if 'auth_done' not in st.session_state:
            st.info("ステップ3：Vertex AIの初期化開始...")
            vertexai.init(project=project_id, location=location)
            st.info("ステップ4：Vertex AIの初期化完了！")
            st.session_state.auth_done = True
        st.sidebar.success("✅ Googleサービス認証完了")
    except Exception as e:
        st.sidebar.error(f"認証に失敗しました: {e}")
        st.stop()

    # --- Geminiモデルの準備 ---
    if 'gemini_model' not in st.session_state:
        try:
            st.info("ステップ5：Geminiモデルのロード開始...")
            model_name = "gemini-1.5-pro"
            st.session_state.gemini_model = GenerativeModel(model_name)
            st.info("ステップ6：Geminiモデルのロード完了！")
        except Exception as e:
            st.error(f"Geminiモデルのロードに失敗しました: {e}")
            st.session_state.gemini_model = None
    
    st.info("ステップ7：UIの描画開始")
    # --- END OF DEBUG MESSAGES ---
    
    # --- サイドバー ---
    st.sidebar.title("AIキャスト控室")
    page = st.sidebar.radio("メニュー", ["投稿管理", "シチュエーション管理", "キャスト管理"])

    # （これ以降のコードは変更なし）
    # ... (if/elif page == ... and the rest of the file)

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
                        themes = ["季節の変わり目について", "最近読んだ本の一節", "喫茶店の窓から", "フィルムカメラの魅力", "コーヒーの香り", "静かな雨の日の過ごし方", "月が綺麗な夜に思うこと"]
                        prompt_template = f"{selected_cast['persona']}\n上記のキャラクター設定になりきり、以下のテーマについて80～120字程度のSNS投稿を一つだけ生成してください。AIであることは隠し、ハッシュタグは含めないでください。\nテーマ: {{theme}}"

                        for i in range(num_posts):
                            selected_theme = random.choice(themes)
                            final_prompt = prompt_template.format(theme=selected_theme)
                            response = gemini_model.generate_content(final_prompt)
                            generated_text = response.text
                            
                            today = datetime.date.today()
                            random_hour = random.randint(9, 23)
                            random_minute = random.randint(0, 59)
                            timestamp = datetime.datetime.combine(today, datetime.time(random_hour, random_minute))
                            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')

                            execute_query("INSERT INTO posts (cast_id, timestamp, content, theme) VALUES (?, ?, ?, ?)", (selected_cast['id'], timestamp_str, generated_text, selected_theme))
                            time.sleep(1)
                        
                        st.success(f"{num_posts}件の投稿案をデータベースに保存しました！")
                        st.balloons()
                else:
                    st.error("AIモデルの読み込みに失敗しているため、投稿を生成できません。")
            
            st.header(f"「{selected_cast_name}」の投稿一覧")
            all_posts = execute_query("SELECT timestamp, content, theme FROM posts WHERE cast_id = ? ORDER BY timestamp DESC", (selected_cast['id'],), fetch="all")
            if all_posts:
                df = pd.DataFrame(all_posts, columns=['投稿日時', '投稿内容', 'テーマ'])
                st.dataframe(df, use_container_width=True)
            else:
                st.info("このキャストの投稿はまだありません。")

    # ==========================================================================
    # ページ2：キャスト管理
    # ==========================================================================
    elif page == "キャスト管理":
        st.title("👤 キャスト管理")

        st.header("新しいキャストの作成")
        with st.form(key="new_cast_form"):
            new_cast_name = st.text_input("新しいキャスト名")
            new_persona = st.text_area("ペルソナ（キャラクター設定）", height=200, placeholder="例：あなたは「〇〇」という名の…")
            if st.form_submit_button(label="新しいキャストを作成"):
                if new_cast_name and new_persona:
                    existing_cast = execute_query("SELECT id FROM casts WHERE name = ?", (new_cast_name,), fetch="one")
                    if existing_cast:
                        st.error(f"エラー: '{new_cast_name}' は既に存在します。")
                    else:
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