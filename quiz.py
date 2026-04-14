"""
quiz.py — Quiz mode engine.
Supports two modes:
  - term_to_meaning : Bot shows term → student types meaning
  - meaning_to_term : Bot shows meaning → student types term
Tracks score, streak, and lives per user session.
"""

import random
import json
import os

# ─── Question bank built from morpheme DB ─────────────────────────────────────

_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "morphemes.json")
with open(_DB_PATH) as f:
    _DB = json.load(f)

# Curated medical term quiz bank: (term, readable_meaning, morpheme_hint)
QUIZ_TERMS = [
    ("tonsillitis",     "inflammation of the tonsils",          "tonsill + -itis"),
    ("bradycardia",     "slow heart rate",                      "brady- + cardi + -ia"),
    ("hepatomegaly",    "enlargement of the liver",             "hepat + -megaly"),
    ("nephritis",       "inflammation of the kidney",           "nephr + -itis"),
    ("dyspnea",         "difficult or labored breathing",       "dys- + -pnea"),
    ("hematuria",       "blood in the urine",                   "hemat + -uria"),
    ("leukocyte",       "white blood cell",                     "leuko- + -cyte"),
    ("hypertension",    "abnormally high blood pressure",       "hyper- + tens + -ion"),
    ("tachycardia",     "fast heart rate",                      "tachy- + cardi + -ia"),
    ("splenomegaly",    "enlargement of the spleen",            "splen + -megaly"),
    ("nephrology",      "study of the kidney",                  "nephr + -ology"),
    ("gastritis",       "inflammation of the stomach",          "gastr + -itis"),
    ("cardiology",      "study of the heart",                   "cardi + -ology"),
    ("pneumonia",       "disease of the lung",                  "pneumon + -ia"),
    ("rhinitis",        "inflammation of the nose",             "rhin + -itis"),
    ("dermatitis",      "inflammation of the skin",             "derm + -itis"),
    ("arthritis",       "inflammation of the joints",           "arthr + -itis"),
    ("osteoporosis",    "porous/weak bone condition",           "osteo- + por + -osis"),
    ("anemia",          "deficiency of blood (or red cells)",   "an- + -emia"),
    ("apnea",           "absence of breathing",                 "a- + -pnea"),
    ("hemiplegia",      "paralysis of half the body",           "hemi- + -plegia"),
    ("cyanosis",        "bluish discoloration of skin",         "cyan + -osis"),
    ("cholecystitis",   "inflammation of the gallbladder",      "cholecyst + -itis"),
    ("appendectomy",    "surgical removal of the appendix",     "append + -ectomy"),
    ("laryngitis",      "inflammation of the larynx",           "laryng + -itis"),
    ("meningitis",      "inflammation of the meninges",         "mening + -itis"),
    ("pancreatitis",    "inflammation of the pancreas",         "pancreat + -itis"),
    ("thrombosis",      "abnormal clotting in a vessel",        "thromb + -osis"),
    ("fibrosis",        "formation of excess fibrous tissue",   "fibr + -osis"),
    ("cardiomegaly",    "enlargement of the heart",             "cardi + -megaly"),
    ("erythrocyte",     "red blood cell",                       "erythro- + -cyte"),
    ("phlebitis",       "inflammation of a vein",               "phleb + -itis"),
    ("hepatitis",       "inflammation of the liver",            "hepat + -itis"),
    ("bronchitis",      "inflammation of the bronchi",          "bronch + -itis"),
    ("colitis",         "inflammation of the colon",            "col + -itis"),
    ("sinusitis",       "inflammation of the sinuses",          "sinus + -itis"),
    ("stomatitis",      "inflammation of the mouth",            "stomat + -itis"),
    ("otitis",          "inflammation of the ear",              "ot + -itis"),
    ("conjunctivitis",  "inflammation of the conjunctiva",      "conjunctiv + -itis"),
    ("tracheotomy",     "incision into the trachea",            "trache + -otomy"),
    ("hysterectomy",    "surgical removal of the uterus",       "hyster + -ectomy"),
    ("mastectomy",      "surgical removal of the breast",       "mast + -ectomy"),
    ("nephrectomy",     "surgical removal of the kidney",       "nephr + -ectomy"),
    ("glossitis",       "inflammation of the tongue",           "gloss + -itis"),
    ("neuralgia",       "nerve pain",                           "neur + -algia"),
    ("myopathy",        "disease of the muscle",                "my + -pathy"),
    ("neuropathy",      "disease of the nerves",                "neur + -pathy"),
    ("cardiomyopathy",  "disease of heart muscle",              "cardi + my + -pathy"),
    ("hemolysis",       "destruction of red blood cells",       "hem + -lysis"),
    ("thrombocytopenia","deficiency of platelets",              "thromb + cyt + -penia"),
]


# ─── Session state (in-memory, per user_id) ───────────────────────────────────

_sessions: dict[int, dict] = {}


