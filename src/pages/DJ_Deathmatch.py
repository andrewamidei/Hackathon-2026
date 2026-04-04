import os
import time

import requests
import streamlit as st
from components.song_input import song_input

API_URL = os.environ.get("API_URL", "http://localhost:8001")

st.set_page_config(page_title="DJ Deathmatch", page_icon="🎮", layout="centered")

# ── Session state defaults ──────────────────────────────────────────────────────

for key, default in {
    "role": None,
    "session_id": None,
    "player_id": None,
    "voted": False,
    "voted_for": None,
    "dj_picked": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Helpers ─────────────────────────────────────────────────────────────────────

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


def auto_rerun(seconds: float = 5.0):
    time.sleep(seconds)
    st.rerun()


# ── Auto-create session for host ────────────────────────────────────────────────

if st.session_state.role == "host" and st.session_state.session_id is None:
    r = api_post("/DJ/host/setup", {"location": [], "id": 0, "name": "host"})
    if r and r.status_code == 200:
        st.session_state.session_id = r.json()["session_id"]
    else:
        st.error("Failed to create game session.")
        st.stop()


# ════════════════════════════════════════════════════════════════════════════════
# HOST VIEW
# ════════════════════════════════════════════════════════════════════════════════

if st.session_state.role == "host":
    sid = st.session_state.session_id
    st.sidebar.code(sid, language=None)
    state = api_get(f"/DJ/status?session_id={sid}")

    if not state:
        st.error("Cannot reach the game API. Is it running?")
        st.stop()

    status = state.get("status")

    if status == "init":
        st.title("🎵 DJ Deathmatch Setup")
        song = song_input(label="Add a song to the queue", key="host_song_input")
        if song:
            r = api_post("/DJ/host/add_song", {"session_id": sid, "song": song})
            if r and r.status_code == 200:
                st.rerun()
            else:
                st.error("Failed to add song.")

        players = state.get("players", {})
        if players:
            st.subheader(f"Players ({len(players)})")
            for p in players.values():
                st.write(f"• {p['name']}")

    elif status == "play":
        st.title("🎶 Now Playing")
        current = state.get("current_song")
        if current:
            st.subheader(current)
        queue = state.get("song_queue", [])
        st.caption(f"Song {state.get('current_song_index', 0) + 1} of {len(queue)}")
        st.info("DJs will be selected when the last song finishes...")
        time.sleep(5)
        st.rerun()

    elif status == "pick":
        st.title("🎧 DJ Pick Phase")
        st.info("DJs are selecting their songs...")
        dj_picks = state.get("dj_picks", {})
        djs = state.get("djs", [])
        st.write(f"Waiting for {len(djs) - len(dj_picks)} more DJ(s) to pick...")
        auto_rerun(5)

    elif status == "vote":
        st.title("🗳️ Voting in Progress")
        players = state.get("players", {})
        votes = {}
        for p in players.values():
            v = p.get("current_vote")
            if v:
                votes[v] = votes.get(v, 0) + 1
        if votes:
            st.subheader("Current Votes")
            for dj, count in sorted(votes.items(), key=lambda x: x[1], reverse=True):
                st.metric(dj, count)
        else:
            st.info("Waiting for votes...")

        st.write("---")
        if st.button("▶ Next Round", type="primary", use_container_width=True):
            api_post(f"/DJ/host/next_round?session_id={sid}")
            st.rerun()
        auto_rerun(5)


# ════════════════════════════════════════════════════════════════════════════════
# PLAYER VIEW
# ════════════════════════════════════════════════════════════════════════════════

elif st.session_state.role == "player":
    sid = st.session_state.get("login_code")
    game_state = api_get(f"/DJ/state?session_id={sid}") if sid else None
    status = game_state.get("status") if game_state else None

    if not sid or not game_state or "detail" in game_state:
        st.error("Invalid lobby code. Go back and try again.")
        st.stop()

    # Register player on first load
    if "player_id" not in st.session_state or st.session_state.player_id is None:
        name = st.session_state.get("player_name") or f"player_{sid}"
        r = api_post("/DJ/player/join", {"session_id": sid, "name": name})
        if r and r.status_code == 200:
            st.session_state.player_id = r.json().get("player_id")

    my_id = st.session_state.get("player_id")
    dj_ids = game_state.get("dj_player_ids", [])
    is_dj = my_id in dj_ids

    # Reset per-round flags when DJ list changes (new round)
    if st.session_state.get("last_dj_ids") != dj_ids:
        st.session_state.last_dj_ids = dj_ids
        st.session_state.dj_picked = False
        st.session_state.voted = False
        st.session_state.voted_for = None

    if status == "init":
        st.title("⏳ Waiting for the host to start...")
        if is_dj:
            st.info("🎧 You are a DJ!")
        auto_rerun(5)

    elif status == "play":
        current = game_state.get("current_song")
        if is_dj:
            st.title("🎧 You're a DJ this round!")
            st.info("Get ready to pick your song when the queue ends...")
        else:
            st.title("🎶 Now Playing")
        if current:
            st.subheader(current)
        auto_rerun(5)

    elif status == "pick":
        if is_dj and not st.session_state.get("dj_picked"):
            st.title("🎧 Pick Your Song!")
            song = song_input(label="Submit your song pick", key="dj_song_input")
            if song:
                r = api_post("/DJ/dj/pick", {
                    "session_id": sid,
                    "player_id": my_id or 0,
                    "song": song,
                })
                if r and r.status_code == 200:
                    st.session_state.dj_picked = True
                    st.rerun()
        elif is_dj:
            st.title("🎧 Song Submitted!")
            st.info("Waiting for other DJs...")
            auto_rerun(5)
        else:
            st.title("⏳ DJs are picking their songs...")
            auto_rerun(5)

    elif status == "vote":
        djs = game_state.get("djs", [])
        if is_dj:
            # ── DJ vote view ───────────────────────────────────────────────
            st.title("🎧 Voting in Progress")
            st.info("Players are voting on the DJs. Results will appear here.")
            auto_rerun(5)
        else:
            st.title("🗳️ Vote for a Song")
            if "last_vote_djs" not in st.session_state or st.session_state.last_vote_djs != djs:
                st.session_state.voted = False
                st.session_state.last_vote_djs = djs
            if not st.session_state.get("voted"):
                for i, dj in enumerate(djs):
                    if st.button(dj, use_container_width=True, key=f"vote_{i}"):
                        api_post("/DJ/player/vote", {
                            "session_id": sid,
                            "player_id": my_id or 0,
                            "vote": dj,
                        })
                        st.session_state.voted = True
                        st.session_state.voted_for = dj
                        st.rerun()
            else:
                for i, dj in enumerate(djs):
                    if dj == st.session_state.get("voted_for"):
                        st.success(f"✅ {dj}")
                    else:
                        st.button(dj, use_container_width=True, key=f"voted_{i}", disabled=True)
                auto_rerun(5)


