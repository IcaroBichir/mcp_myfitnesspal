"""Tests for mfp_mcp.auth cookie cache logic.

browser_cookie3.chrome and requests.Session are mocked — no Chrome or network
access needed.
"""
from __future__ import annotations

import json
import time
from http.cookiejar import CookieJar
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_cookiejar():
    cj = CookieJar()
    return cj


def _valid_cache_payload(username="testuser"):
    return json.dumps({"username": username, "cookies": []})


# ---------------------------------------------------------------------------
# load_auth — valid cache (not expired)
# ---------------------------------------------------------------------------

class TestLoadAuthValidCache:
    def test_returns_cached_username_without_calling_chrome(self, tmp_path, monkeypatch):
        from mfp_mcp import auth as auth_module

        # Point config dir at tmp directory
        cache_file = tmp_path / "cookies.json"
        cache_file.write_text(_valid_cache_payload("icaro"))
        monkeypatch.setattr(auth_module, "COOKIE_CACHE", cache_file)
        monkeypatch.setattr(auth_module, "CONFIG_DIR", tmp_path)

        # Make the file appear fresh (mtime = now)
        now = time.time()
        import os
        os.utime(cache_file, (now, now))

        chrome_mock = MagicMock(return_value=_make_fake_cookiejar())
        with patch("browser_cookie3.chrome", chrome_mock):
            _cj, username = auth_module.load_auth()

        assert username == "icaro"
        chrome_mock.assert_not_called()

    def test_returns_cookiejar_from_cache(self, tmp_path, monkeypatch):
        from mfp_mcp import auth as auth_module

        cache_file = tmp_path / "cookies.json"
        cache_file.write_text(_valid_cache_payload("icaro"))
        monkeypatch.setattr(auth_module, "COOKIE_CACHE", cache_file)
        monkeypatch.setattr(auth_module, "CONFIG_DIR", tmp_path)

        now = time.time()
        import os
        os.utime(cache_file, (now, now))

        with patch("browser_cookie3.chrome", return_value=_make_fake_cookiejar()):
            cj, _ = auth_module.load_auth()

        assert isinstance(cj, CookieJar)


# ---------------------------------------------------------------------------
# load_auth — expired cache (TTL elapsed)
# ---------------------------------------------------------------------------

class TestLoadAuthExpiredCache:
    def test_expired_cache_triggers_chrome_read(self, tmp_path, monkeypatch):
        from mfp_mcp import auth as auth_module

        cache_file = tmp_path / "cookies.json"
        cache_file.write_text(_valid_cache_payload("icaro"))
        monkeypatch.setattr(auth_module, "COOKIE_CACHE", cache_file)
        monkeypatch.setattr(auth_module, "CONFIG_DIR", tmp_path)

        # Age the file beyond TTL
        import os
        old_time = time.time() - auth_module._COOKIE_TTL - 10
        os.utime(cache_file, (old_time, old_time))

        chrome_mock = MagicMock(return_value=_make_fake_cookiejar())
        fetch_mock = MagicMock(return_value="freshuser")

        with patch("browser_cookie3.chrome", chrome_mock), \
             patch.object(auth_module, "_get_username", fetch_mock):
            _cj, username = auth_module.load_auth()

        chrome_mock.assert_called_once_with(domain_name="myfitnesspal.com")
        assert username == "freshuser"

    def test_expired_cache_rewrites_cache_file(self, tmp_path, monkeypatch):
        from mfp_mcp import auth as auth_module

        cache_file = tmp_path / "cookies.json"
        cache_file.write_text(_valid_cache_payload("icaro"))
        monkeypatch.setattr(auth_module, "COOKIE_CACHE", cache_file)
        monkeypatch.setattr(auth_module, "CONFIG_DIR", tmp_path)

        import os
        old_time = time.time() - auth_module._COOKIE_TTL - 10
        os.utime(cache_file, (old_time, old_time))

        with patch("browser_cookie3.chrome", return_value=_make_fake_cookiejar()), \
             patch.object(auth_module, "_get_username", return_value="newuser"):
            auth_module.load_auth()

        # Cache file should have been rewritten with new username
        data = json.loads(cache_file.read_text())
        assert data["username"] == "newuser"


# ---------------------------------------------------------------------------
# load_auth — corrupted JSON cache
# ---------------------------------------------------------------------------

