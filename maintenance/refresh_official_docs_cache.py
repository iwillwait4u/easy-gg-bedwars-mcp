from __future__ import annotations

import json
import re
import time
import urllib.request
from html import unescape
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_CACHE_DIR = PROJECT_ROOT / "docs_cache"
BASE_URL = "https://docs.easy.gg/scripting/bedwars-scripting"
USER_AGENT = "easy-gg-bedwars-custom/0.1"

DOC_FILES = {
    "services": "services.json",
    "events": "events.json",
    "types": "types.json",
    "objects": "objects.json",
    "utilities": "utilities.json",
}

STOP_LINES = {"Previous", "Next", "Last updated"}
NOISE_LINES = {
    "Copy",
    "On this page",
    "Powered by GitBook",
    "BedWars Scripting",
    "Services",
    "Events",
    "Objects",
    "Types",
    "Utilities",
}

OBJECT_DESCRIPTIONS = {
    "AbilityConfig": "Configuration table passed to AbilityService.createAbility().",
    "Block": "Represents a BedWars world block.",
    "Entity": "Represents an in-game entity.",
    "Generator": "Object returned by GeneratorService.createGenerator().",
    "Knockback": "Configuration object for knockback applied during damage events.",
    "Leaderboard": "Object returned by UIService.createLeaderboard().",
    "MatchState": "Represents BedWars match state.",
    "Model": "Object returned by ModelService.createModel().",
    "ParticleEmitter": "Object returned by ParticleService.createEmitter().",
    "Part": "Object returned by PartService.createPart().",
    "Player": "Represents a BedWars player.",
    "Prompt": "Object returned by PromptService.createPrompt().",
    "ProgressBar": "Object returned by UIService.createProgressBar().",
    "TextLabel": "Object returned by UIService.createTextLabel().",
    "Team": "Represents a BedWars team.",
}


def _fetch_html(url: str) -> str | None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"MISS {url}: {exc}")
        return None


def _strip_lines(html: str) -> list[str]:
    text = re.sub(r"<script\b.*?</script>", "", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b.*?</style>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = unescape(text)
    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line and line not in NOISE_LINES:
            lines.append(line)
    return lines


def _code_blocks(html: str) -> list[str]:
    blocks: list[str] = []
    for block in re.findall(r"<code[^>]*>(.*?)</code>", html, flags=re.IGNORECASE | re.DOTALL):
        code = re.sub(r"<[^>]+>", "", block)
        code = unescape(code).strip("\n")
        if code and code not in blocks:
            blocks.append(code)
    return blocks


def _related_docs(html: str) -> list[dict[str, str]]:
    # GitBook renders the whole sidebar in each page, so raw links are mostly
    # navigation noise. Keep source_url on each record instead of storing these.
    return []


def _section_after(lines: list[str], marker: str) -> list[str]:
    if marker not in lines:
        return []
    start = lines.index(marker) + 1
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index] in STOP_LINES:
            end = index
            break
    return lines[start:end]


def _normalize(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("( ", "(").replace(" )", ")").replace(" ,", ",")
    text = text.replace(" []", "[]")
    return text


def _description(lines: list[str], name: str) -> str | None:
    starts = [index for index, line in enumerate(lines) if line == name]
    for start in starts:
        for candidate in lines[start + 1 : start + 12]:
            if candidate in NOISE_LINES or candidate in {"Reference", "Parameters", "Functions", "Example usage:"}:
                continue
            if candidate in {"Previous", "Next"}:
                break
            if len(candidate) > 1 and candidate != name and not candidate.startswith(("📦", "📚", "⚙️", "🤝", "🍊")):
                return candidate.rstrip(".") + "."
    return None


def _official_examples(code_blocks: list[str]) -> list[dict[str, str]]:
    examples: list[dict[str, str]] = []
    for code in code_blocks:
        # Single-token code blocks are usually inline references, not examples.
        if "\n" not in code or len(code) < 40:
            continue
        first_comment = None
        for line in code.splitlines():
            stripped = line.strip()
            if stripped.startswith("-- "):
                first_comment = stripped[3:].strip().rstrip(".")
                break
        examples.append({"description": first_comment or "Official docs example", "code": code})
    return examples


def _is_signature_start(line: str) -> bool:
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*\(", line))


def _is_type_fragment(line: str) -> bool:
    if line in {")", "[]", "|", "| nil", "| bool", "| number", "| string"}:
        return True
    if re.fullmatch(r"\|\s*[A-Za-z_][A-Za-z0-9_]*(\[\])?", line):
        return True
    if re.fullmatch(r"\|\s*[A-Za-z_][A-Za-z0-9_]*(\s*\|\s*[A-Za-z_][A-Za-z0-9_]*)*[)>]?", line):
        return True
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\[\])?", line):
        return True
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\s*\|\s*[A-Za-z_][A-Za-z0-9_]*)+[)>]?", line):
        return True
    if re.fullmatch(r":\s*[A-Za-z_][A-Za-z0-9_]*(\s*\|\s*nil)?", line):
        return True
    return False


def _parse_parameters(lines: list[str]) -> list[dict[str, Any]]:
    body = _section_after(lines, "Parameters")
    params: list[dict[str, Any]] = []
    index = 0
    while index < len(body):
        line = body[index]
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if not match:
            index += 1
            continue

        name = match.group(1)
        type_text = match.group(2).strip()
        index += 1
        while index < len(body) and _is_type_fragment(body[index]):
            type_text = _normalize(f"{type_text} {body[index]}")
            index += 1

        modifiable = False
        if index < len(body) and body[index] == "[modifiable]":
            modifiable = True
            index += 1

        notes: list[str] = []
        while index < len(body):
            next_line = body[index]
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*:", next_line) or next_line in STOP_LINES:
                break
            if next_line in {"Functions", "Reference", "Example usage:", "Copy"}:
                break
            notes.append(next_line)
            index += 1

        record: dict[str, Any] = {
            "name": name,
            "type": _normalize(type_text),
            "notes": _normalize(" ".join(notes)).rstrip(".") + "." if notes else "",
        }
        if modifiable:
            record["modifiable"] = True
        params.append(record)
    return params


