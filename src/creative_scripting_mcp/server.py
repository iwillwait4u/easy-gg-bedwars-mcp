from __future__ import annotations

import json
import os
import re
import shutil
import threading
import time
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import httpx
from mcp.server.fastmcp import FastMCP

from .tools import SERVER_INSTRUCTIONS, tool_kwargs


mcp = FastMCP("easy-gg-bedwars-custom", instructions=SERVER_INSTRUCTIONS)


def bedwars_tool(function: Any) -> Any:
    """Register a function as an MCP tool with shared BedWars metadata."""
    return mcp.tool(**tool_kwargs(function.__name__))(function)

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = Path(os.environ.get("CREATIVE_SCRIPTING_MCP_ROOT", PACKAGE_ROOT.parent.parent)).resolve()
DOCS_CACHE_DIR = PROJECT_ROOT / "docs_cache"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
PROJECTS_DIR = SCRIPTS_DIR / "projects"
DEFAULT_PROJECT_NAME = "default"
CODE_SYNC_BASE_URL = "https://rblx-bedwars-sync-service-o6h4tsr73a-uc.a.run.app"
SYNC_SESSION: dict[str, Any] = {}
SYNC_LOCK = threading.RLock()
SYNC_WATCHER_STOP: threading.Event | None = None
SYNC_WATCHER_THREAD: threading.Thread | None = None

DOC_FILES = {
    "services": "services.json",
    "events": "events.json",
    "types": "types.json",
    "objects": "objects.json",
    "utilities": "utilities.json",
}

