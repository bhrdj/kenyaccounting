"""Tab-by-tab Google Sheets reads, cached on disk until the sheet changes.

Reading a spreadsheet as one big request (an xlsx export, or every tab at
once) is fragile over the office VPN: a stall anywhere loses the lot, and
the retry starts from zero. Here each tab is its own small request and is
cached as soon as it lands, so a run that dies part-way resumes from the
tabs it already has.

A cached spreadsheet is trusted only while its Drive modifiedTime matches
the one recorded when it was cached. That is a single small request per
spreadsheet; any edit -- including payroll's own write of the leave-stocks
tab -- moves it and drops the whole cache for that spreadsheet.

The cache lives in .cache/sheets/ at the repo root (gitignored), dirs 700
and files 600, since it holds employee data. Delete it to force a full
re-download.
"""

import json
import os
import shutil
from pathlib import Path

from gspread.urls import DRIVE_FILES_API_V3_URL

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "sheets"


def _write_private(path: Path, obj) -> None:
    """Write JSON readable only by the owner, atomically."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def drive_modified_time(gc, key: str) -> str:
    r = gc.http_client.request(
        "get", f"{DRIVE_FILES_API_V3_URL}/{key}",
        params={"fields": "modifiedTime", "supportsAllDrives": True})
    return r.json()["modifiedTime"]


def fetch_tabs(gc, key: str, label: str, want=lambda tab: True,
               render: str = "FORMATTED_VALUE", modified: str | None = None,
               log=print) -> list[tuple[str, list[list]]]:
    """Return [(tab title, values)] for the wanted tabs, in sheet order.

    `want` filters tab dicts ({"id", "title", "index"}). `render` is the
    Sheets valueRenderOption; dates come back as serial numbers when it is
    UNFORMATTED_VALUE. Pass `modified` when the caller already has the
    Drive modifiedTime, to save a request.
    """
    if modified is None:
        modified = drive_modified_time(gc, key)

    d = CACHE_DIR / key
    meta_path = d / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.is_file() else {}
    if meta.get("modifiedTime") != modified:
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True, mode=0o700)
        CACHE_DIR.chmod(0o700)
        props = gc.http_client.fetch_sheet_metadata(
            key, params={"fields": "sheets.properties(sheetId,title,index)"})
        tabs = [{"id": s["properties"]["sheetId"],
                 "title": s["properties"]["title"],
                 "index": s["properties"]["index"]} for s in props["sheets"]]
        meta = {"modifiedTime": modified, "tabs": tabs}
        _write_private(meta_path, meta)

    out, cached = [], 0
    for tab in sorted(meta["tabs"], key=lambda t: t["index"]):
        if not want(tab):
            continue
        path = d / f"{tab['id']}.{render}.json"
        if path.is_file():
            values = json.loads(path.read_text(encoding="utf-8"))
            cached += 1
        else:
            title = tab["title"].replace("'", "''")
            resp = gc.http_client.values_get(
                key, f"'{title}'",
                params={"valueRenderOption": render,
                        "dateTimeRenderOption": "SERIAL_NUMBER"})
            values = resp.get("values", [])
            _write_private(path, values)
        out.append((tab["title"], values))

    log(f"  {label}: {len(out)} tab(s), {cached} cached, {len(out) - cached} fetched")
    return out
