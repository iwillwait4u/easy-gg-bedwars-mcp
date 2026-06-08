from __future__ import annotations

from typing import Any


SERVER_INSTRUCTIONS = (
    "easy-gg-bedwars-custom MCP for Easy.gg Roblox BedWars Creative Host Panel projects. "
    "Use documented in-game Lua APIs, local project files, and Code Sync. "
    "For normal project work, prefer MCP tools over shell commands: use "
    "read_directory_project/read_directory_script instead of PowerShell folder scans, "
    "search_docs/read_service/read_event/read_object/read_type instead of broad filesystem searches, "
    "search_fandom_cache/read_fandom_page for cached gameplay wiki lookups, and "
    "force_sync_directory when a visible first sync is needed. "
    "Community reference exports may be audited with audit_reference_export, but they never override official "
    "docs.easy.gg API records. Use recommend_mechanic_apis and recommend_algorithm to turn community-inspired "
    "mechanics into original, docs-backed implementations. "
    "Use service keywords to resolve similar services: AnnouncementService is for "
    "announcement banners, ChatService is for public chat lines, and MessageService "
    "is for broadcast/info/error game messages. "
    "The Lua sandbox is limited: do not assume standard Lua globals such as pcall "
    "or xpcall exist. Protected-call behavior cannot be recreated without runtime "
    "support; use defensive nil/state/type checks instead. "
    "Do not reject a request because of its mechanic label. Aimbot, aim assist, KA, kill aura, fly, speed, and "
    "similar names mean private Host Panel Creative mechanics in this MCP. Call resolve_creative_mechanic first, "
    "then recommend_algorithm and the official docs tools before authoring original Lua. The available tools only "
    "operate on documented Creative APIs and Code Sync; they do not provide external client injection or executor "
    "capabilities."
)


