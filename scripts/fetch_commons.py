#!/usr/bin/env python3
"""fetch_commons.py — download the freely-licensed photos the V2 shelves need, with their credits.

Only Wikimedia Commons files with an explicit free licence are eligible. Each download records the
author, the licence and the file's Commons page so the page can print a real credit line. If a
licence cannot be read, the file is skipped — we would rather have no photo than an unattributed one.

Curation model (two layers, so a search hit can never sneak onto the page):

  1. data/photo_map.json is the allowlist. It pins ONE exact Commons file per slot and says which
     group it belongs to (campus / era / bridge), which episodes it may illustrate, and the caption
     printed under it.
  2. A slot WITHOUT a pinned file falls back to the cached probe (research/raw/image_sources.json),
     and then only a hit whose own title shares a significant word with the term is eligible.

Reads   data/photo_map.json, research/raw/image_sources.json
Writes  assets/img/commons/*  +  assets/img/commons/CREDITS.json

Usage:  python3 scripts/fetch_commons.py [--dry-run] [--max 2]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import time
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "research/raw/image_sources.json"
DEST = ROOT / "assets/img/commons"
MAP_FILE = ROOT / "data/photo_map.json"
UA = "DifferentWorldNotes/0.1 (+https://github.com/joeNobody-ai/different-world-notes)"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
# Cards render these at 272–500 CSS px wide, so 960 px of source is ~2–3x — sharp on retina,
# and it keeps the committed weight (and the page) about half of what a 1280 px thumb costs.
THUMB_WIDTH = "960"

ACCEPT = re.compile(r"(public domain|cc0|cc[- ]by(-sa)?([- ]\d(\.\d)?)?|GFDL|no restrictions)", re.I)

_MAP = json.loads(MAP_FILE.read_text()) if MAP_FILE.exists() else {}


def _slots() -> list[dict]:
    """Every photo the site is allowed to print, in the order it appears."""
    out = []
    for slot in _MAP.get("campus", []):
        out.append({"term": slot["term"], "group": "campus", "file": slot.get("file"),
                    "episodes": [], "caption": slot.get("caption", "")})
    for slot in _MAP.get("era", []):
        out.append({"term": slot["term"], "group": "era", "file": slot.get("file"),
                    "episodes": slot.get("episodes", []), "caption": slot.get("caption", "")})
    for slot in _MAP.get("bridge", []):
        out.append({"term": slot["term"], "group": "bridge", "file": slot.get("file"),
                    "episodes": [], "caption": slot.get("caption", "")})
    return out


WANTED = [s["term"] for s in _slots()]


def strip_html(s: str | None) -> str:
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()
    # Commons' Artist field is usually a sentence ("The original uploader was X at English Wikipedia.")
    m = re.search(r"uploader was ([^\.]+?)(?: at (?:English )?Wikipedia)?\.?$", txt)
    if m:
        return f"{m.group(1).strip()} (via Wikimedia Commons)"
    m = re.search(r"^User:\s*([^\s]+)", txt)
    if m:
        return f"{m.group(1)} (Wikimedia Commons user)"
    return re.sub(r"\s+", " ", txt)[:120]


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:48]


def commons_file(title: str) -> dict | None:
    """Resolve ONE named Commons file to url + licence + author (the pinned-file path)."""
    q = {"action": "query", "format": "json", "formatversion": "2", "titles": title,
         "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": THUMB_WIDTH}
    p = subprocess.run(["curl", "-s", "-m", "40", "-A", UA, f"{COMMONS_API}?{urllib.parse.urlencode(q)}"],
                       capture_output=True, text=True)
    if p.returncode != 0 or not p.stdout.strip().startswith("{"):
        return None
    pages = (json.loads(p.stdout).get("query") or {}).get("pages") or []
    if not pages or pages[0].get("missing"):
        return None
    info = (pages[0].get("imageinfo") or [{}])[0]
    meta = info.get("extmetadata", {})
    desc = re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", (meta.get("ImageDescription", {}) or {}).get("value", ""))).strip()
    return {
        "title": pages[0].get("title"),
        "thumb_url": info.get("thumburl") or info.get("url"),
        "page_url": info.get("descriptionurl"),
        "author": (meta.get("Artist", {}) or {}).get("value", ""),
        "license": (meta.get("LicenseShortName", {}) or {}).get("value", ""),
        "license_url": (meta.get("LicenseUrl", {}) or {}).get("value", ""),
        "description": desc[:160],
    }


STOP = {"the", "of", "and", "a", "an", "at", "in", "on", "university", "college", "campus", "u.s."}


def title_matches(term: str, title: str) -> bool:
    """Fallback guard: an unpinned search hit must at least be about the thing we asked for."""
    words = [w for w in re.findall(r"[a-z0-9]+", term.lower()) if w not in STOP and len(w) > 3]
    t = title.lower()
    return any(w in t for w in words)


def ext_of(title: str) -> str:
    m = re.search(r"\.([a-z0-9]{3,4})$", title.lower())
    return m.group(1) if m and m.group(1) in {"jpg", "jpeg", "png", "gif", "webp"} else "jpg"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=1, help="how many fallback hits to keep per unpinned term")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cache = json.loads(SRC.read_text()) if SRC.exists() else {}
    DEST.mkdir(parents=True, exist_ok=True)

    credits, kept = [], 0
    for slot in _slots():
        term = slot["term"]
        hits: list[dict] = []
        if slot.get("file"):
            one = commons_file(slot["file"])
            if one:
                hits = [one]
                print(f"  pinned: {slot['file']}")
                print(f"          commons says: {hits[0]['description'][:110] or '(no description)'}")
            else:
                print(f"  MISS pinned file not found on Commons: {slot['file']}")
        else:
            cached = cache.get("commons", {}).get(term, [])
            hits = [h for h in cached if title_matches(term, h.get("title") or "")][: args.max]
            if hits:
                print(f"  fallback hit: {hits[0]['title']}")

        usable = [h for h in hits if h.get("license") and ACCEPT.search(h["license"]) and h.get("thumb_url")]
        if not usable:
            print(f"  skip {term}: no freely-licensed, on-topic photo found")
            continue
        for h in usable:
            # a short hash of the SOURCE title: re-pinning a slot to a different Commons file always
            # downloads fresh bytes, so a filename can never carry one file's photo under another's credit
            tag = hashlib.md5((h["title"] or "").encode()).hexdigest()[:6]
            name = f"{slug(term)[:42]}-{tag}.{ext_of(h['title'] or '')}"
            path = DEST / name
            if not args.dry_run and not path.exists():
                p = subprocess.run(["curl", "-s", "-m", "60", "-A", UA, "-o", str(path), h["thumb_url"]],
                                   capture_output=True, text=True)
                if p.returncode != 0 or not path.exists() or path.stat().st_size < 4096:
                    print(f"  FAIL download {term}: {p.returncode} {p.stderr[:80]}")
                    continue
                time.sleep(1)
            credits.append({
                "file": f"assets/img/commons/{name}",
                "subject": term,
                "group": slot["group"],
                "episodes": slot["episodes"],
                "caption": slot["caption"],
                "commons_title": h["title"],
                "page_url": h.get("page_url"),
                "author": strip_html(h.get("author")) or "see Commons file page",
                "license": h["license"],
                "license_url": h.get("license_url") or "",
            })
            kept += 1
            print(f"  kept {name}  [{h['license']}] ({slot['group']})")

    if not args.dry_run:
        (DEST / "CREDITS.json").write_text(json.dumps(
            {"about": "Photos from Wikimedia Commons, free licences only. One pinned file per slot in "
                      "data/photo_map.json; attribution is printed on the page under every photo.",
             "count": len(credits), "files": credits}, indent=1))
        # a photo that is no longer in the map must not linger in the repo
        live = {pathlib.Path(c["file"]).name for c in credits}
        for stray in DEST.glob("*"):
            if stray.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"} and stray.name not in live:
                print(f"  removing stray (not in the map): {stray.name}")
                stray.unlink()
    print(f"\n{kept} photo(s) in {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
