import random
import threading
import time

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/DJ", tags=["DJ"])

# ── In-memory state ─────────────────────────────────────────────────────────────

_lock = threading.Lock()
_sessions = {}

SONG_DURATION = 30  # seconds per song


def _get_session(session_id: str):
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(403, "Invalid session ID")
    return session


def _play_song(session_id: str):
    """Advance to next song or pick DJs when last song starts, then vote when it ends."""
    with _lock:
        session = _sessions.get(session_id)
        if not session or session["status"] not in ("play", "pick"):
            return

        idx = session["current_song_index"]
        is_last = (idx == len(session["song_queue"]) - 1)

        if is_last:
            # Last song is now playing — pick DJs immediately
            player_ids = list(session["players"].keys())
            chosen = random.sample(player_ids, min(2, len(player_ids)))
            session["dj_player_ids"] = chosen
            session["djs"] = [session["players"][pid]["name"] for pid in chosen]
            session["dj_picks"] = {}
            session["status"] = "pick"

    # Wait for the song to finish
    time.sleep(SONG_DURATION)

    with _lock:
        session = _sessions.get(session_id)
        if not session:
            return

        if session["status"] == "pick":
            # Song ended — go to vote
            session["status"] = "vote"
        elif session["status"] == "play":
            # More songs — advance to next
            session["current_song_index"] += 1
            threading.Thread(target=_play_song, args=(session_id,), daemon=True).start()


# ── Pydantic models ─────────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    location: list
    id: int
    name: str


class JoinRequest(BaseModel):
    session_id: str
    name: str


class VoteRequest(BaseModel):
    session_id: str
    player_id: int
    vote: str


class AddSongRequest(BaseModel):
    session_id: str
    song: str


class DJPickRequest(BaseModel):
    session_id: str
    player_id: int
    song: str


# ── Host endpoints ──────────────────────────────────────────────────────────────

@router.post("/host/setup")
def setup_game(req: CreateSessionRequest):
    session_id = str(random.randint(100000, 999999))
    with _lock:
        _sessions[session_id] = {
            "id": req.id,
            "name": req.name,
            "location": req.location,
            "status": "init",
            "song_queue": [],
            "current_song_index": 0,
            "vote_options": {},
            "players": {},
            "djs": [],
            "dj_player_ids": [],
            "dj_picks": {},
            "next_player_id": 1,
        }
    return {"ok": True, "session_id": session_id}


@router.post("/host/add_song")
def add_song(req: AddSongRequest):
    """Add a song to the queue and transition to play if in init."""
    with _lock:
        session = _get_session(req.session_id)
        session["song_queue"].append(req.song)
        if session["status"] == "init":
            session["status"] = "play"
            session["current_song_index"] = 0
    if session["status"] == "play":
        threading.Thread(target=_play_song, args=(req.session_id,), daemon=True).start()
    return {"ok": True}


@router.post("/host/next_round")
def next_round(session_id: str = Query(...)):
    """Transition from vote back to play using DJ picks as the new song queue."""
    with _lock:
        session = _get_session(session_id)
        if session["status"] != "vote":
            raise HTTPException(400, "Not in vote state")
        # DJ picks become the new song queue
        new_songs = list(session["dj_picks"].values())
        session["song_queue"] = new_songs
        session["current_song_index"] = 0
        # Reset all players' votes and DJ status
        for p in session["players"].values():
            p["current_vote"] = None
        session["dj_player_ids"] = []
        session["djs"] = []
        session["dj_picks"] = {}
        session["status"] = "play"
    threading.Thread(target=_play_song, args=(session_id,), daemon=True).start()
    return {"ok": True}


@router.post("/host/end")
def end_game(session_id: str = Query(...)):
    with _lock:
        session = _get_session(session_id)
        session["status"] = "ended"
    return {"ok": True}


# ── Player endpoints ────────────────────────────────────────────────────────────

@router.post("/player/join")
def join(req: JoinRequest):
    name = req.name.strip()
    if not name:
        raise HTTPException(400, "Name cannot be empty")
    with _lock:
        session = _get_session(req.session_id)
        player_id = session["next_player_id"]
        session["next_player_id"] += 1
        session["players"][player_id] = {"name": name, "current_vote": None}
    return {"ok": True, "player_id": player_id}


@router.post("/player/vote")
def vote(req: VoteRequest):
    with _lock:
        session = _get_session(req.session_id)
        if req.player_id not in session["players"]:
            session["players"][req.player_id] = {"name": str(req.player_id), "current_vote": None}
        session["players"][req.player_id]["current_vote"] = req.vote
    return {"ok": True}


@router.post("/dj/pick")
def dj_pick(req: DJPickRequest):
    """DJ submits their song pick. Once all DJs have picked, go to vote."""
    with _lock:
        session = _get_session(req.session_id)
        if session["status"] != "pick":
            raise HTTPException(400, "Not in pick state")
        if req.player_id not in session["dj_player_ids"]:
            raise HTTPException(403, "You are not a DJ this round")
        session["dj_picks"][req.player_id] = req.song
        # All DJs submitted — go to vote
        if len(session["dj_picks"]) >= len(session["dj_player_ids"]):
            session["djs"] = list(session["dj_picks"].values())
            session["status"] = "vote"
    return {"ok": True}


# ── State endpoints ─────────────────────────────────────────────────────────────

@router.get("/state")
def get_state(session_id: str = Query(...)):
    """Player-facing: current status, DJ IDs, and vote options when relevant."""
    with _lock:
        session = _get_session(session_id)
        result = {
            "status": session["status"],
            "dj_player_ids": list(session["dj_player_ids"]),
        }
        if session["status"] == "play":
            idx = session["current_song_index"]
            if idx < len(session["song_queue"]):
                result["current_song"] = session["song_queue"][idx]
        if session["status"] in ("vote", "pick"):
            result["djs"] = list(session["djs"])
        return result


@router.get("/status")
def get_status(session_id: str = Query(...)):
    """Host-facing: full session info."""
    with _lock:
        session = _get_session(session_id)
        idx = session["current_song_index"]
        return {
            "status": session["status"],
            "song_queue": list(session["song_queue"]),
            "current_song": session["song_queue"][idx] if idx < len(session["song_queue"]) else None,
            "djs": list(session["djs"]),
            "dj_player_ids": list(session["dj_player_ids"]),
            "dj_picks": dict(session["dj_picks"]),
            "players": {
                pid: {"name": p["name"], "current_vote": p["current_vote"]}
                for pid, p in session["players"].items()
            },
        }
