import os
import random
import threading
import time

from fastapi import APIRouter, HTTPException, Query
from handlers.database import DatabaseManager
from pydantic import BaseModel

url = os.getenv("DATABASE_URL", "postgresql+psycopg://myuser:mypassword@db:5432/mydatabase")
router = APIRouter(prefix="/DJ", tags=["DJ"])
db_manager = DatabaseManager(url=url)

_lock = threading.Lock()
_sessions: dict = {}

SONG_DURATION = 10   # seconds per song
PICK_DURATION = 60   # seconds DJs have to submit songs
VOTE_DURATION = 30   # seconds for the vote window
MAX_DJ_SONGS  = 3


# ── Internal helpers ─────────────────────────────────────────────────────────────

def _get_session(session_id: str) -> dict:
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=403, detail="Invalid session ID")
    return session


def _current_song(session: dict):
    idx = session["current_song_index"]
    q   = session["song_queue"]
    return q[idx] if idx < len(q) else None


def _build_dj_vote_options(session: dict) -> list:
    return [
        {
            "player_id": pid,
            "name":       session["players"][pid]["name"],
            "songs":      list(session["dj_picks"].get(pid, [])),
            "finalized":  pid in session["dj_finalized"],
            "song_count": len(session["dj_picks"].get(pid, [])),
        }
        for pid in session["dj_player_ids"]
        if pid in session["players"]
    ]


def _tally_winner(session: dict) -> int | None:
    counts: dict[str, int] = {}
    for p in session["players"].values():
        v = p.get("current_vote")
        if v:
            counts[v] = counts.get(v, 0) + 1
    if not counts:
        return None
    winning_name = max(counts, key=counts.get)
    for pid in session["dj_player_ids"]:
        if session["players"].get(pid, {}).get("name") == winning_name:
            return pid
    return None


def _transition_to_next_round(session: dict) -> None:
    """Tally votes, swap in winner's songs, reset to play.
    Caller must hold _lock and start a _play_song thread after releasing."""
    winner_pid = _tally_winner(session)
    if winner_pid is None and session["dj_player_ids"]:
        winner_pid = random.choice(session["dj_player_ids"])

    if winner_pid is not None and session["dj_picks"].get(winner_pid):
        new_queue = list(session["dj_picks"][winner_pid])
    else:
        new_queue = list(session["song_queue"])

    session["song_queue"]         = new_queue
    session["current_song_index"] = 0
    session["dj_player_ids"]      = []
    session["dj_picks"]           = {}
    session["dj_finalized"]       = []
    session["pick_deadline"]      = None
    session["vote_deadline"]      = None
    session["status"]             = "play"
    for p in session["players"].values():
        p["current_vote"] = None


def _start_vote(session: dict) -> float:
    """Record vote deadline and flip status to vote.
    Caller must hold _lock. Returns deadline so caller can start _vote_timer."""
    deadline                 = time.time() + VOTE_DURATION
    session["vote_deadline"] = deadline
    session["pick_deadline"] = None
    session["status"]        = "vote"
    return deadline


# ── Background threads ────────────────────────────────────────────────────────────

def _play_song(session_id: str) -> None:
    """Runs when a song begins. On the last song, DJs are selected immediately
    and the pick timer starts so picking runs in parallel with the final track."""
    is_last = False

    with _lock:
        session = _sessions.get(session_id)
        if not session or session["status"] != "play":
            return
        q = session["song_queue"]
        if not q:
            return
        idx     = session["current_song_index"]
        is_last = idx >= len(q) - 1

        if is_last:
            player_ids = list(session["players"].keys())
            if player_ids:
                chosen = random.sample(player_ids, min(2, len(player_ids)))
                session["dj_player_ids"] = chosen
                session["dj_picks"]      = {pid: [] for pid in chosen}
                session["dj_finalized"]  = []
                pick_deadline            = time.time() + PICK_DURATION
                session["pick_deadline"] = pick_deadline
                session["status"]        = "pick"
            else:
                pick_deadline = None
        else:
            pick_deadline = None

    if is_last and pick_deadline is not None:
        threading.Thread(
            target=_pick_timer, args=(session_id, pick_deadline), daemon=True
        ).start()

    time.sleep(SONG_DURATION)

    if not is_last:
        with _lock:
            session = _sessions.get(session_id)
            if not session or session["status"] != "play":
                return
            session["current_song_index"] += 1
        threading.Thread(target=_play_song, args=(session_id,), daemon=True).start()


