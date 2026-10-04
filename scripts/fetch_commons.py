#!/usr/bin/env python3
"""fetch_commons.py — download the freely-licensed photos the V2 shelf needs, with their credits.

Only Wikimedia Commons files with an explicit free licence are eligible. Each download records the
author, the licence and the file's Commons page so the page can print a real credit line. If a
licence cannot be read, the file is skipped — we would rather have no photo than an unattributed one.

Reads  research/raw/image_sources.json (from scripts/probe_images.py)
Writes assets/img/commons/*.jpg  +  assets/img/commons/CREDITS.json

Usage:  python3 scripts/fetch_commons.py [--max 2] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "research/raw/image_sources.json"
DEST = ROOT / "assets/img/commons"
UA = "DifferentWorldNotes/0.1 (+https://github.com/joeNobody-ai/different-world-notes)"

ACCEPT = re.compile(r"(public domain|cc0|cc[- ]by(-sa)?([- ]\d(\.\d)?)?|GFDL)", re.I)
# terms we want on the page, in the order they should appear
WANTED = [
    "Howard University Founders Library",
    "Spelman College campus",
    "Morehouse College campus",
    "Hampton University campus",
    "Fisk University Jubilee Hall",
    "Tuskegee University campus",
]


def strip_html(s: str) -> str:
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=1, help="how many files to keep per term")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not SRC.exists():
        print(f"missing {SRC} — run: python3 scripts/probe_images.py")
        return 1
    data = json.loads(SRC.read_text())
    DEST.mkdir(parents=True, exist_ok=True)

    credits, kept = [], 0
    for term in WANTED:
        hits = data.get("commons", {}).get(term, [])
        usable = [h for h in hits if h.get("license") and ACCEPT.search(h["license"]) and h.get("thumb_url")]
        if not usable:
            print(f"  skip {term}: no freely-licensed hit found")
            continue
        for h in usable[: args.max]:
            name = f"{slug(term)}-{slug(h['title'].replace('File:', ''))[:32]}.jpg"
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
                "commons_title": h["title"],
                "page_url": h.get("page_url"),
                "author": strip_html(h.get("author")) or "see Commons file page",
                "license": h["license"],
                "license_url": h.get("license_url") or "",
            })
            kept += 1
            print(f"  kept {name}  [{h['license']}]")

    if not args.dry_run:
        (DEST / "CREDITS.json").write_text(json.dumps(
            {"about": "Photos from Wikimedia Commons, free licences only. Attribution is printed on the page.",
             "count": len(credits), "files": credits}, indent=1))
    print(f"\n{kept} photo(s) in {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