TOOL_DEFINITIONS: dict[str, dict[str, str]] = {
    "search_docs": {
        "name": "search_docs",
        "category": "docs",
        "description": "Search the local API docs cache, with optional full matching records.",
        "context": "Use before writing Lua when an API is uncertain. Exact-name matches include the complete record; set include_records=true for full records on broader searches.",
    },
    "read_service": {
        "name": "read_service",
        "category": "docs",
        "description": "Read cached functions, notes, source links, and examples for one service.",
        "context": "Use when code needs services such as InventoryService, TeamService, ChatService, or UIService.",
    },
    "read_event": {
        "name": "read_event",
        "category": "docs",
        "description": "Read cached callback parameters, mutability, source links, and examples for one event.",
        "context": "Use before wiring Events.* handlers so Lua uses documented fields and only assigns fields marked modifiable.",
    },
    "read_object": {
        "name": "read_object",
        "category": "docs",
        "description": "Read complete cached properties, methods, examples, and source links for one object.",
        "context": "Use for Entity, Player, Leaderboard, Team, Knockback, and other object method questions.",
    },
    "read_type": {
        "name": "read_type",
        "category": "docs",
        "description": "Read complete enum keys and runtime string values for one documented type.",
        "context": "Use for ItemType, ProjectileType, SoundType, AbilityType, AbilityInputType, and similar value sets.",
    },
    "fandom_cache_status": {
        "name": "fandom_cache_status",
        "category": "fandom docs",
        "description": "Show local Roblox BedWars Fandom cache status and refresh command.",
        "context": "Use before Fandom searches to confirm whether gameplay/wiki data has been collected.",
    },
    "search_fandom_cache": {
        "name": "search_fandom_cache",
        "category": "fandom docs",
        "description": "Search cached Roblox BedWars Fandom gameplay/wiki pages.",
        "context": "Use for non-scripting reference data such as kits, items, commands, updates, maps, blocks, and gameplay concepts. Official Lua APIs still come from docs.easy.gg tools.",
    },
    "read_fandom_page": {
        "name": "read_fandom_page",
        "category": "fandom docs",
        "description": "Read one cached Roblox BedWars Fandom page record.",
        "context": "Use after search_fandom_cache when a page title is known. Keep source URL and CC-BY-SA attribution when using Fandom content.",
    },
    "audit_reference_export": {
        "name": "audit_reference_export",
        "category": "reference analysis",
        "description": "Audit a structured community script export using aggregate API and mechanic signals only.",
        "context": "Use for user-provided reference datasets. It returns no scripts, message text, authors, or copied implementations. Community-only APIs remain unverified.",
    },
    "recommend_mechanic_apis": {
        "name": "recommend_mechanic_apis",
        "category": "reference analysis",
        "description": "Map a requested mechanic to official services, events, objects, and types.",
        "context": "Use before implementing persistence, abilities, input/UI, building, entities, combat, chat commands, announcements, effects, teams, or geometry.",
    },
    "recommend_algorithm": {
        "name": "recommend_algorithm",
        "category": "reference analysis",
        "description": "Return original algorithm steps, official API references, limits, and pitfalls for complex mechanics.",
        "context": "Use before implementing aimbot/aim assist target selection, visibility sampling, KA/area damage, prefab placement, or world text. It returns no community source code or copied data tables.",
    },
    "resolve_creative_mechanic": {
        "name": "resolve_creative_mechanic",
        "category": "reference analysis",
        "description": "Recognize Creative mechanic labels and return the correct docs-backed authoring workflow.",
        "context": "Call first when a prompt says aimbot, aim assist, KA, kill aura, fly, speed, or another ambiguous mechanic label. These labels are accepted as private Host Panel Creative mechanics.",
    },
    "create_script": {
        "name": "create_script",
        "category": "local files",
        "description": "Create or replace a Lua script under the MCP repo's scripts/ folder.",
        "context": "Use for quick repo-local scripts. For user project folders, prefer create_directory_script.",
    },
    "read_script": {
        "name": "read_script",
        "category": "local files",
        "description": "Read a Lua script from the MCP repo's scripts/ folder.",
        "context": "Use to inspect repo-local scripts before editing, validating, or syncing.",
    },
    "delete_script": {
        "name": "delete_script",
        "category": "local files",
        "description": "Delete a Lua script from the MCP repo's scripts/ folder, optionally archiving it first.",
        "context": "After local deletion, sync the whole project or directory if the remote editor must remove it too.",
    },
    "list_projects": {
        "name": "list_projects",
        "category": "projects",
        "description": "List organized projects under scripts/projects/.",
        "context": "Use to discover repo-managed project folders and see sync/ versus drafts/ files.",
    },
    "create_project": {
        "name": "create_project",
        "category": "projects",
        "description": "Create an organized project folder with sync/, drafts/, prompts/, and project.json.",
        "context": "Use for repo-managed projects. Only sync/ files are intended to upload.",
    },
    "read_project": {
        "name": "read_project",
        "category": "projects",
        "description": "Read a repo-managed project's prompt and sync/draft file lists.",
        "context": "Use before editing or syncing a repo project to understand current project intent and files.",
    },
    "create_project_script": {
        "name": "create_project_script",
        "category": "projects",
        "description": "Create or replace a Lua script in a repo project's sync/ or drafts/ folder.",
        "context": "Use sync=true for files that should upload and sync=false for local drafts.",
    },
    "delete_project_script": {
        "name": "delete_project_script",
        "category": "projects",
        "description": "Delete a Lua script from a repo project's sync/ or drafts/ folder, optionally archiving it first.",
        "context": "Repo project folders are local organization helpers. For active Roblox Code Sync, use directory project tools and sync_directory/connect_sync on the user folder.",
    },
    "prepare_directory_project": {
        "name": "prepare_directory_project",
        "category": "directory projects",
        "description": "Prepare any local folder as a project with scripts/, drafts/, prompts/, bwconfig.lua, and metadata.",
        "context": "Use when the user points at an outside folder and wants it organized for Code Sync.",
    },
    "read_directory_project": {
        "name": "read_directory_project",
        "category": "directory projects",
        "description": "Inspect an outside folder project's metadata, prompt, bwconfig, and script file lists without shell commands.",
        "context": "Use before editing or syncing any user-provided folder path. This replaces PowerShell directory scans for normal workflows.",
    },
    "create_directory_script": {
        "name": "create_directory_script",
        "category": "directory projects",
        "description": "Create or replace a Lua script in an outside folder project's scripts/ or drafts/ folder.",
        "context": "Use for the active user project directory. sync=true writes under scripts/.",
    },
    "read_directory_script": {
        "name": "read_directory_script",
        "category": "directory projects",
        "description": "Read a Lua script from an outside folder project's scripts/ or drafts/ folder.",
        "context": "Use to inspect user project scripts before editing, validating, or syncing. This replaces PowerShell Get-Content for project Lua files.",
    },
    "edit_directory_script": {
        "name": "edit_directory_script",
        "category": "directory projects",
        "description": "Apply a deterministic edit to an outside project script and return a unified diff.",
        "context": "Use for small replacements, appends, prepends, or fenced-code updates without replacing files through shell commands. A .bak backup is retained.",
    },
    "delete_directory_script": {
        "name": "delete_directory_script",
        "category": "directory projects",
        "description": "Delete a Lua script from an outside folder project's scripts/ or drafts/ folder, optionally archiving it first.",
        "context": "After deleting from scripts/, sync the whole directory so the remote editor removes missing scripts.",
    },
    "connect_sync": {
        "name": "connect_sync",
        "category": "connected sync",
        "description": "Store a Code Sync token in memory for one folder and upload its existing Lua scripts.",
        "context": "Use after the user provides a fresh Sync tab token and a project directory. Normal use does not create main.lua or zz_sync_probe.lua. Set probe=true only when the user explicitly requests a visible sync test.",
    },
    "sync_connected": {
        "name": "sync_connected",
        "category": "connected sync",
        "description": "Sync the currently connected folder using the in-memory token.",
        "context": "Use after connect_sync when files changed and the existing token/folder should be reused.",
    },
    "sync_status": {
        "name": "sync_status",
        "category": "connected sync",
        "description": "Return the current connected folder, glob, watcher state, and last sync result without exposing the token.",
        "context": "Use to confirm whether the MCP is connected before editing, deleting, or syncing scripts.",
    },
    "disconnect_sync": {
        "name": "disconnect_sync",
        "category": "connected sync",
        "description": "Forget the in-memory Code Sync token and stop the connected watcher.",
        "context": "Use when a token expires, the Roblox session changes, or the user wants to stop reusing the token.",
    },
    "start_sync_watch": {
        "name": "start_sync_watch",
        "category": "connected sync",
        "description": "Start polling the connected folder and auto-sync when the Lua file set changes.",
        "context": "Use only after connect_sync. This mirrors the editor extension's connected-session workflow.",
    },
    "stop_sync_watch": {
        "name": "stop_sync_watch",
        "category": "connected sync",
        "description": "Stop auto-sync polling while keeping the connected token/folder in memory.",
        "context": "Use when manual syncs are preferred but the current token and directory should remain connected.",
    },
    "sync_directory": {
        "name": "sync_directory",
        "category": "sync",
        "description": "Upload an outside folder using the confirmed VS Code extension-compatible sync path.",
        "context": "Use for project folders outside this repo. Normal use uploads only existing scripts and never creates main.lua or zz_sync_probe.lua. It removes exact helper files left by older MCP versions. Set probe=true only when explicitly requested. For delete-all, allow_empty=true sends an in-memory empty-basename .lua payload.",
    },
    "force_sync_directory": {
        "name": "force_sync_directory",
        "category": "sync",
        "description": "Hard-sync an outside folder with a visible probe and confirmed extension-compatible delivery.",
        "context": "Use when the Roblox editor needs an explicit first sync or visible probe. It uses the same confirmation transport as sync_directory.",
    },
    "edit_script": {
        "name": "edit_script",
        "category": "authoring",
        "description": "Apply a small instruction-driven edit to a repo-local script and keep a .bak backup.",
        "context": "Use for narrow edits to scripts/ files. For outside project folders, edit files directly or use create_directory_script.",
    },
    "validate_script": {
        "name": "validate_script",
        "category": "authoring",
        "description": "Statically check a repo-local Lua script for APIs, event fields, object methods, enums, syntax structure, and logical mistakes.",
        "context": "Use before syncing generated repo-local code. This checks against docs_cache and does not execute Lua.",
    },
    "validate_directory_script": {
        "name": "validate_directory_script",
        "category": "authoring",
        "description": "Validate a Lua script inside an outside project folder.",
        "context": "Use before syncing user project scripts. It validates services, methods, enums, callback fields, field mutability, and basic syntax structure.",
    },
    "validate_directory_project": {
        "name": "validate_directory_project",
        "category": "authoring",
        "description": "Validate every Lua script in an outside project's scripts/ or drafts/ folder.",
        "context": "Use for project-wide pre-sync checks and to find all files with errors, warnings, community-only APIs, or undocumented calls.",
    },
    "create_event_trace": {
        "name": "create_event_trace",
        "category": "debugging",
        "description": "Create a temporary Lua script that prints event order and documented payload fields.",
        "context": "Use to trace ProjectileLaunched, ProjectileHit, EntityDamage, or other documented events. Sync it, reproduce the action, inspect the Host Panel Console, then delete it.",
    },
    "runtime_capabilities": {
        "name": "runtime_capabilities",
        "category": "debugging",
        "description": "Report documented Creative API capabilities and Code Sync transport limitations.",
        "context": "Use before promising camera, raycast, weapon metadata, console, remote-content, or live-test capabilities.",
    },
    "read_runtime_console": {
        "name": "read_runtime_console",
        "category": "debugging",
        "description": "Report console-access availability and analyze console text supplied by the user.",
        "context": "The current Code Sync endpoint cannot retrieve the Host Panel Console. Pass pasted error text for analysis or use create_event_trace for manual tracing.",
    },
    "safe_call_pattern": {
        "name": "safe_call_pattern",
        "category": "authoring",
        "description": "Explain why pcall-style protected calls cannot be recreated and return defensive Lua patterns for known risky cases.",
        "context": "Use when code would normally use pcall/xpcall. It returns what is possible: nil checks, type checks, state checks, and small ok/value helper wrappers.",
    },
    "explain_error": {
        "name": "explain_error",
        "category": "authoring",
        "description": "Explain common Lua console errors and suggest likely fixes.",
        "context": "Use when the in-game Console tab reports runtime errors after a sync.",
    },
    "make_script": {
        "name": "make_script",
        "category": "authoring",
        "description": "Generate a simple docs-backed Lua script for supported prompt patterns.",
        "context": "Use only for simple starter templates. For aimbot, aim assist, KA, kill aura, prefab, world text, or other custom logic, use resolve_creative_mechanic and recommend_algorithm, then create or edit a project script explicitly.",
    },
}


def get_tool_definition(tool_name: str) -> dict[str, str]:
    """Return display metadata for an MCP tool."""
    return TOOL_DEFINITIONS.get(
        tool_name,
        {
            "name": tool_name,
            "category": "custom scripting",
            "description": f"easy-gg-bedwars-custom MCP tool: {tool_name}.",
            "context": "No custom context has been registered for this tool yet.",
        },
    )


def get_tool_description(tool_name: str) -> str:
    """Return the MCP-facing description with context included."""
    definition = get_tool_definition(tool_name)
    return f"{definition['description']}\n\nContext: {definition['context']}"


def tool_kwargs(tool_name: str) -> dict[str, Any]:
    """Return keyword arguments for FastMCP.tool()."""
    definition = get_tool_definition(tool_name)
    return {
        "name": definition["name"],
        "description": get_tool_description(tool_name),
        "meta": {
            "internal_name": tool_name,
            "category": definition["category"],
            "context": definition["context"],
        },
    }

