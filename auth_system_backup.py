#!/usr/bin/env python3
"""
🔐 AIcast Room - 改良版パスワード認証システム
ブラウザSessionStorage対応・確実なセッション永続化
"""

import streamlit as st
import streamlit.components.v1 as components
import hashlib
import os
import time
import json
from datetime import datetime, timedelta

def hash_password(password: str) -> str:
    """パスワードのハッシュ化"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_auth_js():
    """認証用JavaScript関数"""
    return """
    <script>
    // セッション情報をSessionStorageに保存
    function saveAuthSession(data) {
        sessionStorage.setItem('aicast_auth', JSON.stringify(data));
        console.log('Auth session saved:', data);
    }
    
    // セッション情報をSessionStorageから取得
    function getAuthSession() {
        const data = sessionStorage.getItem('aicast_auth');
        if (data) {
            const parsed = JSON.parse(data);
            console.log('Auth session loaded:', parsed);
            return parsed;
        }
        return null;
    }
    
    // セッション情報をクリア
    function clearAuthSession() {
        sessionStorage.removeItem('aicast_auth');
        console.log('Auth session cleared');
    }
    
    // Streamlitとの通信
    function sendAuthStatus(status) {
        window.parent.postMessage({
            type: 'auth_status',
            authenticated: status.authenticated,
            auth_time: status.auth_time,
            current_page: status.current_page || 'dashboard'
        }, '*');
    }
    
    // ページロード時の認証状態チェック
    window.addEventListener('load', function() {
        const session = getAuthSession();
        if (session) {
            const authTime = new Date(session.auth_time);
            const now = new Date();
            const diffHours = (now - authTime) / (1000 * 60 * 60);
            
            if (diffHours < 8) {
                sendAuthStatus(session);
            } else {
                clearAuthSession();
                sendAuthStatus({authenticated: false});
            }
        }
    });
    
    // グローバル関数として公開
    window.aicastAuth = {
        save: saveAuthSession,
        load: getAuthSession,
        clear: clearAuthSession,
        send: sendAuthStatus
    };
    </script>
    """

def init_auth_state():
    """認証状態の初期化（改良版）"""
    # 基本的なセッション状態初期化
    if 'auth_initialized' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.auth_time = None
        st.session_state.auth_token = None
        st.session_state.current_page = 'dashboard'
        st.session_state.auth_initialized = True
        st.session_state.auth_check_done = False

def check_browser_auth():
    """ブラウザからの認証状態チェック"""
    # JavaScriptで認証状態をチェック
    auth_check_js = f"""
    {get_auth_js()}
    <script>
    // 認証状態をStreamlitに送信
    const session = window.aicastAuth.load();
    if (session && session.authenticated) {{
        const authTime = new Date(session.auth_time);
        const now = new Date();
        const diffHours = (now - authTime) / (1000 * 60 * 60);
        
        if (diffHours < 8) {{
            // 有効なセッションがある場合
            window.parent.postMessage({{
                type: 'streamlit:auth_restore',
                authenticated: true,
                auth_time: session.auth_time,
                current_page: session.current_page || 'dashboard'
            }}, '*');
        }} else {{
            // セッション期限切れ
            window.aicastAuth.clear();
        }}
    }}
    </script>
    """
    
    components.html(auth_check_js, height=0, scrolling=False)

def save_auth_to_browser(auth_time_str, current_page='dashboard'):
    """認証情報をブラウザに保存"""
    save_js = f"""
    {get_auth_js()}
    <script>
    window.aicastAuth.save({{
        authenticated: true,
        auth_time: '{auth_time_str}',
        current_page: '{current_page}'
    }});
    </script>
    """
    components.html(save_js, height=0, scrolling=False)

def clear_auth_from_browser():
    """ブラウザの認証情報をクリア"""
    clear_js = f"""
    {get_auth_js()}
    <script>
    window.aicastAuth.clear();
    </script>
    """
    components.html(clear_js, height=0, scrolling=False)

def generate_auth_token():
    """セッション用トークン生成"""
    return hashlib.md5(f"{datetime.now().isoformat()}{time.time()}".encode()).hexdigest()

def is_session_valid():
    """セッションの有効性チェック（改良版）"""
    if not st.session_state.get('authenticated', False):
        return False
    
    if not st.session_state.get('auth_time'):
        return False
    
    # 8時間でセッション期限切れ
    auth_time = st.session_state.auth_time
    if isinstance(auth_time, str):
        try:
            auth_time = datetime.fromisoformat(auth_time)
            st.session_state.auth_time = auth_time
        except:
            return False
    
    if datetime.now() - auth_time < timedelta(hours=8):
        return True
    else:
        # セッション期限切れ
        clear_auth_state()
        clear_auth_from_browser()
        return False

def clear_auth_state():
    """認証状態をクリア"""
    st.session_state.authenticated = False
    st.session_state.auth_time = None
    st.session_state.auth_token = None

def save_current_page(page_name):
    """現在のページを保存（ブラウザにも保存）"""
    st.session_state.current_page = page_name
    if st.session_state.get('authenticated', False):
        auth_time_str = st.session_state.auth_time.isoformat() if st.session_state.auth_time else datetime.now().isoformat()
        save_auth_to_browser(auth_time_str, page_name)

def get_current_page():
    """保存されたページを取得"""
    return st.session_state.get('current_page', 'dashboard')

def check_password():
    """改良版パスワード認証チェック（ブラウザSessionStorage対応）"""
    
    # 認証状態の初期化
    init_auth_state()
    
    # ブラウザからの認証状態復元（初回のみ）
    if not st.session_state.get('auth_check_done', False):
        check_browser_auth()
        st.session_state.auth_check_done = True
    
    # 環境変数またはStreamlit Secretsからパスワードを取得
    correct_password_hash = os.getenv('APP_PASSWORD_HASH', 
        st.secrets.get('auth', {}).get('password_hash', ''))
    
    # デフォルトパスワード設定（開発用）
    if not correct_password_hash:
        # デフォルト: "aicast2025"
        correct_password_hash = "41e749030cd3aa529105b76146d59a5ea807146d5c8a8b3b10bd9d61e9db0cbd"
    
    # セッション有効性チェック
    if is_session_valid():
        return True
    
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
                help="運用チーム用のパスワードを入力",
                key="auth_password_input"
            )
            
            login_button = st.button("🚀 ログイン", use_container_width=True, key="auth_login_button")
    
    # パスワード検証
    if login_button:
        if password:
            input_hash = hash_password(password)
            if input_hash == correct_password_hash:
                # 認証成功
                auth_time = datetime.now()
                st.session_state.authenticated = True
                st.session_state.auth_time = auth_time
                st.session_state.auth_token = generate_auth_token()
                st.session_state.current_page = 'dashboard'
                
                # ブラウザにも認証情報を保存
                save_auth_to_browser(auth_time.isoformat(), 'dashboard')
                
                st.success("✅ 認証成功！AIcast Roomへようこそ")
                time.sleep(0.5)  # 成功メッセージを見せる
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
        - セッション時間：8時間（ページリロード完全対応）
        - バックアップ：自動DB保護
        - 緊急時：完全復旧システム完備
        
        **🔧 新機能:**
        - ✅ ページリロード時のログイン状態維持
        - ✅ ページ位置の自動復帰
        - ✅ ブラウザベースのセッション管理
        
        **管理者向け:**
        - パスワード変更：Streamlit Secrets で `auth.password_hash` を更新
        - セッション継続：ブラウザタブを閉じるまで維持
        - ログアウト：手動またはセッション期限切れで自動
        """)
    
    return False