SCRIPT_NAME_RE = re.compile(r"^[A-Za-z0-9_.\-/\\ ]+\.lua$")
PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,47}$")
SERVICE_USE_RE = re.compile(r"\b([A-Z][A-Za-z0-9]+Service)\s*[:.]")
SERVICE_CALL_RE = re.compile(r"\b([A-Z][A-Za-z0-9]+Service)\s*([:.])\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(")
EVENT_USE_RE = re.compile(r"\bEvents\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(")
ITEM_TYPE_RE = re.compile(r"\bItemType\s*\.\s*([A-Z][A-Z0-9_]*)\b")
TYPE_VALUE_RE = re.compile(r"\b([A-Z][A-Za-z0-9]+Type)\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)\b")
LUA_STRING_RE = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"")
FENCED_CODE_RE = re.compile(r"```(?:lua|luau|bwlua)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
SYNC_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{6,128}$")
LUA_STRING_OR_COMMENT_RE = re.compile(
    r"--[^\n]*|'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"",
    re.DOTALL,
)

DISALLOWED_INTENTS = (
    "script executor",
    "executor",
    "injector",
    "external executor",
    "dupe",
    "public match",
    "ranked",
    "cookie",
    "token",
    "session",
    "bypass",
    "anti cheat bypass",
    "anticheat bypass",
    "steal",
    "cookie logger",
)

LUA_DANGEROUS_PATTERNS = (
    "loadstring",
    "getgenv",
    "setclipboard",
    "queue_on_teleport",
    "syn.",
    "httpget",
    "httppost",
)

ROBLOX_GLOBALS_TO_WARN = (
    "workspace",
    "game",
    "Instance",
    "Players",
    "ReplicatedStorage",
    "ServerScriptService",
    "RunService",
    "HttpService",
    "TeleportService",
)

UNAVAILABLE_LUA_GLOBALS = (
    "pcall",
    "xpcall",
)


class BedWarsMcpError(ValueError):
    """A user-facing MCP tool error."""


@dataclass(frozen=True)
class GeneratedScript:
    file_name: str
    code: str
    explanation: str
    required: dict[str, list[str]]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise BedWarsMcpError(f"Docs cache file is invalid JSON: {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise BedWarsMcpError(f"Docs cache file must contain a JSON object: {path.name}")
    return data


def _load_docs_cache() -> dict[str, dict[str, Any]]:
    return {
        category: _read_json(DOCS_CACHE_DIR / file_name)
        for category, file_name in DOC_FILES.items()
    }


def _casefold_lookup(records: dict[str, Any], name: str) -> tuple[str, Any] | None:
    wanted = name.casefold()
    for key, value in records.items():
        if key.casefold() == wanted:
            return key, value
    return None


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _short_snippet(record: dict[str, Any], query: str) -> str:
    description = str(record.get("description") or record.get("summary") or "")
    if description:
        return description

    examples = record.get("examples") or []
    if isinstance(examples, list) and examples:
        first = examples[0]
        if isinstance(first, dict):
            return str(first.get("description") or first.get("code") or "")[:240]
        return str(first)[:240]

    text = _json_text(record)
    index = text.casefold().find(query.casefold())
    if index == -1:
        return text[:240]
    start = max(index - 80, 0)
    end = min(index + 160, len(text))
    return text[start:end]


def _entry_source(record: dict[str, Any]) -> dict[str, str | None]:
    return {
        "source_name": record.get("source_name"),
        "source_url": record.get("source_url"),
    }


def _safe_script_path(file_name: str, *, must_exist: bool = False) -> Path:
    if not file_name or not file_name.strip():
        raise BedWarsMcpError("file_name is required.")
    if not SCRIPT_NAME_RE.match(file_name):
        raise BedWarsMcpError("file_name must be a relative .lua path using normal file-name characters.")

    requested = Path(file_name)
    if requested.is_absolute() or any(part == ".." for part in requested.parts):
        raise BedWarsMcpError("Path traversal is not allowed. Use a path inside scripts/ only.")
    if requested.suffix.casefold() != ".lua":
        raise BedWarsMcpError("Only .lua files are allowed.")

    resolved = (SCRIPTS_DIR / requested).resolve()
    scripts_root = SCRIPTS_DIR.resolve()
    if resolved != scripts_root and scripts_root not in resolved.parents:
        raise BedWarsMcpError("Resolved path is outside the scripts directory.")
    if must_exist and not resolved.exists():
        raise BedWarsMcpError(f"Script not found: {file_name}")
    return resolved


def _safe_project_name(project_name: str) -> str:
    name = (project_name or DEFAULT_PROJECT_NAME).strip()
    if not PROJECT_NAME_RE.match(name):
        raise BedWarsMcpError(
            "project_name must be 1-48 characters using letters, numbers, hyphen, or underscore."
        )
    return name


def _project_dir(project_name: str) -> Path:
    name = _safe_project_name(project_name)
    resolved = (PROJECTS_DIR / name).resolve()
    projects_root = PROJECTS_DIR.resolve()
    if resolved != projects_root and projects_root not in resolved.parents:
        raise BedWarsMcpError("Resolved project path is outside scripts/projects.")
    return resolved


def _project_relative_script_path(project_name: str, file_name: str, *, sync: bool = True) -> str:
    if not file_name or not file_name.strip():
        raise BedWarsMcpError("file_name is required.")
    if not SCRIPT_NAME_RE.match(file_name):
        raise BedWarsMcpError("file_name must be a relative .lua path using normal file-name characters.")

    requested = Path(file_name)
    if requested.is_absolute() or any(part == ".." for part in requested.parts):
        raise BedWarsMcpError("Path traversal is not allowed. Use a file name inside the project only.")
    if requested.suffix.casefold() != ".lua":
        raise BedWarsMcpError("Only .lua files are allowed.")

    section = "sync" if sync else "drafts"
    return str(Path("projects") / _safe_project_name(project_name) / section / requested).replace("\\", "/")


def _write_script(file_name: str, code: str) -> Path:
    path = _safe_script_path(file_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code.rstrip() + "\n", encoding="utf-8")
    return path


def _archive_script_copy(path: Path, *, relative_root: Path, archive_root: Path) -> Path:
    root = relative_root.resolve()
    relative = path.resolve().relative_to(root)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_path = archive_root / ".deleted" / relative.parent / f"{path.name}.{timestamp}.deleted"

    counter = 2
    while archive_path.exists():
        archive_path = archive_root / ".deleted" / relative.parent / f"{path.name}.{timestamp}.{counter}.deleted"
        counter += 1

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, archive_path)
    return archive_path


def _remove_script_path(
    path: Path,
    *,
    archive: bool,
    relative_root: Path,
    archive_root: Path,
) -> dict[str, Any]:
    root = relative_root.resolve()
    relative_name = str(path.resolve().relative_to(root)).replace("\\", "/")
    size = path.stat().st_size
    archive_path: Path | None = None
    if archive:
        archive_path = _archive_script_copy(path, relative_root=root, archive_root=archive_root)

    path.unlink()

    return {
        "file_name": relative_name,
        "deleted": True,
        "tombstoned": False,
        "bytes": size,
        "archive": archive,
        "archive_path": str(archive_path) if archive_path else None,
        "remote_note": (
            "The local script was removed. Sync the containing folder/project so BedWars receives the current "
            "file set and removes scripts that are no longer present."
        ),
    }


def _delete_script_path(path: Path, *, archive: bool) -> dict[str, Any]:
    return _remove_script_path(
        path,
        archive=archive,
        relative_root=SCRIPTS_DIR,
        archive_root=SCRIPTS_DIR,
    )


def _code_without_lua_strings_or_comments(code: str) -> str:
    return LUA_STRING_OR_COMMENT_RE.sub(" ", code)


def _directory_sync_file_paths(directory: str, glob_pattern: str) -> tuple[Path, list[Path]]:
    if not directory or not directory.strip():
        raise BedWarsMcpError("directory is required.")

    root = _safe_directory_project_path(directory)
    if not root.exists():
        raise BedWarsMcpError(f"Directory not found: {root}")
    if not root.is_dir():
        raise BedWarsMcpError(f"Sync root is not a directory: {root}")

    pattern = (glob_pattern or "**/*.lua").strip() or "**/*.lua"
    if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
        raise BedWarsMcpError("glob_pattern must stay inside the selected directory and cannot use absolute paths or '..'.")

    paths: list[Path] = []
    seen: set[Path] = set()
    for candidate in root.glob(pattern):
        if not candidate.is_file() or candidate.suffix.casefold() != ".lua":
            continue
        if candidate.name.casefold() == "bwconfig.lua":
            continue
        resolved = candidate.resolve()
        if resolved != root and root not in resolved.parents:
            continue
        if ".deleted" in resolved.relative_to(root).parts:
            continue
        if resolved not in seen:
            paths.append(resolved)
            seen.add(resolved)
    return root, sorted(paths)


def _read_bwconfig_sync_glob(root: Path, default: str) -> str:
    config_path = root / "bwconfig.lua"
    if not config_path.exists():
        return default

    text = config_path.read_text(encoding="utf-8")
    match = re.search(r"\bsyncGlob\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not match:
        return default
    return match.group(1).strip() or default


def _lua_quote(text: str) -> str:
    safe = text.encode("ascii", "replace").decode("ascii")
    safe = safe.replace("\\", "\\\\").replace('"', '\\"')
    safe = safe.replace("\r", "\\r").replace("\n", "\\n")
    return f'"{safe}"'


def _write_sync_probe(root: Path, message: str = "") -> dict[str, Any]:
    scripts_dir = root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    probe_message = message.strip() or f"{root.name} sync probe uploaded."
    probe_path = scripts_dir / "zz_sync_probe.lua"
    code = (
        "-- Sync probe generated by easy-gg-bedwars-custom.\n"
        f"-- Updated at {timestamp}.\n"
        f"ChatService.sendMessage({_lua_quote(probe_message)})\n"
    )
    probe_path.write_text(code, encoding="utf-8")
    return {
        "path": str(probe_path),
        "file_name": "scripts/zz_sync_probe.lua",
        "message": probe_message,
        "updated_at": timestamp,
    }


def _auto_upload_root(root: Path, paths: list[Path]) -> Path:
    scripts_dir = root / "scripts"
    if scripts_dir.exists() and paths and all(path == scripts_dir or scripts_dir in path.parents for path in paths):
        return scripts_dir
    return root


def _sync_directory_with_token(
    sync_token: str,
    directory: str,
    glob_pattern: str,
    *,
    upload_root: Path | None = None,
    allow_empty: bool = False,
) -> dict[str, Any]:
    root, paths = _directory_sync_file_paths(directory, glob_pattern)
    if not paths and not allow_empty:
        raise BedWarsMcpError(f"No .lua files matched inside {root} for glob_pattern: {glob_pattern}")

    selected_upload_root = upload_root or _auto_upload_root(root, paths)
    result = _post_sync_files(sync_token, paths, upload_root=selected_upload_root, allow_empty=allow_empty)
    result["directory"] = str(root)
    result["glob_pattern"] = glob_pattern
    result["upload_root"] = str(selected_upload_root)
    return result


def _prepare_directory_for_first_sync(root: Path, glob_pattern: str, *, allow_empty: bool) -> tuple[str, dict[str, Any] | None]:
    if allow_empty:
        return glob_pattern, None
    if root.exists() and not root.is_dir():
        return glob_pattern, None
    if root.exists():
        try:
            _, paths = _directory_sync_file_paths(str(root), glob_pattern)
        except BedWarsMcpError:
            paths = []
        if paths:
            return glob_pattern, None

    prepared = prepare_directory_project(
        directory=str(root),
        prompt=f"BedWars Creative project for {root.name}",
    )
    return "scripts/**/*.lua", prepared


def _store_sync_session(sync_token: str, result: dict[str, Any]) -> None:
    if not result.get("ok"):
        return
    with SYNC_LOCK:
        watcher_running = bool(SYNC_SESSION.get("watcher_running"))
        last_auto_sync_at = SYNC_SESSION.get("last_auto_sync_at")
        SYNC_SESSION.clear()
        SYNC_SESSION.update(
            {
                "sync_token": sync_token,
                "directory": result.get("directory"),
                "glob_pattern": result.get("glob_pattern"),
                "upload_root": result.get("upload_root"),
                "connected": True,
                "last_status_code": result.get("status_code"),
                "last_file_count": result.get("file_count"),
                "last_uploaded_files": result.get("uploaded_files"),
                "last_error": None,
                "watcher_running": watcher_running,
                "last_auto_sync_at": last_auto_sync_at,
                "token_stored_in_memory_only": True,
            }
        )


def _sync_file_snapshot(directory: str, glob_pattern: str) -> tuple[tuple[str, int, int], ...]:
    root, paths = _directory_sync_file_paths(directory, glob_pattern)
    snapshot: list[tuple[str, int, int]] = []
    for path in paths:
        stat = path.stat()
        snapshot.append(
            (
                str(path.relative_to(root)).replace("\\", "/"),
                stat.st_size,
                stat.st_mtime_ns,
            )
        )
    return tuple(sorted(snapshot))


def _sync_connected_internal() -> dict[str, Any]:
    with SYNC_LOCK:
        token = str(SYNC_SESSION.get("sync_token") or "")
        directory = str(SYNC_SESSION.get("directory") or "")
        glob_pattern = str(SYNC_SESSION.get("glob_pattern") or "scripts/**/*.lua")

    if not token or not directory:
        raise BedWarsMcpError("No active sync connection. Call connect_sync first.")

    result = _sync_directory_with_token(token, directory, glob_pattern, allow_empty=True)
    _store_sync_session(token, result)
    return result


def _sync_watcher_loop(poll_seconds: float, debounce_seconds: float) -> None:
    last_snapshot: tuple[tuple[str, int, int], ...] | None = None
    while True:
        stop_event = SYNC_WATCHER_STOP
        if stop_event is None or stop_event.wait(poll_seconds):
            break

        with SYNC_LOCK:
            connected = bool(SYNC_SESSION.get("connected"))
            directory = str(SYNC_SESSION.get("directory") or "")
            glob_pattern = str(SYNC_SESSION.get("glob_pattern") or "scripts/**/*.lua")

        if not connected or not directory:
            continue

        try:
            snapshot = _sync_file_snapshot(directory, glob_pattern)
        except Exception as exc:  # pragma: no cover - defensive runtime state.
            with SYNC_LOCK:
                SYNC_SESSION["last_error"] = str(exc)
            continue

        if last_snapshot is None:
            last_snapshot = snapshot
            continue
        if snapshot == last_snapshot:
            continue

        if stop_event.wait(debounce_seconds):
            break

        try:
            stable_snapshot = _sync_file_snapshot(directory, glob_pattern)
            result = _sync_connected_internal()
            with SYNC_LOCK:
                SYNC_SESSION["last_auto_sync_at"] = datetime.now(timezone.utc).isoformat()
                SYNC_SESSION["last_error"] = None
            last_snapshot = stable_snapshot
        except Exception as exc:  # pragma: no cover - defensive runtime state.
            with SYNC_LOCK:
                SYNC_SESSION["last_error"] = str(exc)


def _start_sync_watcher(poll_seconds: float = 1.0, debounce_seconds: float = 0.4) -> bool:
    global SYNC_WATCHER_STOP, SYNC_WATCHER_THREAD
    if SYNC_WATCHER_THREAD and SYNC_WATCHER_THREAD.is_alive():
        with SYNC_LOCK:
            SYNC_SESSION["watcher_running"] = True
        return False

    SYNC_WATCHER_STOP = threading.Event()
    SYNC_WATCHER_THREAD = threading.Thread(
        target=_sync_watcher_loop,
        args=(poll_seconds, debounce_seconds),
        daemon=True,
        name="bedwars-sync-watch",
    )
    SYNC_WATCHER_THREAD.start()
    with SYNC_LOCK:
        SYNC_SESSION["watcher_running"] = True
    return True


def _stop_sync_watcher() -> bool:
    global SYNC_WATCHER_STOP, SYNC_WATCHER_THREAD
    was_running = bool(SYNC_WATCHER_THREAD and SYNC_WATCHER_THREAD.is_alive())
    if SYNC_WATCHER_STOP:
        SYNC_WATCHER_STOP.set()
    if SYNC_WATCHER_THREAD and SYNC_WATCHER_THREAD.is_alive():
        SYNC_WATCHER_THREAD.join(timeout=2.0)
    SYNC_WATCHER_STOP = None
    SYNC_WATCHER_THREAD = None
    with SYNC_LOCK:
        SYNC_SESSION["watcher_running"] = False
    return was_running


def _safe_directory_project_path(directory: str) -> Path:
    if not directory or not directory.strip():
        raise BedWarsMcpError("directory is required.")

    root = Path(directory.strip()).expanduser().resolve()
    if root == root.anchor or root.parent == root:
        raise BedWarsMcpError("Refusing to use a filesystem root as a BedWars project directory.")
    return root


def _directory_relative_script_path(directory: str, file_name: str, *, sync: bool = True) -> tuple[Path, Path]:
    root = _safe_directory_project_path(directory)
    if not file_name or not file_name.strip():
        raise BedWarsMcpError("file_name is required.")
    if not SCRIPT_NAME_RE.match(file_name):
        raise BedWarsMcpError("file_name must be a relative .lua path using normal file-name characters.")

    requested = Path(file_name)
    if requested.is_absolute() or any(part == ".." for part in requested.parts):
        raise BedWarsMcpError("Path traversal is not allowed. Use a file name inside the directory project only.")
    if requested.suffix.casefold() != ".lua":
        raise BedWarsMcpError("Only .lua files are allowed.")

    section = "scripts" if sync else "drafts"
    if requested.parts and requested.parts[0].casefold() == section:
        requested = Path(*requested.parts[1:])
        if not requested.parts:
            raise BedWarsMcpError("file_name must include a .lua file name.")
    path = (root / section / requested).resolve()
    if path != root and root not in path.parents:
        raise BedWarsMcpError("Resolved script path is outside the selected directory.")
    return root, path


def _directory_lua_file_infos(root: Path, base: Path) -> list[dict[str, Any]]:
    if not base.exists():
        return []

    files: list[dict[str, Any]] = []
    for path in sorted(base.rglob("*.lua")):
        if not path.is_file():
            continue
        resolved = path.resolve()
        if resolved != root and root not in resolved.parents:
            continue
        relative_parts = resolved.relative_to(root).parts
        if ".deleted" in relative_parts:
            continue

        stat = path.stat()
        files.append(
            {
                "file_name": str(path.relative_to(base)).replace("\\", "/"),
                "project_path": str(path.relative_to(root)).replace("\\", "/"),
                "bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds"),
            }
        )
    return files


def _post_sync_files(
    sync_token: str,
    paths: list[Path],
    *,
    upload_root: Path,
    allow_empty: bool = False,
) -> dict[str, Any]:
    token = (sync_token or "").strip()
    if not token:
        raise BedWarsMcpError("sync_token is required. Generate it in the BedWars script editor Sync tab.")
    if not SYNC_TOKEN_RE.match(token):
        raise BedWarsMcpError("sync_token has an unexpected format. Paste only the token, with no URL or spaces.")
    if not paths and not allow_empty:
        raise BedWarsMcpError("No .lua files matched the sync target.")

    root = upload_root.resolve()
    uploaded = [str(path.relative_to(root)).replace("\\", "/") for path in paths]
    url = f"{CODE_SYNC_BASE_URL}/servers/sync-code/{token}/sync-files"

    try:
        with ExitStack() as stack:
            files = [
                (
                    "files",
                    (
                        str(path.relative_to(root)).replace("\\", "/"),
                        stack.enter_context(path.open("rb")),
                        "text/x-lua",
                    ),
                )
                for path in paths
            ]
            if files:
                response = httpx.post(url, files=files, timeout=30.0)
            else:
                response = httpx.post(url, files={}, timeout=30.0)
    except httpx.RequestError as exc:
        raise BedWarsMcpError(f"Code Sync request failed before BedWars responded: {exc}") from exc

    return {
        "ok": 200 <= response.status_code < 300,
        "status_code": response.status_code,
        "uploaded_files": uploaded,
        "file_count": len(uploaded),
        "token_stored": False,
        "note": "The sync token was used for this request only and was not stored or returned.",
        "warning": None
        if 200 <= response.status_code < 300
        else "Sync failed. Generate a fresh token in the BedWars script editor Sync tab and try again.",
    }


def _known_service_functions(service_record: dict[str, Any]) -> set[str]:
    functions = service_record.get("functions")
    if not isinstance(functions, list):
        return set()
    names: set[str] = set()
    for function in functions:
        if isinstance(function, dict) and isinstance(function.get("name"), str):
            names.add(function["name"])
    return names


def _known_type_values(type_record: dict[str, Any]) -> set[str]:
    values = type_record.get("values")
    if isinstance(values, dict):
        return set(values)
    if isinstance(values, list):
        return {str(value) for value in values}
    return set()


def _known_type_string_values(type_record: dict[str, Any]) -> set[str]:
    values = type_record.get("values")
    if isinstance(values, dict):
        return {str(value) for value in values.values()}
    if isinstance(values, list):
        return {str(value) for value in values}
    return set()


def _lua_string_literals(code: str) -> set[str]:
    literals: set[str] = set()
    index = 0
    while index < len(code):
        quote = code[index]
        if quote not in {"'", '"'}:
            index += 1
            continue

        index += 1
        chars: list[str] = []
        while index < len(code):
            char = code[index]
            if char == "\\" and index + 1 < len(code):
                chars.append(code[index + 1])
                index += 2
                continue
            if char == quote:
                index += 1
                break
            chars.append(char)
            index += 1
        literals.add("".join(chars))
    return literals


def _ensure_allowed_prompt(prompt: str) -> None:
    lower_prompt = prompt.casefold()
    blocked = [term for term in DISALLOWED_INTENTS if term in lower_prompt]
    if blocked:
        raise BedWarsMcpError(
            "This MCP is only for Creative Host Panel scripting and documented in-game Lua APIs. "
            f"Blocked unsafe or out-of-scope terms: {', '.join(sorted(blocked))}."
        )


def _docs_have_required(required: dict[str, list[str]]) -> list[str]:
    docs = _load_docs_cache()
    missing: list[str] = []

    for category, names in required.items():
        records = docs.get(category, {})
        for name in names:
            if _casefold_lookup(records, name) is None:
                missing.append(f"{category}:{name}")

    return missing


def _script_basename(prompt: str, fallback: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", prompt.casefold())
    ignored = {
        "a",
        "an",
        "and",
        "bedwars",
        "creative",
        "every",
        "for",
        "from",
        "give",
        "gives",
        "make",
        "me",
        "player",
        "players",
        "script",
        "that",
        "the",
        "to",
        "with",
    }
    useful = [word for word in words if word not in ignored]
    if not useful:
        useful = [fallback]
    return "_".join(useful[:4])[:48].strip("_") or fallback


def _generate_script_from_prompt(prompt: str) -> GeneratedScript:
    _ensure_allowed_prompt(prompt)
    lower_prompt = prompt.casefold()

    if "emerald" in lower_prompt and (
        "every" in lower_prompt or "all player" in lower_prompt or "give" in lower_prompt
    ):
        required = {
            "services": ["PlayerService", "InventoryService"],
            "types": ["ItemType"],
            "utilities": ["task", "ipairs"],
        }
        missing = _docs_have_required(required)
        if missing:
            raise BedWarsMcpError(
                "Cannot generate this script because required APIs are missing from docs_cache: "
                + ", ".join(missing)
            )
        file_name = f"generated_{_script_basename(prompt, 'emerald_timer')}.lua"
        code = """-- Gives every player 1 emerald every 30 seconds.
while task.wait(30) do
    for i, player in ipairs(PlayerService.getPlayers()) do
        InventoryService.giveItem(player, ItemType.EMERALD, 1, true)
    end
end
"""
        return GeneratedScript(
            file_name=file_name,
            code=code,
            explanation="Uses PlayerService.getPlayers() and InventoryService.giveItem(), both present in docs_cache.",
            required=required,
        )

    if any(word in lower_prompt for word in ("join", "joined", "welcome")):
        required = {
            "services": ["ChatService"],
            "events": ["PlayerAdded"],
        }
        missing = _docs_have_required(required)
        if missing:
            raise BedWarsMcpError(
                "Cannot generate this script because required APIs are missing from docs_cache: "
                + ", ".join(missing)
            )
        file_name = f"generated_{_script_basename(prompt, 'player_join_message')}.lua"
        code = """-- Announces players as they join the creative match server.
Events.PlayerAdded(function(event)
    ChatService.sendMessage(event.player.name .. " joined the game!")
end)
"""
        return GeneratedScript(
            file_name=file_name,
            code=code,
            explanation="Uses Events.PlayerAdded and ChatService.sendMessage(), both present in docs_cache.",
            required=required,
        )

    if any(word in lower_prompt for word in ("ui", "progress", "progressbar", "progress bar")):
        required = {
            "services": ["UIService"],
            "objects": ["ProgressBar"],
            "utilities": ["task"],
        }
        missing = _docs_have_required(required)
        if missing:
            raise BedWarsMcpError(
                "Cannot generate this script because required APIs are missing from docs_cache: "
                + ", ".join(missing)
            )
        file_name = f"generated_{_script_basename(prompt, 'simple_ui')}.lua"
        code = """-- Creates a simple global countdown progress bar.
local bar = UIService.createProgressBar(30)
bar:setText("Next reward")
bar:set(0)

while task.wait(1) do
    bar:add(1)
    if bar:get() >= 30 then
        bar:set(0)
    end
end
"""
        return GeneratedScript(
            file_name=file_name,
            code=code,
            explanation="Uses UIService.createProgressBar and documented ProgressBar methods from docs_cache.",
            required=required,
        )

    raise BedWarsMcpError(
        "I could not map that prompt to BedWars Creative APIs in docs_cache. "
        "Use search_docs first, then ask for a script using documented Services, Events, Types, Objects, or Utilities."
    )


@bedwars_tool
def search_docs(query: str) -> dict[str, Any]:
    """Search the local BedWars Creative docs cache."""
    if not query or not query.strip():
        raise BedWarsMcpError("query is required.")

    docs = _load_docs_cache()
    query_text = query.strip()
    query_terms = [term.casefold() for term in re.findall(r"[A-Za-z0-9_]+", query_text)]
    if not query_terms:
        query_terms = [query_text.casefold()]

    results: list[dict[str, Any]] = []
    for category, records in docs.items():
        for name, record in records.items():
            haystack = f"{name}\n{_json_text(record)}".casefold()
            if all(term in haystack for term in query_terms):
                results.append(
                    {
                        "category": category,
                        "name": name,
                        "snippet": _short_snippet(record if isinstance(record, dict) else {}, query_text),
                        **_entry_source(record if isinstance(record, dict) else {}),
                    }
                )

    return {
        "query": query_text,
        "count": len(results),
        "results": results[:25],
        "warning": None
        if results
        else "No matching BedWars API was found in docs_cache. Do not invent an API; refresh or edit docs_cache first.",
    }


@bedwars_tool
def read_service(service_name: str) -> dict[str, Any]:
    """Return cached functions and examples for one BedWars service."""
    docs = _load_docs_cache()
    found = _casefold_lookup(docs["services"], service_name)
    if not found:
        return {
            "service_name": service_name,
            "found": False,
            "warning": "Service not found in docs_cache. Do not use it unless docs.easy.gg is refreshed into the cache.",
        }
    key, record = found
    return {"service_name": key, "found": True, **record}


@bedwars_tool
def read_event(event_name: str) -> dict[str, Any]:
    """Return cached usage and callback parameters for one BedWars event."""
    docs = _load_docs_cache()
    found = _casefold_lookup(docs["events"], event_name)
    if not found:
        return {
            "event_name": event_name,
            "found": False,
            "warning": "Event not found in docs_cache. Do not use it unless docs.easy.gg is refreshed into the cache.",
        }
    key, record = found
    return {"event_name": key, "found": True, **record}


@bedwars_tool
def create_script(file_name: str, code: str) -> dict[str, Any]:
    """Create or replace a Lua script inside scripts/."""
    path = _write_script(file_name, code)
    return {
        "file_name": str(path.relative_to(SCRIPTS_DIR)).replace("\\", "/"),
        "path": str(path),
        "bytes": path.stat().st_size,
    }


@bedwars_tool
def read_script(file_name: str) -> dict[str, Any]:
    """Read a Lua script from scripts/."""
    path = _safe_script_path(file_name, must_exist=True)
    return {
        "file_name": str(path.relative_to(SCRIPTS_DIR)).replace("\\", "/"),
        "code": path.read_text(encoding="utf-8"),
    }


@bedwars_tool
def delete_script(file_name: str, archive: bool = True) -> dict[str, Any]:
    """Delete a Lua script from scripts/, archiving it by default."""
    path = _safe_script_path(file_name, must_exist=True)
    return _delete_script_path(path, archive=archive)


@bedwars_tool
def list_projects() -> dict[str, Any]:
    """List organized BedWars projects under scripts/projects/."""
    projects: list[dict[str, Any]] = []
    if PROJECTS_DIR.exists():
        for project_dir in sorted(path for path in PROJECTS_DIR.iterdir() if path.is_dir()):
            sync_dir = project_dir / "sync"
            draft_dir = project_dir / "drafts"
            prompt_file = project_dir / "prompts" / "brief.md"
            sync_files = sorted(
                str(path.relative_to(sync_dir)).replace("\\", "/")
                for path in sync_dir.rglob("*.lua")
                if path.is_file()
            ) if sync_dir.exists() else []
            draft_files = sorted(
                str(path.relative_to(draft_dir)).replace("\\", "/")
                for path in draft_dir.rglob("*.lua")
                if path.is_file()
            ) if draft_dir.exists() else []
            projects.append(
                {
                    "project_name": project_dir.name,
                    "sync_dir": str(sync_dir),
                    "drafts_dir": str(draft_dir),
                    "prompt_file": str(prompt_file),
                    "sync_files": sync_files,
                    "draft_files": draft_files,
                }
            )
    return {
        "projects_dir": str(PROJECTS_DIR),
        "count": len(projects),
        "projects": projects,
    }


@bedwars_tool
def create_project(project_name: str = DEFAULT_PROJECT_NAME, prompt: str = "") -> dict[str, Any]:
    """Create an organized project folder with sync/, drafts/, and prompts/ directories."""
    name = _safe_project_name(project_name)
    project_dir = _project_dir(name)
    sync_dir = project_dir / "sync"
    drafts_dir = project_dir / "drafts"
    prompts_dir = project_dir / "prompts"
    for directory in (sync_dir, drafts_dir, prompts_dir):
        directory.mkdir(parents=True, exist_ok=True)

    prompt_file = prompts_dir / "brief.md"
    if prompt or not prompt_file.exists():
        prompt_text = (prompt.strip() or "Describe what this BedWars Creative project should do here.")
        prompt_file.write_text(prompt_text.rstrip() + "\n", encoding="utf-8")

    main_script = sync_dir / "main.lua"
    if not main_script.exists():
        main_script.write_text(
            "-- Main script synced to BedWars Creative.\n"
            "ChatService.sendMessage(\"BedWars Creative project loaded.\")\n",
            encoding="utf-8",
        )

    manifest = {
        "project_name": name,
        "sync_dir": "sync",
        "drafts_dir": "drafts",
        "prompt_file": "prompts/brief.md",
        "sync_glob": "*.lua",
        "notes": [
            "Repo-managed projects are local organization helpers.",
            "For Roblox Code Sync, prefer directory project tools with sync_directory or connect_sync.",
        ],
    }
    manifest_path = project_dir / "project.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    return {
        "project_name": name,
        "project_dir": str(project_dir),
        "sync_dir": str(sync_dir),
        "drafts_dir": str(drafts_dir),
        "prompt_file": str(prompt_file),
        "manifest": str(manifest_path),
        "main_script": str(main_script),
    }


@bedwars_tool
def read_project(project_name: str = DEFAULT_PROJECT_NAME) -> dict[str, Any]:
    """Read an organized BedWars project's prompt and file lists."""
    name = _safe_project_name(project_name)
    project_dir = _project_dir(name)
    if not project_dir.exists():
        raise BedWarsMcpError(f"Project not found: {name}")

    sync_dir = project_dir / "sync"
    drafts_dir = project_dir / "drafts"
    prompt_file = project_dir / "prompts" / "brief.md"
    return {
        "project_name": name,
        "project_dir": str(project_dir),
        "prompt": prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else "",
        "sync_files": sorted(
            str(path.relative_to(sync_dir)).replace("\\", "/")
            for path in sync_dir.rglob("*.lua")
            if path.is_file()
        ) if sync_dir.exists() else [],
        "draft_files": sorted(
            str(path.relative_to(drafts_dir)).replace("\\", "/")
            for path in drafts_dir.rglob("*.lua")
            if path.is_file()
        ) if drafts_dir.exists() else [],
    }


@bedwars_tool
def create_project_script(
    project_name: str,
    file_name: str,
    code: str,
    sync: bool = True,
) -> dict[str, Any]:
    """Create or replace a Lua script in a project's sync/ folder or drafts/ folder."""
    relative_name = _project_relative_script_path(project_name, file_name, sync=sync)
    path = _write_script(relative_name, code)
    project_dir = _project_dir(project_name)
    return {
        "project_name": _safe_project_name(project_name),
        "file_name": str(path.relative_to(project_dir)).replace("\\", "/"),
        "path": str(path),
        "sync": sync,
        "bytes": path.stat().st_size,
    }


@bedwars_tool
def delete_project_script(
    project_name: str,
    file_name: str,
    sync: bool = True,
    archive: bool = True,
) -> dict[str, Any]:
    """Delete a Lua script from a project's sync/ folder or drafts/ folder."""
    relative_name = _project_relative_script_path(project_name, file_name, sync=sync)
    path = _safe_script_path(relative_name, must_exist=True)
    project_dir = _project_dir(project_name)
    result = _delete_script_path(path, archive=archive)
    result.update(
        {
            "project_name": _safe_project_name(project_name),
            "project_file_name": str(path.relative_to(project_dir)).replace("\\", "/"),
            "sync": sync,
        }
    )
    return result


@bedwars_tool
def prepare_directory_project(
    directory: str,
    prompt: str = "",
    main_code: str = "",
    overwrite_main: bool = False,
) -> dict[str, Any]:
    """Create BedWars project folders and scripts/main.lua in any local directory."""
    root = _safe_directory_project_path(directory)
    scripts_dir = root / "scripts"
    drafts_dir = root / "drafts"
    prompts_dir = root / "prompts"
    for path in (scripts_dir, drafts_dir, prompts_dir):
        path.mkdir(parents=True, exist_ok=True)

    prompt_file = prompts_dir / "brief.md"
    if prompt or not prompt_file.exists():
        prompt_text = (prompt.strip() or "Describe what this BedWars Creative project should do here.")
        prompt_file.write_text(prompt_text.rstrip() + "\n", encoding="utf-8")

    default_code = (
        "-- Main BedWars script entry point.\n"
        "ChatService.sendMessage(\"BedWars Creative project loaded.\")\n"
    )
    main_script = scripts_dir / "main.lua"
    wrote_main = overwrite_main or not main_script.exists()
    if wrote_main:
        code = (main_code.rstrip() if main_code.strip() else default_code.rstrip()) + "\n"
        main_script.write_text(code, encoding="utf-8")

    manifest = {
        "sync_dir": "scripts",
        "drafts_dir": "drafts",
        "prompt_file": "prompts/brief.md",
        "sync_glob": "scripts/**/*.lua",
        "notes": [
            "Use sync_directory with this directory and glob_pattern='scripts/**/*.lua'.",
            "Only .lua files under scripts/ should be uploaded to BedWars.",
        ],
    }
    manifest_path = root / "bedwars-project.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    bwconfig_path = root / "bwconfig.lua"
    if not bwconfig_path.exists():
        bwconfig_path.write_text('return {\n    syncGlob = "scripts/**/*.lua"\n}\n', encoding="utf-8")

    return {
        "directory": str(root),
        "scripts_dir": str(scripts_dir),
        "drafts_dir": str(drafts_dir),
        "prompt_file": str(prompt_file),
        "manifest": str(manifest_path),
        "bwconfig": str(bwconfig_path),
        "main_script": str(main_script),
        "main_script_written": wrote_main,
        "sync_call": {
            "tool": "sync_directory",
            "directory": str(root),
            "glob_pattern": "scripts/**/*.lua",
        },
    }


@bedwars_tool
def read_directory_project(directory: str) -> dict[str, Any]:
    """Inspect an outside directory project without shell commands."""
    root = _safe_directory_project_path(directory)
    if not root.exists():
        return {
            "directory": str(root),
            "exists": False,
            "is_dir": False,
            "can_prepare": True,
            "suggested_next_tool": "prepare_directory_project",
        }
    if not root.is_dir():
        raise BedWarsMcpError(f"Project path is not a directory: {root}")

    scripts_dir = root / "scripts"
    drafts_dir = root / "drafts"
    prompts_dir = root / "prompts"
    prompt_file = prompts_dir / "brief.md"
    manifest_path = root / "bedwars-project.json"
    bwconfig_path = root / "bwconfig.lua"

    manifest: dict[str, Any] | None = None
    if manifest_path.exists():
        try:
            manifest_value = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(manifest_value, dict):
                manifest = manifest_value
        except json.JSONDecodeError:
            manifest = None

    entries = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        entries.append(
            {
                "name": path.name,
                "kind": "directory" if path.is_dir() else "file",
                "bytes": path.stat().st_size if path.is_file() else None,
            }
        )

    sync_files = _directory_lua_file_infos(root, scripts_dir)
    draft_files = _directory_lua_file_infos(root, drafts_dir)
    return {
        "directory": str(root),
        "exists": True,
        "is_dir": True,
        "scripts_dir": str(scripts_dir),
        "drafts_dir": str(drafts_dir),
        "prompt_file": str(prompt_file),
        "prompt": prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else "",
        "manifest_file": str(manifest_path),
        "manifest": manifest,
        "bwconfig_file": str(bwconfig_path),
        "bwconfig": bwconfig_path.read_text(encoding="utf-8") if bwconfig_path.exists() else "",
        "sync_glob": _read_bwconfig_sync_glob(root, "scripts/**/*.lua"),
        "top_level_entries": entries,
        "sync_files": sync_files,
        "draft_files": draft_files,
        "suggested_sync_tool": "force_sync_directory" if not sync_files else "sync_directory",
    }


@bedwars_tool
def create_directory_script(
    directory: str,
    file_name: str,
    code: str,
    sync: bool = True,
) -> dict[str, Any]:
    """Create or replace a Lua script in an outside directory project's scripts/ or drafts/ folder."""
    root, path = _directory_relative_script_path(directory, file_name, sync=sync)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code.rstrip() + "\n", encoding="utf-8")
    return {
        "directory": str(root),
        "file_name": str(path.relative_to(root)).replace("\\", "/"),
        "path": str(path),
        "sync": sync,
        "bytes": path.stat().st_size,
    }


