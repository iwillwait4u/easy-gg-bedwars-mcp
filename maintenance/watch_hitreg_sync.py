from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from creative_scripting_mcp import server


def main() -> None:
    parser = argparse.ArgumentParser(description="Keep HitReg BedWars Code Sync connected.")
    parser.add_argument("sync_token")
    parser.add_argument("--directory", default=str(server._hitreg_directory()))
    parser.add_argument("--glob", default="")
    args = parser.parse_args()

    connected = server.connect_sync(
        sync_token=args.sync_token,
        directory=args.directory,
        glob_pattern=args.glob,
        watch=True,
    )
    print(connected, flush=True)

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()

