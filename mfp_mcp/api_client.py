"""MFP JSON API client.

Bypasses Cloudflare by using two Cloudflare-free endpoints:
  1. www.myfitnesspal.com/user/auth_token — returns a bearer token using session cookies
  2. api.myfitnesspal.com — the actual JSON API, no Cloudflare Bot Fight Mode

The bearer token has a 10-day expiry and is cached in SQLite.
"""
from __future__ import annotations

import base64
from datetime import date

import requests

from .auth import load_auth
from .cache import CacheStore

_API_BASE = "https://api.myfitnesspal.com"
_TOKEN_URL = "https://www.myfitnesspal.com/user/auth_token?refresh=true"

_TOKEN_TTL = 8 * 86400              # cache for 8 days (token lives 10 days, refresh before expiry)
_DIARY_TTL_TODAY = 1800             # 30 min — today's diary may still be updated
_DIARY_TTL_HISTORICAL = 15 * 86400  # 15 days — past diary entries are immutable
_MEASUREMENTS_TTL = 3600            # 1 hour

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def _decode_user_id(token: str) -> str:
    """Extract numeric user ID from bearer token.

    Token format (base64-encoded): a:mfp-main-js:{user_id}::mfp-js:{ts}:{expiry}{signature}
    """
    padding = 4 - len(token) % 4
    decoded = base64.b64decode(token + "=" * padding, validate=False).decode("utf-8", errors="replace")
    parts = decoded.split(":")
    if len(parts) < 3:
        raise RuntimeError("Unexpected MFP token format — cannot extract user ID")
    return parts[2]


class MFPApiClient:
    def __init__(self) -> None:
        self._cache = CacheStore()
        self._cj, self._username = load_auth()
        self._token, self._user_id = self._ensure_token()
        self._session = self._make_api_session()

    def _ensure_token(self) -> tuple[str, str]:
        cache_key = f"token:{self._username}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached["token"], cached["user_id"]

        s = requests.Session()
        s.cookies.update(self._cj)
        s.headers.update({
            "User-Agent": _UA,
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        })
        r = s.get(_TOKEN_URL, timeout=15)
        if not r.ok:
            raise RuntimeError(
                f"Failed to obtain MFP bearer token (HTTP {r.status_code}). "
                "Run `mfp-mcp auth` to refresh your Chrome cookies."
            )

        data = r.json()
        token = data["access_token"]
        expires_in = data.get("expires_in", _TOKEN_TTL)
        user_id = _decode_user_id(token)

        ttl = max(0, min(expires_in - 86400, _TOKEN_TTL))
        self._cache.set(cache_key, {"token": token, "user_id": user_id}, ttl=ttl)
        return token, user_id

    def _make_api_session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({
            "Authorization": f"Bearer {self._token}",
            "mfp-client-id": "mfp-main-js",
            "mfp-user-id": self._user_id,
            "Accept": "application/json",
            "User-Agent": _UA,
        })
        return s

    def get_diary(self, date_str: str) -> list[dict]:
        cache_key = f"diary:{self._username}:{date_str}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        r = self._session.get(
            f"{_API_BASE}/v2/diary",
            params={"username": self._username, "date": date_str},
            timeout=15,
        )
        r.raise_for_status()
        all_items = r.json().get("items", [])
        # The API currently returns today's diary for every date query; the
        # item-level "date" field reveals the actual date of each entry.
        # Keep only items that match the requested date — this prevents showing
        # today's data on historical days. Historical dates will return empty
        # until the correct endpoint or parameter for past diaries is found.
        items = [item for item in all_items if item.get("date") == date_str]

        # Fallback: if no diary items, try the /v2/nutrition endpoint which may
        # have better historical date support (response shape is different).
        if not items and date_str != date.today().isoformat():
            rn = self._session.get(
                f"{_API_BASE}/v2/nutrition",
                params={"username": self._username, "date": date_str},
                timeout=15,
            )
            if rn.ok:
                nutrition_items = rn.json().get("items", [])
                items = [i for i in nutrition_items if i.get("date") == date_str]

        ttl = _DIARY_TTL_TODAY if date_str == date.today().isoformat() else _DIARY_TTL_HISTORICAL
        self._cache.set(cache_key, items, ttl=ttl)
        return items

    def get_measurements(self, measurement: str, from_date: str, to_date: str) -> list[dict]:
        cache_key = f"measurements:{self._username}:{measurement}:{from_date}:{to_date}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        r = self._session.get(
            f"{_API_BASE}/v2/measurements"
            f"?username={self._username}&type={measurement}"
            f"&from_date={from_date}&to_date={to_date}",
            timeout=15,
        )
        r.raise_for_status()
        items = r.json().get("items", [])

        self._cache.set(cache_key, items, ttl=_MEASUREMENTS_TTL)
        return items
