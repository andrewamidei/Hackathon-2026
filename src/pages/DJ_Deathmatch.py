import os

import requests
import streamlit as st
from components.song_input import song_input

API_URL = os.environ.get("API_URL", "http://localhost:8001")

st.set_page_config(page_title="DJ Deathmatch", page_icon="🎮", layout="centered")

# Hide the form submit button — press Enter to submit instead
st.markdown(
    "<style>[data-testid='stFormSubmitButton']{display:none}</style>",
    unsafe_allow_html=True,
)

# ── Session state defaults ───────────────────────────────────────────────────────

for key, default in {
    "role":          None,
    "session_id":    None,
    "player_id":     None,
    "voted":         False,
    "voted_for":     None,
    "dj_finalized":  False,
    "last_dj_ids":   [],
    "now_playing":   None,   # written by fragment; read by sidebar outside fragment
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

MAX_DJ_SONGS = 3


# ── API helpers ──────────────────────────────────────────────────────────────────

def api_get(path: str):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=3)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def api_post(path: str, body: dict = None):
    try:
        return requests.post(f"{API_URL}{path}", json=body or {}, timeout=3)
    except Exception:
        return None


def vote_timer_bar(remaining: int, duration: int):
    fraction = remaining / duration if duration > 0 else 0
    label    = f"Voting closes in {remaining}s" if remaining > 0 else "Voting closed..."
    st.progress(fraction, text=label)


# ── Host session bootstrap ───────────────────────────────────────────────────────

if st.session_state.role == "host" and st.session_state.session_id is None:
    lat = st.session_state.get("lat")
    lon = st.session_state.get("lon")
    if not lat or not lon:
        st.error("No coordinates found. Please go back and sync GPS first.")
        st.stop()
    r = api_post("/DJ/host/setup", {
        "location": [lat, lon],
        "id":       0,
        "name":     "host",
    })
    if r and r.status_code == 200:
        st.session_state.session_id = r.json()["session_id"]
    else:
        st.error("Failed to create game session.")
        st.stop()


# ── Player registration ──────────────────────────────────────────────────────────

if st.session_state.role == "player" and st.session_state.player_id is None:
    sid  = st.session_state.get("login_code")
    name = (st.session_state.get("player_name") or "").strip() or f"player_{sid}"
    if sid:
        r = api_post("/DJ/player/join", {"session_id": sid, "name": name})
        if r and r.status_code == 200:
            st.session_state.player_id = r.json().get("player_id")


# ── Sidebar: Now Playing ─────────────────────────────────────────────────────────
# Rendered outside the fragment so st.sidebar calls are allowed.
# `now_playing` is kept in session state and updated by the fragments below.

with st.sidebar:
    if st.session_state.role == "host":
        st.code(st.session_state.session_id or "", language=None)
    if st.session_state.now_playing:
        st.markdown("**Now Playing**")
        st.info(st.session_state.now_playing)


# ════════════════════════════════════════════════════════════════════════════════
# HOST VIEW
# ════════════════════════════════════════════════════════════════════════════════

