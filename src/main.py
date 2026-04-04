import streamlit as st

# Session states
if 'login_code' not in st.session_state:
    st.session_state.login_code = None
if 'role' not in st.session_state:
    st.session_state.role = None
if 'player_name' not in st.session_state:
    st.session_state.player_name = None

# if 'message_input' not in st.session_state:
#     st.session_state.message_input = ""

st.switch_page("pages/homepage.py")