@bedwars_tool
def read_directory_script(
    directory: str,
    file_name: str,
    sync: bool = True,
) -> dict[str, Any]:
    """Read a Lua script in an outside directory project's scripts/ or drafts/ folder."""
    root, path = _directory_relative_script_path(directory, file_name, sync=sync)
    if not path.exists():
        raise BedWarsMcpError(f"Script not found: {path}")
    return {
        "directory": str(root),
        "file_name": str(path.relative_to(root)).replace("\\", "/"),
        "path": str(path),
        "sync": sync,
        "code": path.read_text(encoding="utf-8"),
    }


@bedwars_tool
def delete_directory_script(
    directory: str,
    file_name: str,
    sync: bool = True,
    archive: bool = True,
) -> dict[str, Any]:
    """Delete a Lua script from an outside directory project's scripts/ or drafts/ folder."""
    root, path = _directory_relative_script_path(directory, file_name, sync=sync)
    if not path.exists():
        raise BedWarsMcpError(f"Script not found: {path}")

    result = _remove_script_path(
        path,
        archive=archive,
        relative_root=root,
        archive_root=root,
    )
    result.update(
        {
            "directory": str(root),
            "sync": sync,
        }
    )
    return result


@bedwars_tool
def connect_sync(
    sync_token: str,
    directory: str = "",
    glob_pattern: str = "",
    watch: bool = True,
    allow_empty: bool = False,
    probe: bool = True,
    probe_message: str = "",
) -> dict[str, Any]:
    """Connect a BedWars Code Sync token and remember it in MCP memory for later syncs."""
    if not directory.strip():
        existing_directory = str(SYNC_SESSION.get("directory") or "")
        if not existing_directory:
            raise BedWarsMcpError("directory is required for the first connect_sync call.")
        directory = existing_directory
    root_path = _safe_directory_project_path(directory)
    selected_glob = glob_pattern.strip() or _read_bwconfig_sync_glob(root_path, "scripts/**/*.lua")
    prepared = None
    if not allow_empty:
        prepared = prepare_directory_project(
            directory=str(root_path),
            prompt=f"BedWars Creative project for {root_path.name}",
        )
    selected_glob, fallback_prepared = _prepare_directory_for_first_sync(root_path, selected_glob, allow_empty=allow_empty)
    prepared = prepared or fallback_prepared
    probe_result = _write_sync_probe(root_path, probe_message) if probe and not allow_empty else None
    result = _sync_directory_with_token(sync_token, str(root_path), selected_glob, allow_empty=allow_empty)
    _store_sync_session(sync_token, result)
    watcher_started = _start_sync_watcher() if watch and result.get("ok") else False
    return {
        "connected": bool(result.get("ok")),
        "watcher_running": bool(SYNC_SESSION.get("watcher_running")),
        "watcher_started": watcher_started,
        "directory": result.get("directory"),
        "glob_pattern": result.get("glob_pattern"),
        "upload_root": result.get("upload_root"),
        "status_code": result.get("status_code"),
        "uploaded_files": result.get("uploaded_files"),
        "file_count": result.get("file_count"),
        "prepared": prepared,
        "probe": probe_result,
        "token_stored_in_memory_only": True,
    }


