import streamlit as st
import time
from datetime import datetime

st.title("Player's View")

st.markdown(f"lobby code {st.session_state.login_code}")