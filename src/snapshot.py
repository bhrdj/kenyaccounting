"""Freeze the inputs a payroll run used, so the run can be reproduced.

Inputs live in Google Sheets, which are mutable: re-syncing July next year
returns the sheets as they are *then*, not as they were when July was paid.
So every run archives the exact input files it pulled to Drive alongside
the outputs. `--replay` unpacks that archive and runs against it, which is
the only way to recompute a past month and get the same answer.

The archive holds raw file bytes rather than parsed Employee/Contract
objects on purpose: replay then goes through the same loaders as a live
run, and the archive stays readable after src/models.py changes shape.
Deserializing parsed dataclasses would break on the first field rename,
which is exactly when you would want to look at an old run.

It is a plain zip rather than a pickle so that opening one is inert -- you
can unzip an archive from Drive, or read its TSVs, without executing
anything it contains.

Layout inside the zip:
    _snapshot_meta.json   format, year, month, created, git_commit
    inputs/<relpath>      the staged input files, verbatim
"""

import json
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

FORMAT_VERSION = 1
SNAPSHOT_NAME = "inputs_snapshot.zip"

_META_NAME = "_snapshot_meta.json"
_FILE_PREFIX = "inputs/"
# Fixed mtime for stored entries: the same inputs should produce the same
# archive, rather than differing by when the files happened to be written.
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def _git_commit() -> str | None:
    """Current HEAD of the repo this module lives in, or None."""
    try:
        out = subprocess.run(
            ["git", "-C", str(Path(__file__).parent), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def write_snapshot(inputs_dir: str | Path, dest: str | Path,
                   year: int, month: int) -> Path:
    """Archive every file under inputs_dir into dest. Returns dest."""
    inputs_dir = Path(inputs_dir)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    paths = [p for p in sorted(inputs_dir.rglob("*")) if p.is_file()]
    meta = {
        "format": FORMAT_VERSION,
        "year": year,
        "month": month,
        "created": datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "file_count": len(paths),
    }

    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(_META_NAME, json.dumps(meta, indent=2))
        for p in paths:
            info = zipfile.ZipInfo(
                _FILE_PREFIX + p.relative_to(inputs_dir).as_posix(),
                date_time=_ZIP_EPOCH,
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, p.read_bytes())
    return dest


def read_snapshot(data: bytes | str | Path) -> dict:
    """Load a snapshot from raw bytes or a path.

    Returns the metadata dict with a 'files' key mapping relative path to
    bytes. Raises ValueError if the archive is not a readable snapshot.
    """
    from io import BytesIO

    source = BytesIO(data) if isinstance(data, bytes) else data
    try:
        with zipfile.ZipFile(source) as z:
            try:
                meta = json.loads(z.read(_META_NAME))
            except KeyError:
                raise ValueError(
                    f"Not a payroll snapshot: no {_META_NAME} in the archive"
                ) from None
            version = meta.get("format")
            if version != FORMAT_VERSION:
                raise ValueError(
                    f"Unsupported snapshot format {version!r} "
                    f"(this build reads format {FORMAT_VERSION})"
                )
            meta["files"] = {
                name[len(_FILE_PREFIX):]: z.read(name)
                for name in z.namelist()
                if name.startswith(_FILE_PREFIX) and not name.endswith("/")
            }
    except zipfile.BadZipFile as e:
        raise ValueError(f"Not a readable zip archive: {e}") from None
    return meta


def restore_snapshot(payload: dict, inputs_dir: str | Path) -> int:
    """Write a snapshot's files into inputs_dir. Returns the file count."""
    inputs_dir = Path(inputs_dir).resolve()
    for relpath, blob in payload["files"].items():
        out = (inputs_dir / relpath).resolve()
        # Archive paths are data; refuse any that would escape inputs_dir.
        if not out.is_relative_to(inputs_dir):
            raise ValueError(f"Snapshot entry escapes the target directory: {relpath}")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(blob)
    return len(payload["files"])


def describe(payload: dict) -> str:
    """One-line provenance summary for logging."""
    commit = payload.get("git_commit")
    commit = commit[:8] if commit else "unknown"
    return (f"{payload['year']}-{payload['month']:02d} inputs "
            f"synced {payload['created']} at commit {commit} "
            f"({len(payload['files'])} files)")
