import random
import streamlit as st
from components.assets_manager import set_png_as_page_bg, BACKGROUND_IMAGE

st.set_page_config(
    page_title="Get Started",
    page_icon="🎵",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# set_png_as_page_bg(BACKGROUND_IMAGE)

ADJECTIVES = ["Funky", "Groovy", "Blazing", "Cosmic", "Electric", "Neon", "Wild", "Hyper"]
NOUNS = ["DJ", "Beat", "Drop", "Vibe", "Wave", "Bass", "Pulse", "Rhythm"]

def random_name():
    return f"{random.choice(ADJECTIVES)}{random.choice(NOUNS)}{random.randint(10, 99)}"


st.session_state.role = None

st.title("Tune Zone")

if st.button("Host Lobby", use_container_width=True, type="primary"):
    st.session_state.role = "host"
    st.switch_page("pages/DJ_Deathmatch.py")

with st.container(border=True, horizontal_alignment="center", gap="small"):
    st.markdown("Join Lobby")
    if "default_name" not in st.session_state:
        st.session_state.default_name = random_name()
    player_name = st.text_input("Your Name", value=st.session_state.default_name)
    lobby_code = st.text_input("Lobby Code", max_chars=6)
    if st.button("Join Game", use_container_width=True, type="primary"):
        if len(lobby_code) == 6:
            st.session_state.login_code = lobby_code
            st.session_state.player_name = player_name
            st.session_state.role = "player"
            st.switch_page("pages/DJ_Deathmatch.py")
        else:
            st.error("Lobby Code must be 6 characters long")

