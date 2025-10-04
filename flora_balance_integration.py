"""
Flora Balance Viewer Integration Example for Streamlit
This shows how to integrate the responsive Flora Balance Viewer into the existing Streamlit app.
"""

import streamlit as st
import os

def render_flora_balance_viewer():
    """
    Renders the Flora Balance Viewer HTML template within Streamlit.
    This function can be called from any Streamlit page to display the viewer.
    """
    
    # Read the HTML template
    html_file_path = os.path.join(os.path.dirname(__file__), "flora_balance_viewer.html")
    
    if os.path.exists(html_file_path):
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Display the HTML content in Streamlit
        st.components.v1.html(html_content, height=1200, scrolling=True)
    else:
        st.error("Flora Balance Viewer template not found.")

def flora_balance_page():
    """
    Example of how to create a dedicated Flora Balance Viewer page in the Streamlit app.
    """
    st.set_page_config(
        page_title="Flora Balance Viewer",
        page_icon="🌸",
        layout="wide"
    )
    
    st.title("🌸 Flora Balance Viewer")
    st.markdown("健康とウェルネスの総合分析結果を表示します。")
    
    # Display the Flora Balance Viewer
    render_flora_balance_viewer()
    
    # Add some additional controls or information
    with st.expander("ℹ️ Flora Balance Viewer について"):
        st.markdown("""
        **Flora Balance Viewer** は、健康とウェルネスの状態を視覚的に分析・表示するツールです。
        
        ### 主な機能:
        - 📊 総合評価スコアの表示
        - 🔄 理想状態と現在状態の比較
        - 📈 CST（Cognitive, Social, Technical）分析結果
        - 📱 レスポンシブデザイン対応（PC・タブレット・スマートフォン）
        
        ### レスポンシブデザインの特徴:
        - **デスクトップ（>768px）**: 2カラムレイアウト
        - **タブレット（≤768px）**: 1カラムレイアウト
        - **スマートフォン（≤480px）**: モバイル最適化
        - **小型スマートフォン（≤360px）**: コンパクト表示
        """)

# サンプル使用方法
if __name__ == "__main__":
    flora_balance_page()