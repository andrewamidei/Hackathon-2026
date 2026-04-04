import secrets
import threading

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/DJ", tags=["DJ"])

# ── In-memory state ─────────────────────────────────────────────────────────────

_lock = threading.Lock()

# session_id -> session dict
_sessions = {}


def _get_session(session_id: str):
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(403, "Invalid session ID")
    return session


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


# ── Host endpoints ──────────────────────────────────────────────────────────────

@router.post("/host/setup")
def setup_game(req: CreateSessionRequest):
    session_id = secrets.token_hex(16)
    with _lock:
        _sessions[session_id] = {
            "id": req.id,
            "name": req.name,
            "location": req.location,
            "status": "init",
            "song_queue": [],
            "vote_options": {},
            "players": {},
            "next_player_id": 1,
        }
    return {"ok": True, "session_id": session_id}


@router.post("/host/start")
def start_game(session_id: str = Query(...)):
    with _lock:
        session = _get_session(session_id)
        if session["status"] != "lobby":
            raise HTTPException(400, "Game is not in lobby")
        session["status"] = "active"
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
        player = session["players"].get(req.player_id)
        if player is None:
            raise HTTPException(404, "Player not found")
        player["current_vote"] = req.vote
    return {"ok": True}


# ── State endpoints ─────────────────────────────────────────────────────────────

@router.get("/state")
def get_state(session_id: str = Query(...)):
    """Player-facing: returns only the current game status."""
    with _lock:
        session = _get_session(session_id)
        return {"status": session["status"]}


@router.get("/status")
def get_status(session_id: str = Query(...)):
    """Host-facing: returns full session info including all players and votes."""
    with _lock:
        session = _get_session(session_id)
        return {
            "status": session["status"],
            "song_queue": list(session["song_queue"]),
            "vote_options": dict(session["vote_options"]),
            "players": {
                pid: {"name": p["name"], "current_vote": p["current_vote"]}
                for pid, p in session["players"].items()
            },
        }
