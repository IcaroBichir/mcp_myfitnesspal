from __future__ import annotations

from datetime import date

from .auth import load_auth


class MFPClient:
    def __init__(self) -> None:
        import myfitnesspal
        cj, username = load_auth()
        self._mfp = myfitnesspal.Client(username=username, login=False, unit_aware=True)
        self._mfp.session.cookies.update(cj)

    def get_date(self, year: int, month: int, day: int):
        return self._mfp.get_date(year, month, day)

    def get_measurements(self, measurement: str, *, lower_bound: date) -> dict:
        return self._mfp.get_measurements(measurement, lower_bound=lower_bound)
