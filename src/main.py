import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Import your custom function from the handler file
# from spotifyHandler import render_spotify_player
from spotifyHandler import search_spotify_player, render_spotify_player

def main():
    
    if 'selected_track' not in st.session_state:
        st.session_state.selected_track = None

    scope = "streaming user-read-email user-read-private user-read-playback-state user-modify-playback-state"
    sp_oauth = SpotifyOAuth(scope=scope)
    
    token_info = sp_oauth.get_cached_token()
    
    if token_info:
        access_token = token_info['access_token']
        sp = spotipy.Spotify(auth=access_token)
        

        search_spotify_player(sp)
        st.title(st.session_state.selected_track['name'] if st.session_state.selected_track else "No track selected")
        if st.session_state.selected_track:
            # render_spotify_player(access_token, sp, st.session_state.selected_track)
            pass
    else:
        st.warning("Please authenticate with Spotify.")
        # Optional: Add a login button/link here based on sp_oauth.get_authorize_url()

if __name__ == "__main__":
    main()