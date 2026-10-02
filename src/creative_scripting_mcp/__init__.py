"""easy-gg-bedwars-custom MCP package."""

from importlib import import_module
from typing import Any

__all__ = ["main", "mcp"]


def __getattr__(name: str) -> Any:
    # Avoid importing server twice when launched with python -m ...server.
    if name in __all__:
        return getattr(import_module(".server", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
