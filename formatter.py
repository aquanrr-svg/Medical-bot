"""
formatter.py — Converts decoder/AI output into clean Telegram-ready messages.
Uses MarkdownV2 escaping for Telegram.
"""

import re


def _esc(text: str) -> str:
    """Escape special MarkdownV2 characters."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return re.sub(r"([" + re.escape(special) + r"])", r"\\\1", str(text))


def format_decode_result(result: dict, ai_data: dict = None) -> str:
    """
    Build the full Telegram message for a decoded term.
    result   — from decoder.decode()
    ai_data  — optional dict from ai_fallback.explain_with_ai()
    """
    term = result["term"].capitalize()
    parts = result["parts"]
    reconstructed = result.get("reconstructed_meaning")
    lines = []

    # ── Header ──
    lines.append(f"🔬 *{_esc(term)}*")
    lines.append("")

    # ── AI definition (if available) ──
    if ai_data and ai_data.get("definition"):
        lines.append(f"📖 *Definition*")
        lines.append(_esc(ai_data["definition"]))
        lines.append("")

    # ── Morpheme breakdown ──
    breakdown_parts = parts  # from local decoder
    if ai_data and ai_data.get("breakdown"):
        breakdown_parts = ai_data["breakdown"]

    if breakdown_parts:
        lines.append("🧩 *Word Breakdown*")
        icons = {"prefix": "⬅️", "root": "🎯", "suffix": "➡️"}
        for p in breakdown_parts:
            icon = icons.get(p.get("type", "root"), "•")
            part_text = _esc(p["part"])
            meaning = _esc(p["meaning"])
            ptype = _esc(p.get("type", "").capitalize())
            lines.append(f"{icon} `{part_text}` \\({ptype}\\) → _{meaning}_")
        lines.append("")

    # ── Reconstructed meaning ──
    final_meaning = (
        ai_data.get("reconstructed_meaning") if ai_data else None
    ) or reconstructed
    if final_meaning:
        lines.append("💡 *Reconstructed Meaning*")
        lines.append(f"_{_esc(final_meaning)}_")
        lines.append("")

    # ── Pronunciation (AI only) ──
    if ai_data and ai_data.get("pronunciation"):
        lines.append(f"🗣️ *Pronunciation:* `{_esc(ai_data['pronunciation'])}`")
        lines.append("")

    # ── Related terms (AI only) ──
    if ai_data and ai_data.get("related_terms"):
        related = ", ".join(ai_data["related_terms"][:5])
        lines.append(f"🔗 *Related Terms:* {_esc(related)}")
        lines.append("")

    # ── Source label ──
    if ai_data:
        lines.append("🤖 _Explained by AI \\(rare term\\)_")
    else:
        lines.append("📚 _Matched from morpheme database_")

    return "\n".join(lines)


def format_not_found(term: str) -> str:
    return (
        f"❓ Sorry, I couldn't decode *{_esc(term)}*\\.\n\n"
        "This term may be:\n"
        "• A brand name or eponym\n"
        "• An abbreviation\n"
        "• Very specialized jargon\n\n"
        "Try breaking it down manually or check a medical dictionary\\."
    )


def format_help() -> str:
    return (
        "👋 *Medical Term Decoder Bot*\n\n"
        "I help you understand medical terminology by breaking words into "
        "their *prefix*, *root*, and *suffix* — so you learn the logic, "
        "not just the definition\\.\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "📌 *Commands*\n"
        "/decode `<term>` — Decode a medical term\n"
        "/prefix `<text>` — Look up a prefix\n"
        "/root `<text>` — Look up a root\n"
        "/suffix `<text>` — Look up a suffix\n"
        "/random — Get a random term example\n"
        "/quiz — Start a quick quiz \\(coming soon\\)\n"
        "/help — Show this message\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "💬 *Or just type any medical term directly\\!*\n\n"
        "Example: `tonsillitis` → tonsill \\(tonsils\\) \\+ \\-itis \\(inflammation\\)\n"
        "→ _Inflammation of the tonsils_"
    )


def format_morpheme_lookup(key: str, data: dict, mtype: str) -> str:
    icons = {"prefix": "⬅️", "root": "🎯", "suffix": "➡️"}
    icon = icons.get(mtype, "•")
    lines = [
        f"{icon} *{_esc(key)}* \\({_esc(mtype.capitalize())}\\)",
        "",
        f"📖 *Meaning:* {_esc(data['meaning'])}",
        f"📝 *Example:* _{_esc(data['example'])}_",
    ]
    return "\n".join(lines)


def format_random_example() -> str:
    examples = [
        ("tonsillitis", "tonsill (tonsils) + -itis (inflammation)", "Inflammation of the tonsils"),
        ("hypertension", "hyper- (above/excessive) + tens (stretch) + -ion (condition)", "Condition of excessively high pressure"),
        ("nephrology", "nephr (kidney) + -ology (study of)", "Study of the kidney"),
        ("hepatomegaly", "hepat (liver) + -megaly (enlargement)", "Enlargement of the liver"),
        ("bradycardia", "brady- (slow) + cardi (heart) + -ia (condition)", "Condition of slow heart rate"),
        ("dyspnea", "dys- (difficult/abnormal) + -pnea (breathing)", "Difficult or labored breathing"),
        ("leukocyte", "leuko- (white) + -cyte (cell)", "White blood cell"),
        ("hematuria", "hemat (blood) + -uria (urine condition)", "Blood in the urine"),
        ("splenomegaly", "splen (spleen) + -megaly (enlargement)", "Enlargement of the spleen"),
        ("thrombocytopenia", "thromb (clot) + cyt (cell) + -penia (deficiency)", "Deficiency of clot-forming cells (platelets)"),
    ]
    import random
    term, breakdown, meaning = random.choice(examples)
    return (
        f"🎲 *Random Example: {_esc(term)}*\n\n"
        f"🧩 *Breakdown:* {_esc(breakdown)}\n\n"
        f"💡 *Meaning:* _{_esc(meaning)}_\n\n"
        "Try /decode on it for a full analysis\\!"
    )


def format_help_v2() -> str:
    return (
        "👋 *Medical Term Decoder Bot v2*\n\n"
        "Learn medical terminology by understanding word logic — prefix, root, suffix\\.\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "🔬 *Decode*\n"
        "/decode `<term>` — Full morpheme breakdown\n"
        "/prefix `/root` `/suffix` — Look up any part\n"
        "/random — Random example term\n\n"
        "🧠 *Learn*\n"
        "/quiz — Quiz mode \\(term→meaning or meaning→term\\)\n"
        "/flashcard — Spaced repetition flashcards\n"
        "/lookup `<keyword>` — Find terms by meaning\n\n"
        "📄 *Analyze*\n"
        "/scan — Paste lecture text → get all terms decoded\n\n"
        "📊 *You*\n"
        "/profile — Your XP, stats, level\n"
        "/leaderboard — Top students\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "💬 *Or just type any medical term directly\\!*\n"
        "Example: `tonsillitis` → tonsill \\(tonsils\\) \\+ \\-itis \\(inflammation\\)\n"
        "→ _Inflammation of the tonsils_"
    )
