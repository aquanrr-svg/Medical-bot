"""
decoder.py — Medical term morpheme matching engine.
Tries to decompose a term into prefix + root + suffix from the database,
then reconstructs a plain-English meaning.
"""

import json
import os
import re

# Load database once at import
_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "morphemes.json")
with open(_DB_PATH, "r") as f:
    _DB = json.load(f)

PREFIXES: dict = _DB["prefixes"]
ROOTS: dict = _DB["roots"]
SUFFIXES: dict = _DB["suffixes"]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _normalize(word: str) -> str:
    return word.strip().lower()


def _find_prefix(word: str):
    """Return (prefix_key, remaining_word) or (None, word)."""
    for p in sorted(PREFIXES.keys(), key=len, reverse=True):
        # Remove trailing hyphen for matching
        p_clean = p.rstrip("-")
        if word.startswith(p_clean) and len(word) > len(p_clean):
            return p, word[len(p_clean):]
    return None, word


def _find_suffix(word: str):
    """Return (suffix_key, remaining_word) or (None, word)."""
    for s in sorted(SUFFIXES.keys(), key=len, reverse=True):
        # Remove leading hyphen for matching
        s_clean = s.lstrip("-")
        if word.endswith(s_clean) and len(word) > len(s_clean):
            return s, word[: -len(s_clean)]
    return None, word


def _find_root(word: str):
    """Return (root_key, matched_root) or (None, None).
    Tries exact match, then partial match (word contains root or root contains word).
    """
    # Exact match first
    if word in ROOTS:
        return word, word
    # Longest root that fits inside the word
    best = None
    best_len = 0
    for r in ROOTS.keys():
        if r in word and len(r) > best_len:
            best = r
            best_len = len(r)
    if best:
        return best, best
    return None, None


# ─── Public API ───────────────────────────────────────────────────────────────

def decode(term: str) -> dict:
    """
    Attempt to decompose a medical term.
    Returns a dict with:
        - term (str)
        - parts: list of {part, type, meaning, example}
        - reconstructed_meaning (str)
        - found (bool) — True if at least one part matched
        - unmatched (str | None) — leftover string if partial match
    """
    word = _normalize(term)
    parts = []
    found = False

    # Step 1 — prefix
    prefix_key, remainder = _find_prefix(word)
    if prefix_key:
        found = True
        parts.append({
            "part": prefix_key,
            "type": "prefix",
            "meaning": PREFIXES[prefix_key]["meaning"],
            "example": PREFIXES[prefix_key]["example"],
        })

    # Step 2 — suffix (operate on remainder after prefix stripped)
    suffix_key, core = _find_suffix(remainder)
    if suffix_key:
        found = True

    # Step 3 — root (operate on core between prefix and suffix)
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

    # Step 4 — reconstruct meaning
    reconstructed = _reconstruct(parts, term)

    # Determine leftover (unmatched core)
    unmatched = None
    matched_text = ""
    if prefix_key:
        matched_text += prefix_key.rstrip("-")
    if root_key:
        matched_text += root_key
    if suffix_key:
        matched_text += suffix_key.lstrip("-")
    if len(matched_text) < len(word) * 0.5 and not found:
        unmatched = word

    return {
        "term": term,
        "parts": parts,
        "reconstructed_meaning": reconstructed,
        "found": found,
        "unmatched": unmatched if not found else None,
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
        # prefix + root + suffix  →  "[suffix meaning] of the [root meaning] (that is [prefix meaning])"
        p_m = parts[0]["meaning"] if parts[0]["type"] == "prefix" else None
        r_m = next((p["meaning"] for p in parts if p["type"] == "root"), None)
        s_m = next((p["meaning"] for p in parts if p["type"] == "suffix"), None)
        if p_m and r_m and s_m:
            return f"{s_m.capitalize()} of the {r_m} ({p_m})"
        return " + ".join(m.capitalize() for m in meanings)
    else:
        return " + ".join(m.capitalize() for m in meanings)


def list_all_morphemes(mtype: str = None) -> dict:
    """Return all morphemes of a given type (prefix/root/suffix) or all."""
    if mtype == "prefix":
        return PREFIXES
    elif mtype == "root":
        return ROOTS
    elif mtype == "suffix":
        return SUFFIXES
    return {"prefixes": PREFIXES, "roots": ROOTS, "suffixes": SUFFIXES}
