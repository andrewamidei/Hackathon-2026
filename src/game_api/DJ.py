import random
import threading
import time
from handlers.database import DatabaseManager
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import os

url = os.getenv("DATABASE_URL", "postgresql+psycopg://myuser:mypassword@db:5432/mydatabase")
router = APIRouter(prefix="/DJ", tags=["DJ"])
db_manager = DatabaseManager(url=url)

# ── In-memory state ─────────────────────────────────────────────────────────────

_lock = threading.Lock()
_sessions = {}

SONG_DURATION = 10   # seconds a song plays
VOTE_DURATION = 30   # seconds players have to vote
MAX_DJ_SONGS  = 3


def _get_session(session_id: str):
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(403, "Invalid session ID")
    return session


def _build_dj_vote_options(session):
    return [
        {
            "player_id": pid,
            "name": session["players"][pid]["name"],
            "songs": list(session["dj_picks"].get(pid, [])),
            "finalized": pid in session["dj_finalized"],
            "song_count": len(session["dj_picks"].get(pid, [])),
        }
        for pid in session["dj_player_ids"]
        if pid in session["players"]
    ]


def _transition_to_next_round(session):
    """Tally votes and mutate session to play state.
    Must be called while holding _lock. Caller starts _play_song thread after."""
    vote_counts: dict[str, int] = {}
    for p in session["players"].values():
        v = p.get("current_vote")
        if v:
            vote_counts[v] = vote_counts.get(v, 0) + 1

    winner_pid = None
    if vote_counts:
        winning_name = max(vote_counts, key=vote_counts.get)
        for pid in session["dj_player_ids"]:
            if session["players"].get(pid, {}).get("name") == winning_name:
                winner_pid = pid
                break

    if winner_pid is None and session["dj_player_ids"]:
        winner_pid = random.choice(session["dj_player_ids"])

    if winner_pid is not None and session["dj_picks"].get(winner_pid):
        new_songs = list(session["dj_picks"][winner_pid])
    else:
        new_songs = list(session["song_queue"])

    session["song_queue"] = new_songs
    session["current_song_index"] = 0
    for p in session["players"].values():
        p["current_vote"] = None
    session["dj_player_ids"] = []
    session["dj_picks"] = {}
    session["dj_finalized"] = []
    session["vote_deadline"] = None
    session["status"] = "play"


def _vote_timer(session_id: str, deadline: float):
    """Auto-advance from vote to play when the vote timer expires."""
    time.sleep(max(0, deadline - time.time()))
    should_play = False
    with _lock:
        session = _sessions.get(session_id)
        # Only fire if still in vote and this is still the active deadline
        if session and session["status"] == "vote" and session.get("vote_deadline") == deadline:
            _transition_to_next_round(session)
            should_play = True
    if should_play:
        threading.Thread(target=_play_song, args=(session_id,), daemon=True).start()


def _start_vote(session, session_id: str):
    """Set vote deadline and kick off timer. Must be called while holding _lock."""
    deadline = time.time() + VOTE_DURATION
    session["vote_deadline"] = deadline
    session["status"] = "vote"
    # Timer thread is started after releasing lock by the caller
    return deadline


def _play_song(session_id: str):
    """Called when a new song starts playing.
    If this is the last song, DJs are selected immediately so they can start picking
    while the song plays. After SONG_DURATION the thread ends (DJs drive the next transition)."""
    is_last = False

    with _lock:
        session = _sessions.get(session_id)
        if not session or session["status"] != "play":
            return

        queue = session["song_queue"]
        if not queue:
            return

        idx = session["current_song_index"]
        is_last = (idx >= len(queue) - 1)

        if is_last:
            # Last song is NOW starting — select DJs immediately
            player_ids = list(session["players"].keys())
            if not player_ids:
                return
            chosen = random.sample(player_ids, min(2, len(player_ids)))
            session["dj_player_ids"] = chosen
            session["dj_picks"] = {pid: [] for pid in chosen}
            session["dj_finalized"] = []
            session["status"] = "pick"

    # Song plays for full duration regardless
    time.sleep(SONG_DURATION)

    if not is_last:
        with _lock:
            session = _sessions.get(session_id)
            if not session or session["status"] != "play":
                return
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
    vote: str  # DJ name


class AddSongRequest(BaseModel):
    session_id: str
    song: str


