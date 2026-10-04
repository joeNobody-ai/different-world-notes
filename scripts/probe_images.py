#!/usr/bin/env python3
"""probe_images.py — find out which image sources actually work from this box, and record them.

Three candidates, kept separate on purpose:

  A. Wikimedia Commons (free licences, redistributable WITH attribution). Used properly: we download
     the file, then render the author + licence next to it. This is the only source whose files we
     commit.
  B. IMDb's image CDN (the show's key art). NOT redistributable, so we only record the URL and
     hotlink it from the page with a generated-art fallback behind it. Nothing is committed.
  C. Generated art (see scripts/make_art.py) — ours, unlimited, no attribution needed.

Writes research/raw/image_sources.json. Prints a human summary.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import time
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "research/raw/image_sources.json"
UA = "DifferentWorldNotes/0.1 (+https://github.com/joeNobody-ai/different-world-notes)"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"


def curl_json(url: str, tries: int = 3) -> dict | None:
    delay = 4.0
    for attempt in range(1, tries + 1):
        p = subprocess.run(["curl", "-s", "-m", "30", "-A", UA, url], capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip().startswith("{"):
            try:
                return json.loads(p.stdout)
            except json.JSONDecodeError:
                pass
        time.sleep(delay)
        delay *= 2
    return None


def commons_search(term: str, limit: int = 6) -> list[dict]:
    q = {
        "action": "query", "format": "json", "formatversion": "2",
        "generator": "search", "gsrsearch": f"{term} filetype:bitmap", "gsrnamespace": "6",
        "gsrlimit": str(limit), "prop": "imageinfo",
        "iiprop": "url|extmetadata|size", "iiurlwidth": "1280",
    }
    d = curl_json(f"{COMMONS_API}?" + urllib.parse.urlencode(q))
    if not d:
        return []
    out = []
    for page in d.get("query", {}).get("pages", []):
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        out.append({
            "title": page.get("title"),
            "thumb_url": info.get("thumburl") or info.get("url"),
            "page_url": info.get("descriptionurl"),
            "width": info.get("thumbwidth") or info.get("width"),
            "height": info.get("thumbheight") or info.get("height"),
            "author": (meta.get("Artist", {}) or {}).get("value", ""),
            "license": (meta.get("LicenseShortName", {}) or {}).get("value", ""),
            "credit": (meta.get("Credit", {}) or {}).get("value", ""),
            "license_url": (meta.get("LicenseUrl", {}) or {}).get("value", ""),
        })
    return out


def imdb_suggestion(term: str) -> list[dict]:
    url = "https://v3.sg.media-imdb.com/suggestion/x/" + urllib.parse.quote(term) + ".json"
    d = curl_json(url)
    out = []
    for item in (d or {}).get("d", [])[:4]:
        out.append({"id": item.get("id"), "label": item.get("l"), "kind": item.get("q"),
                    "year": item.get("y"), "image": (item.get("i") or {}).get("imageUrl")})
    return out


COMMONS_TERMS = [
    "Howard University Founders Library",
    "Spelman College campus",
    "Morehouse College campus",
    "Hampton University campus",
    "Historically black college students 1980s",
    "Tuskegee University campus",
    "Fisk University Jubilee Hall",
    "Black college homecoming marching band",
]

IMDB_TERMS = ["tt33081352", "tt0092339", "Maleah Joi Moon", "Jasmine Guy", "Kadeem Hardison",
              "Cree Summer", "Glynn Turman", "Jada Pinkett Smith"]


def main() -> int:
    result = {"commons": {}, "imdb": {}, "checked": time.strftime("%Y-%m-%d")}
    print("A. Wikimedia Commons (free licences — these we may commit):")
    for term in COMMONS_TERMS:
        hits = commons_search(term)
        result["commons"][term] = hits
        good = [h for h in hits if h["license"]]
        print(f"  {term:44s} {len(hits)} hits" + (f"  e.g. {good[0]['title']} [{good[0]['license']}]" if good else "  (none licensed)"))
        time.sleep(3)
    print("\nB. IMDb CDN (key art — hotlink only, never committed):")
    for term in IMDB_TERMS:
        hits = imdb_suggestion(term)
        result["imdb"][term] = hits
        first = hits[0] if hits else {}
        print(f"  {term:20s} {first.get('label')} ({first.get('year')}) img={'yes' if first.get('image') else 'no'}")
        time.sleep(1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