def _skip_example_tokens(body: list[str], index: int) -> int:
    while index < len(body):
        line = body[index]
        if _is_signature_start(line) or line in STOP_LINES:
            break
        index += 1
    return index


def _parse_functions(lines: list[str], receiver: str | None = None) -> list[dict[str, str]]:
    body = _section_after(lines, "Functions")
    functions: list[dict[str, str]] = []
    index = 0
    receiver_name = receiver[:1].lower() + receiver[1:] if receiver else None

    while index < len(body):
        line = body[index]
        if line in {"Example usage:", "Copy"}:
            index = _skip_example_tokens(body, index + 1)
            continue
        if not _is_signature_start(line):
            index += 1
            continue

        signature = line
        index += 1
        while index < len(body):
            next_line = body[index]
            if next_line in {"Example usage:", "Copy"} or next_line in STOP_LINES:
                break
            if _is_signature_start(next_line):
                break
            if signature.count("(") > signature.count(")") or signature.endswith(":") or _is_type_fragment(next_line):
                signature = f"{signature} {next_line}"
                index += 1
                continue
            break

        notes: list[str] = []
        while index < len(body):
            next_line = body[index]
            if next_line in {"Example usage:", "Copy"} or next_line in STOP_LINES:
                break
            if _is_signature_start(next_line):
                break
            notes.append(next_line)
            index += 1

        signature = _normalize(signature)
        name_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)", signature)
        if not name_match:
            continue
        name = name_match.group(1)
        if receiver_name and ":" not in signature.split("(", 1)[0] and "." not in signature.split("(", 1)[0]:
            signature = f"{receiver_name}:{signature}"
        functions.append(
            {
                "name": name,
                "signature": signature,
                "notes": _normalize(" ".join(notes)).rstrip(".") + "." if notes else "",
            }
        )

    seen = set()
    deduped: list[dict[str, str]] = []
    for function in functions:
        key = (function["name"], function["signature"])
        if key not in seen:
            deduped.append(function)
            seen.add(key)
    return deduped


def _parse_type_values(code_blocks: list[str]) -> dict[str, str] | list[str]:
    mapped: dict[str, str] = {}
    listed: set[str] = set()

    for code in code_blocks:
        lines = [line.strip().rstrip(",") for line in code.splitlines() if line.strip()]
        if len(lines) == 1:
            line = lines[0]
            if "." in line:
                continue
            if line.startswith('"') and line.endswith('"'):
                listed.add(line.strip('"'))
                continue
            for part in line.split("|"):
                value = part.strip()
                if re.fullmatch(r"[A-Za-z0-9_]+", value):
                    listed.add(value)
            continue

        for line in lines:
            if line.startswith("//"):
                continue
            if line.startswith('"') and line.endswith('"'):
                listed.add(line.strip('"'))
                continue
            match = re.match(r"""^([A-Z][A-Z0-9_]*)\s*=\s*["']?([^"',]+)["']?$""", line)
            if match:
                mapped[match.group(1)] = match.group(2)
            elif re.fullmatch(r"[A-Z][A-Z0-9_]*", line):
                listed.add(line)
            elif re.fullmatch(r"[a-zA-Z0-9_]+", line):
                listed.add(line)

    if mapped:
        return dict(sorted(mapped.items()))
    return sorted(listed)


def _update_record(record: dict[str, Any], name: str, category: str, html: str) -> dict[str, Any]:
    lines = _strip_lines(html)
    code_blocks = _code_blocks(html)
    desc = _description(lines, name)
    if desc:
        record["description"] = desc

    if category == "types":
        values = _parse_type_values(code_blocks)
        if values:
            if name == "ItemType" and isinstance(record.get("values"), dict) and isinstance(values, dict):
                merged = dict(record["values"])
                merged.update(values)
                record["values"] = dict(sorted(merged.items()))
            else:
                record["values"] = values
    elif category == "objects":
        record["description"] = OBJECT_DESCRIPTIONS.get(name, record.get("description") or f"{name} object.")
        params = _parse_parameters(lines)
        functions = _parse_functions(lines, receiver=name)
        examples = _official_examples(code_blocks)
        if params:
            record["parameters"] = params
        if functions:
            record["functions"] = functions
            record["methods"] = functions
        if examples:
            record["examples"] = examples

    related = _related_docs(html)
    if related:
        record["related_docs"] = related

    record["source_name"] = f"{name} | BedWars Creative"
    record["source_url"] = f"{BASE_URL}/{category}/{name.lower()}"
    return record


def refresh_categories(categories: list[str] | None = None) -> None:
    DOCS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    wanted = categories or ["types", "objects"]

    for category in wanted:
        file_name = DOC_FILES[category]
        path = DOCS_CACHE_DIR / file_name
        data = json.loads(path.read_text(encoding="utf-8"))
        updated = 0
        for name, record in data.items():
            url = f"{BASE_URL}/{category}/{name.lower()}"
            html = _fetch_html(url)
            if not html:
                continue
            data[name] = _update_record(record if isinstance(record, dict) else {}, name, category, html)
            updated += 1
            time.sleep(0.05)

        path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        print(f"{file_name}: updated {updated}")


if __name__ == "__main__":
    refresh_categories()
