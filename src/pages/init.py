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

def switch(page):
    st.switch_page(f"pages/{page}.py")

if 'session_id' not in st.session_state:
    st.session_state.session_id = None

if st.session_state.role == "host" and st.session_state.session_id is None:
    r = api_post("/DJ/host/setup", {"location": [], "id": 0, "name": "host"})
    if r and r.status_code == 200:
        st.session_state.session_id = r.json()["session_id"]
    else:
        st.error("Failed to create game session.")
        st.stop()

state = api_get(f"/DJ/status?session_id={st.session_state.session_id}")

current_song = state.get("current_song") if state else None
if current_song:
    st.sidebar.markdown("**Now Playing**")
    st.sidebar.info(current_song)

if not state:
    st.error("Cannot reach the game API. Is it running?")
    st.stop()

status = state.get("status")

if status != "init":
    switch(status)



st.title("DJ Deathmatch Setup")

if st.session_state.role == "host":
    sid = st.session_state.session_id
    st.sidebar.code(sid, language=None)
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

#player
elif st.session_state.role == "player":
    sid = st.session_state.get("login_code")
    game_state = api_get(f"/DJ/state?session_id={sid}") if sid else None

    if not sid or not game_state or "detail" in (game_state or {}):
        st.error("Invalid lobby code. Go back and try again.")
        st.stop()

    current_song = game_state.get("current_song")
    if current_song:
        st.sidebar.markdown("**Now Playing**")
        st.sidebar.info(current_song)

    # Register player on first load
    if st.session_state.player_id is None:
        name = st.session_state.get("player_name") or f"player_{sid}"
        r = api_post("/DJ/player/join", {"session_id": sid, "name": name})
        if r and r.status_code == 200:
            st.session_state.player_id = r.json().get("player_id")

    my_id = st.session_state.player_id
    dj_ids = game_state.get("dj_player_ids", [])
    is_dj = my_id in dj_ids

    # Reset per-round flags only when the DJ lineup changes (new round)
    if st.session_state.last_dj_ids != dj_ids:
        st.session_state.last_dj_ids = dj_ids
        st.session_state.dj_finalized = False
        st.session_state.voted = False
        st.session_state.voted_for = None

    # ── init ────────────────────────────────────────────────────────────────────
    st.title("Waiting for the host to start...")
    poll(3)