@bedwars_tool
def sync_connected() -> dict[str, Any]:
    """Sync using the active in-memory BedWars Code Sync connection."""
    result = _sync_connected_internal()
    return {
        "connected": bool(result.get("ok")),
        **result,
    }


@bedwars_tool
def sync_status() -> dict[str, Any]:
    """Return the active BedWars Code Sync connection status without exposing the token."""
    return {
        "connected": bool(SYNC_SESSION.get("connected")),
        "directory": SYNC_SESSION.get("directory"),
        "glob_pattern": SYNC_SESSION.get("glob_pattern"),
        "upload_root": SYNC_SESSION.get("upload_root"),
        "last_status_code": SYNC_SESSION.get("last_status_code"),
        "last_file_count": SYNC_SESSION.get("last_file_count"),
        "last_uploaded_files": SYNC_SESSION.get("last_uploaded_files"),
        "last_auto_sync_at": SYNC_SESSION.get("last_auto_sync_at"),
        "last_error": SYNC_SESSION.get("last_error"),
        "watcher_running": bool(SYNC_WATCHER_THREAD and SYNC_WATCHER_THREAD.is_alive()),
        "token_stored_in_memory_only": bool(SYNC_SESSION.get("sync_token")),
    }


@bedwars_tool
def disconnect_sync() -> dict[str, Any]:
    """Forget the active in-memory BedWars Code Sync token."""
    was_connected = bool(SYNC_SESSION.get("connected"))
    watcher_was_running = _stop_sync_watcher()
    SYNC_SESSION.clear()
    return {"disconnected": True, "was_connected": was_connected, "watcher_was_running": watcher_was_running}


