import streamlit as st
import streamlit.components.v1 as components
import spotipy
from spotipy.oauth2 import SpotifyOAuth

scope = "streaming user-read-email user-read-private user-read-playback-state user-modify-playback-state"
sp_oauth = SpotifyOAuth(scope=scope)
token_info = sp_oauth.get_cached_token()
class SpotifyHandler:

    
    def get_spotify_client():
        

        
        if "code" in st.query_params:
            auth_code = st.query_params["code"]
            token_info = sp_oauth.get_access_token(auth_code)
            st.query_params.clear() # Clean the URL
            st.rerun()

        if not token_info:
            st.title("Spotify Streamlit Player")
            auth_url = sp_oauth.get_authorize_url()
            st.markdown(f"Please [log in to Spotify]({auth_url}) to use the music features.")
            st.stop() # Halt execution until they log in'
        
        st.session_state.keyToken = token_info
        access_token = token_info['access_token']
        sp = spotipy.Spotify(auth=access_token)
        return sp

    def render_spotify_player(selected_track,sp):


        devices = sp.devices()
        target_device_id = None
        
        for device in devices.get('devices', []):
            if device['name'] == 'Streamlit Web Player':
                target_device_id = device['id']
                break
        
        if target_device_id:
            sp.pause_playback(device_id=target_device_id) 
        
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

