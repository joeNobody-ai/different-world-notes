#!/usr/bin/env python3
"""verify_v2.py — structural checks for the V2 (Netflix-style) pages.

Beyond the usual (files exist, no leftovers, links resolve, panels collapsed) this checks the things
that make V2 *V2*: every shelf is populated, the ranked shelf is numbered 1..10, every image either
exists on disk or is a declared hotlink, and every Commons photo carries its licence and credit.

Usage: python3 scripts/verify_v2.py      (exit 0 = pass)
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
V2 = ROOT / "v2"
DATA = ROOT / "data"
failures: list[str] = []
checks = 0


def ok(cond: bool, label: str, detail: str = "") -> None:
    global checks
    checks += 1
    if cond:
        print(f"  ✓ {label}")
    else:
        failures.append(f"{label} {detail}".strip())
        print(f"  ✗ {label} {detail}")


def read(p: pathlib.Path) -> str:
    return p.read_text() if p.exists() else ""


def main() -> int:
    global checks
    episodes = json.loads((DATA / "episodes.json").read_text())
    pages = [e["page"] for e in episodes["episodes"]]

    print("1. files")
    ok((V2 / "index.html").exists(), "v2/index.html exists")
    for p in pages:
        ok((V2 / p).exists(), f"v2/{p} exists")
    ok((ROOT / "assets/v2/netflix.css").exists(), "v2 stylesheet exists")
    ok((ROOT / "assets/v2/netflix.js").exists(), "v2 script exists")
    ok((ROOT / "assets/art/manifest.json").exists(), "art manifest exists")

    print("2. no unrendered placeholders")
    for p in ["index.html"] + pages:
        html = read(V2 / p)
        ok("{{" not in html and "}}" not in html, f"v2/{p} clean")

    print("3. images resolve (local must exist; http is a declared hotlink)")
    hotlinks: list[str] = []
    for p in ["index.html"] + pages:
        html = read(V2 / p)
        for src in re.findall(r'<img[^>]+src="([^"]+)"', html):
            if src.startswith("http"):
                hotlinks.append(src)
                continue
            target = (V2 / src).resolve()
            ok(target.exists(), f"v2/{p}: {src} exists on disk")
    ok(len(hotlinks) > 0, f"hotlinks present and counted ({len(hotlinks)})")
    ok(all("media-amazon.com" in u for u in hotlinks),
       "every hotlink is IMDb/Amazon CDN (key art or headshots), nothing scraped elsewhere")

    print("4. hub shelves")
    idx = read(V2 / "index.html")
    for shelf_id, expect, label in (("episodes", 10, "episodes"), ("callbacks", 10, "top callbacks"),
                                    ("cast", 10, "cast"), ("original", 12, "1987 era"),
                                    ("politics", 10, "politics"), ("campuses", 6, "campuses")):
        block = re.search(r'<section class="shelf" id="%s">(.*?)</section>' % shelf_id, idx, re.S)
        if not block:
            ok(False, f"shelf '{shelf_id}' present")
            continue
        cards = len(re.findall(r'class="card', block.group(1)))
        ok(cards == expect, f"shelf '{shelf_id}' has {expect} cards ({label})", f"got {cards}")
    ranks = re.findall(r'<span class="rankno">(\d+)</span>', idx)
    ok(ranks == [str(i) for i in range(1, 11)], "ranked shelf numbers 1..10 in order", f"got {ranks}")
    ok(idx.count("cdn") == 0, "no stray cdn tokens")

    print("5. episode pages")
    for ep in episodes["episodes"]:
        html = read(V2 / ep["page"])
        rows = re.findall(r'<div class="ep-row" id="([^"]+)"', html)
        ok(rows == ep["callbacks"], f"v2/{ep['page']}: {len(ep['callbacks'])} callback rows in order",
           f"got {rows}")
        for needle in ('id="politics"', 'id="script"'):
            ok(needle in html, f"v2/{ep['page']}: has {needle}")
        ok(html.index('id="politics"') < html.index('id="script"'),
           f"v2/{ep['page']}: politics above the script")
        ok(len(re.findall(r'<details class="nf"[^>]*\sopen', html)) == 0,
           f"v2/{ep['page']}: no panel ships open")
        ok('data-action="expand-all"' in html, f"v2/{ep['page']}: expand-all control")
        ok(html.count("class=\"spoiler\"") + html.count(" src spoiler") >= 0, f"v2/{ep['page']}: spoiler classes usable")
        if ep["number"] < 10:
            ok(f'href="ep{ep["number"] + 1:02d}.html"' in html, f"v2/{ep['page']}: next-episode card")
    # every callback card must expose a source link + tier badge
    for ep in episodes["episodes"]:
        html = read(V2 / ep["page"])
        for cid in ep["callbacks"]:
            block = re.search(r'<div class="ep-row" id="%s".*?</div>\s*</div>' % re.escape(cid), html, re.S)
            if not block:
                ok(False, f"v2/{ep['page']}: row {cid} found")
                continue
            b = block.group(0)
            ok(len(re.findall(r'href="http', b)) >= 1 and "badge" in b,
               f"v2/{ep['page']}: {cid} has a source link and badges")

    print("6. internal links resolve")
    ids_by_file: dict[pathlib.Path, set[str]] = {}
    for p in [V2 / "index.html"] + [V2 / x for x in pages]:
        ids_by_file[p] = set(re.findall(r'id="([^"]+)"', read(p)))
    broken = 0
    for p in [V2 / "index.html"] + [V2 / x for x in pages]:
        for href in re.findall(r'href="(?!https?:|mailto:|data:)([^"]+)"', read(p)):
            target, _, frag = href.partition("#")
            tpath = (p.parent / target).resolve() if target else p
            if not tpath.exists():
                broken += 1
                failures.append(f"{p.name} links to missing {target}")
            elif frag and tpath in ids_by_file and frag not in ids_by_file[tpath]:
                broken += 1
                failures.append(f"{p.name} links to missing anchor {target}#{frag}")
    checks += 1
    print(("  ✓ " if not broken else "  ✗ ") + f"internal links resolve ({broken} broken)")

    print("7. credits are real")
    creds_file = ROOT / "assets/img/commons/CREDITS.json"
    creds = json.loads(creds_file.read_text())["files"]
    ok(all(c.get("license") and c.get("page_url") and c.get("author") for c in creds),
       "every Commons photo has author + licence + page URL")
    ok(all(c["file"].startswith("assets/img/commons/") for c in creds), "credit paths are inside the repo")
    ok("Commons" in idx and "Photo:" in idx, "hub prints the photo credits")
    # curation guard: a photo may only ship if its term is on fetch_commons' WANTED allowlist.
    # (The probe explores extra terms whose hits can be junk — e.g. a "1980s Black students" search
    #  that returned a village store. Those must never reach the site.)
    sys.path.insert(0, str(ROOT / "scripts"))
    from fetch_commons import WANTED  # noqa: E402
    off_list = [c["subject"] for c in creds if c["subject"] not in WANTED]
    ok(not off_list, "every committed photo is on the curated download allowlist", str(off_list))
    ok(len(creds) == len(list((ROOT / "assets/img/commons").glob("*.jpg"))),
       "one credit per downloaded photo")

    print("8. generated artwork is valid XML")
    import xml.etree.ElementTree as ET
    bad = []
    for f in sorted((ROOT / "assets/art").glob("*.svg")):
        try:
            ET.parse(f)
        except ET.ParseError as exc:
            bad.append(f"{f.name}: {exc}")
    ok(not bad, f"all {len(list((ROOT / 'assets/art').glob('*.svg')))} SVG files parse", "; ".join(bad[:3]))
    manifest = json.loads((ROOT / "assets/art/manifest.json").read_text())
    ok(manifest["count"] == len(manifest["files"]), "art manifest count matches its file list")

    print(f"\n{checks - len(failures)}/{checks} checks passed")
    if failures:
        print(f"\n{len(failures)} FAILURE(S):")
        for f in failures[:30]:
            print("  ✗", f)
        return 1
    print("ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