class DJPickRequest(BaseModel):
    session_id: str
    player_id: int
    song: str


class DJFinalizeRequest(BaseModel):
    session_id: str
    player_id: int


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
            "players": {},
            "dj_player_ids": [],
            "dj_picks": {},      # {player_id: [song1, song2, ...]}
            "dj_finalized": [],  # [player_id, ...]
            "vote_deadline": None,
            "next_player_id": 1,
        }
        location = req.location if req.location else None
        db_manager.add_host((session_id, location))
    return {"ok": True, "session_id": session_id}


@router.post("/host/add_song")
def add_song(req: AddSongRequest):
    """Add a song to the queue. Starts play on the first song added."""
    should_start = False
    with _lock:
        session = _get_session(req.session_id)
        session["song_queue"].append(req.song)
        if session["status"] == "init":
            session["status"] = "play"
            session["current_song_index"] = 0
            should_start = True
    if should_start:
        threading.Thread(target=_play_song, args=(req.session_id,), daemon=True).start()
    return {"ok": True}


@router.post("/host/next_round")
def next_round(session_id: str = Query(...)):
    """Host manually ends voting early and starts next round."""
    with _lock:
        session = _get_session(session_id)
        if session["status"] != "vote":
            raise HTTPException(400, "Not in vote state")
        _transition_to_next_round(session)
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
    """DJ adds one song to their picks (up to MAX_DJ_SONGS)."""
    with _lock:
        session = _get_session(req.session_id)
        if session["status"] != "pick":
            raise HTTPException(400, "Not in pick state")
        if req.player_id not in session["dj_player_ids"]:
            raise HTTPException(403, "You are not a DJ this round")
        if req.player_id in session["dj_finalized"]:
            raise HTTPException(400, "You have already finalized your picks")
        picks = session["dj_picks"].setdefault(req.player_id, [])
        if len(picks) >= MAX_DJ_SONGS:
            raise HTTPException(400, f"Maximum {MAX_DJ_SONGS} songs allowed")
        picks.append(req.song)
    return {"ok": True}


@router.post("/dj/finalize")
def dj_finalize(req: DJFinalizeRequest):
    """DJ finalizes picks. When all DJs finalize, start vote timer."""
    deadline = None
    with _lock:
        session = _get_session(req.session_id)
        if session["status"] != "pick":
            raise HTTPException(400, "Not in pick state")
        if req.player_id not in session["dj_player_ids"]:
            raise HTTPException(403, "You are not a DJ this round")
        if not session["dj_picks"].get(req.player_id):
            raise HTTPException(400, "Pick at least one song before finalizing")
        if req.player_id not in session["dj_finalized"]:
            session["dj_finalized"].append(req.player_id)
        if len(session["dj_finalized"]) >= len(session["dj_player_ids"]):
            deadline = _start_vote(session, req.session_id)
    if deadline is not None:
        threading.Thread(target=_vote_timer, args=(req.session_id, deadline), daemon=True).start()
    return {"ok": True}


# ── State endpoints ─────────────────────────────────────────────────────────────

@router.get("/state")
def get_state(session_id: str = Query(...)):
    """Player-facing state."""
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
            result["dj_vote_options"] = _build_dj_vote_options(session)
        if session["status"] == "vote":
            deadline = session.get("vote_deadline")
            result["vote_time_remaining"] = max(0, int(deadline - time.time())) if deadline else 0
            result["vote_duration"] = VOTE_DURATION
        return result


@router.get("/status")
def get_status(session_id: str = Query(...)):
    """Host-facing full state."""
    with _lock:
        session = _get_session(session_id)
        idx = session["current_song_index"]
        result = {
            "status": session["status"],
            "song_queue": list(session["song_queue"]),
            "current_song": session["song_queue"][idx] if idx < len(session["song_queue"]) else None,
            "dj_player_ids": list(session["dj_player_ids"]),
            "players": {
                str(pid): {"name": p["name"], "current_vote": p["current_vote"]}
                for pid, p in session["players"].items()
            },
        }
        if session["status"] in ("vote", "pick"):
            result["dj_vote_options"] = _build_dj_vote_options(session)
        if session["status"] == "vote":
            deadline = session.get("vote_deadline")
            result["vote_time_remaining"] = max(0, int(deadline - time.time())) if deadline else 0
            result["vote_duration"] = VOTE_DURATION
        return result
