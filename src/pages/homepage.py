import json
import random
import string
import streamlit as st
from streamlit_js_eval import streamlit_js_eval
# from handlers.database import DatabaseManager


st.set_page_config(page_title="DJ Booth", layout="centered")
# dbm = DatabaseManager()

# --- DJ Logic ---

def gen_code():
    first = random.choice(string.ascii_uppercase)
    rest = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return first + rest

def random_u_name():
    adj = ["Funky", "Groovy", "Blazing", "Cosmic", "Electric", "Neon", "Wild", "Hyper"]
    noun = ["DJ", "Beat", "Drop", "Vibe", "Wave", "Bass", "Pulse", "Rhythm"]
    while True:
        name = f"{random.choice(adj)}{random.choice(noun)}{random.randint(10, 99)}"
        if name not in st.session_state.used_names:
            st.session_state.used_names.add(name)
            return name

# --- SESSION STATE DEFAULTS ---
for key, default in {
    "lat": None,
    "lon": None,
    "loc_req": False,
    "used_names": set(),
}.items():
    if key not in st.session_state:
        st.session_state[key] = default
#
# ROOT CAUSE OF THE BUG:
# get_geolocation() from streamlit_js_eval registers a *persistent* Streamlit
# component that keeps firing on every rerun, returning its internal numeric
# component ID (e.g. 905706) before real GPS data arrives. That ID was being
# treated as a session_id and written to the DB.
#
# FIX: Use streamlit_js_eval() with a JS Promise directly. This only runs
# when the block is entered (loc_req=True), and returns exactly once.

# if st.session_state.loc_req and st.session_state.lat is None:
#     st.info("📡 Acquiring GPS signal...")

#     result = streamlit_js_eval(
#         js_expressions="""
#             new Promise((resolve) => {
#                 navigator.geolocation.getCurrentPosition(
#                     (pos) => resolve(JSON.stringify({
#                         lat: pos.coords.latitude,
#                         lon: pos.coords.longitude
#                     })),
#                     (err) => resolve(null),
#                     {enableHighAccuracy: true, timeout: 10000}
#                 );
#             })
#         """,
#         key="gps_eval",
#     )

#     if result is None:
#         st.info("🛰️ Waiting for browser GPS permission...")
#     elif result == "null" or result is False:
#         st.error("❌ GPS denied or unavailable. Please allow location access.")
#         st.session_state.loc_req = False
#     else:
#         try:
#             coords = json.loads(result)
#             lat = coords.get("lat")
#             lon = coords.get("lon")
#             # Must be real floats — reject nulls and the (0, 0) null island
#             if (
#                 lat is not None
#                 and lon is not None
#                 and isinstance(lat, (int, float))
#                 and isinstance(lon, (int, float))
#                 and not (-0.001 < lat < 0.001 and -0.001 < lon < 0.001)
#             ):
#                 st.session_state.lat = float(lat)
#                 st.session_state.lon = float(lon)
#                 st.session_state.loc_req = False
#                 st.rerun()
#             else:
#                 st.warning("📡 Got invalid coordinates, retrying...")
#         except Exception:
#             st.warning("📡 Parsing GPS response...")


# # --- UI STATUS ---
# if st.session_state.lat is None:
#     list1: [str] = ""
#     if st.button("Begin Setup", use_container_width=True, type="primary"):
#         st.session_state.loc_req = True
#         list1 = db.query_nearest((st.session_state.lat, st.session_state.lon))

#         st.rerun()
# else:
#     st.success(f"📍 Position Locked.: {st.session_state.lat:.4f}, {st.session_state.lon:.4f}")
#     st.write("hello")
#     if (list1): st.write(f"a list of things: {list1}")
#     if st.button("Reset GPS"):
#         st.session_state.lat = None
#         st.session_state.lon = None
#         st.session_state.loc_req = False
        
#         st.rerun()

# st.divider()

# # --- HOST SECTION ---
# st.title("Tune Zone")

# can_host = st.session_state.lat is not None and st.session_state.lon is not None

# if st.button("Host Lobby", use_container_width=True, type="primary", disabled=not can_host):
#     val_lat = st.session_state.lat
#     val_lon = st.session_state.lon

#     # Absolute last-line defense — never write NULLs to the DB
#     if val_lat is None or val_lon is None:
#         st.error("❌ No coordinates. Please sync GPS first.")
#         st.stop()

    lobby_id = gen_code()

    try:
        dbm.add_host(entry=(lobby_id, (0, 0)), table_name="sessions")
        st.session_state.update({
            "role": "host",
            "lobby_code": lobby_id,
            "lat": 0,
            "lon": 0,
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
            st.session_state.update({"login_code": l_code, "role": "player"})
            st.switch_page("pages/DJ_Deathmatch.py")
        else:
            st.warning("Please enter a valid 6-character lobby code.")