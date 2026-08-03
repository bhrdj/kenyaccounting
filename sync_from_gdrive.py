#!/usr/bin/env python3
"""Download payroll inputs from Google Drive into a local directory.

run_payroll.py does this for you into a temp dir, so this script is only
for inspecting the raw inputs by hand -- checking what a sheet actually
contains before or after a run. Whatever you dump is private employee data:
put it somewhere outside the working tree.

Usage:
    python sync_from_gdrive.py --dest /tmp/payroll_inputs --year 2026
    python sync_from_gdrive.py --dest /tmp/payroll_inputs --only contracts
"""

import argparse
import sys
from pathlib import Path

from src.gsync import SOURCES, sync_inputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dest", type=Path, required=True,
                        help="Directory to write inputs into")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--only", nargs="+", choices=SOURCES, metavar="SOURCE",
                        help=f"Sync only these sources (default: all). "
                             f"Choices: {', '.join(SOURCES)}")
    args = parser.parse_args()

    wanted = args.only or list(SOURCES)
    print(f"Syncing {sorted(wanted)} for {args.year} from Google Drive into {args.dest}")
    print()

    missing = sync_inputs(args.dest, args.year, only=args.only)

    print()
    if missing:
        print("Skipped (no key configured):")
        for m in missing:
            print(f"  - {m}")
        return 1
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
