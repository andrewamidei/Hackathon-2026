import random
import streamlit as st
# from components.assets_manager import set_png_as_page_bg, BACKGROUND_IMAGE
from streamlit_js_eval import get_geolocation

st.set_page_config(page_title="Get Started", page_icon="🎵", layout="centered")

# --- DJ Logic ---
def random_name():
    adj = ["Funky", "Groovy", "Blazing", "Cosmic", "Neon"]
    noun = ["DJ", "Beat", "Drop", "Vibe", "Wave"]
    return f"{random.choice(adj)}{random.choice(noun)}{random.randint(10, 99)}"


# GPS Session State
if 'loc_requested' not in st.session_state:
    st.session_state.loc_requested = False
if 'final_coords' not in st.session_state:
    st.session_state.final_coords = None


# set_png_as_page_bg(BACKGROUND_IMAGE)

st.title("Tune Zone")

# THE DIALOG (Standard Popup)
@st.dialog("Sync Location")
def location_dialog():
    st.write("Establish satellite uplink to find your local vibe.")

    if st.button("🛰️ Sync GPS", use_container_width=True, type="primary"):
        st.session_state.loc_requested = True
        st.rerun()

# 4. THE CAPTURE LOGIC (The "Fix")
# If the user clicked 'Sync GPS', we run this block until we get data
if st.session_state.loc_requested and st.session_state.final_coords is None:
    # This line triggers the JS. It returns None at first, then the dict later.
    report = get_geolocation()

    if report:
        st.session_state.final_coords = report
        st.session_state.loc_requested = False  # Stop requesting
        st.rerun()  # Refresh to show the success UI
    else:
        # We show a spinner to let the user know we are waiting on the browser
        st.info("🛰️ Awaiting satellite response... Please check for a browser permission popup.")
        # Streamlit-js-eval usually triggers a rerun automatically when data arrives,
        # but if it hangs, the user just needs to wait a second.

# 5. MAIN UI LOGIC
if not st.session_state.final_coords:
    if st.button("Begin Setup", use_container_width=True, type="primary"):
        location_dialog()

# Case A: GPS Success
if st.session_state.final_coords:
    coords = st.session_state.final_coords.get('coords', {})
    lat = coords.get('latitude')
    lon = coords.get('longitude')

    if lat and lon:
        st.success(f"📍 Position Locked: {lat:.4f}, {lon:.4f}")
        if "dj_name" not in st.session_state:
            st.session_state.dj_name = random_name()
        st.info(f"Identity Assigned: **{st.session_state.dj_name}**")

        if st.button("Reset Location"):
            st.session_state.final_coords = None
            st.rerun()

st.divider()

# --- LOBBY CODE ---
if st.button("Host Lobby", use_container_width=True):
    st.session_state.role = "host"
    st.switch_page("pages/init.py")

can_host = st.session_state.lat is not None and st.session_state.lon is not None

if st.button("Host Lobby", use_container_width=True, type="primary", disabled=not can_host):
    val_lat = st.session_state.lat
    val_lon = st.session_state.lon

    # Absolute last-line defense — never write NULLs to the DB
    if val_lat is None or val_lon is None:
        st.error("❌ No coordinates. Please sync GPS first.")
        st.stop()

    lobby_id = gen_code()

    try:
        dbm.add_host(entry=(lobby_id, (val_lat, val_lon)), table_name="sessions")
        st.session_state.update({
            "role": "host",
            "lobby_code": lobby_id,
            "lat": val_lat,
            "lon": val_lon,
        })
        st.switch_page("pages/DJ_Deathmatch.py")
    except Exception as e:
        st.error(f"❌ DB Error: {e}")

if not can_host:
    st.info("Please 'Begin Setup' to enable hosting.")


# --- JOIN SECTION ---
with st.container(border=True):
    st.markdown("### Join Lobby")
    player_name = st.text_input("Your Name", value=st.session_state.get("dj_name", "Enter Name"))
    lobby_code = st.text_input("Lobby Code", max_chars=6)
    if st.button("Join Game", use_container_width=True):
        if len(l_code) == 6:
            st.session_state.update({"login_code": l_code, "role": "player"})
            st.switch_page("pages/DJ_Deathmatch.py")
        else:
            st.error("Code must be 6 chars.")




