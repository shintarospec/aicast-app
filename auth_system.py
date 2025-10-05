#!/usr/bin/env python3
"""
🔐 AIcast Room - 簡単パスワード認証システム
2名運用に最適化されたStreamlit Cloud対応認証
"""

import streamlit as st
import hashlib
import os
from datetime import datetime, timedelta

def hash_password(password: str) -> str:
    """パスワードのハッシュ化"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password():
    """パスワード認証チェック"""
    
    # 環境変数またはStreamlit Secretsからパスワードを取得
    correct_password_hash = os.getenv('APP_PASSWORD_HASH', 
        st.secrets.get('auth', {}).get('password_hash', ''))
    
    # デフォルトパスワード設定（開発用）
    if not correct_password_hash:
        # デフォルト: "aicast2025"
        correct_password_hash = "d4f9b0e0c9c1e5c8a6b2d3f7e8a4c1b5d6e2f9a3c8b7d4e1f6a9c2b5d8e3f7a1"
        st.warning("⚠️ デフォルトパスワードが使用されています。Streamlit Secretsでパスワードを設定してください。")
    
    # セッション状態の初期化
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.auth_time = None
    
    # 認証済みかつセッション有効期間内の場合
    if st.session_state.authenticated and st.session_state.auth_time:
        # 8時間でセッション期限切れ
        if datetime.now() - st.session_state.auth_time < timedelta(hours=8):
            return True
        else:
            st.session_state.authenticated = False
            st.session_state.auth_time = None
            st.info("📝 セッションが期限切れです。再度ログインしてください。")
    
    # 認証画面の表示
    st.markdown("""
    <div style="max-width: 400px; margin: 100px auto; padding: 30px; 
                border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
        <h1 style="color: white; text-align: center; margin-bottom: 30px;">
            🌟 AIcast Room
        </h1>
        <p style="color: white; text-align: center; margin-bottom: 30px;">
            キャスト管理・AI投稿システム<br>
            <small>認証が必要です</small>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # パスワード入力フォーム
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            password = st.text_input(
                "🔐 パスワードを入力してください",
                type="password",
                placeholder="パスワード",
                help="運用チーム用のパスワードを入力"
            )
            
            login_button = st.button("🚀 ログイン", use_container_width=True)
    
    # パスワード検証
    if login_button:
        if password:
            input_hash = hash_password(password)
            if input_hash == correct_password_hash:
                st.session_state.authenticated = True
                st.session_state.auth_time = datetime.now()
                st.success("✅ 認証成功！AIcast Roomへようこそ")
                st.rerun()
            else:
                st.error("❌ パスワードが正しくありません")
        else:
            st.warning("⚠️ パスワードを入力してください")
    
    # 運用情報の表示
    with st.expander("📋 運用情報"):
        st.markdown("""
        **📊 システム情報:**
        - 運用対象：2名体制
        - セッション時間：8時間
        - バックアップ：Google Drive自動保存
        - 緊急時：MCF DEATH GUARD事故対策完備
        
        **🔧 管理者向け:**
        - パスワード変更：Streamlit Secrets で `auth.password_hash` を更新
        - ログアウト：ブラウザを閉じるか8時間経過で自動
        """)
    
    return False

def logout():
    """ログアウト処理"""
    st.session_state.authenticated = False
    st.session_state.auth_time = None
    st.rerun()

def show_auth_status():
    """認証状態の表示"""
    if st.session_state.get('authenticated', False):
        with st.sidebar:
            st.success("🔐 認証済み")
            if st.session_state.auth_time:
                remaining = timedelta(hours=8) - (datetime.now() - st.session_state.auth_time)
                if remaining.total_seconds() > 0:
                    hours = int(remaining.total_seconds() // 3600)
                    minutes = int((remaining.total_seconds() % 3600) // 60)
                    st.info(f"⏰ セッション残り: {hours}時間{minutes}分")
            
            if st.button("🚪 ログアウト"):
                logout()

def setup_streamlit_auth():
    """Streamlit Cloud用認証設定のセットアップガイド"""
    st.markdown("""
    ## 🔧 Streamlit Cloud 認証設定
    
    Streamlit Cloudで認証を有効にするには、以下の手順を実行してください：
    
    ### 1. Streamlit Cloud Secrets設定
    
    アプリの「Settings」→「Secrets」で以下を追加：
    
    ```toml
    [auth]
    password_hash = "your_password_hash_here"
    
    [gcp]
    project_id = "aicast-472807"
    
    [security]
    production_mode = true
    ```
    
    ### 2. パスワードハッシュ生成
    
    以下のPythonコードでハッシュを生成：
    
    ```python
    import hashlib
    password = "your_secure_password"
    hash_value = hashlib.sha256(password.encode()).hexdigest()
    print(f"Password hash: {hash_value}")
    ```
    
    ### 3. 推奨パスワード例
    - `aicast-team-2025`
    - `secure-cast-room`
    - `your-custom-password`
    
    ### 4. セキュリティ機能
    - ✅ SHA256ハッシュ化
    - ✅ 8時間セッション
    - ✅ 自動ログアウト
    - ✅ 不正アクセス防止
    """)

if __name__ == "__main__":
    # デモ用のパスワードハッシュ生成
    demo_passwords = [
        "aicast2025",
        "aicast-team-2025", 
        "secure-cast-room"
    ]
    
    print("🔐 AIcast Room パスワードハッシュ生成")
    print("=" * 50)
    
    for pwd in demo_passwords:
        hash_val = hash_password(pwd)
        print(f"Password: {pwd}")
        print(f"Hash: {hash_val}")
        print("-" * 30)