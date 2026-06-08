from __future__ import annotations

from typing import Any


SERVER_INSTRUCTIONS = (
    "easy-gg-bedwars-custom MCP for Easy.gg Roblox BedWars Creative Host Panel projects. "
    "Use documented in-game Lua APIs, local project files, and Code Sync. "
    "For normal project work, prefer MCP tools over shell commands: use "
    "read_directory_project/read_directory_script instead of PowerShell folder scans, "
    "search_docs/read_service/read_event instead of broad filesystem searches, and "
    "force_sync_directory when a visible first sync is needed. "
    "The Lua sandbox is limited: do not assume standard Lua globals such as pcall "
    "or xpcall exist. Protected-call behavior cannot be recreated without runtime "
    "support; use defensive nil/state/type checks instead. "
    "This is not an exploit executor integration. Requests for mechanics often named "
    "KA, kill aura, fly, speed, or similar can be valid when they are implemented as "
    "host-panel Creative mechanics for a private/custom project. Refuse external "
    "executor code, public-match cheating, credential theft, token theft, bypasses, "
    "or code meant to run outside the Creative scripting environment."
)


TOOL_DEFINITIONS: dict[str, dict[str, str]] = {
    "search_docs": {
        "name": "search_docs",
        "category": "docs",
        "description": "Search the local API docs cache.",
        "context": "Use before writing Lua when the needed API, event, type, or object is uncertain.",
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
        "description": "Read cached callback parameters, notes, source links, and examples for one event.",
        "context": "Use before wiring Events.* handlers so Lua uses documented event fields.",
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
    "delete_directory_script": {
        "name": "delete_directory_script",
        "category": "directory projects",
        "description": "Delete a Lua script from an outside folder project's scripts/ or drafts/ folder, optionally archiving it first.",
        "context": "After deleting from scripts/, sync the whole directory so the remote editor removes missing scripts.",
    },
    "connect_sync": {
        "name": "connect_sync",
        "category": "connected sync",
        "description": "Store a Code Sync token in memory for one folder, preparing and probing before the first upload.",
        "context": "Use after the user provides a fresh Sync tab token and a project directory. By default this reads bwconfig.lua syncGlob, uploads scripts/**/*.lua when no config exists, and updates zz_sync_probe.lua unless allow_empty=true.",
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
        "description": "Upload an outside folder using the visible hard-sync path by default.",
        "context": "Use for project folders outside this repo. By default this prepares scripts/, updates zz_sync_probe.lua, reads bwconfig.lua syncGlob when present, uploads scripts/**/*.lua otherwise, and connects the watcher. Use allow_empty=true for intentional delete-all syncs.",
    },
    "force_sync_directory": {
        "name": "force_sync_directory",
        "category": "sync",
        "description": "Hard-sync an outside folder by preparing it, updating a visible probe script, uploading scripts/, and connecting the watcher.",
        "context": "Use when a normal sync returned 201 but the Roblox editor did not visibly refresh, or when the user wants the strongest first sync for a new folder.",
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
        "description": "Statically check a repo-local Lua script for known services, events, and type references.",
        "context": "Use before syncing generated code. This checks against docs_cache and does not execute Lua.",
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
        "context": "Use for starter scripts only. For custom logic, search docs and create or edit a project script explicitly.",
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