class TestLoadAuthCorruptedCache:
    def test_corrupted_json_is_deleted_and_chrome_called(self, tmp_path, monkeypatch):
        from mfp_mcp import auth as auth_module

        cache_file = tmp_path / "cookies.json"
        cache_file.write_text("{not valid json[[")
        monkeypatch.setattr(auth_module, "COOKIE_CACHE", cache_file)
        monkeypatch.setattr(auth_module, "CONFIG_DIR", tmp_path)

        # Fresh mtime so it would be used if not corrupted
        import os
        os.utime(cache_file, (time.time(), time.time()))

        chrome_mock = MagicMock(return_value=_make_fake_cookiejar())
        fetch_mock = MagicMock(return_value="recovereduser")

        with patch("browser_cookie3.chrome", chrome_mock), \
             patch.object(auth_module, "_get_username", fetch_mock):
            _cj, username = auth_module.load_auth()

        chrome_mock.assert_called_once_with(domain_name="myfitnesspal.com")
        assert username == "recovereduser"

    def test_corrupted_json_cache_deleted_before_chrome_call(self, tmp_path, monkeypatch):
        from mfp_mcp import auth as auth_module

        cache_file = tmp_path / "cookies.json"
        cache_file.write_text("{corrupted}")
        monkeypatch.setattr(auth_module, "COOKIE_CACHE", cache_file)
        monkeypatch.setattr(auth_module, "CONFIG_DIR", tmp_path)

        import os
        os.utime(cache_file, (time.time(), time.time()))

        deleted_before_call = []

        original_chrome = MagicMock(return_value=_make_fake_cookiejar())

        def chrome_side_effect(**kwargs):
            # By the time Chrome is called, the corrupt file should be gone
            deleted_before_call.append(not cache_file.exists())
            return _make_fake_cookiejar()

        original_chrome.side_effect = chrome_side_effect

        with patch("browser_cookie3.chrome", original_chrome), \
             patch.object(auth_module, "_get_username", return_value="u"):
            auth_module.load_auth()

        # The corrupt file was deleted before Chrome was called
        assert deleted_before_call == [True]

    def test_missing_key_in_cache_triggers_reread(self, tmp_path, monkeypatch):
        from mfp_mcp import auth as auth_module

        # Valid JSON but missing 'username' key
        cache_file = tmp_path / "cookies.json"
        cache_file.write_text(json.dumps({"cookies": []}))
        monkeypatch.setattr(auth_module, "COOKIE_CACHE", cache_file)
        monkeypatch.setattr(auth_module, "CONFIG_DIR", tmp_path)

        import os
        os.utime(cache_file, (time.time(), time.time()))

        chrome_mock = MagicMock(return_value=_make_fake_cookiejar())
        with patch("browser_cookie3.chrome", chrome_mock), \
             patch.object(auth_module, "_get_username", return_value="fallbackuser"):
            _cj, username = auth_module.load_auth()

        chrome_mock.assert_called_once()
        assert username == "fallbackuser"


# ---------------------------------------------------------------------------
# load_auth — no cache file (first run)
# ---------------------------------------------------------------------------

class TestLoadAuthNoCache:
    def test_no_cache_calls_chrome_and_writes_file(self, tmp_path, monkeypatch):
        from mfp_mcp import auth as auth_module

        cache_file = tmp_path / "cookies.json"
        monkeypatch.setattr(auth_module, "COOKIE_CACHE", cache_file)
        monkeypatch.setattr(auth_module, "CONFIG_DIR", tmp_path)

        assert not cache_file.exists()

        chrome_mock = MagicMock(return_value=_make_fake_cookiejar())
        with patch("browser_cookie3.chrome", chrome_mock), \
             patch.object(auth_module, "_get_username", return_value="firstrun"):
            _cj, username = auth_module.load_auth()

        chrome_mock.assert_called_once()
        assert username == "firstrun"
        assert cache_file.exists()

    def test_cache_file_written_with_correct_username(self, tmp_path, monkeypatch):
        from mfp_mcp import auth as auth_module

        cache_file = tmp_path / "cookies.json"
        monkeypatch.setattr(auth_module, "COOKIE_CACHE", cache_file)
        monkeypatch.setattr(auth_module, "CONFIG_DIR", tmp_path)

        with patch("browser_cookie3.chrome", return_value=_make_fake_cookiejar()), \
             patch.object(auth_module, "_get_username", return_value="newuser"):
            auth_module.load_auth()

        data = json.loads(cache_file.read_text())
        assert data["username"] == "newuser"
        assert "cookies" in data
