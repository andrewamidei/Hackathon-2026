import streamlit as st
import streamlit.components.v1 as components
import spotipy





def search_spotify_player(sp):
    search_query = st.text_input("Enter a song or artist name:")
    
    if search_query:
        results = sp.search(q=search_query, limit=5, type='track')
        
        tracks = results['tracks']['items']
            
        for track in tracks:
            track_name = track['name']
            artist_name = track['artists'][0]['name'] if track['artists'] else "Unknown Artist"
            album_url = track['album']['images'][0]['url'] if track['album']['images'] else None

            st.image(album_url, width=100)
            st.write(f"**{track_name}** by {artist_name}")
            

            if st.button("▶️ Select Music", key=track['id']):
                st.session_state.selected_track = track
                st.rerun()



def render_spotify_player(access_token, sp, selected_track):
    """
    Displays the UI for the selected track and handles playback logic.
    """
    # 1. Extract data from the SINGLE track object passed in
    track_name = selected_track['name']
    artist_name = selected_track['artists'][0]['name'] if selected_track['artists'] else "Unknown"
    track_uri = selected_track['uri']
   

    st.subheader("Now Playing")
    
    # 2. Display the UI for the selected song
    col1, col2, col3 = st.columns()
    with col2:
        st.write(f"### {track_name}")
        st.write(f"**Artist:** {artist_name}")
    
    with col3:
        if st.button("🚀 Start Playback", key="play_button_final"):
            try:
                # Find the 'Streamlit Web Player' device
                devices = sp.devices()
                target_device_id = None
                
                for device in devices.get('devices', []):
                    if device['name'] == 'Streamlit Web Player':
                        target_device_id = device['id']
                        break
                
                if target_device_id:
                    # Trigger the Spotify Playback API
                    sp.start_playback(device_id=target_device_id, uris=[track_uri])
                    st.toast(f"🎶 Playing {track_name}!")
                else:
                    st.error("Player not found. Is the JS SDK running and have you clicked the page?")
            
            except Exception as e:
                st.error(f"Playback Error: {e}")