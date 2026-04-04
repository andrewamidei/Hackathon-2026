import streamlit as st


def song_input(label: str = "Enter a song", key: str = "song_input") -> str:
    """Returns the submitted song name, or None if not yet submitted.
    Submit button is hidden via CSS in the parent page — press Enter to submit."""
    with st.form(key=key, clear_on_submit=True, border=False):
        song = st.text_input(label, placeholder="Press Enter to add")
        submitted = st.form_submit_button("submit")
    if submitted and song.strip():
        return song.strip()
    return None
