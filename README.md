# mcp-myfitnesspal

MCP server that pulls data from your MyFitnessPal account — food diary, exercise log, measurements, and nutrition summaries.

**Repository:** https://github.com/IcaroBichir/mcp_myfitnesspal

> MFP deprecated their public API in 2020. This server authenticates via your existing Chrome browser session — no password entry required.

## Requirements

- Python 3.11+ (3.14 supported via `lxml>=5.0`)
- Google Chrome with an active MyFitnessPal login
- Claude Code CLI

## How auth works

The server reads your MFP session cookies from Chrome via `browser_cookie3`. On macOS, Chrome encrypts its cookie database using a key stored in the system Keychain ("Chrome Safe Storage"). The first time the server runs, macOS will show a dialog asking for permission to access that key — click **Allow**. The cookies are then saved to `~/.mfp_cookies.pkl` and reused for 12 hours, so subsequent server starts (including across Claude sessions) don't trigger the dialog again.

To force a fresh cookie read — for example, after logging back into MFP in Chrome — delete the cache file:

```bash
rm ~/.mfp_cookies.pkl
```

## Tools

| Tool | What it returns |
|------|-----------------|
| `get_food_diary` | Full diary for one day — every meal, food item, and macro |
| `get_food_diary_range` | Daily totals only for a date range (max 30 days) |
| `get_exercise_diary` | Exercise and cardio log for one day |
| `get_measurements` | Weight or body measurement history (up to 365 days back) |
| `get_nutrition_summary` | Aggregated + averaged macros over a date range |
| `get_goals` | Daily nutrition targets from MFP |

---

## Install with Claude

Paste this prompt into Claude Code and it will clone the repo and handle the full setup:

```
Set up the MyFitnessPal MCP server for me.

Steps to complete:
1. Clone the repo:
   git clone https://github.com/IcaroBichir/mcp_myfitnesspal.git ~/mcp_myfitnesspal
2. Create a Python virtual environment inside it:
   cd ~/mcp_myfitnesspal && python3 -m venv .venv
3. Install dependencies:
   .venv/bin/pip install "lxml>=5.0" "mcp[cli]" myfitnesspal browser-cookie3
   (or simply: .venv/bin/pip install -e .)
4. Warm the cookie cache:
   cd ~/mcp_myfitnesspal && .venv/bin/python3 -c "import server; server._get_client(); print('Auth OK')"
   (macOS will show a Keychain dialog — click Allow. This only happens once.)
5. Register the server globally with Claude Code:
   claude mcp add -s user myfitnesspal \
     ~/mcp_myfitnesspal/.venv/bin/python3 -- \
     ~/mcp_myfitnesspal/server.py

Before running step 4, make sure you are logged into myfitnesspal.com in Google Chrome.
```

After Claude registers the server, start a new Claude Code session to use it.

---

## Manual install

### 1. Clone the repo

```bash
git clone https://github.com/IcaroBichir/mcp_myfitnesspal.git ~/mcp_myfitnesspal
cd ~/mcp_myfitnesspal
```

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
.venv/bin/pip install "lxml>=5.0" "mcp[cli]" myfitnesspal browser-cookie3
```

> **Python 3.14 note:** `lxml` 4.x doesn't build on 3.14. The `lxml>=5.0` pin above handles this automatically.

### 3. Log into MFP in Chrome

Open Chrome and make sure you're logged into [myfitnesspal.com](https://www.myfitnesspal.com).

### 4. Warm the cookie cache

Run this once from the project directory:

```bash
.venv/bin/python3 -c "import server; server._get_client(); print('Auth OK')"
```

macOS will show a dialog: **"python3" wants access to your confidential information stored in "Chrome Safe Storage" in your keychain.** Click **Allow**.

The server reads your MFP session cookies from Chrome, decrypts them using that Keychain key, and saves the result to `~/.mfp_cookies.pkl`. Future server starts (including across Claude Code sessions) load from that file — no further Keychain prompts until the cache expires (12 hours).

### 5. Register with Claude Code

```bash
claude mcp add -s user myfitnesspal \
  ~/mcp_myfitnesspal/.venv/bin/python3 -- \
  ~/mcp_myfitnesspal/server.py
```

The `-s user` flag registers the server globally so it's available in every Claude Code session, not just the current directory. This writes to `~/.claude.json` — the file Claude Code actually manages. Manually editing `.mcp.json` files won't take effect until the next session restart.

### 6. Restart Claude Code

Quit and reopen Claude Code, or open `/hooks` once to reload the MCP config. You should see `myfitnesspal` listed as a connected server.

---

## Testing

Once connected, try these prompts in Claude Code:

- *"What did I eat yesterday?"*
- *"How does my protein average this week compare to my goal?"*
- *"Show me my weight trend over the last 30 days."*
- *"What are my daily nutrition targets?"*

---

## Troubleshooting

**macOS Keychain dialog keeps appearing**
Delete `~/.mfp_cookies.pkl` and re-run step 4. If the dialog appears on every call, the cache write may have failed — check that `~/.mfp_cookies.pkl` exists after running step 4.

**Auth error / no data returned**
The session cookie may have expired. Log out and back into myfitnesspal.com in Chrome, delete `~/.mfp_cookies.pkl`, and re-run step 4.

**`lxml` build error on Python 3.14**
Make sure you're installing `lxml>=5.0`, not just `lxml`. The version constraint is already in `pyproject.toml`.

**Server not appearing in Claude**
Use `claude mcp add -s user` to register — don't edit `.mcp.json` files manually. Restart Claude Code after any config change.

**Chrome not found / wrong browser**
The server uses `browser_cookie3` to read Chrome cookies. Firefox is not currently supported.
