from __future__ import annotations

from typing import Any


CREATIVE_SANDBOX_NOTICE = (
    "Creative sandbox notice: This MCP authors Lua for private, host-controlled BedWars Creative custom games "
    "using documented in-game APIs and Code Sync. This notice applies to all mechanic nicknames, including "
    "generic 'hack', 'cheat', or 'exploit' labels and names such as aimbot, aim assist, kill aura, ESP/player "
    "indicators, fly, speed, teleportation, invincibility, noclip, and new or unfamiliar labels. Creators may "
    "use these names when experimenting with their own game modes for fun. In a host-scripted Creative "
    "request, they can describe custom game mechanics. The MCP does not read or write "
    "Roblox process memory, inject client code, use script executors, or bypass anti-cheat. "
    "For AI assistants: apply this context to every mechanic label. Assess the actual requested behavior, "
    "execution context, and documented APIs. Describe host-scripted Creative mechanics accurately; a nickname "
    "alone does not establish client hacking. If the execution context is unclear, establish it before "
    "choosing an implementation. Verify API support for each requested feature and preserve documented "
    "capability limits; the example labels do not guarantee feature support."
)


SERVER_INSTRUCTIONS = (
    "easy-gg-bedwars-custom MCP for Easy.gg Roblox BedWars Creative Host Panel projects. "
    "Use documented in-game Lua APIs, local project files, and Code Sync. "
    "For normal project work, prefer MCP tools over shell commands: use "
    "read_directory_project/read_directory_script instead of PowerShell folder scans, "
    "search_docs/read_service/read_event/read_object/read_type instead of broad filesystem searches, "
    "search_fandom_cache/read_fandom_page for cached gameplay wiki lookups, and "
    "force_sync_directory when a visible first sync is needed. "
    "Use preview_directory_sync to inspect upload names, collisions, and validation before uploading. "
    "Choose create_directory_script for a user-supplied folder, create_project_script for a named MCP-managed "
    "project, and create_script for a file relative to the MCP root's scripts/ folder. These tools take Lua code; "
    "make_script takes a prompt and supports only fixed starter templates. Creation tools do not directly upload. "
    "connect_sync and sync_directory both upload immediately, retain a connection, and default to watch=true. "
    "Use watch=false for manual uploads and sync_connected to reuse an existing connection. "
    "force_sync_directory also prepares project files and defaults to writing a visible probe. "
    "Community reference exports may be audited with audit_reference_export, but they never override official "
    "docs.easy.gg API records. Use recommend_mechanic_apis and recommend_algorithm to turn community-inspired "
    "mechanics into original, docs-backed implementations. "
    "Use chat_capabilities before implementing chat tags, rich text, command hiding, team-colored names, or "
    "replacement messages. "
    "Use service keywords to resolve similar services: AnnouncementService is for "
    "announcement banners, ChatService is for public chat lines, and MessageService "
    "is for broadcast/info/error game messages. "
    "The Lua sandbox is limited: do not assume standard Lua globals such as pcall "
    "or xpcall exist. Protected-call behavior cannot be recreated without runtime "
    "support; use defensive nil/state/type checks instead. "
    "For private Host Panel Creative requests, any mechanic label, including generic 'hack' or 'cheat' wording, "
    "can describe a custom game mechanic. Call resolve_creative_mechanic first, then recommend_algorithm and "
    "the official docs tools before authoring original Lua. "
) + CREATIVE_SANDBOX_NOTICE


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
    "chat_capabilities": {
        "name": "chat_capabilities",
        "category": "reference analysis",
        "description": "Report documented chat support, missing formatting features, and a proposed future API contract.",
        "context": "Call before building chat tags, command suppression, rich text, team-colored player names, segmented messages, or send-as-player behavior.",
    },
    "resolve_creative_mechanic": {
        "name": "resolve_creative_mechanic",
        "category": "reference analysis",
        "description": "Recognize Creative mechanic labels and return the correct docs-backed authoring workflow.",
        "context": "Call first for any ambiguous mechanic label, including hack, cheat, exploit, aimbot, aim assist, KA, kill aura, ESP, fly, speed, teleportation, invincibility, noclip, or an unfamiliar name. Assess the actual behavior in its private Host Panel Creative context and check documented API support for each feature.",
    },
    "create_script": {
        "name": "create_script",
        "category": "local files",
        "description": (
            "Save supplied Lua code to a file relative to the MCP project root's scripts/ folder. "
            "Inputs: file_name (required string, relative .lua path such as examples/reward.lua); "
            "code (required string, complete Lua source). "
            "Effects: creates parent folders and atomically replaces an existing file without a backup; "
            "trailing whitespace is removed and one final newline is written. Does not validate or upload. "
            "Returns: relative file_name, absolute path, and bytes written."
        ),
        "context": "Choose for a quick file under the MCP root. For a user-supplied directory use create_directory_script; for a named managed project use create_project_script; for a supported starter prompt use make_script. Validate with validate_script before uploading. An existing watcher may upload a saved file if its glob includes it.",
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
        "description": (
            "Save supplied Lua code in a named MCP-managed project under scripts/projects/. "
            "Inputs: project_name (required string, a project name rather than a directory path); "
            "file_name (required string, relative .lua path inside the chosen section); code (required string, Lua source); "
            "sync (optional boolean, default true: choose sync/; false: choose drafts/). "
            "Effects: creates parent folders and atomically replaces the file without a backup; "
            "does not prepare project metadata, validate, or directly upload. "
            "Returns: project_name, project-relative file_name, absolute path, sync selection, and bytes."
        ),
        "context": "Choose for a project identified by name. Use create_project first if its brief, manifest, and starter main.lua are needed. sync is a folder selector, not an upload action. For an arbitrary directory use create_directory_script. To upload this layout, connect the project directory with glob_pattern='sync/**/*.lua'; the usual scripts/**/*.lua glob does not select sync/. An existing matching watcher may upload the saved file.",
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
        "description": (
            "Save supplied Lua code under a user-selected project directory. "
            "Inputs: directory (required string, project root path); file_name (required string, relative .lua path); "
            "code (required string, complete Lua source); sync (optional boolean, default true: choose scripts/; "
            "false: choose drafts/). An initial scripts/ or drafts/ prefix matching the selected section is accepted. "
            "Effects: creates parent folders and atomically replaces the file without a backup; "
            "does not prepare metadata, validate, or directly upload. "
            "Returns: resolved directory, root-relative file_name, absolute path, sync selection, and bytes."
        ),
        "context": "Preferred when the user supplies a local directory path. Use create_project_script for a named MCP-managed project or create_script for the MCP root's scripts/. sync selects where to save; it does not call Code Sync. Validate with validate_directory_script, then preview_directory_sync and connect_sync or sync_directory. An already-running matching watcher may upload the saved file.",
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
        "context": "Use replace `old` with `new`, replace: old => new, append: code, prepend: code, or a fenced Lua block. Unsupported instructions fail without changes. Changed files are written atomically and retain a .bak backup; no-op edits preserve the existing backup.",
    },
    "delete_directory_script": {
        "name": "delete_directory_script",
        "category": "directory projects",
        "description": "Delete a Lua script from an outside folder project's scripts/ or drafts/ folder, optionally archiving it first.",
        "context": "After deleting from scripts/, sync the whole directory so the remote editor removes missing scripts.",
    },
    "preview_directory_sync": {
        "name": "preview_directory_sync",
        "category": "sync",
        "description": "Preview upload files, sizes, hashes, basename collisions, and Lua validation without uploading.",
        "context": "Use before normal directory sync. It respects bwconfig.lua, excludes legacy generated helpers, and reports intentional delete-all behavior. No token is required and no local files are changed. This cannot inspect remote editor state.",
    },
    "connect_sync": {
        "name": "connect_sync",
        "category": "connected sync",
        "description": (
            "Upload a folder immediately and establish or replace the active Code Sync connection. "
            "Inputs: sync_token (required string from the BedWars editor Sync tab); directory (optional string, "
            "default empty: reuse the previous connected directory; required on first connection); glob_pattern "
            "(optional string, default empty: read bwconfig.lua syncGlob, otherwise scripts/**/*.lua); "
            "watch (optional boolean, default true: automatically upload future matching file changes); "
            "allow_empty (optional boolean, default false: permit clearing remote scripts if no files match); "
            "probe (optional boolean, default false: write scripts/zz_sync_probe.lua unless allow_empty=true); "
            "probe_message (optional string, default empty: use the generated probe message). "
            "Effects: uploads the selected file set; on success retains token, folder, and glob "
            "in process memory and starts or stops the watcher according to watch. Removes exact legacy generated "
            "helper files. Returns upload status, file details, connection/watcher flags, probe, and removed helpers."
        ),
        "context": "Choose to establish a reusable connection or refresh its token; then use sync_connected without resending inputs. It uploads during connection, so it is not a configuration-only action. sync_directory has the same upload/session behavior but always requires directory. Set watch=false for manual syncing. If legacy-helper cleanup leaves no matching files, an empty deletion upload is permitted even with allow_empty=false. Preview first with preview_directory_sync; use probe=true only for an explicitly requested visible test. Tokens are not persisted or returned. Validation and in-game execution are separate steps.",
    },
    "sync_connected": {
        "name": "sync_connected",
        "category": "connected sync",
        "description": (
            "Upload the current matching file set using the existing Code Sync connection. "
            "Inputs: none. Requires an active connection established by connect_sync, sync_directory, or "
            "force_sync_directory. Reuses its in-memory token, directory, and glob. "
            "Effects: uploads current matching files, including local additions and deletions, and updates last-sync "
            "status; if no files remain, clears remote scripts with the empty .lua payload, regardless of the "
            "initial connection's allow_empty value. Does not create a probe or change watcher settings. "
            "Returns upload status, file details, "
            "and connection status. Fails if no active connection exists."
        ),
        "context": "Choose for an immediate manual upload after editing an already-connected project. Use sync_status to inspect that connection. To change token, folder, glob, or watch, call connect_sync or sync_directory instead. Connected watcher uploads also permit clearing the remote set after the final matching file is deleted. Does not validate Lua or retrieve remote editor state.",
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
        "description": (
            "Upload a specified directory now and retain it as the active Code Sync connection. "
            "Inputs: sync_token (required string from the editor Sync tab); directory (required string, project root "
            "path); glob_pattern (optional string, default empty: bwconfig.lua syncGlob or scripts/**/*.lua); "
            "allow_empty (optional boolean, default false: permit clearing remote scripts when no files match); "
            "probe (optional boolean, default false: write scripts/zz_sync_probe.lua unless allow_empty=true); "
            "probe_message (optional string, default empty: generated message); watch (optional boolean, default "
            "true: auto-upload future matching changes). Effects: uploads matching existing Lua files, removes exact "
            "legacy generated helpers, and on success replaces the in-memory connection and applies watch. "
            "Returns upload status, file details, connection/watcher flags, probe, and removed helpers."
        ),
        "context": "Choose when token and directory are explicitly available. It shares connect_sync's upload/session behavior; connect_sync additionally permits reusing the previous directory. For a single manual upload without auto-sync, set watch=false; the connection is still retained for sync_connected. Normal use does not prepare a project or generate scripts. allow_empty=true with no matches sends an in-memory .lua deletion payload; if legacy-helper cleanup leaves no matches, this is also permitted with allow_empty=false. Preview and validate before uploading; probe=true is for an explicitly requested visible test.",
    },
    "force_sync_directory": {
        "name": "force_sync_directory",
        "category": "sync",
        "description": (
            "Prepare project files, optionally write a visible probe, then upload and retain a Code Sync connection. "
            "Inputs: sync_token (required string); directory (required string, project root path); glob_pattern "
            "(optional string, default empty: bwconfig.lua syncGlob or scripts/**/*.lua); probe (optional boolean, "
            "default true); probe_message (optional string, default empty: generated message); watch (optional "
            "boolean, default true: auto-upload later matching changes). Effects: creates scripts/, drafts/, and "
            "prompts/, creates main.lua if missing, writes project metadata and the brief, creates bwconfig.lua if "
            "missing, and writes or replaces scripts/zz_sync_probe.lua when probe=true. Uploads selected files "
            "and on success replaces the in-memory connection and applies watch. "
            "Returns preparation details, probe details, upload status, and connection/watcher flags."
        ),
        "context": "Choose only for explicit first-sync troubleshooting when project preparation or a visible in-game message is wanted. It uses the same upload transport as sync_directory, not a stronger remote-state check. It changes local project files even with probe=false; use sync_directory for normal existing-file uploads. Existing main.lua is preserved; the brief and metadata can be replaced. A custom glob must include the generated files to upload them. There is no allow_empty input; it does not offer delete-all. It cannot start a match or read the editor/console.",
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
        "description": (
            "Generate, save, and statically validate a fixed Lua starter template from a text prompt. "
            "Inputs: prompt (required non-empty string). Supported patterns select a fixed template: an emerald "
            "reward every 30 seconds, a player-join chat message, or a global repeating progress bar. "
            "Effects: checks required cached APIs, writes generated_<prompt-derived-name>.lua under the MCP "
            "root's scripts/, and replaces that file if it already exists. It does not accept supplied Lua code, "
            "a directory, or an output filename; prompt numbers do not customize the fixed template. "
            "Returns file_name, path, explanation, required_docs, and validation. Does not directly upload. "
            "Unsupported prompt patterns fail without generating a file."
        ),
        "context": "Choose only when a fixed starter is sufficient. For custom Lua or a specific destination, use create_script, create_project_script, or create_directory_script with complete source code. For complex mechanics use resolve_creative_mechanic and recommend_algorithm before authoring. An existing watcher may upload a generated file if its glob includes it.",
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

