# 新しいキャスト管理セクションのコード
# app.pyの該当セクション（5402行〜6383行）を置き換えるためのコード

NEW_CAST_MANAGEMENT_CODE = '''
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
        
        # セッションステートの初期化
        if 'selected_cast_for_edit' not in st.session_state:
            st.session_state.selected_cast_for_edit = None
        
        # 新UI構造: 4つのメインタブ（新規登録、キャスト一覧、編集、CSV管理）
        tab_new, tab_list, tab_edit, tab_csv = st.tabs([
            "➕ 新規登録",
            "👥 キャスト一覧", 
            "✏️ 編集",
            "📥 CSV管理"
        ])
        
        # ==================== タブ1: 新規登録 ====================
        with tab_new:
            st.header("新しいキャストの作成")
            st.info("新規キャストの情報を入力してください。必須項目はペルソナ管理タブの3項目（name, nickname, age）のみです。")
            
            # セッションステートで新規登録データを管理
            if 'new_cast_data' not in st.session_state:
                st.session_state.new_cast_data = {}
            
            # 新規登録用のサブタブ（ペルソナ/運営指針/キャラクター/X API）
            persona_new_tab, mission_new_tab, character_new_tab, xapi_new_tab = st.tabs([
                "👤 ペルソナ管理",
                "📋 運営指針", 
                "🎭 キャラクター設定",
                "🔐 X API設定"
            ])
            
            # --- サブタブ1-1: ペルソナ管理 ---
            with persona_new_tab:
                st.markdown("### 📌 必須項目")
                col1, col2, col3 = st.columns(3)
                new_name = col1.text_input("ユーザー名 (@username)*", placeholder="@shiori_hoshino", key="new_name")
                new_nickname = col2.text_input("名前（表示名）*", placeholder="星野 詩織", key="new_nickname")
                new_age = col3.text_input("年齢*", placeholder="21", key="new_age")
                
                st.markdown("### 🔍 詳細ペルソナ（オプション）")
                with st.expander("詳細ペルソナを入力（任意）", expanded=False):
                    col1, col2 = st.columns(2)
                    new_archetype = col1.text_input("アーキタイプ", placeholder="例: クリエイター、冒険家、賢者", key="new_archetype")
                    new_occupation_detailed = col2.text_input("職業（詳細）", placeholder="例: フリーランスデザイナー", key="new_occupation_detailed")
                    new_residence = col1.text_input("居住地", placeholder="例: 東京都渋谷区", key="new_residence")
                    new_family_structure = col2.text_input("家族構成", placeholder="例: 両親と弟の4人家族", key="new_family_structure")
                    new_symbolic_quote = st.text_input("象徴的な一言", placeholder="例: 人生は一度きり、後悔しない選択を", key="new_symbolic_quote")
                    new_x_usage_purpose = st.text_input("X利用目的", placeholder="例: 作品を発信し、同じ趣味の仲間と繋がるため", key="new_x_usage_purpose")
                    new_behavior_pattern = st.text_area("行動パターン", placeholder="例: 朝は静かにコーヒーを飲みながら読書、夜は創作活動", key="new_behavior_pattern")
                    new_interested_topics = st.text_input("関心トピック", placeholder="例: アート、テクノロジー、旅行", key="new_interested_topics")
                    new_platform_pain_points = st.text_input("プラットフォーム不満", placeholder="例: タイムラインが時系列順でないこと", key="new_platform_pain_points")
                    new_brand_relationship = st.text_input("ブランド関係", placeholder="例: Apple製品愛用者、無印良品ファン", key="new_brand_relationship")
            
            # --- サブタブ1-2: 運営指針 ---
            with mission_new_tab:
                st.markdown("### アカウント運営指針（オプション）")
                new_mission = st.text_area("運営ミッション", placeholder="このアカウントの目的や使命", key="new_mission", height=100)
                new_persona_design = st.text_area("ペルソナ設計意図", placeholder="なぜこのキャラクターなのか", key="new_persona_design", height=100)
                new_content_strategy = st.text_area("コンテンツ戦略", placeholder="どんな投稿をするか", key="new_content_strategy", height=100)
                new_final_goal = st.text_area("最終目標", placeholder="このアカウントで達成したいこと", key="new_final_goal", height=100)
                new_additional_notes = st.text_area("補足事項", placeholder="その他重要な情報", key="new_additional_notes", height=100)
                
                st.markdown("### サンプルプロフィール（オプション）")
                new_sample_profile = st.text_area("サンプルプロフィール", placeholder="このキャラクターの模範的なプロフィール文", key="new_sample_profile", height=100)
            
            # --- サブタブ1-3: キャラクター設定 ---
            with character_new_tab:
                st.markdown("### キャラクター詳細設定（オプション）")
                col1, col2 = st.columns(2)
                new_birthday = col1.text_input("誕生日", placeholder="例: 3月15日", key="new_birthday")
                new_birthplace = col2.text_input("出身地", placeholder="例: 東京都", key="new_birthplace")
                new_appearance = st.text_area("外見", placeholder="例: 黒髪のロングヘア、明るい笑顔", key="new_appearance")
                new_customer_interaction = st.text_area("顧客対応スタイル", placeholder="例: 親しみやすく丁寧", key="new_customer_interaction")
                col1, col2 = st.columns(2)
                new_hobby = col1.text_input("趣味", placeholder="例: 読書、カフェ巡り", key="new_hobby")
                new_holiday_activity = col2.text_input("休日の過ごし方", placeholder="例: 映画鑑賞、友人とランチ", key="new_holiday_activity")
                new_reason_for_job = st.text_area("この仕事を選んだ理由", placeholder="例: 人と話すのが好きだから", key="new_reason_for_job")
            
            # --- サブタブ1-4: X API設定 ---
            with xapi_new_tab:
                st.markdown("### X API認証情報（オプション）")
                st.info("このキャスト専用のX APIキーを設定できます。空欄の場合はシステムデフォルトが使用されます。")
                new_x_api_key = st.text_input("API Key", type="password", key="new_x_api_key")
                new_x_api_secret = st.text_input("API Secret", type="password", key="new_x_api_secret")
                new_x_bearer_token = st.text_input("Bearer Token", type="password", key="new_x_bearer_token")
                new_x_access_token = st.text_input("Access Token", type="password", key="new_x_access_token")
                new_x_access_token_secret = st.text_input("Access Token Secret", type="password", key="new_x_access_token_secret")
                col1, col2 = st.columns(2)
                new_x_twitter_username = col1.text_input("Twitterユーザー名", placeholder="@username", key="new_x_twitter_username")
                new_x_twitter_user_id = col2.text_input("TwitterユーザーID", placeholder="1234567890", key="new_x_twitter_user_id")
            
            # 登録ボタン（タブの外に配置）
            st.markdown("---")
            if st.button("✅ 新しいキャストを登録", type="primary", key="create_new_cast_btn"):
                if new_name and new_nickname and new_age:
                    try:
                        # castsテーブルに基本情報を登録
                        cast_id = execute_query(
                            """INSERT INTO casts (name, nickname, age, birthday, birthplace, appearance, personality, 
                            strength, weakness, first_person, speech_style, catchphrase, customer_interaction, 
                            occupation, hobby, likes, dislikes, holiday_activity, dream, reason_for_job, secret)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (new_name, new_nickname, new_age, st.session_state.get('new_birthday', ''),
                             st.session_state.get('new_birthplace', ''), st.session_state.get('new_appearance', ''),
                             '', '', '', '', '', '', st.session_state.get('new_customer_interaction', ''),
                             '', st.session_state.get('new_hobby', ''), '', '', st.session_state.get('new_holiday_activity', ''),
                             '', st.session_state.get('new_reason_for_job', ''), '')
                        )
                        
                        if cast_id:
                            # 詳細ペルソナがあれば登録
                            if any([new_archetype, new_occupation_detailed, new_residence, new_family_structure,
                                   new_symbolic_quote, new_x_usage_purpose, new_behavior_pattern, 
                                   new_interested_topics, new_platform_pain_points, new_brand_relationship]):
                                execute_query(
                                    """INSERT INTO persona_detailed 
                                    (cast_id, archetype, occupation, residence, family_structure, symbolic_quote,
                                     x_usage_purpose, behavior_pattern, interested_topics, platform_pain_points, brand_relationship)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                    (cast_id, new_archetype, new_occupation_detailed, new_residence, new_family_structure,
                                     new_symbolic_quote, new_x_usage_purpose, new_behavior_pattern,
                                     new_interested_topics, new_platform_pain_points, new_brand_relationship)
                                )
                            
                            # 運営指針があれば登録
                            if any([new_mission, new_persona_design, new_content_strategy, new_final_goal, new_additional_notes]):
                                execute_query(
                                    """INSERT INTO account_mission 
                                    (cast_id, mission, persona_design, content_strategy, final_goal, additional_notes)
                                    VALUES (?, ?, ?, ?, ?, ?)""",
                                    (cast_id, new_mission, new_persona_design, new_content_strategy, new_final_goal, new_additional_notes)
                                )
                            
                            # サンプルプロフィールがあれば登録
                            if new_sample_profile:
                                execute_query(
                                    "INSERT INTO sample_profiles (cast_id, profile_text) VALUES (?, ?)",
                                    (cast_id, new_sample_profile)
                                )
                            
                            # X API認証情報があれば登録
                            if new_x_api_key:
                                save_cast_x_credentials(
                                    cast_id,
                                    new_x_api_key,
                                    new_x_api_secret,
                                    new_x_bearer_token,
                                    new_x_access_token,
                                    new_x_access_token_secret,
                                    new_x_twitter_username,
                                    new_x_twitter_user_id
                                )
                            
                            st.session_state.cast_import_message = ("success", f"✅ キャスト「{new_name}（{new_nickname}）」を作成しました！")
                            # フォームをクリア
                            for key in list(st.session_state.keys()):
                                if key.startswith('new_'):
                                    del st.session_state[key]
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ キャスト作成中にエラーが発生しました: {e}")
                else:
                    st.error("❌ 必須項目（ユーザー名、名前、年齢）をすべて入力してください。")
        
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
                        
                        # 詳細ペルソナの有無を確認
                        persona_exists = execute_query(
                            "SELECT COUNT(*) as count FROM persona_detailed WHERE cast_id = ?",
                            (cast['id'],),
                            fetch="one"
                        )
                        if persona_exists and persona_exists['count'] > 0:
                            col3.success("✅ 詳細有")
                        else:
                            col3.info("➖ 詳細無")
                        
                        # 編集ボタン
                        if col4.button("✏️ 編集", key=f"edit_cast_{cast['id']}"):
                            st.session_state.selected_cast_for_edit = cast['id']
                            st.rerun()
                        
                        st.markdown("---")
        
        # ==================== タブ3: 編集 ====================
        with tab_edit:
            st.header("既存キャストの編集・削除")
            
            # キャスト一覧から選択された場合、またはドロップダウンで選択
            casts = execute_query("SELECT id, name, nickname FROM casts ORDER BY name", fetch="all")
            
            if not casts:
                st.info("編集できるキャストがまだいません。")
            else:
                # キャスト選択（name（nickname）形式）
                cast_options = {f"{c['name']}（{c['nickname']}）" if c['nickname'] else c['name']: c['id'] for c in casts}
                
                # セッションステートで選択されたキャストがあれば、それをデフォルトに
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
                
                # 選択が変更されたらセッションステートを更新
                if st.session_state.selected_cast_for_edit != selected_cast_id:
                    st.session_state.selected_cast_for_edit = selected_cast_id
                
                # キャスト情報取得
                cast_data = execute_query("SELECT * FROM casts WHERE id = ?", (selected_cast_id,), fetch="one")
                persona_data = execute_query("SELECT * FROM persona_detailed WHERE cast_id = ?", (selected_cast_id,), fetch="one")
                mission_data = execute_query("SELECT * FROM account_mission WHERE cast_id = ?", (selected_cast_id,), fetch="one")
                profile_data = execute_query("SELECT * FROM sample_profiles WHERE cast_id = ?", (selected_cast_id,), fetch="one")
                x_creds = get_cast_x_credentials(selected_cast_id)
                
                if cast_data:
                    # 編集用のサブタブ（ペルソナ/運営指針/キャラクター/X API）
                    persona_edit_tab, mission_edit_tab, character_edit_tab, xapi_edit_tab = st.tabs([
                        "👤 ペルソナ管理",
                        "📋 運営指針", 
                        "🎭 キャラクター設定",
                        "🔐 X API設定"
                    ])
                    
                    # --- サブタブ3-1: ペルソナ管理 ---
                    with persona_edit_tab:
                        st.markdown("### 📌 必須項目")
                        col1, col2, col3 = st.columns(3)
                        edit_name = col1.text_input("ユーザー名*", value=cast_data['name'] if cast_data['name'] else '', key=f"edit_name_{selected_cast_id}")
                        edit_nickname = col2.text_input("名前（表示名）*", value=cast_data['nickname'] if cast_data['nickname'] else '', key=f"edit_nickname_{selected_cast_id}")
                        edit_age = col3.text_input("年齢*", value=str(cast_data['age']) if cast_data['age'] else '', key=f"edit_age_{selected_cast_id}")
                        
                        st.markdown("### 🔍 詳細ペルソナ（オプション）")
                        with st.expander("詳細ペルソナを編集（任意）", expanded=True):
                            col1, col2 = st.columns(2)
                            edit_archetype = col1.text_input("アーキタイプ", value=persona_data['archetype'] if persona_data and persona_data['archetype'] else '', key=f"edit_archetype_{selected_cast_id}")
                            edit_occupation_detailed = col2.text_input("職業（詳細）", value=persona_data['occupation'] if persona_data and persona_data['occupation'] else '', key=f"edit_occupation_detailed_{selected_cast_id}")
                            edit_residence = col1.text_input("居住地", value=persona_data['residence'] if persona_data and persona_data['residence'] else '', key=f"edit_residence_{selected_cast_id}")
                            edit_family_structure = col2.text_input("家族構成", value=persona_data['family_structure'] if persona_data and persona_data['family_structure'] else '', key=f"edit_family_structure_{selected_cast_id}")
                            edit_symbolic_quote = st.text_input("象徴的な一言", value=persona_data['symbolic_quote'] if persona_data and persona_data['symbolic_quote'] else '', key=f"edit_symbolic_quote_{selected_cast_id}")
                            edit_x_usage_purpose = st.text_input("X利用目的", value=persona_data['x_usage_purpose'] if persona_data and persona_data['x_usage_purpose'] else '', key=f"edit_x_usage_purpose_{selected_cast_id}")
                            edit_behavior_pattern = st.text_area("行動パターン", value=persona_data['behavior_pattern'] if persona_data and persona_data['behavior_pattern'] else '', key=f"edit_behavior_pattern_{selected_cast_id}")
                            edit_interested_topics = st.text_input("関心トピック", value=persona_data['interested_topics'] if persona_data and persona_data['interested_topics'] else '', key=f"edit_interested_topics_{selected_cast_id}")
                            edit_platform_pain_points = st.text_input("プラットフォーム不満", value=persona_data['platform_pain_points'] if persona_data and persona_data['platform_pain_points'] else '', key=f"edit_platform_pain_points_{selected_cast_id}")
                            edit_brand_relationship = st.text_input("ブランド関係", value=persona_data['brand_relationship'] if persona_data and persona_data['brand_relationship'] else '', key=f"edit_brand_relationship_{selected_cast_id}")
                    
                    # --- サブタブ3-2: 運営指針 ---
                    with mission_edit_tab:
                        st.markdown("### アカウント運営指針")
                        edit_mission = st.text_area("運営ミッション", value=mission_data['mission'] if mission_data and mission_data['mission'] else '', key=f"edit_mission_{selected_cast_id}", height=100)
                        edit_persona_design = st.text_area("ペルソナ設計意図", value=mission_data['persona_design'] if mission_data and mission_data['persona_design'] else '', key=f"edit_persona_design_{selected_cast_id}", height=100)
                        edit_content_strategy = st.text_area("コンテンツ戦略", value=mission_data['content_strategy'] if mission_data and mission_data['content_strategy'] else '', key=f"edit_content_strategy_{selected_cast_id}", height=100)
                        edit_final_goal = st.text_area("最終目標", value=mission_data['final_goal'] if mission_data and mission_data['final_goal'] else '', key=f"edit_final_goal_{selected_cast_id}", height=100)
                        edit_additional_notes = st.text_area("補足事項", value=mission_data['additional_notes'] if mission_data and mission_data['additional_notes'] else '', key=f"edit_additional_notes_{selected_cast_id}", height=100)
                        
                        st.markdown("### サンプルプロフィール")
                        edit_sample_profile = st.text_area("サンプルプロフィール", value=profile_data['profile_text'] if profile_data and profile_data['profile_text'] else '', key=f"edit_sample_profile_{selected_cast_id}", height=100)
                    
                    # --- サブタブ3-3: キャラクター設定 ---
                    with character_edit_tab:
                        st.markdown("### キャラクター詳細設定")
                        col1, col2 = st.columns(2)
                        edit_birthday = col1.text_input("誕生日", value=cast_data['birthday'] if cast_data['birthday'] else '', key=f"edit_birthday_{selected_cast_id}")
                        edit_birthplace = col2.text_input("出身地", value=cast_data['birthplace'] if cast_data['birthplace'] else '', key=f"edit_birthplace_{selected_cast_id}")
                        edit_appearance = st.text_area("外見", value=cast_data['appearance'] if cast_data['appearance'] else '', key=f"edit_appearance_{selected_cast_id}")
                        edit_customer_interaction = st.text_area("顧客対応スタイル", value=cast_data['customer_interaction'] if cast_data['customer_interaction'] else '', key=f"edit_customer_interaction_{selected_cast_id}")
                        col1, col2 = st.columns(2)
                        edit_hobby = col1.text_input("趣味", value=cast_data['hobby'] if cast_data['hobby'] else '', key=f"edit_hobby_{selected_cast_id}")
                        edit_holiday_activity = col2.text_input("休日の過ごし方", value=cast_data['holiday_activity'] if cast_data['holiday_activity'] else '', key=f"edit_holiday_activity_{selected_cast_id}")
                        edit_reason_for_job = st.text_area("この仕事を選んだ理由", value=cast_data['reason_for_job'] if cast_data['reason_for_job'] else '', key=f"edit_reason_for_job_{selected_cast_id}")
                    
                    # --- サブタブ3-4: X API設定 ---
                    with xapi_edit_tab:
                        st.markdown("### X API認証情報")
                        st.info("このキャスト専用のX APIキーを設定できます。")
                        edit_x_api_key = st.text_input("API Key", value=x_creds['api_key'] if x_creds and x_creds['api_key'] else '', type="password", key=f"edit_x_api_key_{selected_cast_id}")
                        edit_x_api_secret = st.text_input("API Secret", value=x_creds['api_secret'] if x_creds and x_creds['api_secret'] else '', type="password", key=f"edit_x_api_secret_{selected_cast_id}")
                        edit_x_bearer_token = st.text_input("Bearer Token", value=x_creds['bearer_token'] if x_creds and x_creds['bearer_token'] else '', type="password", key=f"edit_x_bearer_token_{selected_cast_id}")
                        edit_x_access_token = st.text_input("Access Token", value=x_creds['access_token'] if x_creds and x_creds['access_token'] else '', type="password", key=f"edit_x_access_token_{selected_cast_id}")
                        edit_x_access_token_secret = st.text_input("Access Token Secret", value=x_creds['access_token_secret'] if x_creds and x_creds['access_token_secret'] else '', type="password", key=f"edit_x_access_token_secret_{selected_cast_id}")
                        col1, col2 = st.columns(2)
                        edit_x_twitter_username = col1.text_input("Twitterユーザー名", value=x_creds['twitter_username'] if x_creds and x_creds['twitter_username'] else '', key=f"edit_x_twitter_username_{selected_cast_id}")
                        edit_x_twitter_user_id = col2.text_input("TwitterユーザーID", value=x_creds['twitter_user_id'] if x_creds and x_creds['twitter_user_id'] else '', key=f"edit_x_twitter_user_id_{selected_cast_id}")
                    
                    # 更新・削除ボタン（タブの外に配置）
                    st.markdown("---")
                    col_update, col_delete = st.columns([3, 1])
                    
                    if col_update.button("💾 更新", type="primary", key=f"update_cast_{selected_cast_id}"):
                        if edit_name and edit_nickname and edit_age:
                            try:
                                # casts更新
                                execute_query(
                                    """UPDATE casts SET name = ?, nickname = ?, age = ?, birthday = ?, birthplace = ?, 
                                    appearance = ?, customer_interaction = ?, hobby = ?, holiday_activity = ?, reason_for_job = ?
                                    WHERE id = ?""",
                                    (edit_name, edit_nickname, edit_age, st.session_state.get(f'edit_birthday_{selected_cast_id}', ''),
                                     st.session_state.get(f'edit_birthplace_{selected_cast_id}', ''), st.session_state.get(f'edit_appearance_{selected_cast_id}', ''),
                                     st.session_state.get(f'edit_customer_interaction_{selected_cast_id}', ''), st.session_state.get(f'edit_hobby_{selected_cast_id}', ''),
                                     st.session_state.get(f'edit_holiday_activity_{selected_cast_id}', ''), st.session_state.get(f'edit_reason_for_job_{selected_cast_id}', ''),
                                     selected_cast_id)
                                )
                                
                                # persona_detailed更新または挿入
                                if any([edit_archetype, edit_occupation_detailed, edit_residence, edit_family_structure,
                                       edit_symbolic_quote, edit_x_usage_purpose, edit_behavior_pattern,
                                       edit_interested_topics, edit_platform_pain_points, edit_brand_relationship]):
                                    if persona_data:
                                        execute_query(
                                            """UPDATE persona_detailed SET 
                                            archetype = ?, occupation = ?, residence = ?, family_structure = ?, symbolic_quote = ?,
                                            x_usage_purpose = ?, behavior_pattern = ?, interested_topics = ?, platform_pain_points = ?, brand_relationship = ?
                                            WHERE cast_id = ?""",
                                            (edit_archetype, edit_occupation_detailed, edit_residence, edit_family_structure,
                                             edit_symbolic_quote, edit_x_usage_purpose, edit_behavior_pattern,
                                             edit_interested_topics, edit_platform_pain_points, edit_brand_relationship, selected_cast_id)
                                        )
                                    else:
                                        execute_query(
                                            """INSERT INTO persona_detailed 
                                            (cast_id, archetype, occupation, residence, family_structure, symbolic_quote,
                                             x_usage_purpose, behavior_pattern, interested_topics, platform_pain_points, brand_relationship)
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                            (selected_cast_id, edit_archetype, edit_occupation_detailed, edit_residence, edit_family_structure,
                                             edit_symbolic_quote, edit_x_usage_purpose, edit_behavior_pattern,
                                             edit_interested_topics, edit_platform_pain_points, edit_brand_relationship)
                                        )
                                
                                # account_mission更新または挿入
                                if any([edit_mission, edit_persona_design, edit_content_strategy, edit_final_goal, edit_additional_notes]):
                                    if mission_data:
                                        execute_query(
                                            """UPDATE account_mission SET mission = ?, persona_design = ?, content_strategy = ?, 
                                            final_goal = ?, additional_notes = ? WHERE cast_id = ?""",
                                            (edit_mission, edit_persona_design, edit_content_strategy, edit_final_goal, edit_additional_notes, selected_cast_id)
                                        )
                                    else:
                                        execute_query(
                                            """INSERT INTO account_mission (cast_id, mission, persona_design, content_strategy, final_goal, additional_notes)
                                            VALUES (?, ?, ?, ?, ?, ?)""",
                                            (selected_cast_id, edit_mission, edit_persona_design, edit_content_strategy, edit_final_goal, edit_additional_notes)
                                        )
                                
                                # sample_profiles更新または挿入
                                if edit_sample_profile:
                                    if profile_data:
                                        execute_query(
                                            "UPDATE sample_profiles SET profile_text = ? WHERE cast_id = ?",
                                            (edit_sample_profile, selected_cast_id)
                                        )
                                    else:
                                        execute_query(
                                            "INSERT INTO sample_profiles (cast_id, profile_text) VALUES (?, ?)",
                                            (selected_cast_id, edit_sample_profile)
                                        )
                                
                                # X API認証情報の更新
                                if edit_x_api_key:
                                    save_cast_x_credentials(
                                        selected_cast_id,
                                        edit_x_api_key,
                                        edit_x_api_secret,
                                        edit_x_bearer_token,
                                        edit_x_access_token,
                                        edit_x_access_token_secret,
                                        edit_x_twitter_username,
                                        edit_x_twitter_user_id
                                    )
                                
                                st.session_state.cast_import_message = ("success", f"✅ キャスト「{edit_name}（{edit_nickname}）」を更新しました！")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 更新中にエラーが発生しました: {e}")
                        else:
                            st.error("❌ 必須項目をすべて入力してください。")
                    
                    if col_delete.button("🗑️ 削除", type="secondary", key=f"delete_cast_{selected_cast_id}"):
                        try:
                            execute_query("DELETE FROM casts WHERE id = ?", (selected_cast_id,))
                            st.session_state.cast_import_message = ("success", f"🗑️ キャスト「{cast_data['name']}」を削除しました！")
                            st.session_state.selected_cast_for_edit = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 削除中にエラーが発生しました: {e}")
        
        # ==================== タブ4: CSV管理 ====================
        with tab_csv:
            st.header("📥 CSV一括管理")
            st.info("キャスト基本情報（38項目）とサンプル投稿（4項目）をCSVで管理できます。")
            
            csv_import_tab, csv_export_tab, csv_sample_posts_tab = st.tabs(["📥 インポート", "📤 エクスポート", "📝 サンプル投稿CSV"])
            
            # TODO: CSV管理のコードをここに移植（既存のコードから）
            with csv_import_tab:
                st.markdown("### キャスト基本情報のインポート")
                st.info("CSVの1行目はヘッダー行、2行目以降がデータです。必須項目は`name`のみ。")
                
            with csv_export_tab:
                st.markdown("### キャスト基本情報のエクスポート")
                
            with csv_sample_posts_tab:
                st.markdown("### サンプル投稿のCSV管理")
'''

if __name__ == "__main__":
    print("新しいキャスト管理セクションのコードを用意しました。")
    print("app.pyの該当セクションをこのコードで置き換えてください。")