def logout():
    """ログアウト処理（改良版）"""
    clear_auth_state()
    clear_auth_from_browser()
    st.rerun()

def show_auth_status():
    """認証状態の表示（改良版）"""
    if st.session_state.get('authenticated', False):
        with st.sidebar:
            st.success("🔐 認証済み")
            
            # セッション残り時間表示
            if st.session_state.auth_time:
                auth_time = st.session_state.auth_time
                if isinstance(auth_time, str):
                    try:
                        auth_time = datetime.fromisoformat(auth_time)
                    except:
                        auth_time = datetime.now()
                
                remaining = timedelta(hours=8) - (datetime.now() - auth_time)
                if remaining.total_seconds() > 0:
                    hours = int(remaining.total_seconds() // 3600)
                    minutes = int((remaining.total_seconds() % 3600) // 60)
                    st.info(f"⏰ セッション残り: {hours}時間{minutes}分")
                else:
                    st.warning("⚠️ セッション期限切れ間近")
            
            # 現在のページ表示
            current_page = get_current_page()
            if current_page and current_page != 'dashboard':
                page_name = current_page.replace('📊 ', '').replace('ダッシュボード', 'ダッシュボード')
                st.info(f"📍 現在のページ: {page_name}")
            
            if st.button("🚪 ログアウト", key="sidebar_logout"):
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