if st.session_state.role == "host":
    sid = st.session_state.session_id

    @st.fragment(run_every=1)
    def host_view():
        state = api_get(f"/DJ/status?session_id={sid}")
        if not state:
            st.error("Cannot reach the game API. Is it running?")
            return

        # Push current song to session state so sidebar (outside fragment) can read it
        st.session_state.now_playing = state.get("current_song")

        status = state.get("status")

        # ── init ─────────────────────────────────────────────────────────────────
        if status == "init":
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

        # ── play ──────────────────────────────────────────────────────────────────
        elif status == "play":
            st.title("Now Playing")
            current = state.get("current_song")
            if current:
                st.subheader(current)
            queue = state.get("song_queue", [])
            idx   = state.get("current_song_index", 0)
            st.caption(f"Song {idx + 1} of {len(queue)}")
            st.info("DJs are selected when the last song starts playing.")

        # ── pick ──────────────────────────────────────────────────────────────────
        elif status == "pick":
            st.title("DJ Pick Phase")
            dj_vote_options = state.get("dj_vote_options", [])
            pending         = sum(1 for d in dj_vote_options if not d["finalized"])
            st.info(f"Waiting for {pending} DJ(s) to finalize their picks...")

            for opt in dj_vote_options:
                status_text = "Done" if opt["finalized"] else "Picking..."
                with st.container(border=True):
                    st.write(f"**{opt['name']}** — {status_text}")
                    for slot in range(MAX_DJ_SONGS):
                        if slot < len(opt["songs"]):
                            st.write(f"  {slot + 1}. {opt['songs'][slot]}")
                        else:
                            st.write(f"  {slot + 1}. —")

        # ── vote ──────────────────────────────────────────────────────────────────
        elif status == "vote":
            st.title("Voting in Progress")
            dj_vote_options = state.get("dj_vote_options", [])
            players         = state.get("players", {})
            remaining       = state.get("vote_time_remaining", 0)
            duration        = state.get("vote_duration", 30)

            vote_timer_bar(remaining, duration)

            vote_counts: dict[str, int] = {}
            for p in players.values():
                v = p.get("current_vote")
                if v:
                    vote_counts[v] = vote_counts.get(v, 0) + 1

            st.caption(f"{sum(vote_counts.values())} vote(s) cast")

            for opt in dj_vote_options:
                with st.container(border=True):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.subheader(opt["name"])
                        for i, song in enumerate(opt["songs"]):
                            st.write(f"{i + 1}. {song}")
                    with col2:
                        st.metric("Votes", vote_counts.get(opt["name"], 0))

            st.divider()
            if st.button("End Voting Early", use_container_width=True):
                r = api_post(f"/DJ/host/next_round?session_id={sid}")
                if r and r.status_code == 200:
                    st.rerun()
                else:
                    st.error("Failed to start next round.")

        # ── ended ─────────────────────────────────────────────────────────────────
        elif status == "ended":
            st.title("Game Over")
            st.balloons()

    host_view()


# ════════════════════════════════════════════════════════════════════════════════
# PLAYER VIEW
# ════════════════════════════════════════════════════════════════════════════════

