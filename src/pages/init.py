import os
import time

import requests
import streamlit as st
from components.song_input import song_input

API_URL = os.environ.get("API_URL", "http://localhost:8001")

st.set_page_config(page_title="DJ Deathmatch", page_icon="🎮", layout="centered")

def api_get(path: str):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=3)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def api_post(path: str, body: dict = None):
    try:
        r = requests.post(f"{API_URL}{path}", json=body or {}, timeout=3)
        return r
    except Exception:
        return None


def poll(seconds: float = 2.0):
    """Auto-refresh for waiting states."""
    time.sleep(seconds)
    st.rerun()

if st.session_state.role == "host":
    if st.session_state.session_id is None:
        r = api_post("/DJ/host/setup", {"location": None, "id": 0, "name": "host"})
        st.session_state.session_id = r.json()["session_id"]
    sid = st.session_state.session_id
    st.sidebar.code(sid, language=None)
    state = api_get(f"/DJ/status?session_id={sid}")

    if not state:
        st.error("Cannot reach the game API. Is it running?")
        st.stop()

    status = state.get("status")
    if status != "init":
        st.switch_page(f"pages/{status}.py")

    st.title("DJ Deathmatch Setup")
    song = song_input(label="Add a song to the queue", key="host_song_input")
    if song:
        r = api_post("/DJ/host/add_song", {"session_id": sid, "song": song})
        if r and r.status_code == 200:
            st.rerun()
        else:
            st.error("Failed to add song.")

    queue = state.get("song_queue", [])
    if queue:
        st.subheader(f"Queue ({len(queue)} songs)")
        for i, s in enumerate(queue):
            st.write(f"{i + 1}. {s}")

    players = state.get("players", {})
    if players:
        st.subheader(f"Players ({len(players)})")
        for p in players.values():
            st.write(f"- {p['name']}")

    poll(3)