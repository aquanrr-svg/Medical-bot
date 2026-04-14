"""
ai_fallback.py — Uses Google Gemini API to explain rare/unrecognized medical terms.
Called only when the local decoder fails to find any morpheme match.
Free tier: 15 req/min, 1M tokens/day via gemini-1.5-flash.
"""

import os
import json
import google.generativeai as genai

_model = None


def _get_model():
    global _model
    if _model is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY not set.")
        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel("gemini-1.5-flash")
    return _model


PROMPT_TEMPLATE = """You are a medical terminology expert helping medical students.
Explain the medical term: {term}

Respond ONLY with a JSON object, no markdown, no extra text:
{{
  "definition": "brief clinical definition in 1-2 sentences",
  "breakdown": [
    {{"part": "prefix/root/suffix text", "type": "prefix|root|suffix", "meaning": "what it means"}}
  ],
  "reconstructed_meaning": "plain English meaning built from the parts",
  "related_terms": ["term1", "term2", "term3"],
  "pronunciation": "phonetic e.g. kar-dee-oh-MY-oh-puh-thee"
}}
If no clear morpheme breakdown, set breakdown to []. Be medically accurate."""


def explain_with_ai(term: str) -> dict | None:
    """
    Ask Gemini to explain a medical term.
    Returns a dict on success, None on failure.
    """
    try:
        model = _get_model()
        response = model.generate_content(PROMPT_TEMPLATE.format(term=term))
        raw = response.text.strip()

        # Strip markdown fences if Gemini adds them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        return json.loads(raw)

    except Exception as e:
        print(f"[ai_fallback] Gemini error: {e}")
        return None
