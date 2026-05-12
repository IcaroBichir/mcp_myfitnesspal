from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as Date


# ---------------------------------------------------------------------------
# Data model returned by get_date() — matches what server.py expects.
# ---------------------------------------------------------------------------

@dataclass
class FoodEntry:
    name: str
    nutrition_information: dict


@dataclass
class Meal:
    name: str
    entries: list[FoodEntry]
    totals: dict


@dataclass
class ExerciseEntry:
    name: str
    nutrition_information: dict


@dataclass
class ExerciseSet:
    name: str
    entries: list[ExerciseEntry]
    totals: dict


@dataclass
class DayData:
    meals: list[Meal] = field(default_factory=list)
    exercises: list[ExerciseSet] = field(default_factory=list)
    goals: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _nc_to_dict(nc: dict) -> dict:
    """Convert API nutritional_contents → flat dict with 'calories' key."""
    result = {}
    for k, v in nc.items():
        if k == "energy":
            result["calories"] = round(v["value"], 1) if isinstance(v, dict) else v
        else:
            result[k] = v
    return result


def _build_day(items: list[dict]) -> DayData:
    meals: list[Meal] = []
    exercise_entries: list[ExerciseEntry] = []

    for item in items:
        itype = item.get("type")

        if itype == "diary_meal":
            nc = item.get("nutritional_contents", {})
            meals.append(Meal(
                name=item.get("diary_meal", ""),
                entries=[],
                totals=_nc_to_dict(nc),
            ))

        elif itype == "exercise_entry" and not item.get("is_calorie_adjustment", False):
            exercise = item.get("exercise", {})
            energy = item.get("energy", {})
            calories = round(energy["value"], 1) if isinstance(energy, dict) else 0
            exercise_entries.append(ExerciseEntry(
                name=exercise.get("description", "Exercise"),
                nutrition_information={"calories": calories},
            ))

    exercise_sets: list[ExerciseSet] = []
    if exercise_entries:
        total_cal = round(sum(e.nutrition_information.get("calories", 0) for e in exercise_entries), 1)
        exercise_sets.append(ExerciseSet(
            name="Cardio",
            entries=exercise_entries,
            totals={"calories": total_cal},
        ))

    return DayData(meals=meals, exercises=exercise_sets, goals={})


# ---------------------------------------------------------------------------
# Public client
# ---------------------------------------------------------------------------

class MFPClient:
    def __init__(self) -> None:
        from .api_client import MFPApiClient
        self._api = MFPApiClient()

    def get_date(self, year: int, month: int, day: int) -> DayData:
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        items = self._api.get_diary(date_str)
        return _build_day(items)

    def get_measurements(self, measurement: str, *, lower_bound: Date) -> dict:
        to_date = Date.today().isoformat()
        items = self._api.get_measurements(measurement, lower_bound.isoformat(), to_date)
        return {
            Date.fromisoformat(item["date"]): item["value"]
            for item in items
        }
