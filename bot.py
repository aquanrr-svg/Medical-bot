"""
bot.py — Medical Term Decoder Bot v2
Features: decode, quiz, flashcards, batch scan, reverse lookup,
          leaderboard, user profiles, XP system.
"""

import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

import decoder
import formatter
import quiz as quiz_engine
import flashcards as fc_engine
import batch_scan
import reverse_lookup
import stats

_AI_ENABLED = bool(os.environ.get("GEMINI_API_KEY"))
if _AI_ENABLED:
    import ai_fallback

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _uid(update): return update.effective_user.id
def _uname(update):
    u = update.effective_user
    return u.username or u.first_name or str(u.id)

def _esc(text):
    import re
    return re.sub(r"([\_\*\[\]\(\)\~\`\>\#\+\-\=\|\{\}\.\!])", r"\\\1", str(text))

async def _reply(update, text):
    await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

async def _typing(update):
    await update.effective_message.chat.send_action("typing")

# ─── /start /help ─────────────────────────────────────────────────────────────

async def cmd_start(update, ctx):
    stats.record_event(_uid(update), "decode", _uname(update), 0)
    await _reply(update, formatter.format_help_v2())

async def cmd_help(update, ctx):
    await _reply(update, formatter.format_help_v2())

# ─── /decode ──────────────────────────────────────────────────────────────────

async def cmd_decode(update, ctx):
    if not ctx.args:
        await _reply(update, "Usage: /decode `tonsillitis`")
        return
    await _process_term(update, " ".join(ctx.args).strip())

async def _process_term(update, term):
    await _typing(update)
    result = decoder.decode(term)
    ai_data = None
    if result["found"]:
        if _AI_ENABLED and len(result["parts"]) < 2:
            ai_data = ai_fallback.explain_with_ai(term)
        msg = formatter.format_decode_result(result, ai_data)
    else:
        if _AI_ENABLED:
            ai_data = ai_fallback.explain_with_ai(term)
        msg = formatter.format_decode_result(result, ai_data) if ai_data else formatter.format_not_found(term)
    stats.record_event(_uid(update), "decode", _uname(update))
    await _reply(update, msg)

# ─── /prefix /root /suffix ────────────────────────────────────────────────────

async def cmd_prefix(update, ctx):
    if not ctx.args:
        await _reply(update, "Usage: /prefix hyper"); return
    key = ctx.args[0].lower().rstrip("-") + "-"
    data = decoder.PREFIXES.get(key) or decoder.PREFIXES.get(
        next((k for k in decoder.PREFIXES if k.startswith(ctx.args[0].lower())), ""), None)
    if data:
        stats.record_event(_uid(update), "lookup", _uname(update))
        await _reply(update, formatter.format_morpheme_lookup(key, data, "prefix"))
    else:
        await _reply(update, "Prefix not found\\.")

async def cmd_root(update, ctx):
    if not ctx.args:
        await _reply(update, "Usage: /root cardi"); return
    key = ctx.args[0].lower()
    data = decoder.ROOTS.get(key)
    if not data:
        key = next((k for k in decoder.ROOTS if key in k or k in key), None)
        data = decoder.ROOTS.get(key) if key else None
    if data:
        stats.record_event(_uid(update), "lookup", _uname(update))
        await _reply(update, formatter.format_morpheme_lookup(key, data, "root"))
    else:
        await _reply(update, "Root not found\\.")

async def cmd_suffix(update, ctx):
    if not ctx.args:
        await _reply(update, "Usage: /suffix \\-itis"); return
    key = "-" + ctx.args[0].lower().lstrip("-")
    data = decoder.SUFFIXES.get(key)
    if not data:
        key = next((k for k in decoder.SUFFIXES if key.lstrip("-") in k), None)
        data = decoder.SUFFIXES.get(key) if key else None
    if data:
        stats.record_event(_uid(update), "lookup", _uname(update))
        await _reply(update, formatter.format_morpheme_lookup(key, data, "suffix"))
    else:
        await _reply(update, "Suffix not found\\.")

async def cmd_random(update, ctx):
    await _reply(update, formatter.format_random_example())

# ─── QUIZ ─────────────────────────────────────────────────────────────────────

async def cmd_quiz(update, ctx):
    keyboard = [[
        InlineKeyboardButton("📖 Term → Meaning", callback_data="quiz_mode:term_to_meaning"),
        InlineKeyboardButton("🔤 Meaning → Term",  callback_data="quiz_mode:meaning_to_term"),
    ]]
    await update.effective_message.reply_text(
        "🧠 *Quiz Mode*\n\nChoose your quiz style:",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

def _fmt_question(q):
    if q["type"] == "end": return _fmt_end(q)
    hearts = "❤️" * q["lives"] + "🖤" * (3 - q["lives"])
    streak = f" 🔥{q['streak']}" if q["streak"] >= 2 else ""
    return (
        f"*Question {_esc(q['index'])}/{_esc(q['total'])}* {hearts}{_esc(streak)}\n\n"
        f"{_esc(q['question'])}\n\n"
        f"_Score: {_esc(q['score'])} pts — type your answer_"
    )

def _fmt_end(q):
    return (
        f"🏁 *Quiz Complete\\!*\n\n"
        f"Score: {_esc(q['score'])}/{_esc(q['total'])} \\({_esc(q['pct'])}%\\)\n"
        f"Best streak: {_esc(q['best_streak'])} 🔥\n\n"
        f"{_esc(q['grade'])}\n\n"
        f"Use /quiz to play again or /profile to see your stats\\."
    )

def _quiz_btns():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("💡 Hint", callback_data="quiz_action:hint"),
        InlineKeyboardButton("⏭️ Skip", callback_data="quiz_action:skip"),
        InlineKeyboardButton("🛑 End",  callback_data="quiz_action:end"),
    ]])

