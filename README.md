# easy-gg-bedwars-mcp

Local-first Python MCP server for Easy.gg BedWars custom scripting. The MCP server registers as `easy-gg-bedwars-custom`.

This project writes Roblox BedWars scripts that run through documented in-game APIs and Code Sync. 

## Source Of Truth

The docs cache is seeded from official BedWars Creative documentation at `docs.easy.gg`:

- BedWars scripting overview: https://docs.easy.gg/scripting/bedwars-scripting
- Services index: https://docs.easy.gg/scripting/bedwars-scripting/services
- Events index: https://docs.easy.gg/scripting/bedwars-scripting/events
- Objects index: https://docs.easy.gg/scripting/bedwars-scripting/objects
- Types index: https://docs.easy.gg/scripting/bedwars-scripting/types
- Utilities index: https://docs.easy.gg/scripting/bedwars-scripting/utilities


## Setup

```powershell
cd "C:\path\to\easy-gg-bedwars-mcp"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e .
```

The server uses the Python MCP SDK package `mcp`. Codex/Claude starts the MCP server from its config; do not keep `python server.py` running for normal use.

## Project Layout

```text
src/creative_scripting_mcp/  # MCP runtime package
  server.py                  # FastMCP server and tool implementations
  tools.py                   # Public tool names, descriptions, and context
maintenance/                 # local helper scripts for docs refresh/watch jobs
docs_cache/                  # cached official API references
scripts/                     # Lua examples and repo-managed sync projects
server.py                    # thin compatibility entry point
tools.py                     # thin compatibility re-export
```

## Claude Desktop MCP Config

```json
{
  "mcpServers": {
    "easy-gg-bedwars-custom": {
      "command": "C:\\path\\to\\easy-gg-bedwars-mcp\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "creative_scripting_mcp.server"
      ],
      "cwd": "C:\\path\\to\\easy-gg-bedwars-mcp"
    }
  }
}
```

## Codex MCP Config Example

```toml
[mcp_servers.easy-gg-bedwars-custom]
command = "C:\\path\\to\\easy-gg-bedwars-mcp\\.venv\\Scripts\\python.exe"
args = ["-m", "creative_scripting_mcp.server"]
cwd = "C:\\path\\to\\easy-gg-bedwars-mcp"
```

## Tools

Tool names, descriptions, and usage context are registered from `src/creative_scripting_mcp/tools.py`.

Main groups:

- Docs: search/read cached services and events.
- Script files: create, read, edit, validate, and delete Lua files.
- Projects: organize `sync/`, `drafts/`, and `prompts/` folders.
- Code Sync: connect a token, sync one folder, check status, and run a watcher.
- Debugging: explain console errors and generate defensive patterns for missing APIs like `pcall`.

Ask the MCP client to list tools for exact schemas.

## BedWars Code Sync

Use organized project folders so Roblox only receives the scripts you intend to sync:

```text
scripts/projects/default/
  sync/       # uploaded to BedWars
  drafts/     # local-only work in progress
  prompts/    # project brief / build notes
  project.json
```

Generate a token in the `Sync` tab of the BedWars script editor, then call:

```text
sync_project(sync_token="{sync-token}", project_name="default")
```

The token is sent to Easy.gg's Code Sync endpoint for that request only. The MCP does not save it or return it in tool output. By default, only `.lua` files in `scripts/projects/default/sync/` are uploaded. Keep examples and drafts outside `sync/` unless you want them to appear in the Roblox editor.

To sync a folder outside this MCP repo, pass the folder as the upload root:

```text
connect_sync(
  sync_token="{sync-token}",
  directory="C:\\path\\to\\your-project",
  glob_pattern="scripts/**/*.lua",
  watch=true
)

sync_connected()
```

When `watch=true`, the MCP keeps the token in memory and polls the connected folder for saved, deleted, or renamed `.lua` files. When the file set changes, it syncs the whole current folder, matching the VS Code extension's connected-session behavior.

The MCP also reads the VS Code extension's `bwconfig.lua` format when no glob is provided:

```lua
return {
    syncGlob = "scripts/**/*.lua"
}
```

For a persistent local HitReg watcher process:

```text
python maintenance/watch_hitreg_sync.py {sync-token}
```

For a one-shot HitReg sync:

```text
sync_hitreg(sync_token="{sync-token}")
```

For other folders:

```text
read_directory_project(directory="C:\\path\\to\\your-project")

sync_directory(
  sync_token="{sync-token}",
  directory="C:\\path\\to\\your-project"
)
```

