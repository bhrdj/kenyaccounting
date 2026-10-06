"""Tab-by-tab sheet reads: cache invalidation, resume, retries, cell mapping.

A stale cache would silently pay from old inputs, so the invalidation rule
-- trust the cache only while Drive's modifiedTime is unchanged -- is the
part most worth pinning down.
"""

from datetime import datetime
from types import SimpleNamespace

import pytest
import requests

from src import netretry, sheetcache
from src.gsync import _attendance_cell


class FakeHTTP:
    """Stands in for gspread's HTTPClient; counts the reads it serves."""

    def __init__(self, modified="t1", tabs=None):
        self.modified = modified
        self.tabs = tabs or {"Beth_1": [["date", "x"], [1, 2]],
                             "Ann_2": [["date", "x"], [3, 4]]}
        self.values_calls = []
        self.fail_on = set()

    def request(self, method, url, params=None):
        return SimpleNamespace(json=lambda: {"modifiedTime": self.modified})

    def fetch_sheet_metadata(self, key, params=None):
        return {"sheets": [{"properties": {"sheetId": i, "title": t, "index": i}}
                           for i, t in enumerate(self.tabs)]}

    def values_get(self, key, rng, params=None):
        title = rng.strip("'")
        if title in self.fail_on:
            raise requests.exceptions.ConnectionError("stalled")
        self.values_calls.append(title)
        return {"values": self.tabs[title]}


@pytest.fixture
def gc(tmp_path, monkeypatch):
    monkeypatch.setattr(sheetcache, "CACHE_DIR", tmp_path / "sheets")
    return SimpleNamespace(http_client=FakeHTTP())


def fetch(gc, **kw):
    return sheetcache.fetch_tabs(gc, "KEY", "test", log=lambda _: None, **kw)


def test_second_read_comes_from_cache(gc):
    first = fetch(gc)
    assert gc.http_client.values_calls == ["Beth_1", "Ann_2"]
    assert fetch(gc) == first
    assert gc.http_client.values_calls == ["Beth_1", "Ann_2"]


def test_edited_sheet_is_refetched(gc):
    fetch(gc)
    gc.http_client.modified = "t2"
    gc.http_client.tabs["Beth_1"] = [["date", "x"], [9, 9]]
    assert dict(fetch(gc))["Beth_1"] == [["date", "x"], [9, 9]]
    assert gc.http_client.values_calls == ["Beth_1", "Ann_2", "Beth_1", "Ann_2"]


def test_interrupted_read_resumes_from_fetched_tabs(gc):
    gc.http_client.fail_on = {"Ann_2"}
    with pytest.raises(requests.exceptions.ConnectionError):
        fetch(gc)
    gc.http_client.fail_on = set()
    fetch(gc)
    assert gc.http_client.values_calls == ["Beth_1", "Ann_2"]


def test_cache_files_are_owner_only(gc):
    fetch(gc)
    for p in (sheetcache.CACHE_DIR / "KEY").iterdir():
        assert p.stat().st_mode & 0o077 == 0


def test_want_filters_tabs(gc):
    assert [t for t, _ in fetch(gc, want=lambda t: t["index"] == 0)] == ["Beth_1"]


def test_retries_transient_then_succeeds(monkeypatch):
    monkeypatch.setattr(netretry.time, "sleep", lambda _: None)
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise requests.exceptions.ReadTimeout()
        return "ok"

    assert netretry.with_retries(flaky, "x", log=lambda _: None) == "ok"
    assert len(calls) == 3


def test_does_not_retry_client_errors(monkeypatch):
    monkeypatch.setattr(netretry.time, "sleep", lambda _: None)
    err = requests.exceptions.HTTPError(response=SimpleNamespace(status_code=403))
    calls = []

    def denied():
        calls.append(1)
        raise err

    with pytest.raises(requests.exceptions.HTTPError):
        netretry.with_retries(denied, "x", log=lambda _: None)
    assert len(calls) == 1


def test_gives_up_after_attempts(monkeypatch):
    monkeypatch.setattr(netretry.time, "sleep", lambda _: None)

    def dead():
        raise requests.exceptions.ConnectionError()

    with pytest.raises(requests.exceptions.ConnectionError):
        netretry.with_retries(dead, "x", attempts=3, log=lambda _: None)


@pytest.mark.parametrize("value,row,col,expected", [
    (46023, 1, 0, datetime(2026, 1, 1)),        # date serial in column A
    (46023, 1, 1, datetime(2026, 1, 1)),        # and column B (weekday)
    (46023, 0, 0, 46023),                       # header row left alone
    (8, 1, 2, 8),                               # hours column left alone
    ("", 1, 3, None),                           # blank reads as None, as from xlsx
    ("#REF! (Reference does not exist.)", 1, 4, "#REF!"),
    ("#N/A (Did not find value.)", 1, 4, "#N/A"),
    ("off sick (flu)", 1, 10, "off sick (flu)"),  # ordinary notes untouched
    (True, 1, 0, True),                         # a bool is not a serial
])
def test_attendance_cell(value, row, col, expected):
    assert _attendance_cell(value, row, col) == expected



def test_token_refresh_network_failure_is_retried():
    from google.auth.exceptions import TransportError
    assert netretry.is_transient(TransportError("oauth2.googleapis.com: Read timed out."))