async def quiz_mode_cb(update, ctx):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    mode = q.data.split(":")[1]
    question = quiz_engine.start_session(uid, mode)
    await q.edit_message_text(_fmt_question(question), parse_mode=ParseMode.MARKDOWN_V2, reply_markup=_quiz_btns())

async def quiz_action_cb(update, ctx):
    q = update.callback_query
    uid = q.from_user.id
    action = q.data.split(":")[1]
    await q.answer()
    if action == "hint":
        hint = quiz_engine.hint_for_current(uid)
        await q.answer(hint or "No hint available.", show_alert=True)
        return
    if action in ("skip", "end"):
        session = quiz_engine.get_session(uid)
        if session and action == "end":
            session["lives"] = 0
        nq = quiz_engine.skip_question(uid)
        txt = _fmt_end(nq) if nq["type"] == "end" else _fmt_question(nq)
        markup = None if nq["type"] == "end" else _quiz_btns()
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=markup)

async def _handle_quiz_answer(update, ctx):
    uid = _uid(update)
    if not quiz_engine.get_session(uid):
        return False
    result = quiz_engine.check_answer(uid, update.message.text.strip())
    stats.record_event(uid, "quiz_correct" if result["correct"] else "quiz_total", _uname(update))
    nq = result["next"]
    feedback = _esc(result["feedback"])
    if nq["type"] == "end":
        await _reply(update, f"{feedback}\n\n{_fmt_end(nq)}")
    else:
        await update.message.reply_text(
            f"{feedback}\n\n{_fmt_question(nq)}",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_quiz_btns(),
        )
    return True

# ─── FLASHCARDS ───────────────────────────────────────────────────────────────

async def cmd_flashcard(update, ctx):
    uid = _uid(update)
    s = fc_engine.get_stats(uid)
    if s["due"] == 0:
        await _reply(update,
            f"✅ No cards due right now\\!\n\n"
            f"Mastered: {s['mastered']} \\| Learning: {s['learning']} \\| New: {s['new']}\n"
            f"Come back tomorrow\\.")
        return
    card = fc_engine.get_due_card(uid)
    await update.effective_message.reply_text(
        f"🃏 *Flashcard* \\({_esc(card['due_count'])} due today\\)\n\n"
        f"*What does this mean?*\n\n`{_esc(card['term'])}`",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("👁️ Reveal", callback_data=f"fc_reveal:{card['term']}")
        ]]),
    )

async def fc_reveal_cb(update, ctx):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    term = q.data.split(":", 1)[1]
    card = fc_engine.get_due_card(uid)
    if not card or card["term"] != term:
        await q.edit_message_text("Card expired\\. Use /flashcard\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    await q.edit_message_text(
        f"🃏 *{_esc(term)}*\n\n✅ *Answer:* _{_esc(card['meaning'])}_\n🧩 *Parts:* `{_esc(card['hint'])}`\n\nDid you know it?",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Got it",    callback_data=f"fc_mark:{term}:correct"),
            InlineKeyboardButton("❌ Missed it", callback_data=f"fc_mark:{term}:wrong"),
        ]]),
    )

async def fc_mark_cb(update, ctx):
    q = update.callback_query
    await q.answer()
    _, term, result_str = q.data.split(":", 2)
    uid = q.from_user.id
    correct = result_str == "correct"
    fc_result = fc_engine.mark_result(uid, term, correct)
    stats.record_event(uid, "flashcard", q.from_user.username or "")
    interval = fc_result.get("interval", 1)
    remaining = fc_result.get("remaining_today", 0)
    feedback = "✅ Scheduled further out\\." if correct else "❌ Will repeat sooner\\."
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Next Card", callback_data="fc_next")]]) if remaining > 0 else None
    await q.edit_message_text(
        f"{feedback}\n📅 Next in: *{interval} day\\(s\\)*\n📋 Remaining: *{remaining}*",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=markup,
    )

async def fc_next_cb(update, ctx):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    card = fc_engine.get_due_card(uid)
    if not card:
        await q.edit_message_text("✅ All done for today\\! Come back tomorrow\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    await q.edit_message_text(
        f"🃏 *Flashcard* \\({_esc(card['due_count'])} due\\)\n\n*What does this mean?*\n\n`{_esc(card['term'])}`",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👁️ Reveal", callback_data=f"fc_reveal:{card['term']}")]]),
    )

