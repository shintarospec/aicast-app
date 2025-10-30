import streamlit as st

st.set_page_config(
    page_title="サイドバーテスト",
    layout="wide",
    initial_sidebar_state="expanded"
)

# シンプルなCSS
st.markdown("""
<style>
/* 開くボタンのテスト */
[data-testid="collapsedControl"] {
    background-color: red !important;
    border: 5px solid yellow !important;
    padding: 20px !important;
    position: fixed !important;
    top: 10px !important;
    left: 10px !important;
    z-index: 999999 !important;
}

/* すべてのボタンを赤くしてみる */
button {
    border: 2px solid red !important;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("サイドバー")
    st.write("このサイドバーを閉じてください")
    st.write("開くボタンが赤と黄色で表示されるはずです")

st.title("メインコンテンツ")
st.write("サイドバーを閉じた時に、赤と黄色のボタンが表示されますか?")
