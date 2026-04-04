import os
import time

import requests
import streamlit as st
from components.song_input import song_input

API_URL = os.environ.get("API_URL", "http://localhost:8001")

st.set_page_config(page_title="DJ Deathmatch", page_icon="🎮", layout="centered")
