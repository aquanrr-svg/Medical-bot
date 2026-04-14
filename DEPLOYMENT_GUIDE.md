# Medical Term Decoder Bot — Complete Setup Guide

## What This Bot Does
Teaches medical students the **logic of word construction** — not just definitions.
- Breaks medical terms into prefix / root / suffix
- Reconstructs plain-English meaning from parts
- Falls back to AI (Claude Haiku) for rare or unknown terms
- Commands: /decode, /prefix, /root, /suffix, /random

---

## Step 1 — Create Your Telegram Bot (2 min)

1. Open Telegram → search **@BotFather**
2. Send: `/newbot`
3. Choose a name: e.g. `Medical Term Decoder`
4. Choose a username: e.g. `MedTermDecoderBot` (must end in "bot")
5. BotFather gives you a **token** → save it (looks like `123456:ABCdef...`)
6. Optional — set bot commands via BotFather:
   ```
   /setcommands
   decode - Decode a medical term
   prefix - Look up a prefix
   root - Look up a root
   suffix - Look up a suffix
   random - Get a random example
   help - Show help
   ```

---

## Step 2 — Get Anthropic API Key (Optional but recommended)

1. Go to https://console.anthropic.com
2. Sign up → go to **API Keys** → **Create Key**
3. Copy the key (starts with `sk-ant-...`)
4. The bot uses `claude-haiku` (cheapest model ~$0.001 per query)
5. Free tier / $5 credit is enough for thousands of student queries
6. **If you skip this**: bot still works fully using its local morpheme database

---

## Step 3 — Deploy on Railway (Recommended Free Host)

Railway gives 500 free hours/month — enough for a 24/7 bot.

### 3a. Push code to GitHub
```bash
cd medical_term_decoder
git init
git add .
git commit -m "Initial commit"
# Create a repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/medical-term-decoder.git
git push -u origin main
```

### 3b. Deploy on Railway
1. Go to https://railway.app → Sign up with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your repo
4. Railway auto-detects Python via Procfile ✓

### 3c. Set Environment Variables on Railway
In your Railway project dashboard:
- Go to **Variables** tab
- Add:
  ```
  TELEGRAM_BOT_TOKEN = your_token_here
  ANTHROPIC_API_KEY  = your_key_here   (optional)
  ```
- Railway will automatically redeploy

### 3d. Verify
- Go to **Deployments** tab → check logs
- You should see: `Bot started. Polling...`
- Test by messaging your bot on Telegram

---

## Step 4 — Keep It Awake with UptimeRobot (Optional)

Railway's free tier keeps the bot running as a **background worker** (not a web server), 
so it doesn't sleep. UptimeRobot is not strictly needed, but you can add a simple 
health-check HTTP endpoint if you want monitoring.

**To add a health endpoint** (optional):
Add this to bot.py before `app.run_polling()`:
```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args): pass

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

start_health_server()  # Add this line before app.run_polling()
```
Then in UptimeRobot, monitor: `https://your-railway-app.railway.app/`

---

## Project File Structure

```
medical_term_decoder/
├── bot.py              ← Main bot (Telegram handlers)
├── decoder.py          ← Morpheme matching engine
├── ai_fallback.py      ← Claude API for unknown terms
├── formatter.py        ← Telegram message formatting
├── requirements.txt    ← Python dependencies
├── railway.toml        ← Railway deployment config
├── Procfile            ← Process definition
├── .env.example        ← Environment variable template
├── .gitignore
└── data/
    └── morphemes.json  ← Database of 200+ prefixes, roots, suffixes
```

---

## Running Locally (for testing)

```bash
cd medical_term_decoder
pip install -r requirements.txt

# Set env vars
export TELEGRAM_BOT_TOKEN="your_token"
export ANTHROPIC_API_KEY="your_key"   # optional

python bot.py
```

---

## Bot Commands Reference

| Command | Usage | Example |
|---------|-------|---------|
| /decode | /decode \<term\> | /decode tonsillitis |
| /prefix | /prefix \<text\> | /prefix hyper |
| /root   | /root \<text\>   | /root cardi |
| /suffix | /suffix \<text\> | /suffix itis |
| /random | /random          | Random example |
| /help   | /help            | Show all commands |
| (text)  | Just type a term | tonsillitis |

---

## How the Decoder Works

1. **Prefix match** — scans start of word against 70+ prefixes
2. **Suffix match** — scans end of word against 80+ suffixes
3. **Root match** — scans middle of word against 120+ roots
4. **Reconstruction** — combines meanings into plain English:
   - `brady` (slow) + `cardi` (heart) + `-ia` (condition) → *Condition of slow heart rate*
5. **AI fallback** — if <2 parts matched, calls Claude Haiku for explanation

---

## Expanding the Database

Edit `data/morphemes.json` to add more terms. Format:
```json
"prefixes": {
  "new-": { "meaning": "...", "example": "..." }
},
"roots": {
  "newroot": { "meaning": "...", "example": "..." }
},
"suffixes": {
  "-newsuffix": { "meaning": "...", "example": "..." }
}
```

---

## Future Features (Roadmap)

- [ ] **Quiz mode** — `/quiz` gives a term, student guesses meaning
- [ ] **Reverse lookup** — search by meaning → find terms
- [ ] **Batch scan** — paste lecture text, bot highlights all medical terms
- [ ] **Flashcard mode** — spaced repetition for morphemes
- [ ] **Language support** — Arabic/Urdu explanations for regional students

---

## Cost Estimate

| Component | Cost |
|-----------|------|
| Railway hosting | Free (500 hrs/month) |
| Telegram Bot API | Free (unlimited) |
| Claude Haiku (AI fallback) | ~$0.001/query — $5 credit = 5,000 AI queries |
| UptimeRobot | Free |
| **Total** | **~$0/month** |
