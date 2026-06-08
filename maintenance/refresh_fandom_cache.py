from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FANDOM_CACHE_DIR = PROJECT_ROOT / "docs_cache" / "fandom"
API_URL = "https://robloxbedwars.fandom.com/api.php"
WIKI_URL = "https://robloxbedwars.fandom.com/wiki/BedWars_Wiki"
USER_AGENT = "easy-gg-bedwars-custom/0.1 (+local MCP cache)"


def api_get(params: dict[str, Any]) -> dict[str, Any]:
    query = urllib.parse.urlencode(params, doseq=True)
    request = urllib.request.Request(
        f"{API_URL}?{query}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Fandom API returned a non-object JSON response.")
    if "error" in data:
        raise RuntimeError(f"Fandom API error: {data['error']}")
    return data


def fetch_all_pages(*, limit: int | None = None, sleep_seconds: float = 0.0) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    params: dict[str, Any] = {
        "action": "query",
        "format": "json",
        "list": "allpages",
        "apnamespace": 0,
        "apfilterredir": "nonredirects",
        "aplimit": 500,
    }
    while True:
        data = api_get(params)
        pages.extend(data.get("query", {}).get("allpages", []))
        if limit is not None and len(pages) >= limit:
            return pages[:limit]
        continuation = data.get("continue")
        if not continuation:
            return pages
        params.update(continuation)
        if sleep_seconds:
            time.sleep(sleep_seconds)


def _merge_page(target: dict[str, Any], incoming: dict[str, Any]) -> None:
    for key, value in incoming.items():
        if key == "categories":
            categories = target.setdefault("categories", [])
            for category in value or []:
                title = category.get("title") if isinstance(category, dict) else None
                if not isinstance(title, str):
                    continue
                title = title.replace("Category:", "", 1)
                if title not in categories:
                    categories.append(title)
            continue
        if key == "thumbnail" and isinstance(value, dict):
            target["thumbnail"] = value.get("source")
            continue
        if key == "original" and isinstance(value, dict):
            target["image"] = value.get("source")
            continue
        target[key] = value


def fetch_page_records(
    titles: list[str],
    *,
    include_text: bool,
    sleep_seconds: float = 0.0,
) -> list[dict[str, Any]]:
    records_by_id: dict[int, dict[str, Any]] = {}
    for index in range(0, len(titles), 50):
        batch = titles[index:index + 50]
        params: dict[str, Any] = {
            "action": "query",
            "format": "json",
            "prop": "info|categories|extracts|pageimages",
            "inprop": "url",
            "cllimit": "max",
            "explaintext": 1,
            "exsectionformat": "plain",
            "piprop": "thumbnail|original|name",
            "pithumbsize": 256,
            "redirects": 1,
            "titles": "|".join(batch),
        }
        if not include_text:
            params["exintro"] = 1

        while True:
            data = api_get(params)
            pages = data.get("query", {}).get("pages", {})
            for raw_pageid, page in pages.items():
                if not isinstance(page, dict) or "missing" in page:
                    continue
                pageid = int(page.get("pageid") or raw_pageid)
                record = records_by_id.setdefault(pageid, {})
                _merge_page(record, page)

            continuation = data.get("continue")
            if not continuation:
                break
            params.update(continuation)
            if sleep_seconds:
                time.sleep(sleep_seconds)

        if sleep_seconds:
            time.sleep(sleep_seconds)

    records: list[dict[str, Any]] = []
    for record in records_by_id.values():
        title = str(record.get("title") or "")
        extract = str(record.get("extract") or "").strip()
        fullurl = str(record.get("fullurl") or "")
        record = {
            "pageid": record.get("pageid"),
            "title": title,
            "url": fullurl or f"https://robloxbedwars.fandom.com/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
            "length": record.get("length"),
            "lastrevid": record.get("lastrevid"),
            "touched": record.get("touched"),
            "categories": sorted(record.get("categories") or []),
            "summary": extract if not include_text else extract[:1000].strip(),
            "extract": extract if include_text else "",
            "thumbnail": record.get("thumbnail"),
            "image": record.get("image"),
        }
        records.append(record)
    records.sort(key=lambda item: str(item.get("title", "")).casefold())
    return records


def write_cache(*, include_text: bool, limit: int | None, sleep_seconds: float) -> dict[str, Any]:
    FANDOM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    pages = fetch_all_pages(limit=limit, sleep_seconds=sleep_seconds)
    records = fetch_page_records(
        [str(page["title"]) for page in pages if isinstance(page.get("title"), str)],
        include_text=include_text,
        sleep_seconds=sleep_seconds,
    )

    category_counts = Counter(
        category
        for record in records
        for category in record.get("categories", [])
    )
    categories = [
        {"name": name, "page_count": count}
        for name, count in sorted(category_counts.items(), key=lambda item: (-item[1], item[0].casefold()))
    ]
    manifest = {
        "source": "Roblox BedWars Wiki on Fandom",
        "source_url": WIKI_URL,
        "api_url": API_URL,
        "license": "CC-BY-SA unless otherwise noted on individual pages",
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "include_text": include_text,
        "page_count": len(records),
        "category_count": len(categories),
        "note": (
            "This cache is a local gameplay/wiki reference. Official scripting APIs still come from docs.easy.gg. "
            "Keep attribution and source URLs when using Fandom content."
        ),
    }

    (FANDOM_CACHE_DIR / "pages.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (FANDOM_CACHE_DIR / "categories.json").write_text(
        json.dumps(categories, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (FANDOM_CACHE_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh the Roblox BedWars Fandom cache.")
    parser.add_argument("--include-text", action="store_true", help="Store full plain-text extracts, not only summaries.")
    parser.add_argument("--limit", type=int, default=None, help="Fetch only the first N pages for testing.")
    parser.add_argument("--sleep", type=float, default=0.05, help="Delay between API requests.")
    args = parser.parse_args()

    manifest = write_cache(
        include_text=args.include_text,
        limit=args.limit,
        sleep_seconds=max(args.sleep, 0.0),
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
