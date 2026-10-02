"""Python 3.10+ / mcp 1.x: python tests/smoke_installed.py after installing a wheel."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def check_installed_server() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        env = dict(os.environ)
        env.pop("CREATIVE_SCRIPTING_MCP_ROOT", None)
        env.pop("PYTHONPATH", None)
        # A fresh interpreter outside the checkout must find packaged docs.
        check = subprocess.run(
            [sys.executable, "-c", (
                "from pathlib import Path; from creative_scripting_mcp import server; "
                "assert server.PROJECT_ROOT == Path.cwd().resolve(); "
                "assert all(server._load_docs_cache().values()); "
                "assert server.read_service('InventoryService')['found']; "
                "assert server.read_object('Entity')['found']; "
                "assert server.read_type('ItemType')['found']; "
                "print(server.DOCS_CACHE_DIR)"
            )],
            cwd=temp_dir, env=env, check=True, capture_output=True, text=True,
        )
        docs_path = Path(check.stdout.strip())
        assert "site-packages" in docs_path.parts, f"Expected installed docs, got {docs_path}"
        # A locally collected Fandom cache must not hide bundled API categories.
        (Path(temp_dir) / "docs_cache" / "fandom").mkdir(parents=True)
        subprocess.run(
            [sys.executable, "-c", (
                "from creative_scripting_mcp import server; "
                "assert server.read_service('InventoryService')['found']; "
                "assert server.read_event('PlayerAdded')['found']; "
                "assert server.read_type('ItemType')['found']"
            )], cwd=temp_dir, env=env, check=True,
        )
        params = StdioServerParameters(
            command=sys.executable,
            args=["-W", "error::RuntimeWarning", "-m", "creative_scripting_mcp.server"],
            cwd=temp_dir, env=env,
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                assert {"read_service", "connect_sync", "validate_directory_script", "preview_directory_sync"} <= names
                result = await session.call_tool("read_service", {"service_name": "InventoryService"})
                assert not result.isError, result
                payload = json.loads(result.content[0].text)
                assert payload["found"], payload
                preview = await session.call_tool("preview_directory_sync", {"directory": temp_dir})
                assert not preview.isError, preview
                preview_payload = json.loads(preview.content[0].text)
                assert preview_payload["file_count"] == 0, preview_payload
                assert not preview_payload["ready_to_sync"], preview_payload
                assert not preview_payload["uploaded"], preview_payload
                print(f"Installed MCP smoke passed: {len(names)} tools, packaged InventoryService docs available.")


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(check_installed_server(), timeout=30))
