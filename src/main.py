import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
import sys

load_dotenv()

st.title("Spotify Library Loader")

# 1. Force terminal output for debugging
print("\n" + "="*40, flush=True)
print("SPOTIFY AUTH PROCESS STARTING", flush=True)
print("="*40 + "\n", flush=True)

scope = "user-library-read"

# 2. Setup Auth Manager with a persistent cache path
auth_manager = SpotifyOAuth(
    scope=scope,
    open_browser=False,
    cache_path=".cache" # This saves the token to your project folder
)

sp = spotipy.Spotify(auth_manager=auth_manager)

st.write("Checking Spotify connection... (Check terminal if this spins forever)")

try:
    # This line triggers the "Enter URL" prompt in your terminal
    results = sp.current_user_saved_tracks()

    if results:
        st.subheader("Your Saved Tracks:")
        for idx, item in enumerate(results['items']):
            track = item['track']
            st.write(f"**{idx + 1}.** {track['name']} — *{track['artists'][0]['name']}*")
            
except Exception as e:
    st.error("Action Required: Please check your Docker Terminal/Logs!")
    # This print will definitely show up because of PYTHONUNBUFFERED=1
    print(f"AUTHENTICATION NEEDED: {e}", flush=True)