elif st.session_state.role == "player":
    sid = st.session_state.get("login_code")
    if not sid:
        st.error("Invalid lobby code. Go back and try again.")
        st.stop()

    @st.fragment(run_every=1)
    def player_view():
        game_state = api_get(f"/DJ/state?session_id={sid}")
        if not game_state or "detail" in game_state:
            st.error("Could not load game state. Check your lobby code.")
            return

        status = game_state.get("status")
        my_id  = st.session_state.player_id
        dj_ids = game_state.get("dj_player_ids", [])
        is_dj  = my_id in dj_ids

        # Push current song to session state so sidebar can read it
        st.session_state.now_playing = game_state.get("current_song")

        # Reset per-round flags when the DJ lineup changes (new round)
        if st.session_state.last_dj_ids != dj_ids:
            st.session_state.last_dj_ids  = dj_ids
            st.session_state.dj_finalized = False
            st.session_state.voted        = False
            st.session_state.voted_for    = None

        # ── init ──────────────────────────────────────────────────────────────
        if status == "init":
            st.title("Waiting for the host to start...")

        # ── play ──────────────────────────────────────────────────────────────
        elif status == "play":
            if is_dj:
                st.title("You're a DJ this round!")
                st.info("Start picking your songs — the last song is playing now.")
            else:
                st.title("Now Playing")
            current = game_state.get("current_song")
            if current:
                st.subheader(current)

        # ── pick ──────────────────────────────────────────────────────────────
        elif status == "pick":
            dj_vote_options = game_state.get("dj_vote_options", [])
            my_option       = next(
                (d for d in dj_vote_options if d["player_id"] == my_id), None
            )

            if is_dj and not st.session_state.dj_finalized:
                st.title("Pick Your Songs!")
                current_picks = my_option["songs"] if my_option else []

                if len(current_picks) < 3:
                    song = song_input(
                        label=f"Song {len(current_picks) + 1} of 3",
                        key=f"dj_song_{len(current_picks)}",
                    )
                    if song:
                        r = api_post("/DJ/dj/pick", {
                            "session_id": sid,
                            "player_id":  my_id,
                            "song":       song,
                        })
                        if r and r.status_code == 200:
                            st.rerun()
                        else:
                            st.error("Failed to add song. Try again.")
                else:
                    st.info("You've picked 3 songs. Finalize when ready.")

                if current_picks:
                    st.subheader("Your picks:")
                    for i, s in enumerate(current_picks):
                        st.write(f"{i + 1}. {s}")
                    st.divider()
                    if st.button(
                        "Finalize My Picks", type="primary", use_container_width=True
                    ):
                        r = api_post("/DJ/dj/finalize", {
                            "session_id": sid,
                            "player_id":  my_id,
                        })
                        if r and r.status_code == 200:
                            st.session_state.dj_finalized = True
                            st.rerun()
                        else:
                            st.error("Failed to finalize. Try again.")

            elif is_dj:   # finalized, waiting for other DJ
                st.title("Picks Submitted!")
                if my_option:
                    st.subheader("Your songs:")
                    for i, song in enumerate(my_option["songs"]):
                        st.write(f"{i + 1}. {song}")
                st.info("Waiting for the other DJ to finalize...")

            else:
                st.title("DJs are picking their songs...")
                for opt in dj_vote_options:
                    icon = "Done" if opt["finalized"] else "Still picking..."
                    st.write(f"**{opt['name']}** — {icon}")

        # ── vote ──────────────────────────────────────────────────────────────
        elif status == "vote":
            dj_vote_options = game_state.get("dj_vote_options", [])
            remaining       = game_state.get("vote_time_remaining", 0)
            duration        = game_state.get("vote_duration", 30)

            if is_dj:
                st.title("Voting in Progress")
                vote_timer_bar(remaining, duration)
                st.info("Players are voting. Hang tight!")
                for opt in dj_vote_options:
                    heading = "Your picks" if opt["player_id"] == my_id else opt["name"]
                    with st.container(border=True):
                        st.subheader(heading)
                        for i, song in enumerate(opt["songs"]):
                            st.write(f"{i + 1}. {song}")

            elif not st.session_state.voted:
                st.title("Vote for a DJ!")
                vote_timer_bar(remaining, duration)
                st.write("Choose the DJ whose songs you want to hear next:")
                for opt in dj_vote_options:
                    with st.container(border=True):
                        st.subheader(opt["name"])
                        for i, song in enumerate(opt["songs"]):
                            st.write(f"{i + 1}. {song}")
                        if st.button(
                            f"Vote for {opt['name']}",
                            key=f"vote_{opt['player_id']}",
                            use_container_width=True,
                            type="primary",
                        ):
                            r = api_post("/DJ/player/vote", {
                                "session_id": sid,
                                "player_id":  my_id,
                                "vote":       opt["name"],
                            })
                            if r and r.status_code == 200:
                                st.session_state.voted     = True
                                st.session_state.voted_for = opt["name"]
                                st.rerun()

            else:   # already voted
                st.title("Vote Submitted!")
                vote_timer_bar(remaining, duration)
                st.success(f"You voted for **{st.session_state.voted_for}**")
                for opt in dj_vote_options:
                    heading = (
                        f"✓ {opt['name']} (your vote)"
                        if opt["name"] == st.session_state.voted_for
                        else opt["name"]
                    )
                    with st.container(border=True):
                        st.subheader(heading)
                        for i, song in enumerate(opt["songs"]):
                            st.write(f"{i + 1}. {song}")

        # ── ended ─────────────────────────────────────────────────────────────
        elif status == "ended":
            st.title("Game Over!")
            st.balloons()

    player_view()


# ── No role: redirect to homepage ────────────────────────────────────────────────

else:
    st.switch_page("pages/homepage.py")
