"""
decoder.py — Medical term morpheme matching engine.
"""

import json
import os
import re

# Try multiple path strategies to find morphemes.json
def _find_db():
    candidates = [
        "/app/data/morphemes.json",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "morphemes.json"),
        os.path.join(os.getcwd(), "data", "morphemes.json"),
        "data/morphemes.json",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"morphemes.json not found. Tried: {candidates}")

with open(_find_db(), "r") as f:
    _DB = json.load(f)

PREFIXES: dict = _DB["prefixes"]
ROOTS: dict = _DB["roots"]
SUFFIXES: dict = _DB["suffixes"]


def _normalize(word: str) -> str:
    return word.strip().lower()


def _find_prefix(word: str):
    for p in sorted(PREFIXES.keys(), key=len, reverse=True):
        p_clean = p.rstrip("-")
        if word.startswith(p_clean) and len(word) > len(p_clean):
            return p, word[len(p_clean):]
    return None, word


def _find_suffix(word: str):
    for s in sorted(SUFFIXES.keys(), key=len, reverse=True):
        s_clean = s.lstrip("-")
        if word.endswith(s_clean) and len(word) > len(s_clean):
            return s, word[: -len(s_clean)]
    return None, word


def _find_root(word: str):
    if word in ROOTS:
        return word, word
    best = None
    best_len = 0
    for r in ROOTS.keys():
        if r in word and len(r) > best_len:
            best = r
            best_len = len(r)
    if best:
        return best, best
    return None, None


def decode(term: str) -> dict:
    word = _normalize(term)
    parts = []
    found = False

    prefix_key, remainder = _find_prefix(word)
    if prefix_key:
        found = True
        parts.append({
            "part": prefix_key,
            "type": "prefix",
            "meaning": PREFIXES[prefix_key]["meaning"],
            "example": PREFIXES[prefix_key]["example"],
        })

    suffix_key, core = _find_suffix(remainder)
    if suffix_key:
        found = True

    root_key, _ = _find_root(core)
    if root_key:
        found = True
        parts.append({
            "part": root_key,
            "type": "root",
            "meaning": ROOTS[root_key]["meaning"],
            "example": ROOTS[root_key]["example"],
        })

    if suffix_key:
        parts.append({
            "part": suffix_key,
            "type": "suffix",
            "meaning": SUFFIXES[suffix_key]["meaning"],
            "example": SUFFIXES[suffix_key]["example"],
        })

    reconstructed = _reconstruct(parts, term)

    return {
        "term": term,
        "parts": parts,
        "reconstructed_meaning": reconstructed,
        "found": found,
        "unmatched": word if not found else None,
    }


def _reconstruct(parts: list, original_term: str) -> str:
    if not parts:
        return None
    meanings = [p["meaning"] for p in parts]
    if len(meanings) == 1:
        return f"{meanings[0].capitalize()}"
    elif len(meanings) == 2:
        t0, t1 = parts[0]["type"], parts[1]["type"]
        if t0 == "root" and t1 == "suffix":
            return f"{meanings[1].capitalize()} of the {meanings[0]}"
        if t0 == "prefix" and t1 == "suffix":
            return f"{meanings[1].capitalize()} that is {meanings[0]}"
        if t0 == "prefix" and t1 == "root":
            return f"{meanings[0].capitalize()} {meanings[1]}"
        return f"{meanings[0].capitalize()} + {meanings[1]}"
    elif len(meanings) == 3:
        p_m = parts[0]["meaning"] if parts[0]["type"] == "prefix" else None
        r_m = next((p["meaning"] for p in parts if p["type"] == "root"), None)
        s_m = next((p["meaning"] for p in parts if p["type"] == "suffix"), None)
        if p_m and r_m and s_m:
            return f"{s_m.capitalize()} of the {r_m} ({p_m})"
        return " + ".join(m.capitalize() for m in meanings)
    else:
        return " + ".join(m.capitalize() for m in meanings)


def list_all_morphemes(mtype: str = None) -> dict:
    if mtype == "prefix":
        return PREFIXES
    elif mtype == "root":
        return ROOTS
    elif mtype == "suffix":
        return SUFFIXES
    return {"prefixes": PREFIXES, "roots": ROOTS, "suffixes": SUFFIXES}