@bedwars_tool
def start_sync_watch() -> dict[str, Any]:
    """Start auto-sync polling for the active BedWars Code Sync connection."""
    if not SYNC_SESSION.get("sync_token") or not SYNC_SESSION.get("directory"):
        raise BedWarsMcpError("No active sync connection. Call connect_sync first.")
    started = _start_sync_watcher()
    return {"watcher_running": True, "watcher_started": started}


@bedwars_tool
def stop_sync_watch() -> dict[str, Any]:
    """Stop auto-sync polling for the active BedWars Code Sync connection."""
    stopped = _stop_sync_watcher()
    return {"watcher_running": False, "watcher_was_running": stopped}


@bedwars_tool
def sync_directory(
    sync_token: str,
    directory: str,
    glob_pattern: str = "",
    allow_empty: bool = False,
    probe: bool = True,
    probe_message: str = "",
    watch: bool = True,
) -> dict[str, Any]:
    """Upload .lua files from any local directory to BedWars Code Sync."""
    root = _safe_directory_project_path(directory)
    selected_glob = glob_pattern.strip() or _read_bwconfig_sync_glob(root, "scripts/**/*.lua")
    prepared = None
    if not allow_empty:
        prepared = prepare_directory_project(
            directory=str(root),
            prompt=f"BedWars Creative project for {root.name}",
        )
    selected_glob, fallback_prepared = _prepare_directory_for_first_sync(root, selected_glob, allow_empty=allow_empty)
    prepared = prepared or fallback_prepared
    probe_result = _write_sync_probe(root, probe_message) if probe and not allow_empty else None
    result = _sync_directory_with_token(sync_token, str(root), selected_glob, allow_empty=allow_empty)
    _store_sync_session(sync_token, result)
    watcher_started = _start_sync_watcher() if watch and result.get("ok") else False
    if prepared:
        result["prepared"] = prepared
    result["probe"] = probe_result
    result["connected"] = bool(result.get("ok"))
    result["watcher_running"] = bool(SYNC_SESSION.get("watcher_running"))
    result["watcher_started"] = watcher_started
    result["token_stored_in_memory_only"] = True
    return result


