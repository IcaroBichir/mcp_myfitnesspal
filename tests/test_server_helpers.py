"""Tests for helper functions in mfp_mcp.server (no I/O, no auth needed)."""
from __future__ import annotations

import pytest
from datetime import date

from mfp_mcp.server import _parse_date, _to_number, _format_nutrition, _sum_meal_totals


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------

class TestParseDate:
    def test_iso_format(self):
        assert _parse_date("2026-05-01") == date(2026, 5, 1)

    def test_slash_ymd_format(self):
        assert _parse_date("2026/05/01") == date(2026, 5, 1)

    def test_us_format(self):
        assert _parse_date("05/01/2026") == date(2026, 5, 1)

    def test_iso_first_of_year(self):
        assert _parse_date("2025-01-01") == date(2025, 1, 1)

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Unrecognized date format"):
            _parse_date("01-05-2026")

    def test_gibberish_raises(self):
        with pytest.raises(ValueError):
            _parse_date("not-a-date")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            _parse_date("")


# ---------------------------------------------------------------------------
# _to_number
# ---------------------------------------------------------------------------

class TestToNumber:
    def test_float_is_rounded(self):
        assert _to_number(3.14159) == 3.1

    def test_float_already_clean(self):
        assert _to_number(2.5) == 2.5

    def test_plain_int_passthrough(self):
        assert _to_number(42) == 42

    def test_object_with_value_attr(self):
        class Energy:
            value = 2000.678

        assert _to_number(Energy()) == 2000.7

    def test_object_value_rounded_to_one_decimal(self):
        class Mass:
            value = 75.999

        assert _to_number(Mass()) == 76.0

    def test_zero_float(self):
        assert _to_number(0.0) == 0.0


# ---------------------------------------------------------------------------
# _format_nutrition
# ---------------------------------------------------------------------------

class TestFormatNutrition:
    def test_plain_dict_passthrough(self):
        result = _format_nutrition({"calories": 500, "protein": 30})
        assert result == {"calories": 500, "protein": 30}

    def test_float_values_rounded(self):
        result = _format_nutrition({"fat": 12.3456, "carbs": 99.9999})
        assert result["fat"] == 12.3
        assert result["carbs"] == 100.0

    def test_unit_aware_objects_converted(self):
        class Energy:
            def __init__(self, v):
                self.value = v

        result = _format_nutrition({"calories": Energy(1987.567)})
        assert result["calories"] == 1987.6

    def test_empty_dict(self):
        assert _format_nutrition({}) == {}

    def test_mixed_types(self):
        class Mass:
            value = 55.64  # rounds unambiguously to 55.6

        result = _format_nutrition({"protein": Mass(), "carbs": 200})
        assert result["protein"] == 55.6
        assert result["carbs"] == 200


# ---------------------------------------------------------------------------
# _sum_meal_totals
# ---------------------------------------------------------------------------

class TestSumMealTotals:
    def test_single_meal(self):
        meals = [{"totals": {"calories": 500, "protein": 30}}]
        result = _sum_meal_totals(meals)
        assert result == {"calories": 500, "protein": 30}

    def test_multiple_meals_sum_correctly(self):
        meals = [
            {"totals": {"calories": 400, "protein": 20, "fat": 10}},
            {"totals": {"calories": 600, "protein": 40, "fat": 15}},
            {"totals": {"calories": 200, "protein": 10, "fat": 5}},
        ]
        result = _sum_meal_totals(meals)
        assert result["calories"] == 1200.0
        assert result["protein"] == 70.0
        assert result["fat"] == 30.0

    def test_empty_list_returns_empty_dict(self):
        assert _sum_meal_totals([]) == {}

    def test_none_values_treated_as_zero(self):
        meals = [
            {"totals": {"calories": 300, "sodium": None}},
            {"totals": {"calories": 200, "sodium": 500}},
        ]
        result = _sum_meal_totals(meals)
        assert result["calories"] == 500.0
        assert result["sodium"] == 500.0

    def test_partial_keys_across_meals(self):
        """Meals may not share the same set of keys."""
        meals = [
            {"totals": {"calories": 100}},
            {"totals": {"protein": 50}},
        ]
        result = _sum_meal_totals(meals)
        assert result["calories"] == 100.0
        assert result["protein"] == 50.0
