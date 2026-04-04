import time
import threading
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="QuizGame API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory game state (single active game) ──────────────────────────────────

_lock = threading.Lock()

_state = {
    "status": "idle",          # idle | lobby | question | reveal | ended
    "questions": [],           # [{"question": str, "options": [str], "correct": int}]
    "current_index": -1,
    "players": {},             # name -> {"score": int, "answered": bool}
    "current_answers": {},     # name -> answer_index  (current question only)
    "question_start_time": 0.0,
}


# ── Pydantic models ─────────────────────────────────────────────────────────────

class Question(BaseModel):
    question: str
    options: List[str]
    correct: int  # 0-based index into options


class SetupRequest(BaseModel):
    questions: List[Question]


class JoinRequest(BaseModel):
    name: str


class AnswerRequest(BaseModel):
    name: str
    answer: int  # 0-based index


# ── Host endpoints ──────────────────────────────────────────────────────────────

@app.post("/host/setup")
def setup_game(data: SetupRequest):
    """Create / reset a game with the given question set. Moves to lobby."""
    with _lock:
        _state["status"] = "lobby"
        _state["questions"] = [q.model_dump() for q in data.questions]
        _state["current_index"] = -1
        _state["players"] = {}
        _state["current_answers"] = {}
        _state["question_start_time"] = 0.0
    return {"ok": True}


@app.post("/host/start")
def start_game():
    """Kick off the game — show the first question."""
    with _lock:
        if _state["status"] != "lobby":
            raise HTTPException(400, "Game is not in lobby")
        if not _state["questions"]:
            raise HTTPException(400, "No questions loaded")
        _state["status"] = "question"
        _state["current_index"] = 0
        _state["current_answers"] = {}
        _state["question_start_time"] = time.time()
        for p in _state["players"].values():
            p["answered"] = False
    return {"ok": True}


@app.post("/host/next")
def advance():
    """
    From 'question' → 'reveal'.
    From 'reveal'   → next 'question' or 'ended'.
    """
    with _lock:
        status = _state["status"]
        if status == "question":
            _state["status"] = "reveal"
        elif status == "reveal":
            idx = _state["current_index"] + 1
            if idx >= len(_state["questions"]):
                _state["status"] = "ended"
            else:
                _state["current_index"] = idx
                _state["current_answers"] = {}
                _state["question_start_time"] = time.time()
                _state["status"] = "question"
                for p in _state["players"].values():
                    p["answered"] = False
        else:
            raise HTTPException(400, f"Cannot advance from status '{status}'")
    return {"ok": True}


# ── Player endpoints ────────────────────────────────────────────────────────────

@app.post("/player/join")
def join(req: JoinRequest):
    name = req.name.strip()
    if not name:
        raise HTTPException(400, "Name cannot be empty")
    with _lock:
        if _state["status"] not in ("lobby", "idle"):
            raise HTTPException(400, "Game already in progress")
        if name in _state["players"]:
            raise HTTPException(400, "Name already taken")
        _state["players"][name] = {"score": 0, "answered": False}
    return {"ok": True}


@app.post("/player/answer")
def answer(req: AnswerRequest):
    with _lock:
        if _state["status"] != "question":
            raise HTTPException(400, "No active question right now")
        player = _state["players"].get(req.name)
        if player is None:
            raise HTTPException(404, "Player not found")
        if player["answered"]:
            raise HTTPException(400, "Already answered")

        player["answered"] = True
        _state["current_answers"][req.name] = req.answer

        # Points: 1000 base, decay 50 pts/s, min 100 — only for correct answers
        q = _state["questions"][_state["current_index"]]
        if req.answer == q["correct"]:
            elapsed = time.time() - _state["question_start_time"]
            points = max(1000 - int(elapsed * 50), 100)
            player["score"] += points
            return {"ok": True, "correct": True, "points": points}

    return {"ok": True, "correct": False, "points": 0}


# ── Shared state endpoint ───────────────────────────────────────────────────────

@app.get("/game/state")
def get_state():
    with _lock:
        result = {
            "status": _state["status"],
            "player_count": len(_state["players"]),
            "current_index": _state["current_index"],
            "total_questions": len(_state["questions"]),
            "players": {
                name: {"score": p["score"], "answered": p["answered"]}
                for name, p in _state["players"].items()
            },
            "question": None,
        }

        idx = _state["current_index"]
        if _state["status"] in ("question", "reveal") and idx >= 0:
            q = _state["questions"][idx]
            result["question"] = {
                "text": q["question"],
                "options": q["options"],
            }
            if _state["status"] == "reveal":
                result["question"]["correct"] = q["correct"]
                result["question"]["answers"] = dict(_state["current_answers"])

        return result
