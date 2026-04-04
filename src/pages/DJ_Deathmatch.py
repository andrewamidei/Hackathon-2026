import os
import time

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="DJ_DeathMatch", page_icon="🎮", layout="centered")

# ── Session state defaults ──────────────────────────────────────────────────────

for key, default in {
    "role": None,           # "host" | "player"
    "player_name": None,
    "answered": False,
    "last_q_index": -1,
    "questions": [],        # host's staged questions before setup
    "last_answer_result": None,  # {"correct": bool, "points": int}
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Helpers ─────────────────────────────────────────────────────────────────────

def api_get(path: str):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=3)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def api_post(path: str, body: dict = None):
    try:
        r = requests.post(f"{API_URL}{path}", json=body or {}, timeout=3)
        return r
    except Exception:
        return None


def leaderboard(players: dict):
    sorted_p = sorted(players.items(), key=lambda x: x[1]["score"], reverse=True)
    medals = ["🥇", "🥈", "🥉"]
    for rank, (name, data) in enumerate(sorted_p):
        prefix = medals[rank] if rank < 3 else f"{rank + 1}."
        you = " ← you" if name == st.session_state.player_name else ""
        st.write(f"{prefix} **{name}** — {data['score']} pts{you}")


def auto_rerun(seconds: float = 2.0):
    time.sleep(seconds)
    st.rerun()


if st.session_state.role == "player":

    pass


if st.session_state.role == "DJ":
    pass
# ════════════════════════════════════════════════════════════════════════════════
# HOST VIEW
# ════════════════════════════════════════════════════════════════════════════════

if st.session_state.role == "host":
    state = api_get("/DJ/state")
    if game["status"] in ("init"):

    pass

if st.session_state.role == "host":
    game = api_get("/DJ/state")

    if game is None:
        st.error("Cannot reach the game API. Is it running?")
        st.stop()

    # ── Lobby / Setup ──────────────────────────────────────────────────────────
    if game["status"] in ("idle", "lobby"):
        st.title("🎯 Game Setup")

        with st.form("add_q", clear_on_submit=True):
            q_text = st.text_input("Question")
            col1, col2 = st.columns(2)
            with col1:
                opt_a = st.text_input("Option A")
                opt_b = st.text_input("Option B")
            with col2:
                opt_c = st.text_input("Option C")
                opt_d = st.text_input("Option D")
            correct = st.selectbox("Correct answer", ["A", "B", "C", "D"])
            add = st.form_submit_button("Add Question")

        if add and q_text.strip():
            st.session_state.questions.append({
                "question": q_text.strip(),
                "options": [opt_a, opt_b, opt_c, opt_d],
                "correct": ["A", "B", "C", "D"].index(correct),
            })

        if st.session_state.questions:
            st.subheader(f"Questions ({len(st.session_state.questions)})")
            for i, q in enumerate(st.session_state.questions):
                c1, c2 = st.columns([8, 1])
                c1.write(f"**{i+1}.** {q['question']}")
                if c2.button("✕", key=f"del_{i}"):
                    st.session_state.questions.pop(i)
                    st.rerun()

            st.write("---")
            st.subheader(f"Players in lobby: {game['player_count']}")
            for name in game["players"]:
                st.write(f"• {name}")

            if st.button("🚀 Start Game", type="primary", use_container_width=True):
                r = api_post("/DJ/host/setup", {"questions": st.session_state.questions})
                if r and r.status_code == 200:
                    api_post("/DJ/host/start")
                    st.rerun()
                else:
                    st.error("Failed to set up game.")

        # Refresh lobby player count
        if game["status"] == "lobby":
            auto_rerun(3)

    # ── Active question ────────────────────────────────────────────────────────
    elif game["status"] == "question":
        q = game["question"]
        idx = game["current_index"]
        total = game["total_questions"]

        st.progress((idx + 1) / total)
        st.caption(f"Question {idx + 1} of {total}")
        st.title(q["text"])

        cols = st.columns(2)
        for i, opt in enumerate(q["options"]):
            cols[i % 2].button(
                f"{'ABCD'[i]}. {opt}",
                use_container_width=True,
                disabled=True,
            )

        answered = sum(1 for p in game["players"].values() if p["answered"])
        st.metric("Answered", f"{answered} / {game['player_count']}")

        st.write("---")
        if st.button("⏭ Reveal Answers", type="primary", use_container_width=True):
            api_post("/DJ/host/next")
            st.rerun()

        auto_rerun(2)

    # ── Reveal ─────────────────────────────────────────────────────────────────
    elif game["status"] == "reveal":
        q = game["question"]
        idx = game["current_index"]
        total = game["total_questions"]

        st.progress((idx + 1) / total)
        st.caption(f"Question {idx + 1} of {total}")
        st.title(q["text"])

        correct_i = q["correct"]
        for i, opt in enumerate(q["options"]):
            label = f"{'ABCD'[i]}. {opt}"
            if i == correct_i:
                st.success(f"✅ {label}")
            else:
                st.button(label, use_container_width=True, disabled=True)

        answers = q.get("answers", {})
        correct_players = [n for n, a in answers.items() if a == correct_i]
        wrong_players = [n for n, a in answers.items() if a != correct_i]
        no_answer = [n for n in game["players"] if n not in answers]

        col1, col2, col3 = st.columns(3)
        col1.metric("Correct", len(correct_players))
        col2.metric("Wrong", len(wrong_players))
        col3.metric("No answer", len(no_answer))

        st.write("---")
        st.subheader("Leaderboard")
        leaderboard(game["players"])

        st.write("---")
        next_label = "➡ Next Question" if idx + 1 < total else "🏁 Show Final Results"
        if st.button(next_label, type="primary", use_container_width=True):
            api_post("/DJ/host/next")
            st.rerun()

    # ── Ended ──────────────────────────────────────────────────────────────────
    elif game["status"] == "ended":
        st.title("🏆 Final Results")
        leaderboard(game["players"])

        st.write("---")
        if st.button("🔄 Play Again", use_container_width=True):
            st.session_state.questions = []
            st.session_state.role = "host"
            api_post("/DJ/host/setup", {"questions": []})
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# PLAYER VIEW
# ════════════════════════════════════════════════════════════════════════════════