def _pick_timer(session_id: str, deadline: float) -> None:
    """Auto-finalizes all DJs when pick time expires.
    DJs with at least one song are finalized and advance to vote.
    DJs with no songs are removed from the lineup.
    If no DJ picked anything, the round replays the current queue."""
    time.sleep(max(0.0, deadline - time.time()))
    vote_deadline = None
    go_play       = False
    with _lock:
        session = _sessions.get(session_id)
        if not session:
            return
        if session["status"] != "pick" or session.get("pick_deadline") != deadline:
            return  # Already advanced manually
        # Keep only DJs who picked at least one song
        active_djs = [
            pid for pid in session["dj_player_ids"]
            if session["dj_picks"].get(pid)
        ]
        for pid in active_djs:
            if pid not in session["dj_finalized"]:
                session["dj_finalized"].append(pid)
        session["dj_player_ids"] = active_djs

        if active_djs:
            vote_deadline = _start_vote(session)
        else:
            _transition_to_next_round(session)
            go_play = True

    if vote_deadline is not None:
        threading.Thread(
            target=_vote_timer, args=(session_id, vote_deadline), daemon=True
        ).start()
    elif go_play:
        threading.Thread(target=_play_song, args=(session_id,), daemon=True).start()


def _vote_timer(session_id: str, deadline: float) -> None:
    """Auto-advances to next round when the vote window closes."""
    time.sleep(max(0.0, deadline - time.time()))
    with _lock:
        session = _sessions.get(session_id)
        if not session:
            return
        if session["status"] != "vote" or session.get("vote_deadline") != deadline:
            return
        _transition_to_next_round(session)
    threading.Thread(target=_play_song, args=(session_id,), daemon=True).start()


# ── Request models ────────────────────────────────────────────────────────────────

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

class DJFinalizeRequest(BaseModel):
    session_id: str
    player_id: int


# ── Host endpoints ────────────────────────────────────────────────────────────────

@router.post("/host/setup")
def setup_game(req: CreateSessionRequest):
    session_id = str(random.randint(100000, 999999))
    with _lock:
        _sessions[session_id] = {
            "id":                 req.id,
            "name":               req.name,
            "location":           req.location,
            "status":             "init",
            "song_queue":         [],
            "current_song_index": 0,
            "players":            {},
            "dj_player_ids":      [],
            "dj_picks":           {},
            "dj_finalized":       [],
            "pick_deadline":      None,
            "vote_deadline":      None,
            "next_player_id":     1,
        }
        db_manager.add_host((session_id, req.location if req.location else None))
    return {"ok": True, "session_id": session_id}


@router.post("/host/add_song")
def add_song(req: AddSongRequest):
    should_start = False
    with _lock:
        session = _get_session(req.session_id)
        session["song_queue"].append(req.song)
        if session["status"] == "init":
            session["status"]             = "play"
            session["current_song_index"] = 0
            should_start                  = True
    if should_start:
        threading.Thread(target=_play_song, args=(req.session_id,), daemon=True).start()
    return {"ok": True}


@router.post("/host/next_round")
def next_round(session_id: str = Query(...)):
    """Host ends voting early and starts the next round."""
    with _lock:
        session = _get_session(session_id)
        if session["status"] != "vote":
            raise HTTPException(status_code=400, detail="Not in vote state")
        _transition_to_next_round(session)
    threading.Thread(target=_play_song, args=(session_id,), daemon=True).start()
    return {"ok": True}


@router.post("/host/end")
def end_game(session_id: str = Query(...)):
    with _lock:
        session = _get_session(session_id)
        session["status"] = "ended"
    return {"ok": True}


# ── Player endpoints ──────────────────────────────────────────────────────────────

@router.post("/player/join")
def join(req: JoinRequest):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    with _lock:
        session   = _get_session(req.session_id)
        player_id = session["next_player_id"]
        session["next_player_id"] += 1
        session["players"][player_id] = {"name": name, "current_vote": None}
    return {"ok": True, "player_id": player_id}


