#!/usr/bin/env python3
"""verify_pages.py — the structural check. Raises on anything that would embarrass us.

Checks, in order:
  1. every expected file exists (index + 10 episode pages + assets + data)
  2. no unrendered {{placeholders}} anywhere in the HTML
  3. each episode page carries exactly its own callbacks, and all 47 appear across the site
  4. every callback card has a tier badge, a confidence badge and at least one source link
  5. the hub has 10 episode cards, the callback table has 47 rows, and the filters exist
  6. every internal link (page + #anchor) resolves to a real file and a real id
  7. the collapsed panels are actually collapsed in the served HTML
  8. tag balance sanity for details/article/table

Exit 0 = all checks pass. Any failure prints the line and exits 1.

Usage:  python3 scripts/verify_pages.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
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
    callbacks = json.loads((DATA / "callbacks.json").read_text())
    pages = [e["page"] for e in episodes["episodes"]]

    print("1. files")
    ok((ROOT / "index.html").exists(), "index.html exists")
    for p in pages:
        ok((ROOT / p).exists(), f"{p} exists")
    ok((ROOT / "assets/styles.css").exists(), "styles.css exists")
    ok((ROOT / "assets/app.js").exists(), "app.js exists")

    print("2. no unrendered placeholders")
    for p in ["index.html"] + pages:
        html = read(ROOT / p)
        ok("{{" not in html and "}}" not in html, f"{p} has no template leftovers")

    print("3. callbacks per page")
    total = 0
    for ep in episodes["episodes"]:
        html = read(ROOT / ep["page"])
        ids = re.findall(r'data-callback="([^"]+)"', html)
        expected = ep["callbacks"]
        total += len(ids)
        ok(ids == expected, f"{ep['page']} renders its {len(expected)} callbacks in order",
           f"got {len(ids)}: {ids}")
    ok(total == len(callbacks["callbacks"]),
       f"all {len(callbacks['callbacks'])} callbacks appear across the site", f"got {total}")

    print("4. every card is sourced and badged")
    all_html = "\n".join(read(ROOT / p) for p in pages)
    for c in callbacks["callbacks"]:
        block = re.search(r'<article class="cb" id="%s".*?</article>' % re.escape(c["id"]), all_html, re.S)
        if not block:
            ok(False, f"{c['id']} card present in HTML")
            continue
        b = block.group(0)
        has_src = len(re.findall(r'href="http', b)) >= 1
        has_tier = "badge" in b and c["tier"] in b
        has_conf = c["confidence"] in b
        ok(has_src and has_tier and has_conf, f"{c['id']} card: tier + confidence + source link",
           f"src={has_src} tier={has_tier} conf={has_conf}")

    print("5. hub structure")
    idx = read(ROOT / "index.html")
    ok(len(re.findall(r"data-episode-card", idx)) == 10, "hub shows 10 episode cards")
    ok(len(re.findall(r"<tr data-tier=", idx)) == len(callbacks["callbacks"]),
       f"callback index has {len(callbacks['callbacks'])} rows")
    for needle in ('id="episode-filter"', 'id="cb-filter-text"', 'id="cb-filter-tier"', 'id="callback-table"'):
        ok(needle in idx, f"hub has {needle}")
    ok("ep09-rodney-king-precedent" in idx, "the Rodney King precedent is indexed")

    print("6. internal links resolve")
    ids_by_file: dict[str, set[str]] = {}
    for p in ["index.html"] + pages:
        ids_by_file[p] = set(re.findall(r'id="([^"]+)"', read(ROOT / p)))
    broken = 0
    for p in ["index.html"] + pages:
        for href in re.findall(r'href="(?!https?:|mailto:|data:)([^"]+)"', read(ROOT / p)):
            target, _, frag = href.partition("#")
            target = target or p
            if not (ROOT / target).exists():
                broken += 1
                failures.append(f"{p} links to missing file {target}")
            elif frag and frag not in ids_by_file.get(target, set()):
                broken += 1
                failures.append(f"{p} links to missing anchor {target}#{frag}")
    checks += 1
    print(("  ✓ " if not broken else "  ✗ ") + f"internal links resolve ({broken} broken)")

    print("7. panels are collapsed in the HTML")
    for p in pages:
        html = read(ROOT / p)
        open_panels = re.findall(r"<details class=\"panel\"[^>]*\sopen", html)
        ok(len(open_panels) == 0, f"{p}: no panel ships open")
        ok('id="politics"' in html and 'id="script"' in html, f"{p}: has politics + script panels")
        ok(html.index('id="politics"') < html.index('id="script"'), f"{p}: politics sits above the script")

    print("8. tag balance")
    for p in ["index.html"] + pages:
        html = read(ROOT / p)
        for tag in ("details", "article", "table", "main", "html"):
            o = len(re.findall(rf"<{tag}[\s>]", html))
            c = len(re.findall(rf"</{tag}>", html))
            ok(o == c, f"{p}: <{tag}> balanced ({o}/{c})")

    print(f"\n{checks - len(failures)}/{checks} checks passed")
    if failures:
        print(f"\n{len(failures)} FAILURE(S):")
        for f in failures[:40]:
            print("  ✗", f)
        return 1
    print("ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
