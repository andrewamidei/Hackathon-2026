import streamlit as st
import streamlit.components.v1 as components
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from components.spotifyHandler import SpotifyHandler

class SpotifyComponents:

    def search_spotify_player():
        # --- Get Spotify client ---
        sp = SpotifyHandler.get_spotify_client()
        if not sp:
            st.info("Spotify client not ready. Please log in.")
            return
        print("Spotify client ready! You can search for tracks now.", icon="✅")
        # --- Search input ---
        search_query = st.text_input("Enter a song or artist name:")
        print("Spotify client ready! You can search for tracks now.", icon="✅")
        if search_query:
            results = sp.search(q=search_query, limit=5, type='track')
            tracks = results['tracks']['items']
                
            for track in tracks:
                track_name = track['name']
                artist_name = track['artists'][0]['name'] if track['artists'] else "Unknown Artist"
                album_url = track['album']['images'][0]['url'] if track['album']['images'] else None

                col1, col2 = st.columns(2)
                with col1:
                    st.image(album_url, width=100)
                with col2:
                    st.write(f"**{track_name}** by {artist_name}")
                    if st.button("▶️ Select Music", key=track['id']): 
                        st.session_state.selected_track = track
                        st.session_state.selected_sp = sp
                        st.rerun()

  