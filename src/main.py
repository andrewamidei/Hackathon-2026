import streamlit as st


# Import your custom function from the handler file
# from spotifyHandler import render_spotify_player
from spotifyHandler import SpotifyHandler

def main():
    
    if 'selected_track' not in st.session_state:
        st.session_state.selected_track = None
    if 'selected_sp' not in st.session_state:
        st.session_state.selected_sp = None

    SpotifyHandler.search_spotify_player()
    st.title("Spotify Player")
    if st.session_state.selected_track:
        SpotifyHandler.render_spotify_player(st.session_state.selected_track,st.session_state.selected_sp)
    
if __name__ == "__main__":
    main()