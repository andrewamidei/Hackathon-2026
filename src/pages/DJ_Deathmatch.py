import os

import requests
import streamlit as st
import streamlit.components.v1 as components
from components.song_input import song_input
import spotifyHandler as sp_handler

API_URL = os.environ.get("API_URL", "http://localhost:8001")

st.set_page_config(page_title="DJ Deathmatch", page_icon="🎮", layout="centered")

# Hide the form submit button — press Enter to submit instead
st.markdown(
    "<style>[data-testid='stFormSubmitButton']{display:none}</style>",
    unsafe_allow_html=True,
)

# ── Session state defaults ───────────────────────────────────────────────────────

for key, default in {
    "role":            None,
    "session_id":      None,
    "player_id":       None,
    "voted":           False,
    "voted_for":       None,
    "dj_finalized":    False,
    "last_dj_ids":     [],
    "now_playing":     None,   # written by fragment; read by sidebar outside fragment
    # Spotify (token lives in spotifyHandler module, not here)
    "sp_track_uris":   {},     # {song_label: uri} built as host adds songs
    "sp_search":       [],     # current search results
    "sp_last_played":  None,   # song label last sent to Spotify
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


def timer_bar(remaining: int, duration: int, label_open: str, label_closed: str):
    fraction = remaining / duration if duration > 0 else 0
    label    = f"{label_open} {remaining}s" if remaining > 0 else label_closed
    st.progress(fraction, text=label)


# Inject the Web Playback SDK once for the host (outside the fragment so the
# iframe is not re-mounted on every fragment cycle).
if st.session_state.role == "host" and sp_handler.is_authenticated():
    try:
        components.html(sp_handler.player_html(), height=50)
    except Exception:
        pass


# ── Host session bootstrap ───────────────────────────────────────────────────────

if st.session_state.role == "host" and st.session_state.session_id is None:
    # lat = st.session_state.get("lat")
    # lon = st.session_state.get("lon")
    # if not lat or not lon:
    #     st.error("No coordinates found. Please go back and sync GPS first.")
    #     st.stop()
    r = api_post("/DJ/host/setup", {
        "location": [None, None],
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
        if not sp_handler.is_authenticated():
            auth_url = sp_handler.get_auth_url(st.session_state.session_id or "")
            st.markdown(
                f'<a href="{auth_url}" target="_self">'
                '<div style="background:#1DB954;color:white;padding:8px;'
                'text-align:center;border-radius:6px;font-weight:bold;">'
                'Connect Spotify</div></a>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("Spotify connected")
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

        if status in ("play","pick","vote"):
            st.title(f"Now Playing: {sp_handler.get_current_track_name()}")
            current = state.get("current_song")


            # Auto-play on Spotify when the song advances
            if current and current != st.session_state.sp_last_played and sp_handler.is_authenticated():
                try:
                    device_id = sp_handler.get_player_device_id()
                    uri       = st.session_state.sp_track_uris.get(current)
                    if device_id and uri:
                        sp_handler.play_track(uri, device_id)
                        st.session_state.sp_last_played = current
                    elif not device_id:
                        st.warning("Spotify player not found — click the page once to wake it up.")
                except Exception as e:
                    st.warning(f"Spotify playback error: {e}")

            queue = state.get("song_queue", [])
            idx   = state.get("current_song_index", 0)
            st.caption(f"Song 1 of {sp_handler.get_queue_size()}")
            st.info("DJs are selected when the last song starts playing.")

        # ── init ─────────────────────────────────────────────────────────────────
        if status == "init":
            st.title("DJ Deathmatch Setup")

            # Spotify search to add songs — falls back to plain text if not connected
            if sp_handler.is_authenticated():
                with st.form("sp_search_form", clear_on_submit=True):
                    query = st.text_input("Search Spotify", placeholder="Artist or song name")
                    st.form_submit_button("Search")
                if query and query.strip():
                    try:
                        st.session_state.sp_search = sp_handler.search_tracks(query.strip())
                    except Exception as e:
                        st.error(f"Search failed: {e}")

                for track in st.session_state.sp_search:
                    col1, col2 = st.columns([1, 5])
                    with col1:
                        if track["album_art"]:
                            st.image(track["album_art"], width=60)
                    with col2:
                        st.write(f"**{track['name']}** — {track['artist']}")
                        if st.button("Add to queue", key=f"add_{track['id']}"):
                            label = f"{track['name']} — {track['artist']}"
                            r = api_post("/DJ/host/add_song", {"session_id": sid, "song": label})
                            if r and r.status_code == 200:
                                st.session_state.sp_track_uris[label] = track["uri"]
                                st.session_state.sp_search = []
                                st.rerun()
                            else:
                                st.error("Failed to add song.")
                

                
                
            else:
                st.info("Connect Spotify in the sidebar to search for songs.")
                song = song_input(label="Or add a song title manually", key="host_song_input")
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


        # ── pick ──────────────────────────────────────────────────────────────────
        elif status == "pick":
            st.title("DJ Pick Phase")
            dj_vote_options  = state.get("dj_vote_options", [])
            pending          = sum(1 for d in dj_vote_options if not d["finalized"])
            pick_remaining   = state.get("pick_time_remaining", 0)
            pick_duration    = state.get("pick_duration", 60)

            timer_bar(pick_remaining, pick_duration, "Pick time remaining:", "Pick time over")
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

            timer_bar(remaining, duration, "Voting closes in", "Voting closed...")

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
                st.title(f"Now Playing: {sp_handler.get_current_track_name()}")
            current = game_state.get("current_song")

        # ── pick ──────────────────────────────────────────────────────────────
        elif status == "pick":
            dj_vote_options = game_state.get("dj_vote_options", [])
            my_option       = next(
                (d for d in dj_vote_options if d["player_id"] == my_id), None
            )

            pick_remaining = game_state.get("pick_time_remaining", 0)
            pick_duration  = game_state.get("pick_duration", 60)

            if is_dj and not st.session_state.dj_finalized:
                st.title("You're a DJ! Pick Your Songs!")
                timer_bar(pick_remaining, pick_duration, "Time to pick:", "Time's up!")

                current_picks = my_option["songs"] if my_option else []
                slots_left    = MAX_DJ_SONGS - len(current_picks)

                if slots_left > 0:
                    with st.form("dj_pick_form", clear_on_submit=True):
                        song = st.text_input(
                            f"Add a song ({len(current_picks) + 1} of {MAX_DJ_SONGS})",
                            placeholder="Press Enter to add",
                        )
                        st.form_submit_button("add", use_container_width=True)

                    # Auto-focus the input so the cursor stays after each rerun
                    components.html(
                        "<script>"
                        "const inputs = window.parent.document.querySelectorAll('.stTextInput input');"
                        "if (inputs.length) inputs[inputs.length - 1].focus();"
                        "</script>",
                        height=0,
                    )

                    if song and song.strip():
                        r = api_post("/DJ/dj/pick", {
                            "session_id": sid,
                            "player_id":  my_id,
                            "song":       song.strip(),
                        })
                        if r and r.status_code == 200:
                            st.rerun()
                        else:
                            st.error("Failed to add song. Try again.")
                else:
                    st.info("You've added 3 songs. Finalize when ready.")

                if current_picks:
                    st.subheader("Your picks:")
                    for i, s in enumerate(current_picks):
                        st.write(f"{i + 1}. {s}")
                    st.divider()
                    if st.button("Finalize My Picks", type="primary", use_container_width=True):
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
                timer_bar(pick_remaining, pick_duration, "Time to pick:", "Time's up!")
                st.info("Waiting for the other DJ to finalize...")

            else:
                st.title("DJs are picking their songs...")
                timer_bar(pick_remaining, pick_duration, "Time to pick:", "Time's up!")
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
                timer_bar(remaining, duration, "Voting closes in", "Voting closed...")
                st.info("Players are voting. Hang tight!")
                for opt in dj_vote_options:
                    heading = "Your picks" if opt["player_id"] == my_id else opt["name"]
                    with st.container(border=True):
                        st.subheader(heading)
                        for i, song in enumerate(opt["songs"]):
                            st.write(f"{i + 1}. {song}")

            elif not st.session_state.voted:
                st.title("Vote for a DJ!")
                timer_bar(remaining, duration, "Voting closes in", "Voting closed...")
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
                timer_bar(remaining, duration, "Voting closes in", "Voting closed...")
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
