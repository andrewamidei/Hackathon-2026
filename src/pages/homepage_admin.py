import json
import random
import string
import streamlit as st
import os
from pathlib import Path
from streamlit_js_eval import get_geolocation, streamlit_js_eval
from handlers.database import DatabaseManager
import spotifyHandler as sp_handler

# --- ASSET PATHS ---
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
FAVICON = ASSETS_DIR / "favicon_tp.png"
TEXT_LOGO = ASSETS_DIR / "text_logo.png"

# --- DATABASE SETUP ---
url = os.getenv("DATABASE_URL", "postgresql+psycopg://myuser:mypassword@db:5432/mydatabase")
dbm = DatabaseManager(url=url)

# --- PAGE CONFIG ---
st.set_page_config(page_title="Tune Zone", page_icon=str(FAVICON), layout="centered")

# ── Spotify OAuth callback ────────────────────────────────────────────────────────
# Spotify redirects to the root URL (http://127.0.0.1:8501/?code=...&state=sid=XXX).
# Intercept it here before any other UI renders, exchange the code, restore
# session state from the OAuth state param, then send the host back to the game.

if "code" in st.query_params:
    raw_state = st.query_params.get("state", "")
    for part in raw_state.split("&"):
        if part.startswith("sid="):
            st.session_state.session_id = part.split("=", 1)[1]
            st.session_state.role       = "host"
            break
    try:
        sp_handler.handle_callback(st.query_params["code"])
    except Exception as e:
        st.error(f"Spotify auth failed: {e}")
        st.stop()
    st.query_params.clear()
    st.switch_page("pages/DJ_Deathmatch.py")

# --- UTILITY FUNCTIONS ---
def gen_code():
    """Generate a unique 6-character lobby code."""
    first = random.choice(string.ascii_uppercase)
    rest = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return first + rest

ADJECTIVES = ["Funky", "Groovy", "Blazing", "Cosmic", "Electric", "Neon", "Wild", "Hyper"]
NOUNS = ["DJ", "Beat", "Drop", "Vibe", "Wave", "Bass", "Pulse", "Rhythm"]

def random_u_name():
    """Generate a unique username (adjective + noun + number)."""
    while True:
        name = f"{random.choice(ADJECTIVES)}{random.choice(NOUNS)}{random.randint(10, 99)}"
        if name not in st.session_state.used_names:
            st.session_state.used_names.add(name)
            return name

# --- SESSION STATE DEFAULTS ---
for key, default in {
    "lat": None,
    "lon": None,
    "loc_req": False,
    "host_saved": False,
    "used_names": set(),
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

if 'selected_track' not in st.session_state:
    st.session_state.selected_track = None
if 'selected_sp' not in st.session_state:
    st.session_state.selected_sp = None
if 'player_name' not in st.session_state:
    st.session_state.player_name = None

# --- DISPLAY LOGO ---
st.image(str(TEXT_LOGO), width=150)

# --- HOST SECTION ---
can_host = (
    st.session_state.lat is not None
    and st.session_state.lon is not None
)

if st.button("Host Lobby", use_container_width=True, type="primary"):#, disabled=not can_host):
    lobby_id = gen_code()

    try:
        dbm.add_host(entry=(lobby_id, (0.0, 0.0)), table_name="sessions")
        st.session_state.update({
            "role": "host",
            "lobby_code": lobby_id,
            "lat": 0.0,
            "lon": 0.0,
        })
        st.switch_page("pages/DJ_Deathmatch.py")
    except Exception as e:
        st.error(f"❌ DB Error: {e}")

# --- JOIN SECTION ---
with st.container(border=True):
    st.markdown("### Join Lobby")
    u_name = st.text_input("Username", random_u_name(), max_chars=6)
    l_code = st.text_input("Lobby Code", max_chars=6)
    if st.button("Join Game", use_container_width=True, type="primary"):
        if len(l_code) == 6:
            st.session_state.player_name = u_name
            st.session_state.update({"login_code": l_code, "role": "player"})
            st.switch_page("pages/DJ_Deathmatch.py")
        else:
            st.warning("Please enter a valid 6-character lobby code.")

# --- COMMENTED GPS/LOCATION LOGIC (for future use) ---
# @st.dialog("Sync Location")
# def loc_dialog():
#     st.write("Establish GPS link...")
#     if st.button("🛰️ Sync GPS", use_container_width=True, type="primary"):
#         st.session_state.loc_req = True
#         st.rerun()

# if st.session_state.loc_req and st.session_state.lat is None:
#     raw_data = get_geolocation()
#     if isinstance(raw_data, dict) and 'coords' in raw_data:
#         lat = raw_data['coords'].get('latitude')
#         lon = raw_data['coords'].get('longitude')
#         if lat is not None and lon is not None:
#             st.session_state.lat = float(lat)
#             st.session_state.lon = float(lon)
#             st.session_state.loc_req = False
#             st.rerun()
#         else:
#             st.info("📡 GPS returned empty coords, retrying...")
#     elif raw_data:
#         st.info("📡 Connecting... awaiting real GPS data")
#     else:
#         st.info("🛰️ Awaiting GPS signal...")
