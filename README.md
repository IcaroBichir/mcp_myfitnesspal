# mcp-myfitnesspal

MCP server that pulls data from your MyFitnessPal account — food diary, exercise log, measurements, and nutrition summaries.

**Repository:** https://github.com/IcaroBichir/mcp_myfitnesspal

> MFP deprecated their public API in 2020. This server uses cookie-based auth against the MFP website via the `myfitnesspal` Python library.

## Requirements

- Python 3.11+ (3.14 supported via `lxml>=5.0`)
- A MyFitnessPal account with a username and password (Google/Facebook SSO accounts won't work — MFP must have a password set)
- Claude Code CLI

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
   .venv/bin/pip install "lxml>=5.0" "mcp[cli]" myfitnesspal python-dotenv
4. Create a .env file at ~/mcp_myfitnesspal/.env with my credentials:
   MFP_USERNAME=<my MFP email or username>
   MFP_PASSWORD=<my MFP password>
5. Register the server globally with Claude Code:
   claude mcp add -s user myfitnesspal \
     ~/mcp_myfitnesspal/.venv/bin/python3 -- \
     ~/mcp_myfitnesspal/server.py
6. Verify it works:
   ~/mcp_myfitnesspal/.venv/bin/python3 -c "import server; print('OK')"

Do not hardcode credentials anywhere except the .env file. Do not commit the .env file.
```

Fill in your MFP credentials before sending. After Claude registers the server, start a new Claude Code session to use it.

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
.venv/bin/pip install "lxml>=5.0" "mcp[cli]" myfitnesspal python-dotenv
```

> **Python 3.14 note:** `lxml` 4.x doesn't build on 3.14. The `lxml>=5.0` pin above handles this automatically.

### 3. Add your credentials

```bash
cp .env.example .env
```

Edit `.env`:

```
MFP_USERNAME=your_email_or_username
MFP_PASSWORD=your_password
```

Keep this file out of version control — `.gitignore` already excludes it.

> **SSO accounts:** If you signed up via Google or Facebook, you'll need to set a password on your MFP account first (Settings → Change Password).

### 4. Verify the server starts cleanly

```bash
.venv/bin/python3 -c "import server; print('OK')"
```

### 5. Register with Claude Code

Run this command (replace the path with wherever you cloned the repo):

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

**Login fails / authentication error**
MFP occasionally adds extra verification steps. Try logging into myfitnesspal.com in a browser first, complete any email verification, then retry.

**`lxml` build error on Python 3.14**
Make sure you're installing `lxml>=5.0`, not just `lxml`. The version constraint is already in `pyproject.toml`.

**Server not appearing in Claude**
Check that the paths in `.mcp.json` are absolute (not `~/` or relative). Restart Claude Code after any config change.

**SSO account / no password**
Go to myfitnesspal.com → Settings → Change Password to set a standalone password for API access.