# ─── BATCH SCAN ───────────────────────────────────────────────────────────────

_scan_awaiting: set = set()

async def cmd_scan(update, ctx):
    _scan_awaiting.add(_uid(update))
    await _reply(update,
        "📄 *Batch Scan Mode*\n\nPaste your lecture text or clinical notes below\\.\n"
        "I'll identify all medical terms and add inline mini\\-definitions\\.\n\n_Send /cancel to abort\\._"
    )

async def _handle_scan(update, ctx):
    uid = _uid(update)
    if uid not in _scan_awaiting:
        return False
    _scan_awaiting.discard(uid)
    text = update.message.text.strip()
    if len(text) < 20:
        await _reply(update, "Text too short\\. Please paste actual lecture content\\.")
        return True
    await _typing(update)
    result = batch_scan.scan_text(text, use_ai=_AI_ENABLED)
    stats.record_event(uid, "scan", _uname(update))
    for chunk in batch_scan.format_scan_report(result):
        await _reply(update, chunk)
    return True

# ─── REVERSE LOOKUP ───────────────────────────────────────────────────────────

async def cmd_lookup(update, ctx):
    if not ctx.args:
        await _reply(update, "Usage: /lookup `inflammation`\nSearch terms by meaning or morpheme\\.")
        return
    keyword = " ".join(ctx.args).strip()
    await _typing(update)
    morpheme_results = reverse_lookup.search_by_meaning(keyword)
    term_results = reverse_lookup.search_terms_by_meaning(keyword)
    morph_usage = reverse_lookup.morpheme_reverse(keyword)
    stats.record_event(_uid(update), "lookup", _uname(update))
    if not morpheme_results and not term_results and not morph_usage:
        await _reply(update, f"No results for *{_esc(keyword)}*\\.")
        return
    lines = [f"🔍 *Reverse Lookup: {_esc(keyword)}*\n"]
    if morpheme_results:
        lines.append("🧩 *Morphemes with this meaning:*")
        for r in morpheme_results[:5]:
            icon = {"prefix":"⬅️","root":"🎯","suffix":"➡️"}.get(r["type"],"•")
            lines.append(f"{icon} `{_esc(r['part'])}` → _{_esc(r['meaning'])}_")
        lines.append("")
    if term_results:
        lines.append("📋 *Terms with this meaning:*")
        for r in term_results[:6]:
            lines.append(f"• *{_esc(r['term'])}* — _{_esc(r['meaning'])}_")
        lines.append("")
    if morph_usage:
        lines.append(f"📚 *Terms using `{_esc(keyword)}`:*")
        for r in morph_usage[:5]:
            lines.append(f"• *{_esc(r['term'])}* — _{_esc(r['meaning'])}_")
    await _reply(update, "\n".join(lines))

# ─── PROFILE & LEADERBOARD ────────────────────────────────────────────────────

async def cmd_profile(update, ctx):
    await _reply(update, stats.format_profile(stats.get_profile(_uid(update))))

async def cmd_leaderboard(update, ctx):
    await _reply(update, stats.format_leaderboard(_uid(update)))

async def cmd_cancel(update, ctx):
    _scan_awaiting.discard(_uid(update))
    await _reply(update, "✅ Cancelled\\.")

# ─── TEXT ROUTER ──────────────────────────────────────────────────────────────

async def handle_text(update, ctx):
    text = update.message.text.strip()
    if text.startswith("/"): return
    if await _handle_quiz_answer(update, ctx): return
    if await _handle_scan(update, ctx): return
    if len(text.split()) > 5:
        await _reply(update, "💬 Send one medical term, or /scan for full text\\.")
        return
    await _process_term(update, text)

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise EnvironmentError("TELEGRAM_BOT_TOKEN not set.")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("help",        cmd_help))
    app.add_handler(CommandHandler("decode",      cmd_decode))
    app.add_handler(CommandHandler("prefix",      cmd_prefix))
    app.add_handler(CommandHandler("root",        cmd_root))
    app.add_handler(CommandHandler("suffix",      cmd_suffix))
    app.add_handler(CommandHandler("random",      cmd_random))
    app.add_handler(CommandHandler("quiz",        cmd_quiz))
    app.add_handler(CommandHandler("flashcard",   cmd_flashcard))
    app.add_handler(CommandHandler("scan",        cmd_scan))
    app.add_handler(CommandHandler("lookup",      cmd_lookup))
    app.add_handler(CommandHandler("profile",     cmd_profile))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_handler(CommandHandler("cancel",      cmd_cancel))
    app.add_handler(CallbackQueryHandler(quiz_mode_cb,   pattern="^quiz_mode:"))
    app.add_handler(CallbackQueryHandler(quiz_action_cb, pattern="^quiz_action:"))
    app.add_handler(CallbackQueryHandler(fc_reveal_cb,   pattern="^fc_reveal:"))
    app.add_handler(CallbackQueryHandler(fc_mark_cb,     pattern="^fc_mark:"))
    app.add_handler(CallbackQueryHandler(fc_next_cb,     pattern="^fc_next$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("Bot v2 started. Polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
