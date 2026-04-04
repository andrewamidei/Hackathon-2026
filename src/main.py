import random
import string
import streamlit as st
import os
from streamlit_js_eval import get_geolocation
from handlers.database import DatabaseManager
import spotifyHandler as sp_handler

url = os.getenv("DATABASE_URL", "postgresql+psycopg://myuser:mypassword@db:5432/mydatabase")

st.set_page_config(page_title="DJ Booth", layout="centered")

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

dbm = DatabaseManager(url=url)

# if 'message_input' not in st.session_state:
#     st.session_state.message_input = ""

def gen_code():
    # Ensure the code always starts with a letter so it can never be
    # confused with the numeric IDs the geolocation library leaks.
    first = random.choice(string.ascii_uppercase)
    rest = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return first + rest

ADJECTIVES = ["Funky", "Groovy", "Blazing", "Cosmic", "Electric", "Neon", "Wild", "Hyper"]
NOUNS = ["DJ", "Beat", "Drop", "Vibe", "Wave", "Bass", "Pulse", "Rhythm"]

def random_u_name():
    while True:
        name = f"{random.choice(ADJECTIVES)}{random.choice(NOUNS)}{random.randint(10, 99)}"
        if name not in st.session_state.used_names:
            st.session_state.used_names.add(name)
            return name

# Import your custom function from the handler file
# from spotifyHandler import render_spotify_player

# --- SESSION STATE DEFAULTS ---
for key, default in {
    "lat": None,
    "lon": None,
    "loc_req": False,
    "host_saved": False,   # NEW: prevents re-running the DB write on reruns
    "used_names": set(),
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# st.title("🎧 DJ Booth")

if 'selected_track' not in st.session_state:
    st.session_state.selected_track = None
if 'selected_sp' not in st.session_state:
    st.session_state.selected_sp = None

# # --- LOCATION DIALOG ---
# @st.dialog("Sync Location")
# def loc_dialog():
#     st.write("Establish GPS link...")
#     if st.button("🛰️ Sync GPS", use_container_width=True, type="primary"):
#         st.session_state.loc_req = True
#         st.rerun()


# # --- GPS RESOLUTION ---
# # Only run geolocation widget when we're actively waiting for a fix
# # and don't already have coordinates.
# if st.session_state.loc_req and st.session_state.lat is None:
#     raw_data = get_geolocation()

#     if isinstance(raw_data, dict) and 'coords' in raw_data:
#         lat = raw_data['coords'].get('latitude')
#         lon = raw_data['coords'].get('longitude')

#         # Extra guard: coords must be real floats, not None/zero junk
#         if lat is not None and lon is not None:
#             st.session_state.lat = float(lat)
#             st.session_state.lon = float(lon)
#             st.session_state.loc_req = False
#             st.rerun()
#         else:
#             st.info("📡 GPS returned empty coords, retrying...")
#     elif raw_data:
#         # Numeric library ID — ignore completely, do NOT write anything
#         st.info("📡 Connecting... awaiting real GPS data")
#     else:
#         st.info("🛰️ Awaiting GPS signal...")

# list1: [str] = ""

# # --- UI STATUS ---
# if st.session_state.lat is None:
#     if st.button("Begin Setup", use_container_width=True, type="primary"):

#         loc_dialog()
# else:
#     st.success(f"📍 Position Locked!: {st.session_state.lat:.4f}, {st.session_state.lon:.4f}")
#     list1 = dbm.query_nearest((st.session_state.lat, st.session_state.lon))

#     if list1 != "": st.write(f"a list of things: {list1}")
#     if st.button("Reset GPS"):
#         st.session_state.lat = None
#         st.session_state.lon = None
#         st.session_state.loc_req = False
#         st.rerun()

# st.divider()

# --- HOST SECTION ---
st.title("Tune Zone")

can_host = (
    st.session_state.lat is not None
    and st.session_state.lon is not None
)

if st.button("Host Lobby", use_container_width=True, type="primary"):#, disabled=not can_host):
    # val_lat = st.session_state.lat
    # val_lon = st.session_state.lon

    # # Hard gate: never write NULL coordinates, even if button state was wrong
    # if val_lat is None or val_lon is None:
    #     st.error("❌ Coordinates not ready. Please sync GPS first.")
    #     st.stop()

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

# if not can_host:
#     st.info("Please 'Begin Setup' to enable hosting.")


# --- JOIN SECTION ---
with st.container(border=True):
    st.markdown("### Join Lobby")
    u_name = st.text_input("Username", random_u_name(), max_chars=6)
    l_code = st.text_input("Lobby Code", max_chars=6)
    if st.button("Join Game", use_container_width=True, type="primary"):
        if len(l_code) == 6:
            st.session_state.update({"login_code": l_code, "role": "player"})
            st.switch_page("pages/DJ_Deathmatch.py")
        else:
            st.warning("Please enter a valid 6-character lobby code.")
