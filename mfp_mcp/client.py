from __future__ import annotations

from datetime import date

from .auth import load_auth


class MFPClient:
    def __init__(self) -> None:
        import myfitnesspal
        from unittest.mock import patch
        cj, username = load_auth()
        # myfitnesspal.Client.__init__ calls get_password_from_keyring unconditionally,
        # even with login=False. Suppress it — we authenticate via injected cookies.
        with patch("myfitnesspal.client.get_password_from_keyring", return_value=None):
            self._mfp = myfitnesspal.Client(username=username, login=False, unit_aware=True)
        self._mfp.session.cookies.update(cj)

    def get_date(self, year: int, month: int, day: int):
        return self._mfp.get_date(year, month, day)

    def get_measurements(self, measurement: str, *, lower_bound: date) -> dict:
        return self._mfp.get_measurements(measurement, lower_bound=lower_bound)