@router.post("/player/vote")
def vote(req: VoteRequest):
    with _lock:
        session = _get_session(req.session_id)
        if session["status"] != "vote":
            raise HTTPException(status_code=400, detail="Not in vote state")
        if req.player_id not in session["players"]:
            raise HTTPException(status_code=403, detail="Player not registered")
        valid_names = {
            session["players"][pid]["name"]
            for pid in session["dj_player_ids"]
            if pid in session["players"]
        }
        if req.vote not in valid_names:
            raise HTTPException(status_code=400, detail="Invalid vote: DJ not found")
        session["players"][req.player_id]["current_vote"] = req.vote
    return {"ok": True}


@router.post("/dj/pick")
def dj_pick(req: DJPickRequest):
    """DJ adds one song to their list (up to MAX_DJ_SONGS)."""
    with _lock:
        session = _get_session(req.session_id)
        if session["status"] != "pick":
            raise HTTPException(status_code=400, detail="Not in pick state")
        if req.player_id not in session["dj_player_ids"]:
            raise HTTPException(status_code=403, detail="You are not a DJ this round")
        if req.player_id in session["dj_finalized"]:
            raise HTTPException(status_code=400, detail="Already finalized")
        picks = session["dj_picks"].setdefault(req.player_id, [])
        if len(picks) >= MAX_DJ_SONGS:
            raise HTTPException(status_code=400, detail=f"Maximum {MAX_DJ_SONGS} songs per DJ")
        picks.append(req.song)
    return {"ok": True}


@router.post("/dj/finalize")
def dj_finalize(req: DJFinalizeRequest):
    """Mark DJ as done. When all DJs finalize, voting begins."""
    vote_deadline = None
    with _lock:
        session = _get_session(req.session_id)
        if session["status"] != "pick":
            raise HTTPException(status_code=400, detail="Not in pick state")
        if req.player_id not in session["dj_player_ids"]:
            raise HTTPException(status_code=403, detail="You are not a DJ this round")
        if not session["dj_picks"].get(req.player_id):
            raise HTTPException(status_code=400, detail="Pick at least one song first")
        if req.player_id not in session["dj_finalized"]:
            session["dj_finalized"].append(req.player_id)
        if len(session["dj_finalized"]) >= len(session["dj_player_ids"]):
            vote_deadline = _start_vote(session)
    if vote_deadline is not None:
        threading.Thread(
            target=_vote_timer, args=(req.session_id, vote_deadline), daemon=True
        ).start()
    return {"ok": True}


# ── State endpoints ───────────────────────────────────────────────────────────────

def _pick_fields(session: dict) -> dict:
    deadline = session.get("pick_deadline")
    return {
        "pick_time_remaining": max(0, int(deadline - time.time())) if deadline else 0,
        "pick_duration":       PICK_DURATION,
    }


def _vote_fields(session: dict) -> dict:
    deadline = session.get("vote_deadline")
    return {
        "vote_time_remaining": max(0, int(deadline - time.time())) if deadline else 0,
        "vote_duration":       VOTE_DURATION,
    }


@router.get("/state")
def get_state(session_id: str = Query(...)):
    """Player-facing state snapshot."""
    with _lock:
        session = _get_session(session_id)
        result = {
            "status":        session["status"],
            "dj_player_ids": list(session["dj_player_ids"]),
            "current_song":  _current_song(session),
        }
        if session["status"] in ("vote", "pick"):
            result["dj_vote_options"] = _build_dj_vote_options(session)
        if session["status"] == "pick":
            result.update(_pick_fields(session))
        if session["status"] == "vote":
            result.update(_vote_fields(session))
        return result


@router.get("/status")
def get_status(session_id: str = Query(...)):
    """Host-facing full state snapshot."""
    with _lock:
        session = _get_session(session_id)
        idx     = session["current_song_index"]
        result  = {
            "status":               session["status"],
            "song_queue":           list(session["song_queue"]),
            "current_song_index":   idx,
            "current_song":         _current_song(session),
            "dj_player_ids":        list(session["dj_player_ids"]),
            "players": {
                str(pid): {"name": p["name"], "current_vote": p["current_vote"]}
                for pid, p in session["players"].items()
            },
        }
        if session["status"] in ("vote", "pick"):
            result["dj_vote_options"] = _build_dj_vote_options(session)
        if session["status"] == "pick":
            result.update(_pick_fields(session))
        if session["status"] == "vote":
            result.update(_vote_fields(session))
        return result
