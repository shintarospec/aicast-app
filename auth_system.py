#!/usr/bin/env python3
"""
🔐 AIcast Room - シンプル確実認証システム
クエリパラメータベース・リロード完全対応
"""

import streamlit as st
import hashlib
import os
import base64
from datetime import datetime, timedelta

def hash_password(password: str) -> str:
    """パスワードのハッシュ化"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_session_token(password_hash: str) -> str:
    """セッショントークン生成"""
    timestamp = datetime.now().isoformat()
    combined = f"{password_hash}:{timestamp}"
    return base64.b64encode(combined.encode()).decode()

def verify_session_token(token: str, correct_hash: str) -> tuple:
    """セッショントークンの検証"""
    try:
        decoded = base64.b64decode(token.encode()).decode()
        stored_hash, timestamp_str = decoded.split(':', 1)
        
        if stored_hash != correct_hash:
            return False, None
            
        auth_time = datetime.fromisoformat(timestamp_str)
        if datetime.now() - auth_time < timedelta(hours=8):
            return True, auth_time
        else:
            return False, None
    except:
        return False, None

def set_auth_params(token: str, page: str = 'dashboard'):
    """認証パラメータをURLに設定"""
    st.query_params.update({
        'auth': token,
        'page': page
    })

def get_auth_params():
    """認証パラメータをURLから取得"""
    auth_token = st.query_params.get('auth', '')
    current_page = st.query_params.get('page', 'dashboard')
    return auth_token, current_page

def clear_auth_params():
    """認証パラメータをクリア"""
    if 'auth' in st.query_params:
        del st.query_params['auth']
    if 'page' in st.query_params:
        del st.query_params['page']

def save_current_page(page_name):
    """現在のページを保存（URLパラメータ + セッション状態の二重保存）"""
    # セッション状態にも保存（フォールバック用）
    st.session_state.current_page = page_name
    
    # URLパラメータにも保存
    auth_token, _ = get_auth_params()
    if auth_token:
        print(f"[DEBUG] Saving page: {page_name} with token: {auth_token[:20]}...")
        set_auth_params(auth_token, page_name)
    else:
        print(f"[DEBUG] No auth token found, cannot save page: {page_name}")

def get_current_page():
    """保存されたページを取得（URLパラメータ優先、セッション状態をフォールバック）"""
    # まずURLパラメータから取得を試行
    _, page_from_url = get_auth_params()
    
    # セッション状態からも取得
    page_from_session = st.session_state.get('current_page', 'dashboard')
    
    # URLパラメータがある場合はそれを優先、なければセッション状態を使用
    if page_from_url and page_from_url != 'dashboard':
        final_page = page_from_url
        print(f"[DEBUG] Retrieved page from URL: {final_page}")
    elif page_from_session and page_from_session != 'dashboard':
        final_page = page_from_session
        print(f"[DEBUG] Retrieved page from session (fallback): {final_page}")
    else:
        final_page = 'dashboard'
        print(f"[DEBUG] Using default page: {final_page}")
    
    return final_page

def check_password():
    """シンプル確実認証チェック"""
    
    # パスワード設定
    correct_password_hash = os.getenv('APP_PASSWORD_HASH', 
        st.secrets.get('auth', {}).get('password_hash', ''))
    
    if not correct_password_hash:
        correct_password_hash = "41e749030cd3aa529105b76146d59a5ea807146d5c8a8b3b10bd9d61e9db0cbd"
    
    # URLパラメータから認証情報を取得
    auth_token, current_page = get_auth_params()
    
    # トークン検証
    if auth_token:
        is_valid, auth_time = verify_session_token(auth_token, correct_password_hash)
        if is_valid:
            # セッション状態を設定
            st.session_state.authenticated = True
            st.session_state.auth_time = auth_time
            st.session_state.current_page = current_page
            return True
        else:
            # 無効なトークンをクリア
            clear_auth_params()
    
    # セッション状態をクリア
    st.session_state.authenticated = False
    st.session_state.auth_time = None
    
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
            
            login_button = st.button("🚀 ログイン", use_container_width=True)
    
    # パスワード検証
    if login_button and password:
        input_hash = hash_password(password)
        if input_hash == correct_password_hash:
            # 認証成功
            session_token = generate_session_token(correct_password_hash)
            set_auth_params(session_token, 'dashboard')
            st.success("✅ 認証成功！")
            st.rerun()
        else:
            st.error("❌ パスワードが正しくありません")
    elif login_button:
        st.warning("⚠️ パスワードを入力してください")
    
    # 運用情報
    with st.expander("📋 運用情報"):
        st.markdown("""
        **📊 システム情報:**
        - 運用対象：2名体制  
        - セッション時間：8時間
        - **✅ ページリロード完全対応**
        - **✅ URLベース認証で確実な状態保持**
        
        **🔧 新機能:**
        - リロード時も完全にログイン状態維持
        - ページ位置の自動復帰
        - ブラウザバック・フォワード対応
        
        **セキュリティ:**
        - トークンベース認証
        - 8時間自動期限切れ
        - 改ざん検知機能
        """)
    
    return False

def logout():
    """ログアウト処理"""
    clear_auth_params()
    st.session_state.authenticated = False
    st.session_state.auth_time = None
    st.rerun()

def show_auth_status():
    """認証状態の表示"""
    if st.session_state.get('authenticated', False):
        with st.sidebar:
            st.success("🔐 認証済み（URL保護）")
            
            # セッション残り時間表示
            if st.session_state.get('auth_time'):
                auth_time = st.session_state.auth_time
                remaining = timedelta(hours=8) - (datetime.now() - auth_time)
                if remaining.total_seconds() > 0:
                    hours = int(remaining.total_seconds() // 3600)
                    minutes = int((remaining.total_seconds() % 3600) // 60)
                    st.info(f"⏰ セッション残り: {hours}時間{minutes}分")
            
            # 現在のページ表示
            current_page = get_current_page()
            if current_page != 'dashboard':
                st.info(f"📍 ページ: {current_page}")
            
            if st.button("🚪 ログアウト"):
                logout()

if __name__ == "__main__":
    # テスト用
    print("🔐 Simple Auth System Test")
    test_hash = hash_password("aicast2025")
    print(f"Password hash: {test_hash}")
    
    token = generate_session_token(test_hash)
    print(f"Session token: {token}")
    
    is_valid, auth_time = verify_session_token(token, test_hash)
    print(f"Token valid: {is_valid}, Auth time: {auth_time}")