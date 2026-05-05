from __future__ import annotations

import json
import os
import time
from http.cookiejar import Cookie, CookieJar
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "mfp-mcp"
COOKIE_CACHE = CONFIG_DIR / "cookies.json"
_COOKIE_TTL = 12 * 3600  # seconds before re-reading from Chrome


def _cookies_to_list(cj: CookieJar) -> list[dict]:
    return [
        {k: getattr(c, k) for k in ("name", "value", "domain", "path", "secure", "expires")}
        for c in cj
    ]


def _list_to_cookiejar(cookie_list: list[dict]) -> CookieJar:
    cj = CookieJar()
    for attrs in cookie_list:
        c = Cookie(
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


def load_cookiejar() -> CookieJar:
    """Return cached cookiejar from disk, or read fresh from Chrome and cache it."""
    import browser_cookie3

    if COOKIE_CACHE.exists():
        age = time.time() - COOKIE_CACHE.stat().st_mtime
        if age < _COOKIE_TTL:
            try:
                with open(COOKIE_CACHE) as f:
                    return _list_to_cookiejar(json.load(f))
            except (json.JSONDecodeError, KeyError, OSError):
                COOKIE_CACHE.unlink(missing_ok=True)

    cj = browser_cookie3.chrome(domain_name="myfitnesspal.com")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # Use os.open with O_CREAT and mode 0o600 so the file is never readable by
    # other local users, even briefly between creation and a separate chmod call.
    fd = os.open(COOKIE_CACHE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(_cookies_to_list(cj), f)
    return cj
