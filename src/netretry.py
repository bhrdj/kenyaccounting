"""Timeouts and retries for every Google API call payroll makes.

The office VPN (Astrill) intermittently stalls HTTPS responses part-way
through the body: the headers arrive, then the connection goes silent. With
no timeout that is a hang, and gspread's default is no timeout at all -- it
passes timeout=None, which also overrides google-auth's own 120s default.
So every request gets a short read timeout, and transient failures are
retried with backoff.

Only idempotent requests are retried blindly. A POST that timed out may
still have landed, so retrying it can create a duplicate file; callers that
POST handle their own retry by checking for the result first.
"""

import random
import time
from urllib.parse import urlparse

import requests
from google.auth.transport.requests import AuthorizedSession
from gspread.http_client import HTTPClient
from gspread.urls import DRIVE_FILES_API_V3_URL

# (connect, read) seconds. The read timeout is per socket read, not for the
# whole response, so a slow-but-flowing download is not cut off; only
# silence is.
TIMEOUT = (10, 30)
ATTEMPTS = 5

_RETRY_STATUS = {408, 429, 500, 502, 503, 504}
_NETWORK_ERRORS = (
    requests.exceptions.ConnectionError,  # includes a read timeout mid-body
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
)


def is_transient(exc: BaseException) -> bool:
    """True for failures worth retrying: network trouble or a 429/5xx."""
    if isinstance(exc, _NETWORK_ERRORS):
        return True
    status = getattr(getattr(exc, "response", None), "status_code", None)
    return status in _RETRY_STATUS


def with_retries(fn, what: str, attempts: int = ATTEMPTS, log=print):
    """Call fn(), retrying transient failures with exponential backoff."""
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as e:
            if attempt == attempts or not is_transient(e):
                raise
            delay = min(2 ** (attempt - 1), 8) + random.random()
            log(f"  ... {what}: {type(e).__name__}; "
                f"retry {attempt}/{attempts - 1} in {delay:.0f}s")
            time.sleep(delay)


def _label(method: str, url: str) -> str:
    path = urlparse(url).path
    return f"{method.upper()} ...{path[-40:]}" if len(path) > 40 else f"{method.upper()} {path}"


class RetryingHTTPClient(HTTPClient):
    """gspread HTTP client with a timeout and retries on transient errors.

    Drive file creation (POST to the Drive files API, used by gc.create) is
    sent once: a retry after a lost response would make a second spreadsheet.
    Sheets batchUpdate POSTs are retried; the ones payroll sends are
    idempotent except addSheet, which fails loudly on a repeat rather than
    duplicating.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = TIMEOUT

    def request(self, method, endpoint, *args, **kwargs):
        send = lambda: super(RetryingHTTPClient, self).request(
            method, endpoint, *args, **kwargs)
        if method.lower() == "post" and endpoint.startswith(DRIVE_FILES_API_V3_URL):
            return send()
        return with_retries(send, _label(method, endpoint))


class RetryingSession(AuthorizedSession):
    """AuthorizedSession for raw Drive calls, with a timeout and retries.

    POSTs are sent once (see module docstring). For everything else a 429/5xx
    is retried too; once retries run out the error is raised, which callers
    would have done anyway via raise_for_status().
    """

    def request(self, method, url, *args, **kwargs):
        kwargs.setdefault("timeout", TIMEOUT)
        send = lambda: super(RetryingSession, self).request(method, url, *args, **kwargs)
        if method.upper() == "POST":
            return send()

        def checked():
            r = send()
            if r.status_code in _RETRY_STATUS:
                r.raise_for_status()
            return r

        return with_retries(checked, _label(method, url))
