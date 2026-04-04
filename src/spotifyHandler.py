import streamlit as st
import streamlit.components.v1 as components
import spotipy
from spotipy.oauth2 import SpotifyOAuth

scope = "streaming user-read-email user-read-private user-read-playback-state user-modify-playback-state"
sp_oauth = SpotifyOAuth(scope=scope)
token_info = sp_oauth.get_cached_token()

access_token = token_info['access_token']
sp = spotipy.Spotify(auth=access_token)

def search_spotify_player():
    if token_info:

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

                    devices = sp.devices()
                    target_device_id = None 
                    for device in devices.get('devices', []):
                        if device['name'] == 'Streamlit Web Player':
                            target_device_id = device['id']
                            break
                    
                    if target_device_id:
                        sp.pause_playback(device_id=target_device_id) 
               
                    st.session_state.selected_track = track
                    st.rerun()
    else:
        st.warning("Please authenticate with Spotify.")
        



def render_spotify_player(selected_track):
     
    if token_info:
        access_token = token_info['access_token']
        
        # --- THE JS SDK ENGINE (The "Speaker") ---
        # This MUST be rendered so the browser creates the device
        player_html = f"""
        <script src="https://sdk.scdn.co/spotify-player.js"></script>
        <script>
            window.onSpotifyWebPlaybackSDKReady = () => {{
                const player = new Spotify.Player({{
                    name: 'Streamlit Web Player',
                    getOAuthToken: cb => {{ cb('{access_token}'); }},
                    volume: 0.5
                }});
                player.addListener('ready', ({{ device_id }}) => {{
                    console.log('Connected with Device ID', device_id);
                }});
                player.connect();
            }};
        </script>
        <div style="background: #191414; color: #1DB954; padding: 10px; text-align: center; border-radius: 5px;">
            🎧 Web Player Active (Click page to enable audio)
        </div>
        """
        components.html(player_html, height=60)

        track_name = selected_track['name']
        artist_name = selected_track['artists'][0]['name'] if selected_track['artists'] else "Unknown"
        track_uri = selected_track['uri']

        st.subheader("Now Playing")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"### {track_name}")
            st.write(f"**Artist:** {artist_name}")
        
        with col2:
            if st.button("🚀 Start Playback", key="play_button_final"):
                try:
                    # Now sp.devices() will actually see the 'Streamlit Web Player'
                    devices = sp.devices()
                    target_device_id = None
                    
                    for device in devices.get('devices', []):
                        if device['name'] == 'Streamlit Web Player':
                            target_device_id = device['id']
                            break
                    
                    if target_device_id:
                        sp.start_playback(device_id=target_device_id, uris=[track_uri])
                        st.toast(f"🎶 Playing {track_name}!")
                    else:
                        st.error("Player not found. Did you click the page to 'wake up' the browser audio?")
                
                except Exception as e:
                    st.error(f"Playback Error: {e}")
    else:
        st.warning("Please authenticate with Spotify.")