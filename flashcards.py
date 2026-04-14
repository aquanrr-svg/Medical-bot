"""
flashcards.py — Spaced repetition flashcard system.
Uses a simplified SM-2-like algorithm:
  - New cards shown first
  - Correct → interval doubles (1d → 2d → 4d → 8d...)
  - Wrong → card resets to interval=1
Stores per-user data in data/flashcards/{user_id}.json
"""

import json
import os
import time
from quiz import QUIZ_TERMS

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "flashcards")
os.makedirs(_DATA_DIR, exist_ok=True)


def _path(user_id: int) -> str:
    return os.path.join(_DATA_DIR, f"{user_id}.json")


def _load(user_id: int) -> dict:
    p = _path(user_id)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    # Initialize with all terms as new
    cards = {}
    for term, meaning, hint in QUIZ_TERMS:
        cards[term] = {
            "meaning": meaning,
            "hint": hint,
            "interval": 1,       # days until next review
            "next_review": 0,    # unix timestamp (0 = due now)
            "correct_count": 0,
            "wrong_count": 0,
        }
    return {"cards": cards, "total_reviewed": 0}


def _save(user_id: int, data: dict):
    with open(_path(user_id), "w") as f:
        json.dump(data, f, indent=2)


def get_due_card(user_id: int) -> dict | None:
    """Return the next due card, or None if all reviewed for today."""
    data = _load(user_id)
    now = time.time()
    due = [
        (term, card) for term, card in data["cards"].items()
        if card["next_review"] <= now
    ]
    if not due:
        return None
    # Prioritize: new cards first (next_review==0), then earliest due
    due.sort(key=lambda x: x[1]["next_review"])
    term, card = due[0]
    return {
        "term": term,
        "meaning": card["meaning"],
        "hint": card["hint"],
        "correct_count": card["correct_count"],
        "wrong_count": card["wrong_count"],
        "due_count": len(due),
    }


def mark_result(user_id: int, term: str, correct: bool) -> dict:
    """Update card interval based on result. Returns updated stats."""
    data = _load(user_id)
    card = data["cards"].get(term)
    if not card:
        return {}

    now = time.time()
    if correct:
        card["correct_count"] += 1
        card["interval"] = min(card["interval"] * 2, 64)  # cap at 64 days
    else:
        card["wrong_count"] += 1
        card["interval"] = 1  # reset

    card["next_review"] = now + card["interval"] * 86400  # seconds in a day
    data["total_reviewed"] += 1
    _save(user_id, data)

    # Count remaining due
    remaining = sum(
        1 for c in data["cards"].values() if c["next_review"] <= now
    )
    return {
        "interval": card["interval"],
        "remaining_today": remaining,
        "total_reviewed": data["total_reviewed"],
    }


def get_stats(user_id: int) -> dict:
    data = _load(user_id)
    now = time.time()
    cards = data["cards"].values()
    due = sum(1 for c in cards if c["next_review"] <= now)
    mastered = sum(1 for c in cards if c["interval"] >= 16)
    learning = sum(1 for c in cards if 0 < c["next_review"] > now and c["interval"] < 16)
    new = sum(1 for c in cards if c["next_review"] == 0)
    return {
        "due": due,
        "mastered": mastered,
        "learning": learning,
        "new": new,
        "total": len(data["cards"]),
        "total_reviewed": data["total_reviewed"],
    }
