# mcp-myfitnesspal

MCP server that pulls data from your MyFitnessPal account — food diary, exercise log, measurements, and nutrition summaries.

> MFP deprecated their public API in 2020. This server uses cookie-based auth against the MFP website via the `myfitnesspal` Python library.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e .

cp .env.example .env
# edit .env with your MFP credentials
```

## Tools

| Tool | Description |
|------|-------------|
| `get_food_diary` | Full diary for one day — all meals, foods, macros |
| `get_food_diary_range` | Daily totals for a date range (max 30 days) |
| `get_exercise_diary` | Exercise/cardio log for one day |
| `get_measurements` | Weight or body measurement history (up to 365 days) |
| `get_nutrition_summary` | Aggregated + averaged macros for a date range |
| `get_goals` | Daily nutrition targets from MFP |

## Claude Code integration

Add to `.claude/mcp_servers.json` (project) or `~/.claude/mcp_servers.json` (global):

```json
{
  "mcpServers": {
    "myfitnesspal": {
      "command": "/Users/icaro/icaro_lifestyle/tech/mcp_myfitnesspal/.venv/bin/python3",
      "args": ["/Users/icaro/icaro_lifestyle/tech/mcp_myfitnesspal/server.py"],
      "env": {
        "MFP_USERNAME": "your_username",
        "MFP_PASSWORD": "your_password"
      }
    }
  }
}
```

Or use a `.env` file in the project directory instead of hardcoding credentials in the MCP config.
