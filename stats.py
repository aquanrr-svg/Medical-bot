"""
stats.py — Per-user stats tracking and leaderboard.
Stores: total_decoded, quiz_score, flashcard_reviews, streak_days, last_active
Data stored in data/stats/{user_id}.json
Leaderboard stored in data/leaderboard.json (shared)
"""

import json
import os
import time
from datetime import datetime, date

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "stats")
_LB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "leaderboard.json")
os.makedirs(_DATA_DIR, exist_ok=True)


# ─── Per-user stats ───────────────────────────────────────────────────────────

def _path(user_id: int) -> str:
    return os.path.join(_DATA_DIR, f"{user_id}.json")


def _default(user_id: int, username: str = "") -> dict:
    return {
        "user_id": user_id,
        "username": username,
        "total_decoded": 0,
        "quiz_correct": 0,
        "quiz_total": 0,
        "flashcard_reviews": 0,
        "scans_done": 0,
        "lookups_done": 0,
        "login_streak": 0,
        "last_active_date": "",
        "joined": date.today().isoformat(),
        "xp": 0,  # gamification points
    }


def load(user_id: int, username: str = "") -> dict:
    p = _path(user_id)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    d = _default(user_id, username)
    save(user_id, d)
    return d


def save(user_id: int, data: dict):
    with open(_path(user_id), "w") as f:
        json.dump(data, f, indent=2)


def record_event(user_id: int, event: str, username: str = "", value: int = 1):
    """
    event: 'decode' | 'quiz_correct' | 'quiz_total' | 'flashcard' | 'scan' | 'lookup'
    """
    data = load(user_id, username)

    # Update streak
    today = date.today().isoformat()
    if data["last_active_date"] != today:
        yesterday = (date.today().replace(day=date.today().day - 1)).isoformat()
        if data["last_active_date"] == yesterday:
            data["login_streak"] += 1
        else:
            data["login_streak"] = 1
        data["last_active_date"] = today

    xp_gain = 0
    if event == "decode":
        data["total_decoded"] += value
        xp_gain = 2
    elif event == "quiz_correct":
        data["quiz_correct"] += value
        data["quiz_total"] += value
        xp_gain = 5
    elif event == "quiz_total":
        data["quiz_total"] += value
        xp_gain = 1
    elif event == "flashcard":
        data["flashcard_reviews"] += value
        xp_gain = 3
    elif event == "scan":
        data["scans_done"] += value
        xp_gain = 4
    elif event == "lookup":
        data["lookups_done"] += value
        xp_gain = 1

    data["xp"] += xp_gain
    if username:
        data["username"] = username

    save(user_id, data)
    _update_leaderboard(user_id, data)
    return data


def get_profile(user_id: int) -> dict:
    return load(user_id)


def _level(xp: int) -> tuple[int, str]:
    levels = [
        (0,    "🩺 Intern"),
        (50,   "📖 Resident"),
        (150,  "🔬 Junior Doctor"),
        (350,  "🏥 Senior Doctor"),
        (700,  "🧠 Specialist"),
        (1200, "⭐ Consultant"),
        (2000, "🏆 Professor"),
    ]
    for threshold, title in reversed(levels):
        if xp >= threshold:
            return threshold, title
    return 0, "🩺 Intern"


def format_profile(data: dict) -> str:
    xp = data.get("xp", 0)
    _, lvl = _level(xp)
    quiz_acc = (
        f"{round(data['quiz_correct']/data['quiz_total']*100)}%"
        if data.get("quiz_total", 0) > 0 else "N/A"
    )

    def esc(t): 
        import re
        return re.sub(r"([\_\*\[\]\(\)\~\`\>\#\+\-\=\|\{\}\.\!])", r"\\\1", str(t))

    return (
        f"👤 *Your Profile*\n\n"
        f"🎖️ Level: {esc(lvl)}\n"
        f"⭐ XP: {xp}\n"
        f"🔥 Daily streak: {data.get('login_streak', 0)} days\n\n"
        f"📊 *Activity*\n"
        f"🔬 Terms decoded: {data.get('total_decoded', 0)}\n"
        f"📝 Quiz accuracy: {quiz_acc}\n"
        f"🃏 Flashcard reviews: {data.get('flashcard_reviews', 0)}\n"
        f"📄 Text scans: {data.get('scans_done', 0)}\n"
        f"🔍 Reverse lookups: {data.get('lookups_done', 0)}\n\n"
        f"📅 Member since: {esc(data.get('joined', 'unknown'))}"
    )


# ─── Leaderboard ──────────────────────────────────────────────────────────────

def _load_leaderboard() -> list:
    if os.path.exists(_LB_PATH):
        with open(_LB_PATH) as f:
            return json.load(f)
    return []


def _save_leaderboard(lb: list):
    with open(_LB_PATH, "w") as f:
        json.dump(lb, f, indent=2)


def _update_leaderboard(user_id: int, data: dict):
    lb = _load_leaderboard()
    entry = {
        "user_id": user_id,
        "username": data.get("username") or f"user_{user_id}",
        "xp": data.get("xp", 0),
        "quiz_correct": data.get("quiz_correct", 0),
    }
    # Update or insert
    existing = next((i for i, e in enumerate(lb) if e["user_id"] == user_id), None)
    if existing is not None:
        lb[existing] = entry
    else:
        lb.append(entry)
    # Sort by XP
    lb.sort(key=lambda x: x["xp"], reverse=True)
    _save_leaderboard(lb[:100])  # Keep top 100


def format_leaderboard(current_user_id: int = None) -> str:
    lb = _load_leaderboard()
    if not lb:
        return "🏆 Leaderboard is empty\\. Be the first\\!"

    def esc(t):
        import re
        return re.sub(r"([\_\*\[\]\(\)\~\`\>\#\+\-\=\|\{\}\.\!])", r"\\\1", str(t))

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 *Top Medical Decoders*\n"]
    for i, entry in enumerate(lb[:10], 1):
        medal = medals[i - 1] if i <= 3 else f"{i}\\."
        name = esc(entry.get("username") or f"user_{entry['user_id']}")
        xp = entry["xp"]
        is_you = " ← you" if entry["user_id"] == current_user_id else ""
        lines.append(f"{medal} *{name}* — {xp} XP{esc(is_you)}")

    # Show current user's rank if not in top 10
    if current_user_id:
        user_rank = next(
            (i + 1 for i, e in enumerate(lb) if e["user_id"] == current_user_id), None
        )
        if user_rank and user_rank > 10:
            lines.append(f"\n_Your rank: #{user_rank}_")

    return "\n".join(lines)
