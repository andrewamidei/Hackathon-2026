import random
import streamlit as st
from streamlit_js_eval import get_geolocation

# 1. MUST BE FIRST
st.set_page_config(page_title="Get Started", page_icon="🎵", layout="centered")

# --- DJ Logic ---


def random_name():
    adj = ["Funky", "Groovy", "Blazing", "Cosmic", "Neon"]
    noun = ["DJ", "Beat", "Drop", "Vibe", "Wave"]
    return f"{random.choice(adj)}{random.choice(noun)}{random.randint(10, 99)}"


# 2. SESSION STATE INITIALIZATION
if 'loc_requested' not in st.session_state:
    st.session_state.loc_requested = False
if 'final_coords' not in st.session_state:
    st.session_state.final_coords = None
if 'manual_mode' not in st.session_state:
    st.session_state.manual_mode = False

st.title("🎧 DJ Booth")

# 3. THE DIALOG (Standard Popup)


@st.dialog("Sync Location")
def location_dialog():
    st.write("Establish satellite uplink to find your local vibe.")

    if st.button("🛰️ Sync GPS", use_container_width=True, type="primary"):
        st.session_state.loc_requested = True
        st.rerun()

    if st.button("⌨️ Manual Entry", use_container_width=True):
        st.session_state.manual_mode = True
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
if not st.session_state.final_coords and not st.session_state.manual_mode:
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

# Case B: Manual Entry
if st.session_state.manual_mode and not st.session_state.final_coords:
    st.warning("GPS Bypassed.")
    loc_code = st.text_input("Enter Location Code")
    if loc_code:
        st.success(f"Location set: {loc_code}")
        if "dj_name" not in st.session_state:
            st.session_state.dj_name = random_name()

st.divider()

# --- LOBBY CODE ---
st.title("Tune Zone")
if st.button("Host Lobby", use_container_width=True):
    st.session_state.role = "host"
    st.switch_page("pages/init.py")

with st.container(border=True):
    st.markdown("### Join Lobby")
    player_name = st.text_input("Your Name", value=st.session_state.get("dj_name", "Enter Name"))
    lobby_code = st.text_input("Lobby Code", max_chars=6)
    if st.button("Join Game", use_container_width=True):
        if len(lobby_code) == 6:
            st.session_state.update({"login_code": lobby_code, "player_name": player_name, "role": "player"})
            st.switch_page("pages/DJ_Deathmatch.py")
        else:
            st.error("Code must be 6 chars.")




