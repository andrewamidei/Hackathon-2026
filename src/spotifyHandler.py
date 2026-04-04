"""
spotifyHandler.py

Module-level _oauth and _token_info mirror the original working pattern:
  - _oauth is created once at import time and reused for all calls so that
    spotipy's disk cache (.cache file) is read and written correctly.
  - _token_info starts from the cached token (if any) so the host stays
    logged in across Streamlit reruns and OAuth redirects without needing
    st.session_state.
  - UI code lives in DJ_Deathmatch.py; this file has no Streamlit imports.
"""

from typing import Optional
import spotipy
from spotipy.oauth2 import SpotifyOAuth

SCOPE = (
    "streaming "
    "user-read-email "
    "user-read-private "
    "user-read-playback-state "
    "user-modify-playback-state"
)

PLAYER_NAME = "DJ Deathmatch Player"

# Module-level — created once per worker process, survives Streamlit reruns.
_oauth      = SpotifyOAuth(scope=SCOPE)
_token_info = _oauth.get_cached_token()   # None if no cache yet; populated after auth


# ── Auth ──────────────────────────────────────────────────────────────────────────

def get_auth_url(session_id: str) -> str:
    """Return the Spotify authorization URL.
    session_id is encoded in the OAuth state param so the page can restore
    the host's game session after the browser redirect wipes st.session_state."""
    return _oauth.get_authorize_url(state=f"sid={session_id}")


def handle_callback(code: str) -> None:
    """Exchange the OAuth code for a token and cache it.
    Call this when ?code= appears in st.query_params."""
    global _token_info
    _token_info = _oauth.get_access_token(code, as_dict=True)

def get_current_track_name() -> Optional[str]:
    """
    Returns only the name of the currently playing track.
    Returns None if no track is playing.
    """
    try:
        sp = get_client()
        playback = sp.current_playback()
        if playback and playback.get("item"):
            return playback["item"]["name"]
        return None
    except Exception as e:
        print(f"Error fetching track name: {e}")
        return None

def is_authenticated() -> bool:
    return _token_info is not None

def get_queue_size() -> int:
    """
    Returns the number of tracks currently in the Spotify queue 
    (excluding the currently playing track).
    """
    try:
        sp = get_client()
        queue_data = sp.queue()
        if queue_data and "queue" in queue_data:
            return len(queue_data["queue"])
        return 0
    except Exception as e:
        print(f"Error fetching queue size: {e}")
        return 0

def get_client() -> spotipy.Spotify:
    """Return a ready Spotify client, refreshing the token if needed."""
    global _token_info
    if _token_info is None:
        raise RuntimeError("Not authenticated — call handle_callback first")
    if _oauth.is_token_expired(_token_info):
        _token_info = _oauth.refresh_access_token(_token_info["refresh_token"])
    return spotipy.Spotify(auth=_token_info["access_token"])


def get_access_token() -> str:
    """Return the current access token (refreshing if needed). Used to boot the SDK."""
    get_client()   # ensures token is fresh and _token_info is updated
    return _token_info["access_token"]


# ── Search & playback ─────────────────────────────────────────────────────────────

def search_tracks(query: str, limit: int = 5) -> list[dict]:
    """Search Spotify. Returns simplified dicts: {id, uri, name, artist, album_art}."""
    sp      = get_client()
    results = sp.search(q=query, limit=limit, type="track")
    tracks  = []
    for t in results["tracks"]["items"]:
        tracks.append({
            "id":        t["id"],
            "uri":       t["uri"],
            "name":      t["name"],
            "artist":    t["artists"][0]["name"] if t["artists"] else "Unknown",
            "album_art": t["album"]["images"][0]["url"] if t["album"]["images"] else None,
        })
    return tracks


def get_player_device_id() -> Optional[str]:
    """Find the DJ Deathmatch web player in the user's active device list."""
    sp = get_client()
    for device in sp.devices().get("devices", []):
        if device["name"] == PLAYER_NAME:
            return device["id"]
    return None


def play_track(track_uri: str, device_id: str) -> bool:
    """Start playback of track_uri on device_id. Returns True on success."""
    try:
        get_client().start_playback(device_id=device_id, uris=[track_uri])
        return True
    except Exception:
        return False


def pause(device_id: str) -> bool:
    """Pause playback. Returns True on success."""
    try:
        get_client().pause_playback(device_id=device_id)
        return True
    except Exception:
        return False


def player_html() -> str:
    """HTML/JS that boots the Spotify Web Playback SDK in the browser.
    Inject once per host page load via st.components.v1.html(..., height=50)."""
    token = get_access_token()
    return f"""
    <script src="https://sdk.scdn.co/spotify-player.js"></script>
    <script>
        window.onSpotifyWebPlaybackSDKReady = () => {{
            const player = new Spotify.Player({{
                name: '{PLAYER_NAME}',
                getOAuthToken: cb => {{ cb('{token}'); }},
                volume: 0.8
            }});
            player.addListener('ready', ({{ device_id }}) => {{
                console.log('[DJ Deathmatch] Spotify ready, device_id:', device_id);
            }});
            player.addListener('not_ready', ({{ device_id }}) => {{
                console.warn('[DJ Deathmatch] Spotify offline, device_id:', device_id);
            }});
            player.connect();
        }};
    </script>
    """


def search_and_add_to_queue(query: str, device_id: Optional[str] = None) -> bool:
    """
    Takes a string, searches Spotify for the top result, and adds it to the queue.
    """
    try:
        sp = get_client()
        # Search for the track
        results = sp.search(q=query, limit=1, type="track")
        items = results.get("tracks", {}).get("items", [])
        
        if not items:
            print(f"No results found for: {query}")
            return False
            
        track_uri = items[0]["uri"]
        
        # If no device_id provided, try to find the DJ Deathmatch player
        if not device_id:
            device_id = get_player_device_id()
            
        if device_id:
            sp.add_to_queue(uri=track_uri, device_id=device_id)
            return True
        return False
    except Exception as e:
        print(f"Error in search_and_add_to_queue: {e}")
        return False

def add_to_queue(track_uri: str, device_id: str) -> bool:
    """Adds a specific URI to the Spotify queue."""
    try:
        get_client().add_to_queue(uri=track_uri, device_id=device_id)
        return True
    except Exception:
        return False