elif st.session_state.role == "player":

    # ── Join screen ────────────────────────────────────────────────────────────
    if st.session_state.player_name is None:
        st.title("🙋 Join Game")
        name = st.text_input("Your name")
        if st.button("Join", type="primary") and name.strip():
            r = api_post("/DJ/player/join", {"name": name.strip()})
            if r and r.status_code == 200:
                st.session_state.player_name = name.strip()
                st.rerun()
            else:
                detail = r.json().get("detail", "Error") if r else "Cannot reach server"
                st.error(detail)
        st.stop()

    # ── In-game ────────────────────────────────────────────────────────────────
    name = st.session_state.player_name
    game = api_get("/DJ/state")

    if game is None:
        st.error("Cannot reach the game server. Retrying...")
        auto_rerun(3)
        st.stop()

    my_score = game["players"].get(name, {}).get("score", 0)
    st.sidebar.metric("Your score", my_score)
    st.sidebar.write(f"Players: {game['player_count']}")

    # ── Waiting in lobby ───────────────────────────────────────────────────────
    if game["status"] in ("idle", "lobby"):
        st.title("⏳ Waiting for the host to start...")
        st.write(f"**{game['player_count']}** player(s) in lobby.")
        auto_rerun(2)

    # ── Active question ────────────────────────────────────────────────────────
    elif game["status"] == "question":
        q = game["question"]
        idx = game["current_index"]
        total = game["total_questions"]

        # Reset answered flag when question changes
        if idx != st.session_state.last_q_index:
            st.session_state.answered = False
            st.session_state.last_q_index = idx
            st.session_state.last_answer_result = None

        st.progress((idx + 1) / total)
        st.caption(f"Question {idx + 1} of {total}")
        st.title(q["text"])

        if not st.session_state.answered:
            cols = st.columns(2)
            for i, opt in enumerate(q["options"]):
                with cols[i % 2]:
                    if st.button(f"{'ABCD'[i]}. {opt}", use_container_width=True, key=f"opt_{i}"):
                        r = api_post("/DJ/player/answer", {"name": name, "answer": i})
                        if r and r.status_code == 200:
                            st.session_state.answered = True
                            st.session_state.last_answer_result = r.json()
                            st.rerun()
                        elif r:
                            st.error(r.json().get("detail", "Error"))
        else:
            result = st.session_state.last_answer_result
            if result and result.get("correct"):
                st.success(f"✅ Correct! +{result['points']} pts")
            elif result:
                st.error("❌ Wrong answer")
            st.info("Waiting for the host to reveal answers...")
            auto_rerun(2)

    # ── Reveal ─────────────────────────────────────────────────────────────────
    elif game["status"] == "reveal":
        q = game["question"]
        idx = game["current_index"]
        total = game["total_questions"]

        st.progress((idx + 1) / total)
        st.caption(f"Question {idx + 1} of {total}")
        st.title(q["text"])

        correct_i = q["correct"]
        my_answer = q.get("answers", {}).get(name)

        for i, opt in enumerate(q["options"]):
            label = f"{'ABCD'[i]}. {opt}"
            if i == correct_i:
                st.success(f"✅ {label}")
            elif my_answer == i:
                st.error(f"❌ {label} (your answer)")
            else:
                st.button(label, use_container_width=True, disabled=True)

        if my_answer is None:
            st.warning("⏰ You didn't answer in time.")

        st.metric("Your Score", my_score)
        auto_rerun(2)

    # ── Ended ──────────────────────────────────────────────────────────────────
    elif game["status"] == "ended":
        st.title("🏆 Game Over!")
        leaderboard(game["players"])
