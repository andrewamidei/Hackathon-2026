import os

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")

def api_get(path: str):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=3)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None
    
game = api_get("/DJ/status")

st.markdown(game)

if game is None:
    st.error("Cannot reach the game API. Is it running?")
    st.stop()


st.title("Host view")

def lobby_info(join_code, player_count):
    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.metric("Players", player_count)
    
    with col2:
        with st.container(border=True):
            st.metric("Join Code", join_code)

    st.info("Player1 and Player2 Are the Selected DJ's")


def song_card(image, title, artist):
    col1, col2 = st.columns([2,4])

    with col1:
        st.image(image, width=200)

    with col2:
        st.markdown("")
        st.markdown(f"### {title}")
        st.markdown(artist)

def song_queue(image, title, artist, player):
    with st.container(border=True):
        col1, col2 = st.columns([2,10], vertical_alignment="center")

        with col1:
            st.image(image, width=70)

        with col2:
            st.markdown(f"**{title}** | {artist}")
            st.caption(f"Picked by {player}")

image = "https://cdn1.byjus.com/wp-content/uploads/2020/08/ShapeArtboard-1-copy-4.png"
title = "the title"
artist = "the artist"
player = "Player2"
player_count = 11
join_code = 110294

lobby_info(join_code, player_count)

song_card(image, title, artist)

st.markdown("### Up Next")
song_queue(image, title, artist, player)
song_queue(image, title, artist, player)

