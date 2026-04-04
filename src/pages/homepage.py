import streamlit as st

st.set_page_config(
    page_title="Get Started",
    page_icon="🎵",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("Tune Zone")

if st.button("Host Lobby", use_container_width=True):
    st.session_state.role = "host"
    st.switch_page("pages/host_page.py")

with st.container(border=True, horizontal_alignment="center",gap="small"):
    st.markdown("Join Lobby")
    lobby_code = st.text_input("Lobby Code", max_chars=6)
    if st.button("Join Game", use_container_width=True):
        if (len(lobby_code) == 6):
            st.session_state.login_code = lobby_code
            st.session_state.role = "player"
            st.switch_page("pages/player_page.py")
        else:
            st.error("Lobby Code must be 6 characters long")

