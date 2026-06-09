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

The optional Fandom cache is seeded from the Roblox BedWars Wiki on Fandom:

- Fandom wiki: https://robloxbedwars.fandom.com/wiki/BedWars_Wiki
- MediaWiki API: https://robloxbedwars.fandom.com/api.php

Use Fandom data for gameplay/wiki references such as kits, items, blocks, commands, maps, and updates. Do not use it as proof that a Lua scripting API exists; official scripting validation still comes from `docs.easy.gg`.

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
maintenance/                 # local helper scripts for docs refresh jobs
docs_cache/                  # cached official API references
scripts/                     # Lua examples and optional local project files
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

- Docs: search/read complete cached services, events, objects, and types.
- Fandom docs: search/read cached gameplay wiki pages from Roblox BedWars Fandom.
- Reference analysis: audit user-provided exports and map mechanics to official APIs without copying source scripts.
- Script files: create, read, diff/edit, validate, and delete Lua files.
- Projects: organize `sync/`, `drafts/`, and `prompts/` folders.
- Code Sync: connect a token, sync one folder, check status, and run a watcher.
- Debugging: validate external scripts, generate event traces, report runtime capabilities, and explain pasted console errors.

Ask the MCP client to list tools for exact schemas.

## Community Reference Exports

Use `audit_reference_export(directory="C:\\path\\to\\export")` to inspect a structured script export. The tool returns aggregate mechanic, API, and risk counts only. It does not return or import scripts, messages, authors, or copied implementations.

Use `recommend_mechanic_apis(topic="persistent player upgrades")` to map an observed mechanic to official cached services, events, objects, and types before writing original code.

Use `recommend_algorithm(topic="bounded target selection with wall checks")` for original design steps and pitfalls covering target selection, segment visibility, area damage, prefab placement, and world text. Community evidence can suggest behavior and test cases, but only the `docs.easy.gg` cache validates scripting APIs.

Use `chat_capabilities()` before implementing chat tags, rich text, hidden commands, team-colored names, or replacement messages. It separates the documented `ChatService.sendMessage` and `PlayerChatted` surface from missing features and includes a proposal-only segmented-message/cancellable-event contract.

Mechanic labels are not blocked. Use `resolve_creative_mechanic(prompt="host-only aimbot with wall checks")` to classify names such as aimbot, aim assist, KA, kill aura, fly, or speed as private Creative Host Panel mechanics and receive the correct tool sequence and documented capability limits.

Run `validate_directory_project(directory="C:\\path\\to\\project")` before sync to validate every Lua file under `scripts/`.

## Fandom Gameplay Cache

Collect gameplay/wiki data from Roblox BedWars Fandom into a local cache:

```powershell
python maintenance/refresh_fandom_cache.py --include-text
```

This writes ignored generated files under `docs_cache/fandom/`:

- `manifest.json`
- `pages.json`
- `categories.json`

Then use:

```text
fandom_cache_status()
search_fandom_cache(query="commands", include_text=true)
read_fandom_page(title="Commands", include_text=true)
```

Fandom content is community-authored and CC-BY-SA unless a page says otherwise. Keep source URLs and attribution when using it. The repo commits the collector and cache README, not the scraped JSON dump.

## BedWars Code Sync

Use normal project folders so Roblox only receives the scripts you intend to sync:

```text
C:\path\to\your-project\
  scripts\    # uploaded to BedWars
  drafts\     # local-only work in progress
  prompts\    # project brief / build notes
  bwconfig.lua
```

Generate a token in the `Sync` tab of the BedWars script editor, then connect the folder:

```text
connect_sync(
  sync_token="{sync-token}",
  directory="C:\\path\\to\\your-project",
  glob_pattern="scripts/**/*.lua",
  watch=true
)

sync_connected()
```

The token is sent to Easy.gg's Code Sync endpoint and kept only in MCP memory for the current running server process. It is not saved or returned in tool output.

When `watch=true`, the MCP polls the connected folder for saved, deleted, or renamed `.lua` files. When the file set changes, it syncs the whole current folder, matching the VS Code extension's connected-session behavior.

The MCP also reads the VS Code extension's `bwconfig.lua` format when no glob is provided:

```lua
return {
    syncGlob = "scripts/**/*.lua"
}
```

For one-shot folder syncs:

```text
read_directory_project(directory="C:\\path\\to\\your-project")

sync_directory(
  sync_token="{sync-token}",
  directory="C:\\path\\to\\your-project"
)
```

By default, `sync_directory` and `connect_sync` upload only the Lua scripts already in the project. They do not create `main.lua` or `zz_sync_probe.lua`. Exact helper files left by older MCP versions are removed automatically during normal sync. Uploads match the official VS Code extension's multipart filename, content type, and request headers, then repeat once after a short delay to confirm delivery to the active Roblox editor session.

BedWars rejects a truly empty multipart upload with `File is required`. For intentional delete-all syncs, use `allow_empty=true`. The MCP sends an in-memory zero-byte file named `.lua`; the request still contains the required file part, while the empty Lua basename clears the remote script set. Nothing is written to the project folder.

For normal project work, use MCP tools instead of terminal file scans:

- `read_directory_project` to inspect folder state, scripts, prompt, and config.
- `read_directory_script` to read a project Lua file.
- `create_directory_script` to write scripts under `scripts/`.
- `edit_directory_script` to make a small edit and return a unified diff.
- `validate_directory_script` to check APIs, enum values, callback fields, object methods, and basic syntax structure.
- `sync_directory` for normal sync without generated scripts.

If the HTTP upload succeeds but the Roblox editor does not visibly refresh, use the explicit hard-sync tool:

```text
force_sync_directory(
  sync_token="{sync-token}",
  directory="C:\\path\\to\\your-project"
)
```

This explicitly prepares the project and creates a visible probe. Use it only for first-sync troubleshooting.

To remove a script from BedWars, delete it locally and sync the whole containing folder/project:

```text
delete_directory_script(directory="C:\\path\\to\\your-project", file_name="old_script.lua", sync=true)
sync_directory(sync_token="{sync-token}", directory="C:\\path\\to\\your-project")
```

Deleted scripts are archived under `.deleted/` by default. Sync the whole folder after deleting so BedWars receives the current file set and removes scripts that are no longer present.

When deleting the final script in a folder, sync with `allow_empty=true` so the MCP clears the remote file set without creating a placeholder.

## Runtime Limits

The Creative Lua sandbox does not expose every standard Lua global. In particular, do not assume `pcall(...)` or `xpcall(...)` exist.

The Code Sync transport only uploads scripts and reports HTTP delivery. It cannot retrieve the Host Panel Console, read exact remote script contents, start matches, spawn players, or inspect live entities. Use `runtime_capabilities()` before relying on a runtime feature.

For event debugging, generate a temporary trace script:

```text
create_event_trace(
  directory="C:\\path\\to\\your-project",
  event_names=["ProjectileLaunched", "ProjectileHit", "EntityDamage"]
)
```

Sync the trace, reproduce the action, and inspect the Host Panel Console tab. Delete the trace script after debugging. `read_runtime_console(error_text="...")` can analyze console text you paste, but it cannot fetch the Console tab itself.

Use `read_object("Entity")`, `read_type("ProjectileType")`, and `read_event("EntityDamage")` for complete methods, enum values, payload fields, and documented field mutability. Exact-name `search_docs` matches also include the full cached record.

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
