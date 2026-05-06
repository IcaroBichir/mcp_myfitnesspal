# mcp-myfitnesspal

MCP server that pulls data from your MyFitnessPal account — food diary, exercise log, measurements, and nutrition summaries.

**Repository:** https://github.com/IcaroBichir/mcp_myfitnesspal

> MFP deprecated their public API in 2020. This server authenticates via your existing Chrome browser session — no password entry required.

## Requirements

- Python 3.11+ (3.14 supported via `lxml>=5.0`)
- Google Chrome with an active MyFitnessPal login
- Claude Code CLI

## How auth works

The server reads your MFP session cookies from Chrome via `browser_cookie3`. On macOS, Chrome encrypts its cookie database using a key stored in the system Keychain ("Chrome Safe Storage"). The first time the server runs, macOS will show a dialog asking for permission to access that key — click **Allow**.

After reading the cookies, the server follows the MFP `/food/diary` redirect to resolve your MFP username. Both the cookies and username are saved to `~/.config/mfp-mcp/cookies.json` (mode 0600) and reused for 12 hours, so subsequent server starts don't trigger the Keychain dialog again.

To force a fresh auth — for example, after logging back into MFP in Chrome — re-run `mfp-mcp auth`, or delete the cache file manually:

```bash
rm ~/.config/mfp-mcp/cookies.json
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
   .venv/bin/pip install -e .
4. Warm the cookie cache:
   ~/mcp_myfitnesspal/.venv/bin/mfp-mcp auth
   (macOS will show a Keychain dialog — click Allow. This only happens once.)
5. Register the server globally with Claude Code:
   claude mcp add -s user myfitnesspal \
     ~/mcp_myfitnesspal/.venv/bin/mfp-mcp -- serve

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
.venv/bin/pip install -e .
```

> **Python 3.14 note:** `lxml` 4.x doesn't build on 3.14. The `lxml>=5.0` pin in `pyproject.toml` handles this automatically.

### 3. Log into MFP in Chrome

Open Chrome and make sure you're logged into [myfitnesspal.com](https://www.myfitnesspal.com).

### 4. Warm the cookie cache

```bash
.venv/bin/mfp-mcp auth
```

macOS will show a dialog: **"python3" wants access to your confidential information stored in "Chrome Safe Storage" in your keychain.** Click **Allow**.

The command reads your MFP session cookies from Chrome, resolves your MFP username via the `/food/diary` redirect, and saves both to `~/.config/mfp-mcp/cookies.json` (mode 0600). On success it prints:

```
Auth OK — logged in as: your_mfp_username
Cache saved to: /Users/you/.config/mfp-mcp/cookies.json
```

Future server starts load from that file — no further Keychain prompts until the cache expires (12 hours).

### 5. Register with Claude Code

```bash
claude mcp add -s user myfitnesspal \
  ~/mcp_myfitnesspal/.venv/bin/mfp-mcp -- serve
```

The `-s user` flag registers the server globally so it's available in every Claude Code session.

### 6. Restart Claude Code

Quit and reopen Claude Code. You should see `myfitnesspal` listed as a connected server.

---

## Tests

```bash
pip install -e ".[dev]"   # installs pytest
pytest tests/ -v
```

68 tests covering server helper functions (`_parse_date`, `_to_number`, `_format_nutrition`, `_sum_meal_totals`), all 6 MCP tool functions (date validation, range limits, output structure), and `auth.py` cookie-cache logic (valid cache, stale cache, corrupted JSON fallback). No live MFP or Chrome calls — `MFPClient` and `browser_cookie3` are mocked.

---

## Example prompts

Once connected, try these prompts in Claude Code:

- *"What did I eat yesterday?"*
- *"How does my protein average this week compare to my goal?"*
- *"Show me my weight trend over the last 30 days."*
- *"What are my daily nutrition targets?"*

---

## Troubleshooting

**macOS Keychain dialog keeps appearing**
Delete `~/.config/mfp-mcp/cookies.json` and re-run `mfp-mcp auth`. If the dialog appears on every call, the cache write may have failed — check that the file exists after running auth.

**Auth error / no data returned**
The session cookie may have expired. Log out and back into myfitnesspal.com in Chrome, delete `~/.config/mfp-mcp/cookies.json`, and re-run `mfp-mcp auth`.

**`lxml` build error on Python 3.14**
Make sure you're installing via `pip install -e .` — the `lxml>=5.0` constraint in `pyproject.toml` handles this automatically.

**Server not appearing in Claude**
Use `claude mcp add -s user` to register — don't edit `.mcp.json` files manually. Restart Claude Code after any config change.

**Chrome not found / wrong browser**
The server uses `browser_cookie3` to read Chrome cookies. Firefox is not currently supported.