@bedwars_tool
def force_sync_directory(
    sync_token: str,
    directory: str,
    glob_pattern: str = "",
    probe: bool = True,
    probe_message: str = "",
    watch: bool = True,
) -> dict[str, Any]:
    """Prepare a directory, update a visible probe, upload scripts/, and connect the watcher."""
    root = _safe_directory_project_path(directory)
    prepared = prepare_directory_project(
        directory=str(root),
        prompt=f"BedWars Creative project for {root.name}",
    )
    selected_glob = glob_pattern.strip() or _read_bwconfig_sync_glob(root, "scripts/**/*.lua")

    probe_result = _write_sync_probe(root, probe_message) if probe else None
    result = _sync_directory_with_token(sync_token, str(root), selected_glob, allow_empty=False)
    _store_sync_session(sync_token, result)
    watcher_started = _start_sync_watcher() if watch and result.get("ok") else False

    return {
        "connected": bool(result.get("ok")),
        "watcher_running": bool(SYNC_SESSION.get("watcher_running")),
        "watcher_started": watcher_started,
        "prepared": prepared,
        "probe": probe_result,
        **result,
        "token_stored_in_memory_only": True,
    }


@bedwars_tool
def edit_script(file_name: str, instructions: str) -> dict[str, Any]:
    """Edit a Lua script using simple, deterministic instructions and keep a .bak backup."""
    if not instructions or not instructions.strip():
        raise BedWarsMcpError("instructions are required.")

    path = _safe_script_path(file_name, must_exist=True)
    original = path.read_text(encoding="utf-8")
    backup_path = path.with_name(path.name + ".bak")
    shutil.copy2(path, backup_path)

    updated = original
    mode = "todo_note"

    fenced = FENCED_CODE_RE.search(instructions)
    if fenced:
        updated = fenced.group(1).strip() + "\n"
        mode = "replace_with_fenced_lua"
    else:
        replace_match = re.search(
            r"replace\s+`(?P<old>.*?)`\s+with\s+`(?P<new>.*?)`",
            instructions,
            flags=re.IGNORECASE | re.DOTALL,
        )
        arrow_match = re.search(
            r"replace\s*:\s*(?P<old>.*?)\s*=>\s*(?P<new>.*)",
            instructions,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if replace_match:
            old = replace_match.group("old")
            new = replace_match.group("new")
            if old not in updated:
                raise BedWarsMcpError("Replacement text was not found. Backup was still created.")
            updated = updated.replace(old, new)
            mode = "replace"
        elif arrow_match:
            old = arrow_match.group("old").strip()
            new = arrow_match.group("new").strip()
            if old not in updated:
                raise BedWarsMcpError("Replacement text was not found. Backup was still created.")
            updated = updated.replace(old, new)
            mode = "replace"
        elif instructions.casefold().startswith("append:"):
            updated = original.rstrip() + "\n" + instructions.split(":", 1)[1].strip() + "\n"
            mode = "append"
        elif instructions.casefold().startswith("prepend:"):
            updated = instructions.split(":", 1)[1].strip() + "\n" + original.lstrip()
            mode = "prepend"
        else:
            note = "\n-- TODO from edit_script:\n"
            note += "\n".join(f"-- {line}" for line in instructions.strip().splitlines())
            updated = original.rstrip() + note + "\n"

    path.write_text(updated.rstrip() + "\n", encoding="utf-8")
    return {
        "file_name": str(path.relative_to(SCRIPTS_DIR)).replace("\\", "/"),
        "backup": str(backup_path.relative_to(SCRIPTS_DIR)).replace("\\", "/"),
        "edit_mode": mode,
        "bytes": path.stat().st_size,
    }


@bedwars_tool
def validate_script(file_name: str) -> dict[str, Any]:
    """Inspect a Lua script for likely fake or out-of-scope BedWars APIs without executing it."""
    path = _safe_script_path(file_name, must_exist=True)
    code = path.read_text(encoding="utf-8")
    code_for_global_scan = _code_without_lua_strings_or_comments(code)
    docs = _load_docs_cache()
    services = docs["services"]
    events = docs["events"]
    item_type = docs["types"].get("ItemType", {})

    warnings: list[str] = []
    errors: list[str] = []

    for pattern in LUA_DANGEROUS_PATTERNS:
        if pattern.casefold() in code.casefold():
            errors.append(f"Disallowed or exploit-style Lua pattern found: {pattern}")

    for global_name in UNAVAILABLE_LUA_GLOBALS:
        if re.search(rf"\b{re.escape(global_name)}\s*\(", code_for_global_scan):
            errors.append(
                f"{global_name}(...) is not available in the Creative Lua sandbox. "
                "It cannot be recreated as a true protected call; use defensive checks or safe_call_pattern instead."
            )

    used_services = sorted(set(SERVICE_USE_RE.findall(code)))
    used_events = sorted(set(EVENT_USE_RE.findall(code)))
    used_item_types = sorted(set(ITEM_TYPE_RE.findall(code)))
    used_type_values: dict[str, list[str]] = {}
    for type_name, value_name in TYPE_VALUE_RE.findall(code):
        used_type_values.setdefault(type_name, [])
        if value_name not in used_type_values[type_name]:
            used_type_values[type_name].append(value_name)

    for service in used_services:
        service_lookup = _casefold_lookup(services, service)
        if not service_lookup:
            warnings.append(
                f"{service} is not in docs_cache. Treat this as likely fake until docs.easy.gg is refreshed."
            )
            continue

    for service, separator, function_name in SERVICE_CALL_RE.findall(code):
        service_lookup = _casefold_lookup(services, service)
        if not service_lookup:
            continue
        canonical, record = service_lookup
        known_functions = _known_service_functions(record)
        if known_functions and function_name not in known_functions:
            warnings.append(
                f"{canonical}.{function_name}() is not listed for {canonical} in docs_cache."
            )
        if separator == ":" and canonical.endswith("Service"):
            warnings.append(
                f"{canonical}:{function_name}() uses colon syntax. BedWars service docs usually show dot syntax; verify this in docs before syncing."
            )

    for event in used_events:
        if _casefold_lookup(events, event) is None:
            warnings.append(
                f"Events.{event} is not in docs_cache. Treat this as likely fake until docs.easy.gg is refreshed."
            )

    for type_name, value_names in sorted(used_type_values.items()):
        type_record = docs["types"].get(type_name, {})
        if not isinstance(type_record, dict):
            warnings.append(f"{type_name} is not in docs_cache. Treat this as likely fake until docs.easy.gg is refreshed.")
            continue
        known_values = _known_type_values(type_record)
        for value_name in value_names:
            if known_values and value_name not in known_values:
                warnings.append(f"{type_name}.{value_name} is not in the cached {type_name} values.")

    string_literals = _lua_string_literals(code)
    used_type_strings: dict[str, list[str]] = {}
    for type_name, type_record in docs["types"].items():
        if not isinstance(type_record, dict):
            continue
        known_strings = _known_type_string_values(type_record)
        matching_strings = sorted(string_literals & known_strings)
        if matching_strings:
            used_type_strings[type_name] = matching_strings

    used_item_strings = used_type_strings.get("ItemType", [])

    for global_name in ROBLOX_GLOBALS_TO_WARN:
        if _casefold_lookup(services, global_name):
            continue
        if re.search(rf"\b{re.escape(global_name)}\b", code_for_global_scan):
            warnings.append(
                f"{global_name} is a normal Roblox API/global. It may not work in BedWars Creative unless docs_cache explicitly allows it."
            )

    return {
        "file_name": str(path.relative_to(SCRIPTS_DIR)).replace("\\", "/"),
        "executed": False,
        "valid": not errors,
        "used_services": used_services,
        "used_events": used_events,
        "used_item_types": used_item_types,
        "used_item_strings": used_item_strings,
        "used_type_values": {key: sorted(value) for key, value in sorted(used_type_values.items())},
        "used_type_strings": used_type_strings,
        "errors": errors,
        "warnings": warnings,
        "note": "Static validation only. The script was not executed.",
    }


@bedwars_tool
def safe_call_pattern(topic: str = "generic") -> dict[str, Any]:
    """Return defensive Lua patterns for cases where pcall/xpcall would normally be used."""
    normalized = (topic or "generic").strip().casefold()

    examples = {
        "entity": """local function safeGetEntity(player)
    if player == nil then
        return false, "player is nil"
    end

    local entity = player:getEntity()
    if entity == nil then
        return false, "player has no active entity"
    end

    return true, entity
end

local ok, entity = safeGetEntity(player)
if not ok then
    return
end

local position = entity:getPosition()
""",
        "number": """local function safeNumber(value, fallback)
    local numberValue = tonumber(value)
    if numberValue == nil then
        return false, fallback
    end

    return true, numberValue
end

local ok, amount = safeNumber(commandArgs[2], 1)
if not ok then
    MessageService.sendError(player, "Amount must be a number")
    return
end
""",
        "command": """local function getArg(args, index, name)
    local value = args[index]
    if value == nil or value == "" then
        return false, name .. " is required"
    end

    return true, value
end

local ok, targetName = getArg(commandArgs, 2, "target")
if not ok then
    MessageService.sendError(event.player, targetName)
    return
end
""",
        "optional": """local function requireValue(value, errorMessage)
    if value == nil then
        return false, errorMessage
    end

    return true, value
end

local ok, team = requireValue(TeamService.getTeam(player), "player has no team")
if not ok then
    return
end
""",
        "generic": """local function requireValue(value, errorMessage)
    if value == nil then
        return false, errorMessage
    end

    return true, value
end

local ok, value = requireValue(maybeNilValue, "value was missing")
if not ok then
    return
end
""",
    }

    if "entity" in normalized or "player" in normalized:
        selected = "entity"
    elif "number" in normalized or "tonumber" in normalized or "color" in normalized or "rgb" in normalized:
        selected = "number"
    elif "command" in normalized or "arg" in normalized or "chat" in normalized:
        selected = "command"
    elif "team" in normalized or "optional" in normalized or "nil" in normalized:
        selected = "optional"
    else:
        selected = "generic"

    return {
        "topic": topic,
        "selected_pattern": selected,
        "can_recreate_pcall": False,
        "why_not": (
            "pcall/xpcall require protected-call support from the Lua runtime. "
            "A Lua function cannot catch its own runtime errors if the sandbox does not expose that runtime feature."
        ),
        "possible": [
            "Check nil before indexing or calling methods.",
            "Check command arguments before using them.",
            "Use tonumber(...) and reject nil before numeric logic.",
            "Check service return values such as player:getEntity() or TeamService.getTeam(player).",
            "Return ok, value_or_message from small helper functions for expected failure states.",
        ],
        "not_possible": [
            "Catching arbitrary runtime errors after they happen.",
            "Continuing after an invalid method call or nil index without checking first.",
            "Recreating true pcall/xpcall semantics in plain Lua inside this sandbox.",
        ],
        "lua_pattern": examples[selected],
    }


@bedwars_tool
def explain_error(error_text: str) -> dict[str, Any]:
    """Explain a BedWars Creative Lua error and suggest a docs-safe correction."""
    if not error_text or not error_text.strip():
        raise BedWarsMcpError("error_text is required.")

    text = error_text.strip()
    lower = text.casefold()

    if "pcall" in lower or "xpcall" in lower:
        return {
            "plain_english": "The script tried to use pcall/xpcall, but the Creative Lua sandbox does not expose protected calls.",
            "likely_cause": "pcall/xpcall are runtime features. They cannot be recreated in plain Lua when unavailable.",
            "corrected_example": """local function requireValue(value, errorMessage)
    if value == nil then
        return false, errorMessage
    end

    return true, value
end

local ok, entity = requireValue(player:getEntity(), "player has no active entity")
if not ok then
    return
end
""",
            "next_tool": "safe_call_pattern",
        }

    if "attempt to index nil" in lower or "nil value" in lower:
        return {
            "plain_english": "The script tried to use a value that was nil, usually an entity, player, or API lookup that did not exist.",
            "likely_cause": "A callback field was missing, player:getEntity() returned nil, or an API/type name was not in the BedWars docs.",
            "corrected_example": """local entity = player:getEntity()
if not entity then
    return
end

local position = entity:getPosition()
""",
        }

    if "unknown global" in lower or "not a valid member" in lower or "is not a valid member" in lower:
        return {
            "plain_english": "The script is using a name that BedWars Creative does not recognize.",
            "likely_cause": "The API may be a normal Roblox API or a fake BedWars API that is not in docs_cache.",
            "corrected_example": """-- Search docs_cache before using an API:
-- search_docs("InventoryService")
InventoryService.giveItem(player, ItemType.EMERALD, 1, true)
""",
        }

    if "yield" in lower or "timeout" in lower:
        return {
            "plain_english": "The script waited inside a place where waiting can delay game behavior.",
            "likely_cause": "BedWars event callbacks should not contain task.wait(), long loops, or yielding service calls directly.",
            "corrected_example": """Events.PlayerAdded(function(event)
    task.spawn(function()
        task.wait(1)
        ChatService.sendMessage(event.player.name .. " joined the game!")
    end)
end)
""",
        }

    if "expected" in lower or "syntax" in lower or "unfinished" in lower:
        return {
            "plain_english": "Lua could not parse the script.",
            "likely_cause": "A missing end, parenthesis, comma, quote, or function wrapper.",
            "corrected_example": """Events.PlayerAdded(function(event)
    ChatService.sendMessage(event.player.name .. " joined the game!")
end)
""",
        }

    return {
        "plain_english": "The error is not a known pattern in this MCP.",
        "likely_cause": "Check the exact line number, then verify every Service, Event, Object, Type, and Utility against docs_cache.",
        "corrected_example": """-- Safe pattern: check optional values before using them.
for i, player in ipairs(PlayerService.getPlayers()) do
    local entity = player:getEntity()
    if entity then
        print(player.name .. " is active")
    end
end
""",
    }


@bedwars_tool
def make_script(prompt: str) -> dict[str, Any]:
    """Generate and save a BedWars Creative Lua script using only APIs present in docs_cache."""
    if not prompt or not prompt.strip():
        raise BedWarsMcpError("prompt is required.")

    script = _generate_script_from_prompt(prompt.strip())
    path = _write_script(script.file_name, script.code)
    validation = validate_script(script.file_name)
    return {
        "file_name": str(path.relative_to(SCRIPTS_DIR)).replace("\\", "/"),
        "path": str(path),
        "explanation": script.explanation,
        "required_docs": script.required,
        "validation": validation,
    }


def main() -> None:
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    mcp.run()


if __name__ == "__main__":
    main()
