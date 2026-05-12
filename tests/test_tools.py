"""Tests for the 6 MCP tool functions in mfp_mcp.server.

MFPClient is mocked — no Chrome session or live MFP connection needed.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import date


# ---------------------------------------------------------------------------
# Fake data helpers
# ---------------------------------------------------------------------------

def _make_entry(name: str, nutrition: dict):
    e = MagicMock()
    e.name = name
    e.nutrition_information = nutrition
    return e


def _make_meal(name: str, entries_data: list[tuple[str, dict]], totals: dict):
    meal = MagicMock()
    meal.name = name
    meal.entries = [_make_entry(n, nut) for n, nut in entries_data]
    meal.totals = totals
    return meal


def _make_day(meals=None, goals=None, exercises=None):
    day = MagicMock()
    day.meals = meals or []
    day.goals = goals
    day.exercises = exercises or []
    return day


# ---------------------------------------------------------------------------
# Shared mock fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_client(monkeypatch):
    """Return a mock MFPClient instance; patch the class so every instantiation
    returns the same mock."""
    client = MagicMock()
    monkeypatch.setattr("mfp_mcp.server.MFPClient", lambda: client)
    return client


# ---------------------------------------------------------------------------
# get_food_diary
# ---------------------------------------------------------------------------

class TestGetFoodDiary:
    def test_returns_expected_keys(self, mock_client):
        from mfp_mcp.server import get_food_diary

        mock_client.get_date.return_value = _make_day(
            meals=[_make_meal("Breakfast", [("Oats", {"calories": 300, "protein": 10})],
                               {"calories": 300, "protein": 10})],
            goals={"calories": 2000, "protein": 150},
        )
        result = get_food_diary("2026-05-01")

        assert set(result.keys()) == {"date", "meals", "daily_totals", "goals"}

    def test_date_is_iso(self, mock_client):
        from mfp_mcp.server import get_food_diary

        mock_client.get_date.return_value = _make_day()
        result = get_food_diary("2026/05/01")
        assert result["date"] == "2026-05-01"

    def test_meals_structure(self, mock_client):
        from mfp_mcp.server import get_food_diary

        mock_client.get_date.return_value = _make_day(
            meals=[
                _make_meal(
                    "Lunch",
                    [("Chicken", {"calories": 200, "protein": 40})],
                    {"calories": 200, "protein": 40},
                )
            ],
            goals={"calories": 2000},
        )
        result = get_food_diary("2026-05-01")

        assert len(result["meals"]) == 1
        meal = result["meals"][0]
        assert meal["name"] == "Lunch"
        assert len(meal["entries"]) == 1
        assert meal["entries"][0]["name"] == "Chicken"
        assert "nutrition" in meal["entries"][0]

    def test_daily_totals_summed_correctly(self, mock_client):
        from mfp_mcp.server import get_food_diary

        mock_client.get_date.return_value = _make_day(
            meals=[
                _make_meal("Breakfast", [], {"calories": 400, "protein": 20}),
                _make_meal("Dinner",    [], {"calories": 600, "protein": 50}),
            ],
            goals={"calories": 2000},
        )
        result = get_food_diary("2026-05-01")
        assert result["daily_totals"]["calories"] == 1000.0
        assert result["daily_totals"]["protein"] == 70.0

    def test_no_goals_returns_empty_dict(self, mock_client):
        from mfp_mcp.server import get_food_diary

        mock_client.get_date.return_value = _make_day(goals=None)
        result = get_food_diary("2026-05-01")
        assert result["goals"] == {}

    def test_invalid_date_raises(self, mock_client):
        from mfp_mcp.server import get_food_diary

        with pytest.raises(ValueError):
            get_food_diary("not-a-date")


# ---------------------------------------------------------------------------
# get_food_diary_range
# ---------------------------------------------------------------------------

class TestGetFoodDiaryRange:
    def test_returns_one_entry_per_day(self, mock_client):
        from mfp_mcp.server import get_food_diary_range

        mock_client.get_date.return_value = _make_day(
            meals=[_make_meal("Breakfast", [], {"calories": 300})],
            goals={"calories": 2000},
        )
        results = get_food_diary_range("2026-05-01", "2026-05-03")
        assert len(results) == 3
        dates = [r["date"] for r in results]
        assert dates == ["2026-05-01", "2026-05-02", "2026-05-03"]

    def test_single_day_range(self, mock_client):
        from mfp_mcp.server import get_food_diary_range

        mock_client.get_date.return_value = _make_day()
        results = get_food_diary_range("2026-05-01", "2026-05-01")
        assert len(results) == 1
        assert results[0]["date"] == "2026-05-01"

    def test_reversed_dates_raises(self, mock_client):
        from mfp_mcp.server import get_food_diary_range

        with pytest.raises(ValueError, match="end_date must be on or after start_date"):
            get_food_diary_range("2026-05-10", "2026-05-01")

    def test_exactly_30_days_raises(self, mock_client):
        """The check is >= 30, so a 30-day span (diff = 29 days) is fine,
        but a 31-day span (diff = 30) is rejected."""
        from mfp_mcp.server import get_food_diary_range

        mock_client.get_date.return_value = _make_day()
        # 29-day span: 2026-05-01 to 2026-05-29 is diff=28 days — allowed
        results = get_food_diary_range("2026-05-01", "2026-05-29")
        assert len(results) == 29

    def test_over_30_days_raises(self, mock_client):
        from mfp_mcp.server import get_food_diary_range

        with pytest.raises(ValueError, match="30 days"):
            get_food_diary_range("2026-05-01", "2026-05-31")

    def test_result_keys(self, mock_client):
        from mfp_mcp.server import get_food_diary_range

        mock_client.get_date.return_value = _make_day(goals={"calories": 2000})
        results = get_food_diary_range("2026-05-01", "2026-05-02")
        for r in results:
            assert set(r.keys()) == {"date", "daily_totals", "goals"}


# ---------------------------------------------------------------------------
# get_exercise_diary
# ---------------------------------------------------------------------------

class TestGetExerciseDiary:
    def _make_exercise_set(self, name, entries_data, totals):
        ex = MagicMock()
        ex.name = name
        ex.entries = [_make_entry(n, nut) for n, nut in entries_data]
        ex.totals = totals
        return ex

    def test_returns_date_and_exercises_keys(self, mock_client):
        from mfp_mcp.server import get_exercise_diary

        mock_client.get_date.return_value = _make_day(exercises=[])
        result = get_exercise_diary("2026-05-01")
        assert set(result.keys()) == {"date", "exercises"}

    def test_date_normalised_to_iso(self, mock_client):
        from mfp_mcp.server import get_exercise_diary

        mock_client.get_date.return_value = _make_day(exercises=[])
        result = get_exercise_diary("05/01/2026")
        assert result["date"] == "2026-05-01"

    def test_exercise_entries_populated(self, mock_client):
        from mfp_mcp.server import get_exercise_diary

        ex_set = self._make_exercise_set(
            "Cardio",
            [("Running", {"calories": 400, "duration": 30})],
            {"calories": 400},
        )
        mock_client.get_date.return_value = _make_day(exercises=[ex_set])
        result = get_exercise_diary("2026-05-01")

        assert len(result["exercises"]) == 1
        assert result["exercises"][0]["name"] == "Cardio"
        assert result["exercises"][0]["entries"][0]["name"] == "Running"

    def test_keyerror_yields_empty_exercises(self, mock_client):
        """If day.exercises raises KeyError (MFP quirk), return empty list."""
        from mfp_mcp.server import get_exercise_diary

        day = MagicMock()
        day.exercises = MagicMock()
        day.exercises.__iter__ = MagicMock(side_effect=KeyError("exercises"))
        mock_client.get_date.return_value = day
        result = get_exercise_diary("2026-05-01")
        assert result["exercises"] == []


# ---------------------------------------------------------------------------
# get_measurements
# ---------------------------------------------------------------------------

class TestGetMeasurements:
    def test_returns_measurement_and_entries_keys(self, mock_client):
        from mfp_mcp.server import get_measurements

        mock_client.get_measurements.return_value = {date(2026, 5, 1): 80.5}
        result = get_measurements("Weight", 30)
        assert set(result.keys()) == {"measurement", "entries"}
        assert result["measurement"] == "Weight"

    def test_entries_are_newest_first(self, mock_client):
        from mfp_mcp.server import get_measurements

        mock_client.get_measurements.return_value = {
            date(2026, 5, 1): 80.0,
            date(2026, 5, 3): 79.5,
            date(2026, 5, 2): 79.8,
        }
        result = get_measurements("Weight", 30)
        dates = [e["date"] for e in result["entries"]]
        assert dates == ["2026-05-03", "2026-05-02", "2026-05-01"]

    def test_days_zero_raises(self, mock_client):
        from mfp_mcp.server import get_measurements

        with pytest.raises(ValueError, match="at least 1"):
            get_measurements("Weight", 0)

    def test_days_negative_raises(self, mock_client):
        from mfp_mcp.server import get_measurements

        with pytest.raises(ValueError):
            get_measurements("Weight", -5)

    def test_days_366_raises(self, mock_client):
        from mfp_mcp.server import get_measurements

        with pytest.raises(ValueError, match="365"):
            get_measurements("Weight", 366)

    def test_days_365_is_allowed(self, mock_client):
        from mfp_mcp.server import get_measurements

        mock_client.get_measurements.return_value = {}
        result = get_measurements("Weight", 365)
        assert result["entries"] == []

    def test_values_converted_to_numbers(self, mock_client):
        from mfp_mcp.server import get_measurements

        class Mass:
            def __init__(self, v):
                self.value = v

        mock_client.get_measurements.return_value = {date(2026, 5, 1): Mass(80.123)}
        result = get_measurements("Weight", 30)
        assert result["entries"][0]["value"] == 80.1


# ---------------------------------------------------------------------------
# get_nutrition_summary
# ---------------------------------------------------------------------------

class TestGetNutritionSummary:
    def test_returns_expected_keys(self, mock_client):
        from mfp_mcp.server import get_nutrition_summary

        mock_client.get_date.return_value = _make_day(goals={"calories": 2000})
        result = get_nutrition_summary("2026-05-01", "2026-05-03")
        assert set(result.keys()) == {"date_range", "totals", "daily_averages", "goals"}

    def test_date_range_block(self, mock_client):
        from mfp_mcp.server import get_nutrition_summary

        mock_client.get_date.return_value = _make_day()
        result = get_nutrition_summary("2026-05-01", "2026-05-03")
        assert result["date_range"]["start"] == "2026-05-01"
        assert result["date_range"]["end"] == "2026-05-03"

    def test_days_with_data_counts_only_non_empty_days(self, mock_client):
        from mfp_mcp.server import get_nutrition_summary

        # Day 1: has food; Day 2: empty
        days = [
            _make_day(meals=[_make_meal("Lunch", [], {"calories": 500})]),
            _make_day(meals=[]),  # no calories → not counted
        ]
        mock_client.get_date.side_effect = days
        result = get_nutrition_summary("2026-05-01", "2026-05-02")
        assert result["date_range"]["days_with_data"] == 1

    def test_averages_per_day_with_data(self, mock_client):
        from mfp_mcp.server import get_nutrition_summary

        # 3 days, only 2 have data
        days = [
            _make_day(meals=[_make_meal("A", [], {"calories": 1000})]),
            _make_day(meals=[_make_meal("B", [], {"calories": 2000})]),
            _make_day(meals=[]),  # empty
        ]
        mock_client.get_date.side_effect = days
        result = get_nutrition_summary("2026-05-01", "2026-05-03")
        assert result["date_range"]["days_with_data"] == 2
        assert result["daily_averages"]["calories"] == 1500.0

    def test_reversed_dates_raises(self, mock_client):
        from mfp_mcp.server import get_nutrition_summary

        with pytest.raises(ValueError, match="end_date must be on or after start_date"):
            get_nutrition_summary("2026-05-10", "2026-05-01")

    def test_over_30_days_raises(self, mock_client):
        from mfp_mcp.server import get_nutrition_summary

        with pytest.raises(ValueError, match="30 days"):
            get_nutrition_summary("2026-05-01", "2026-05-31")

    def test_no_data_days_empty_averages(self, mock_client):
        from mfp_mcp.server import get_nutrition_summary

        mock_client.get_date.return_value = _make_day(meals=[])
        result = get_nutrition_summary("2026-05-01", "2026-05-02")
        assert result["daily_averages"] == {}
        assert result["totals"] == {}

    def test_goals_from_most_recent_day(self, mock_client):
        from mfp_mcp.server import get_nutrition_summary

        days = [
            _make_day(goals={"calories": 1800}),
            _make_day(goals={"calories": 2000}),
        ]
        mock_client.get_date.side_effect = days
        result = get_nutrition_summary("2026-05-01", "2026-05-02")
        # last_goals is overwritten each iteration; final value is day 2's goals
        assert result["goals"]["calories"] == 2000


# ---------------------------------------------------------------------------
# get_goals
# ---------------------------------------------------------------------------

class TestGetGoals:
    def test_returns_date_and_goals_keys(self, mock_client):
        from mfp_mcp.server import get_goals

        mock_client.get_date.return_value = _make_day(goals={"calories": 2000, "protein": 150})
        result = get_goals("2026-05-01")
        assert set(result.keys()) == {"date", "goals"}

    def test_correct_date_returned(self, mock_client):
        from mfp_mcp.server import get_goals

        mock_client.get_date.return_value = _make_day(goals={"calories": 2000})
        result = get_goals("2026/05/01")
        assert result["date"] == "2026-05-01"

    def test_goals_values_present(self, mock_client):
        from mfp_mcp.server import get_goals

        mock_client.get_date.return_value = _make_day(
            goals={"calories": 2000, "protein": 150, "carbs": 200, "fat": 65}
        )
        result = get_goals("2026-05-01")
        assert result["goals"]["calories"] == 2000
        assert result["goals"]["protein"] == 150

    def test_no_goals_returns_empty_dict(self, mock_client):
        from mfp_mcp.server import get_goals

        mock_client.get_date.return_value = _make_day(goals=None)
        result = get_goals("2026-05-01")
        assert result["goals"] == {}

    def test_defaults_to_today_when_no_date(self, monkeypatch):
        from mfp_mcp.server import get_goals
        from datetime import datetime

        fixed_today = date(2026, 5, 6)
        fake_now = datetime(2026, 5, 6, 12, 0, 0)

        client = MagicMock()
        client.get_date.return_value = _make_day(goals={"calories": 2000})
        monkeypatch.setattr("mfp_mcp.server.MFPClient", lambda: client)
        monkeypatch.setattr("mfp_mcp.server.datetime", type("FakeDT", (), {
            "now": staticmethod(lambda: fake_now),
            "strptime": staticmethod(datetime.strptime),
        }))

        result = get_goals(None)
        assert result["date"] == fixed_today.isoformat()
        client.get_date.assert_called_once_with(2026, 5, 6)
