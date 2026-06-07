from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from creative_scripting_mcp import server as _server

mcp = _server.mcp
main = _server.main


def __getattr__(name: str):
    return getattr(_server, name)


if __name__ == "__main__":
    main()
