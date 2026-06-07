from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_CACHE_DIR = PROJECT_ROOT / "docs_cache"
BASE_URL = "https://docs.easy.gg/scripting/bedwars-scripting"

PAGES = {
    "services": f"{BASE_URL}/services",
    "events": f"{BASE_URL}/events",
    "objects": f"{BASE_URL}/objects",
    "types": f"{BASE_URL}/types",
    "utilities": f"{BASE_URL}/utilities",
}


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "easy-gg-bedwars-custom/0.1"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def strip_html(html: str) -> str:
    text = re.sub(r"<script\b.*?</script>", "", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b.*?</style>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def refresh_index_pages() -> None:
    DOCS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for category, url in PAGES.items():
        text = strip_html(fetch_text(url))
        output_path = DOCS_CACHE_DIR / f"{category}_raw.txt"
        output_path.write_text(text, encoding="utf-8")

    manifest = {
        "source": "docs.easy.gg",
        "note": (
            "This helper stores raw index text only. Review docs.easy.gg manually before "
            "promoting entries into services.json, events.json, types.json, objects.json, or utilities.json."
        ),
        "pages": PAGES,
    }
    (DOCS_CACHE_DIR / "refresh_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    refresh_index_pages()
