"""
batch_scan.py — Scans a block of lecture/medical text.
For every recognized word:
  - Decodes it using decoder.py
  - Calls AI for unknown ones (optional)
Returns a structured report with all terms found + their mini-definitions.
"""

import re
import decoder

# Common English stop-words and short words to skip
_STOP = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "her",
    "was", "one", "our", "out", "day", "get", "has", "him", "his", "how",
    "its", "may", "new", "now", "old", "see", "two", "way", "who", "boy",
    "did", "let", "put", "say", "she", "too", "use", "with", "this", "that",
    "have", "from", "they", "will", "been", "were", "what", "when", "your",
    "each", "does", "into", "most", "also", "some", "than", "then", "them",
    "well", "just", "more", "been", "only", "very", "even", "back", "after",
    "used", "such", "here", "both", "made", "over", "give", "take", "know",
    "during", "often", "cause", "cases", "which", "there", "these", "those",
    "patient", "patients", "signs", "symptoms", "treatment", "diagnosis",
    "clinical", "associated", "common", "rare", "fever", "pain", "acute",
    "chronic", "blood", "cells", "body", "heart", "lung", "skin", "bone",
    "tissue", "found", "shows", "shown", "noted", "seen", "result", "results",
    "include", "includes", "present", "caused", "due", "type", "types",
    "form", "forms", "level", "levels", "high", "low", "normal", "abnormal",
    "primary", "secondary", "bilateral", "unilateral", "lateral", "medial",
}

# Min word length to bother decoding
_MIN_LEN = 5


def scan_text(text: str, use_ai: bool = False) -> dict:
    """
    Scan text for medical terms.
    Returns:
      - annotated_text: original text with [TERM: mini-def] markers
      - terms_found: list of {word, parts, meaning, source}
      - summary: stats
    """
    # Tokenize: split on non-alpha, preserve original positions
    words = re.findall(r"[a-zA-Z]{" + str(_MIN_LEN) + r",}", text)
    seen = set()
    terms_found = []

    for word in words:
        w_lower = word.lower()
        if w_lower in _STOP or w_lower in seen:
            continue
        seen.add(w_lower)

        result = decoder.decode(w_lower)
        if result["found"] and len(result["parts"]) >= 1:
            entry = {
                "word": word,
                "parts": result["parts"],
                "meaning": result["reconstructed_meaning"] or _fallback_meaning(result["parts"]),
                "source": "database",
            }

            # AI enrichment for partial matches (only if enabled)
            if use_ai and len(result["parts"]) < 2:
                try:
                    import ai_fallback
                    ai_data = ai_fallback.explain_with_ai(w_lower)
                    if ai_data and ai_data.get("reconstructed_meaning"):
                        entry["meaning"] = ai_data["reconstructed_meaning"]
                        entry["definition"] = ai_data.get("definition", "")
                        entry["source"] = "ai"
                except Exception:
                    pass

            terms_found.append(entry)

    # Build annotated text
    annotated = _annotate(text, terms_found)

    return {
        "annotated_text": annotated,
        "terms_found": terms_found,
        "summary": {
            "total_words_scanned": len(seen),
            "medical_terms_found": len(terms_found),
            "db_matched": sum(1 for t in terms_found if t["source"] == "database"),
            "ai_explained": sum(1 for t in terms_found if t["source"] == "ai"),
        },
    }


def _fallback_meaning(parts: list) -> str:
    if not parts:
        return "Medical term"
    return " + ".join(p["meaning"] for p in parts)


def _annotate(text: str, terms: list) -> str:
    """Replace each found term in text with 'term [= meaning]'."""
    result = text
    for entry in sorted(terms, key=lambda x: len(x["word"]), reverse=True):
        word = entry["word"]
        meaning = entry["meaning"] or ""
        # Case-insensitive replacement of first occurrence
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        replacement = f"{word} [= {meaning}]"
        result = pattern.sub(replacement, result, count=1)
    return result


def format_scan_report(scan_result: dict, max_terms: int = 20) -> list[str]:
    """
    Returns a list of message chunks (Telegram has 4096 char limit).
    """
    terms = scan_result["terms_found"]
    summary = scan_result["summary"]

    chunks = []

    # Chunk 1: Summary
    s = summary
    header = (
        f"🔍 *Batch Scan Complete*\n\n"
        f"📊 Words scanned: {s['total_words_scanned']}\n"
        f"🏥 Medical terms found: {s['medical_terms_found']}\n"
        f"📚 DB matched: {s['db_matched']}\n"
        f"🤖 AI explained: {s['ai_explained']}\n"
    )
    chunks.append(header)

    # Chunk 2+: Term list
    if not terms:
        chunks.append("No recognizable medical terms found\\. Try a more clinical passage\\.")
        return chunks

    term_lines = ["📋 *Terms Detected:*\n"]
    icons = {"prefix": "⬅️", "root": "🎯", "suffix": "➡️"}

    for i, entry in enumerate(terms[:max_terms], 1):
        word = entry["word"]
        meaning = entry["meaning"] or "—"
        parts_str = " \\+ ".join(
            f"`{p['part']}`\\({p['meaning']}\\)" for p in entry["parts"][:3]
        )
        line = f"*{i}\\. {_esc(word)}*\n   {parts_str}\n   💡 _{_esc(meaning)}_\n"
        term_lines.append(line)

        # Split into new chunk every ~3500 chars
        if sum(len(l) for l in term_lines) > 3200:
            chunks.append("\n".join(term_lines))
            term_lines = []

    if term_lines:
        chunks.append("\n".join(term_lines))

    if len(terms) > max_terms:
        chunks.append(f"_...and {len(terms) - max_terms} more terms\\. Showing top {max_terms}\\._")

    return chunks


def _esc(text: str) -> str:
    import re
    special = r"\_*[]()~`>#+-=|{}.!"
    return re.sub(r"([" + re.escape(special) + r"])", r"\\\1", str(text))
