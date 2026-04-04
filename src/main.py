import streamlit as st


# Import your custom function from the handler file
# from spotifyHandler import render_spotify_player
from spotifyHandler import search_spotify_player, render_spotify_player

def main():
    
    if 'selected_track' not in st.session_state:
        st.session_state.selected_track = None


    search_spotify_player()
    st.title("Spotify Player")
    if st.session_state.selected_track:
        render_spotify_player(st.session_state.selected_track)
        pass
    
if __name__ == "__main__":
    main()