By default, `sync_directory` and `connect_sync` use the visible hard-sync path: they prepare `scripts/`, `drafts/`, `prompts/`, `bwconfig.lua`, `bedwars-project.json`, and `scripts/main.lua` when needed, update `scripts/zz_sync_probe.lua`, upload `scripts/**/*.lua`, and connect the watcher. Use `allow_empty=true` only when intentionally deleting every remote script.

For normal project work, use MCP tools instead of terminal file scans:

- `read_directory_project` to inspect folder state, scripts, prompt, and config.
- `read_directory_script` to read a project Lua file.
- `create_directory_script` to write scripts under `scripts/`.
- `sync_directory` for the strongest first sync.

If the HTTP upload succeeds but the Roblox editor does not visibly refresh, use the explicit hard-sync tool:

```text
force_sync_directory(
  sync_token="{sync-token}",
  directory="C:\\path\\to\\your-project"
)
```

This does the same hard-sync steps explicitly.

To remove a script from BedWars, delete it locally and sync the whole containing folder/project:

```text
delete_project_script(project_name="default", file_name="old_script.lua", sync=true)
sync_project(sync_token="{sync-token}", project_name="default")
```

Deleted scripts are archived under `.deleted/` by default. Sync the whole folder/project after deleting so BedWars receives the current file set and removes scripts that are no longer present.

When deleting the final script in a folder, sync with `allow_empty=true` so the empty file set is sent to BedWars.

## Runtime Limits

The Creative Lua sandbox does not expose every standard Lua global. In particular, do not assume `pcall(...)` or `xpcall(...)` exist.

True protected-call behavior cannot be recreated in plain Lua: catching arbitrary runtime errors requires runtime support. What is possible is defensive scripting:

- Check nil before indexing or calling methods.
- Check command arguments before using them.
- Use `tonumber(...)` and reject nil before numeric logic.
- Check service return values such as `player:getEntity()` or `TeamService.getTeam(player)`.
- Return `ok, value_or_message` from small helper functions for expected failure states.

Use `safe_call_pattern(topic="entity")`, `safe_call_pattern(topic="number")`, or `safe_call_pattern(topic="command")` for replacement patterns.

## Example Usage

Prompt:

```text
Make a script that gives every player 1 emerald every 30 seconds.
```

The server checks for:

- `PlayerService` in `docs_cache/services.json`
- `InventoryService` in `docs_cache/services.json`
- `ItemType` in `docs_cache/types.json`
- `task` and `ipairs` in `docs_cache/utilities.json`

Example output file:

```lua
-- Gives every player 1 emerald every 30 seconds.
while task.wait(30) do
    for i, player in ipairs(PlayerService.getPlayers()) do
        InventoryService.giveItem(player, ItemType.EMERALD, 1, true)
    end
end
```

The same example is included at `scripts/examples/emerald_generator.lua`.

## Refreshing Docs Cache Later

The cache files are intentionally plain JSON so they are easy to inspect and edit:

- `docs_cache/services.json`
- `docs_cache/events.json`
- `docs_cache/types.json`
- `docs_cache/objects.json`
- `docs_cache/utilities.json`

The helper below fetches raw index text from `docs.easy.gg` into `docs_cache/*_raw.txt` for manual review:

```powershell
python maintenance/refresh_docs_cache.py
```

It does not automatically promote scraped content into the JSON cache. Review official docs before adding or changing APIs.

## GitHub Release Checklist

Before publishing:

- Make sure no sync tokens, cookies, sessions, or private Roblox data are in the repo.
- Keep `.venv/`, logs, caches, `build/`, and `dist/` out of git.
- Review `scripts/projects/` and remove personal test scripts you do not want public.
- Run a quick import check:

```powershell
.\.venv\Scripts\python.exe -c "import creative_scripting_mcp.server as server; print(len(server.mcp._tool_manager._tools), 'tools registered')"
```

First push:

```powershell
git init
git status
git add README.md pyproject.toml .gitignore server.py tools.py src maintenance docs_cache scripts
git commit -m "Initial release"
git branch -M main
git remote add origin https://github.com/RareFlames36/easy-gg-bedwars-mcp.git
git push -u origin main
```

Tag a release:

```powershell
git tag -a v0.1.0 -m "v0.1.0"
git push origin v0.1.0
```

Create the GitHub release:

```powershell
gh release create v0.1.0 --title "v0.1.0" --notes "Initial easy-gg-bedwars-mcp release."
```

If the GitHub CLI is not installed, open the repo on GitHub, go to **Releases**, choose **Draft a new release**, select tag `v0.1.0`, and publish it.
