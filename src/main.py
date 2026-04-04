import streamlit as st

if 'login_code' not in st.session_state:
    st.session_state.login_code = None
if 'message_input' not in st.session_state:
    st.session_state.message_input = ""

st.switch_page("pages/homepage.py")

