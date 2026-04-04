import streamlit as st
import pandas as pd
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

st.title("Hello World test")
st.title("Hello World test")
st.title("Hello World")

scope = "user-library-read"

# Make sure your .env variables from earlier are still active!
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

results = sp.current_user_saved_tracks()

# Display the tracks
for idx, item in enumerate(results['items']):
    track = item['track']
    artist_name = track['artists'][0]['name']
    track_name = track['name']
    
    # FORMATTED FIX: Passed as a single string
    st.text(f"{idx + 1}. {artist_name} – {track_name}")

