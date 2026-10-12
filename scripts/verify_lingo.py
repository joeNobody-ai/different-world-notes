#!/usr/bin/env python3
"""verify_lingo.py — machine checks for the Lingo & slang reference. Stdlib only.

Default: offline structural checks. With --links: also HTTP-check every source URL the reference uses.

Exit 0 = ALL CHECKS PASS.

The strongest check here is citation integrity: every "SxEy" the reference cites must exist in the
1987-1993 episode list, and where the citation also states an air date, that date must match the record.
A reference that cites an episode that does not exist is worse than no reference.
"""
from __future__ import annotations

import json
import html as html_mod
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_pages import SOURCES  # noqa: E402

ORIG = json.loads((ROOT / "karens-class/data/original_episodes.json").read_text())
OIDX = {(x["season"], x["ep"]): x for x in ORIG}
LINGO = json.loads((ROOT / "data/lingo.json").read_text())

# URLs a headless checker cannot reach; each justified. Kept in step with make_sources.py in the course.
BLOCKED_OK = {"https://www.bls.gov/"}
BLOCKED_LABELS = ("Merriam-Webster",)          # label-only sources, no URL to check

checks = 0
fails: list[str] = []


def ok(cond: bool, label: str) -> None:
    global checks
    checks += 1
    if not cond:
        fails.append(label)


def main() -> int:                                          # noqa: C901
    statuses = set(LINGO["legend"])
    entries = [(s["id"], x) for s in LINGO["sections"] for x in s["entries"]]

    print("1. data shape")
    ok(len(LINGO["sections"]) >= 5, "at least 5 sections")
    ok(statuses == {"documented", "era-lexicon", "handle-with-care", "project-jargon"},
       f"legend defines exactly the four statuses (got {sorted(statuses)})")
    ok(len(entries) >= 100, f"at least 100 entries (got {len(entries)})")
    for s in LINGO["sections"]:
        ok(bool(s.get("id") and s.get("title") and s.get("blurb")), f"section {s.get('id')} complete")
        ok(bool(s.get("entries")), f"section {s.get('id')} has entries")

    print("2. entry integrity")
    seen: set[str] = set()
    for sid, x in entries:
        t = x.get("term", "")
        ok(bool(t.strip()), f"{sid}: term missing")
        key = t.lower()
        ok(key not in seen, f"duplicate term: {t}")
        seen.add(key)
        ok(bool(x.get("gloss", "").strip()), f"{t}: empty gloss")
        ok(x.get("status") in statuses, f"{t}: status not in legend")
        if x.get("status") == "documented":
            ok(bool(x.get("evidence")), f"{t}: documented with no citation")
        if x.get("status") == "handle-with-care":
            ok(bool(x.get("sources")) or bool(x.get("evidence")), f"{t}: care entry with no source")
        for k in x.get("sources", []):
            ok(k in SOURCES, f"{t}: unknown source key {k}")

    print("3. citation integrity — every cited episode must exist, and dates must match")
    for sid, x in entries:
        ev = x.get("evidence", "") or ""
        for season, ep in re.findall(r"S(\d{1,2})E(\d{1,3})", ev):
            rec = OIDX.get((int(season), int(ep)))
            ok(rec is not None, f"{x['term']}: cites S{season}E{ep}, which is not in the episode list")
            dates = re.findall(r"\((\d{4}-\d{2}-\d{2})\)", ev)
            if rec and dates:
                ok(rec["air_date"] in dates,
                   f"{x['term']}: S{season}E{ep} air date {rec['air_date']} not among cited {dates}")
            if rec:
                ok(rec["title"].lower() in ev.lower(),
                   f"{x['term']}: does not name the title of S{season}E{ep} ({rec['title']})")
        for n in re.findall(r"(?:2026 Ep|Ep) (\d{1,2})", ev):
            ok(1 <= int(n) <= 10, f"{x['term']}: cites 2026 episode {n}, out of range 1-10")

    print("4. rendered pages")
    doc = (ROOT / "lingo.html")
    v2doc = (ROOT / "v2/lingo.html")
    ok(doc.exists(), "lingo.html exists (V1)")
    ok(v2doc.exists(), "v2/lingo.html exists (V2)")
    if doc.exists() and v2doc.exists():
        v1, v2 = html_mod.unescape(doc.read_text()), html_mod.unescape(v2doc.read_text())
        for name, html in (("lingo.html", v1), ("v2/lingo.html", v2)):
            ok(html.count("<dt ") == len(entries), f"{name}: renders all {len(entries)} entries")
            for _, x in entries:
                ok(x["term"].replace("&", "&amp;") in html or x["term"] in html,
                   f"{name}: missing term {x['term']}")
            for st in statuses:
                ok(st.replace("-", " ") in html or st in html, f"{name}: legend status {st} present")
            ok("{{" not in html and "}}" not in html, f"{name}: no template leftovers")
            ok(len(re.findall(r'class="lg-ev"', html)) ==
               sum(1 for _, x in entries if x.get("evidence")), f"{name}: one evidence line per citation")
            ok(len(re.findall(r'class="lg-caution"', html)) ==
               sum(1 for _, x in entries if x.get("caution")), f"{name}: caution lines rendered")
        # nav + cross-links
        ok('href="lingo.html"' in (ROOT / "index.html").read_text(), "V1 index links to the lingo page")
        ok('href="lingo.html"' in (ROOT / "v2/index.html").read_text(), "V2 index links to the lingo page")
        ok('href="lingo.html"' in v2, "V2 lingo page has the nav link")
        ok('href="index.html#glossary"' in v1 or 'href="index.html"' in v1,
           "V1 lingo page links back to the site")
        ok("lg-care" in v2 and "lg-care" in v1, "handle-with-care entries are visually flagged")

    print("4b. every lingo source key is actually cited somewhere")
    LINGO_KEYS = {k for k in SOURCES if k.startswith(("wiki-", "lsa-", "book-"))
                  or k in {"greens", "oed", "dialects", "mw"}}
    cited = {k for _, x in entries for k in x.get("sources", [])}
    unused = sorted(LINGO_KEYS - cited)
    ok(not unused, f"unused lingo source keys: {unused}")

    print("5. counts by status")
    by: dict[str, int] = {}
    for _, x in entries:
        by[x["status"]] = by.get(x["status"], 0) + 1
    print("   " + " · ".join(f"{k}: {v}" for k, v in sorted(by.items())))

    if "--links" in sys.argv:
        print("6. source URLs")
        urls = sorted({SOURCES[k] for _, x in entries for k in x.get("sources", [])
                       if SOURCES.get(k)})
        for u in urls:
            code = "000"
            for attempt in (1, 2):
                p = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-L",
                                    "-m", "25", "-A",
                                    "Mozilla/5.0 (compatible; OriginNotesLingo/1.0)", u],
                                   capture_output=True, text=True)
                code = (p.stdout or "000").strip()
                if code in ("200", "403", "202"):
                    break
                time.sleep(2)
            good = code in ("200", "403", "202")
            ok(good, f"source URL not reachable/known-blocked: {u} -> {code}")
            print(f"   {'✓' if code == '200' else ('~' if code in ('403', '202') else '✗')} {code}  {u}")
        print("   (403/202 = refuses automated clients; those are labelled as such on the page)")

    print(f"\n{checks - len(fails)}/{checks} checks passed")
    if fails:
        print(f"\n{len(fails)} FAILURE(S):")
        for f in fails[:40]:
            print("  ✗", f)
        return 1
    print("ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
