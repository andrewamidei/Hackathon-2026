from spotifyHandler import SpotifyHandler
import streamlit as st

# Session states
if 'login_code' not in st.session_state:
    st.session_state.login_code = None
if 'role' not in st.session_state:
    st.session_state.role = None
if 'player_name' not in st.session_state:
    st.session_state.player_name = None
if 'session_id' not in st.session_state:
    st.session_state.session_id

# if 'message_input' not in st.session_state:
#     st.session_state.message_input = ""

st.switch_page("pages/homepage.py")

# Import your custom function from the handler file
# from spotifyHandler import render_spotify_player


def main():

    if 'selected_track' not in st.session_state:
        st.session_state.selected_track = None
    if 'selected_sp' not in st.session_state:
        st.session_state.selected_sp = None

    SpotifyHandler.search_spotify_player()
    st.title("Spotify Player")
    if st.session_state.selected_track:
        SpotifyHandler.render_spotify_player(st.session_state.selected_track, st.session_state.selected_sp)


if __name__ == "__main__":
    main()

