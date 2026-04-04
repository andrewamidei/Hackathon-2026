import streamlit as st


def song_input(label: str = "Enter a song", key: str = "song_input") -> str:
    """Returns the submitted song name, or None if not yet submitted."""
    with st.form(key=key, clear_on_submit=True):
        song = st.text_input(label)
        submitted = st.form_submit_button("Submit")
    if submitted and song.strip():
        return song.strip()
    return None
