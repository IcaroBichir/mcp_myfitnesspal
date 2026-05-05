#!/usr/bin/env python3
"""MyFitnessPal MCP server — pulls diary, exercise, and measurement data."""

import pickle
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional
from mcp.server.fastmcp import FastMCP

_COOKIE_CACHE = Path.home() / ".mfp_cookies.pkl"
_COOKIE_TTL = 12 * 3600  # seconds before re-reading from Chrome

mcp = FastMCP("MyFitnessPal")

_client = None


def _cookies_to_list(cj):
    return [
        {k: getattr(c, k) for k in ("name", "value", "domain", "path", "secure", "expires")}
        for c in cj
    ]


def _list_to_cookiejar(cookie_list):
    import http.cookiejar
    cj = http.cookiejar.CookieJar()
    for attrs in cookie_list:
        c = http.cookiejar.Cookie(
            version=0,
            name=attrs["name"],
            value=attrs["value"],
            port=None, port_specified=False,
            domain=attrs["domain"],
            domain_specified=bool(attrs["domain"]),
            domain_initial_dot=attrs["domain"].startswith("."),
            path=attrs["path"],
            path_specified=bool(attrs["path"]),
            secure=attrs["secure"],
            expires=attrs["expires"],
            discard=True,
            comment=None, comment_url=None,
            rest={},
        )
        cj.set_cookie(c)
    return cj


def _load_cookiejar():
    """Return cached cookiejar from disk, or read fresh from Chrome and cache it."""
    import browser_cookie3
    if _COOKIE_CACHE.exists():
        age = time.time() - _COOKIE_CACHE.stat().st_mtime
        if age < _COOKIE_TTL:
            with open(_COOKIE_CACHE, "rb") as f:
                return _list_to_cookiejar(pickle.load(f))
    cj = browser_cookie3.chrome(domain_name="myfitnesspal.com")
    with open(_COOKIE_CACHE, "wb") as f:
        pickle.dump(_cookies_to_list(cj), f)
    return cj


def _get_client():
    global _client
    if _client is None:
        import myfitnesspal
        _client = myfitnesspal.Client(cookiejar=_load_cookiejar(), unit_aware=True)
    return _client


def _parse_date(date_str: str) -> date:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {date_str!r}. Use YYYY-MM-DD.")


def _to_number(v):
    """Convert measurement library objects (Energy, Mass) or floats to plain numbers."""
    if isinstance(v, float):
        return round(v, 1)
    if hasattr(v, "value"):
        return round(v.value, 1)
    return v


def _format_nutrition(nutrition: dict) -> dict:
    return {k: _to_number(v) for k, v in nutrition.items()}


def _sum_meal_totals(meals: list[dict]) -> dict:
    totals: dict = {}
    for meal in meals:
        for k, v in meal["totals"].items():
            totals[k] = round(totals.get(k, 0) + (v or 0), 1)
    return totals


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
        "daily_totals": _sum_meal_totals(meals),
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
        meal_totals = [
            {"totals": _format_nutrition(dict(meal.totals))}
            for meal in day.meals
        ]
        results.append({
            "date": current.isoformat(),
            "daily_totals": _sum_meal_totals(meal_totals),
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
    try:
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
    except KeyError:
        pass

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
    lower_bound = (datetime.now() - timedelta(days=days)).date()
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
        meal_totals = [
            {"totals": _format_nutrition(dict(meal.totals))}
            for meal in day.meals
        ]
        day_totals = _sum_meal_totals(meal_totals)
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