def start_session(user_id: int, mode: str) -> dict:
    """
    mode: 'term_to_meaning' or 'meaning_to_term'
    Returns the first question dict.
    """
    pool = QUIZ_TERMS.copy()
    random.shuffle(pool)
    _sessions[user_id] = {
        "mode": mode,
        "pool": pool,
        "index": 0,
        "score": 0,
        "streak": 0,
        "best_streak": 0,
        "lives": 3,
        "total": min(10, len(pool)),  # 10 questions per round
        "answered": [],
    }
    return _next_question(user_id)


def _next_question(user_id: int) -> dict:
    s = _sessions[user_id]
    if s["index"] >= s["total"] or s["lives"] <= 0:
        return _end_session(user_id)

    term, meaning, hint = s["pool"][s["index"]]
    mode = s["mode"]

    if mode == "term_to_meaning":
        question_text = f"❓ What does *{term}* mean?"
        answer = meaning
    else:
        question_text = f"❓ Name the term that means:\n_{meaning}_"
        answer = term

    return {
        "type": "question",
        "question": question_text,
        "answer": answer,
        "hint": hint,
        "term": term,
        "meaning": meaning,
        "index": s["index"] + 1,
        "total": s["total"],
        "score": s["score"],
        "lives": s["lives"],
        "streak": s["streak"],
    }


def check_answer(user_id: int, user_answer: str) -> dict:
    """
    Returns dict with:
      - correct (bool)
      - feedback (str)
      - next: question dict or end dict
    """
    if user_id not in _sessions:
        return {"type": "no_session"}

    s = _sessions[user_id]
    q_index = s["index"]
    term, meaning, hint = s["pool"][q_index]
    mode = s["mode"]
    correct_answer = meaning if mode == "term_to_meaning" else term

    # Flexible matching: lowercase, strip, partial
    ua = user_answer.strip().lower()
    ca = correct_answer.strip().lower()

    # Check: exact, or all key words present, or edit distance close
    correct = (ua == ca) or _fuzzy_match(ua, ca)

    if correct:
        s["score"] += 1
        s["streak"] += 1
        s["best_streak"] = max(s["streak"], s["best_streak"])
        feedback = _correct_feedback(s["streak"])
    else:
        s["lives"] -= 1
        s["streak"] = 0
        feedback = _wrong_feedback(correct_answer, hint)

    s["index"] += 1
    s["answered"].append({"term": term, "correct": correct})
    next_q = _next_question(user_id)

    return {
        "type": "answer",
        "correct": correct,
        "feedback": feedback,
        "next": next_q,
    }


def _fuzzy_match(user: str, correct: str) -> bool:
    """True if user answer contains all key content words from correct answer."""
    stop = {"of", "the", "a", "an", "in", "or", "and", "is", "to", "that"}
    key_words = [w for w in correct.split() if w not in stop and len(w) > 3]
    if not key_words:
        return False
    matched = sum(1 for w in key_words if w in user)
    return matched >= max(1, len(key_words) * 0.6)


def _correct_feedback(streak: int) -> str:
    if streak >= 5:
        return f"🔥 INCREDIBLE! {streak} in a row!"
    elif streak >= 3:
        return f"⚡ On fire! {streak} streak!"
    return random.choice(["✅ Correct!", "✅ Well done!", "✅ Exactly right!", "✅ Perfect!"])


def _wrong_feedback(correct: str, hint: str) -> str:
    return f"❌ Not quite.\n✅ Answer: _{correct}_\n🧩 Breakdown: `{hint}`"


def _end_session(user_id: int) -> dict:
    s = _sessions.pop(user_id, {})
    total = s.get("total", 10)
    score = s.get("score", 0)
    best_streak = s.get("best_streak", 0)
    pct = round(score / total * 100)

    if pct == 100:
        grade = "🏆 Perfect score!"
    elif pct >= 80:
        grade = "🌟 Excellent!"
    elif pct >= 60:
        grade = "📈 Good effort!"
    elif pct >= 40:
        grade = "📚 Keep studying!"
    else:
        grade = "💪 Don't give up — practice makes perfect!"

    return {
        "type": "end",
        "score": score,
        "total": total,
        "pct": pct,
        "best_streak": best_streak,
        "grade": grade,
    }


def get_session(user_id: int) -> dict | None:
    return _sessions.get(user_id)


def hint_for_current(user_id: int) -> str | None:
    s = _sessions.get(user_id)
    if not s:
        return None
    idx = s["index"]
    if idx >= len(s["pool"]):
        return None
    term, meaning, hint = s["pool"][idx]
    return f"🧩 Hint: `{hint}`"


def skip_question(user_id: int) -> dict:
    s = _sessions.get(user_id)
    if not s:
        return {"type": "no_session"}
    s["lives"] -= 1
    s["streak"] = 0
    s["index"] += 1
    return _next_question(user_id)
