#!/usr/bin/env python3
"""MyFitnessPal MCP server — pulls diary, exercise, and measurement data."""

import os
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).parent / ".env")

mcp = FastMCP("MyFitnessPal")

_client = None


def _get_client():
    global _client
    if _client is None:
        import myfitnesspal
        username = os.environ.get("MFP_USERNAME")
        password = os.environ.get("MFP_PASSWORD")
        if not username or not password:
            raise RuntimeError("MFP_USERNAME and MFP_PASSWORD must be set")
        _client = myfitnesspal.Client(username, password=password, unit_aware=True)
    return _client


def _parse_date(date_str: str) -> date:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {date_str!r}. Use YYYY-MM-DD.")


def _format_nutrition(nutrition: dict) -> dict:
    """Round floats to one decimal for cleaner output."""
    return {k: round(v, 1) if isinstance(v, float) else v for k, v in nutrition.items()}


@mcp.tool()
def get_food_diary(date: str) -> dict:
    """
    Return the full food diary for a single day.

    Args:
        date: Date in YYYY-MM-DD format (e.g. "2026-05-01")

    Returns a dict with keys:
    - date: the queried date
    - meals: list of meals, each with name, entries (food items + nutrition), and meal totals
    - daily_totals: summed nutrition across all meals
    - goals: daily nutrition targets
    """
    d = _parse_date(date)
    client = _get_client()
    day = client.get_date(d.year, d.month, d.day)

    meals = []
    for meal in day.meals:
        entries = []
        for entry in meal.entries:
            entries.append({
                "name": entry.name,
                "nutrition": _format_nutrition(dict(entry.nutrition_information)),
            })
        meals.append({
            "name": meal.name,
            "entries": entries,
            "totals": _format_nutrition(dict(meal.totals)),
        })

    return {
        "date": date,
        "meals": meals,
        "daily_totals": _format_nutrition(dict(day.totals)),
        "goals": _format_nutrition(dict(day.goals)) if day.goals else {},
    }


@mcp.tool()
def get_food_diary_range(start_date: str, end_date: str) -> list[dict]:
    """
    Return food diary summaries (totals only, no per-entry detail) for a date range.

    Args:
        start_date: Start date in YYYY-MM-DD format (inclusive)
        end_date:   End date in YYYY-MM-DD format (inclusive)

    Each item in the returned list contains: date, daily_totals, goals.
    Limit: 30 days maximum per call to avoid rate limiting.
    """
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if (end - start).days > 30:
        raise ValueError("Date range cannot exceed 30 days per call.")
    if end < start:
        raise ValueError("end_date must be on or after start_date.")

    client = _get_client()
    results = []
    current = start
    while current <= end:
        day = client.get_date(current.year, current.month, current.day)
        results.append({
            "date": current.isoformat(),
            "daily_totals": _format_nutrition(dict(day.totals)),
            "goals": _format_nutrition(dict(day.goals)) if day.goals else {},
        })
        current += timedelta(days=1)
    return results


@mcp.tool()
def get_exercise_diary(date: str) -> dict:
    """
    Return the exercise/cardio log for a single day.

    Args:
        date: Date in YYYY-MM-DD format

    Returns a dict with keys:
    - date: the queried date
    - exercises: list of exercise categories, each with name, entries, and totals
    """
    d = _parse_date(date)
    client = _get_client()
    day = client.get_date(d.year, d.month, d.day)

    exercise_categories = []
    for exercise_set in day.exercises:
        entries = []
        for entry in exercise_set.entries:
            entries.append({
                "name": entry.name,
                "nutrition_information": _format_nutrition(dict(entry.nutrition_information)),
            })
        exercise_categories.append({
            "name": exercise_set.name,
            "entries": entries,
            "totals": _format_nutrition(dict(exercise_set.totals)),
        })

    return {
        "date": date,
        "exercises": exercise_categories,
    }


@mcp.tool()
def get_measurements(measurement: str = "Weight", days: int = 30) -> dict:
    """
    Return measurement history for a given metric.

    Args:
        measurement: The measurement name as it appears in MFP (default: "Weight").
                     Common values: "Weight", "Body Fat", "Neck", "Waist", "Hips"
        days:        How many days back to fetch (default: 30, max: 365)

    Returns a dict with keys:
    - measurement: the metric name
    - unit: the unit string if available
    - entries: list of {date, value} dicts ordered newest-first
    """
    if days > 365:
        raise ValueError("days cannot exceed 365.")
    lower_bound = datetime.now() - timedelta(days=days)
    client = _get_client()
    raw = client.get_measurements(measurement, lower_bound=lower_bound)

    entries = [
        {"date": dt.isoformat() if hasattr(dt, "isoformat") else str(dt), "value": v}
        for dt, v in raw.items()
    ]
    entries.sort(key=lambda x: x["date"], reverse=True)

    return {
        "measurement": measurement,
        "entries": entries,
    }


@mcp.tool()
def get_nutrition_summary(start_date: str, end_date: str) -> dict:
    """
    Return aggregated and averaged nutrition stats for a date range.

    Args:
        start_date: Start date in YYYY-MM-DD format (inclusive)
        end_date:   End date in YYYY-MM-DD format (inclusive)

    Returns a dict with:
    - date_range: {start, end, days_with_data}
    - totals: summed values across all days
    - daily_averages: totals ÷ days_with_data
    - goals: the most recently seen daily goals
    """
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if (end - start).days > 30:
        raise ValueError("Date range cannot exceed 30 days per call.")

    client = _get_client()
    totals: dict = {}
    days_with_data = 0
    last_goals: dict = {}

    current = start
    while current <= end:
        day = client.get_date(current.year, current.month, current.day)
        day_totals = dict(day.totals)
        if any(v for v in day_totals.values()):
            days_with_data += 1
            for key, val in day_totals.items():
                totals[key] = totals.get(key, 0) + (val or 0)
        if day.goals:
            last_goals = dict(day.goals)
        current += timedelta(days=1)

    averages = (
        {k: round(v / days_with_data, 1) for k, v in totals.items()}
        if days_with_data > 0
        else {}
    )

    return {
        "date_range": {
            "start": start_date,
            "end": end_date,
            "days_with_data": days_with_data,
        },
        "totals": _format_nutrition(totals),
        "daily_averages": averages,
        "goals": _format_nutrition(last_goals),
    }


@mcp.tool()
def get_goals(date: Optional[str] = None) -> dict:
    """
    Return the daily nutrition goals from MFP.

    Args:
        date: Optional date in YYYY-MM-DD format. Defaults to today.

    Returns the nutrition goal targets (calories, macros, etc.).
    """
    if date is None:
        d = datetime.now().date()
    else:
        d = _parse_date(date)

    client = _get_client()
    day = client.get_date(d.year, d.month, d.day)
    goals = dict(day.goals) if day.goals else {}
    return {
        "date": d.isoformat(),
        "goals": _format_nutrition(goals),
    }


if __name__ == "__main__":
    mcp.run()
