"""everse_lookup.py — Search medical terms by meaning keyword.
e.g. user types "inflammation" → returns all terms containing -itis etc.
Also supports morpheme reverse search: "what terms use brady-?"
"""

import json
import os
from quiz import QUIZ_TERMS

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "morphemes.json")
with open(_DB_PATH) as f:
    _DB = json.load(f)

PREFIXES = _DB["prefixes"]
ROOTS = _DB["roots"]
SUFFIXES = _DB["suffixes"]

def search_by_meaning(keyword: str) -> list[dict]:
    """
    Find morphemes whose meaning contains the keyword.
    Returns list of {part, type, meaning, example, terms_using_it}
    """
    kw = keyword.strip().lower()
    results = []

    for part, data in PREFIXES.items():
        if kw in data["meaning"].lower():
            results.append({"part": part, "type": "prefix", **data})
    for part, data in ROOTS.items():
        if kw in data["meaning"].lower():
            results.append({"part": part, "type": "root", **data})
    for part, data in SUFFIXES.items():
        if kw in data["meaning"].lower():
            results.append({"part": part, "type": "suffix", **data})

    return results

def search_terms_by_meaning(keyword: str) -> list[dict]:
    """
    Search through the quiz term bank for terms whose meaning contains keyword.
    Returns list of {term, meaning, hint}
    """
    kw = keyword.strip().lower()
    return [
        {"term": t, "meaning": m, "hint": h}
        for t, m, h in QUIZ_TERMS
        if kw in m.lower()
    ]

def morpheme_reverse(part: str) -> list[dict]:
    """
    Find all known terms that use a given morpheme.
    e.g. "brady" → bradycardia, etc.
    """
    part_clean = part.strip().lower().strip("-")
    matches = []
    for term, meaning, hint in QUIZ_TERMS:
        if part_clean in term.lower():
            matches.append({"term": term, "meaning": meaning, "hint": hint})
    return matches