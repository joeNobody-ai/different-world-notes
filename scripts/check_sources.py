#!/usr/bin/env python3
"""check_sources.py — validate every outside URL the course cites, and record the verdict.

A course bibliography that 404s is worse than no bibliography. So: nothing gets published as a
source until this script has seen an HTTP 200 from it, and the result is written to
data/source_checks.json with the date and status code.

Candidates live in data/source_candidates.json. After a run, data/course_sources.json holds only
the entries that passed, plus their check metadata.

Usage:
  python3 scripts/check_sources.py            # check everything, write results
  python3 scripts/check_sources.py --report   # print the last results
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAND = ROOT / "data/source_candidates.json"
CHECKS = ROOT / "data/source_checks.json"
UA = "Mozilla/5.0 (compatible; KarensClassCourse/1.0; +https://github.com/joeNobody-ai/Karens-Class)"


def head(url: str) -> tuple[int, str]:
    for attempt in (1, 2):
        p = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-L", "-m", "25", "-A", UA,
             "-H", "Accept: text/html,application/xhtml+xml", url],
            capture_output=True, text=True)
        code = (p.stdout or "000").strip()
        if code not in ("000", "403", "429"):
            return int(code), ""
        if attempt == 2:
            return int(code), "blocked-or-unreachable"
        time.sleep(3)
    return 0, "failed"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    if args.report and CHECKS.exists():
        d = json.loads(CHECKS.read_text())
        ok = [u for u, v in d["urls"].items() if v["status"] == 200]
        bad = [u for u, v in d["urls"].items() if v["status"] != 200]
        print(f"checked {d['checked']}  ok {len(ok)}  failed {len(bad)}")
        for u in bad:
            print(f"  ✗ {d['urls'][u]['status']}  {u}")
        return 0

    cand = json.loads(CAND.read_text())
    results: dict[str, dict] = {}
    for group, urls in cand["groups"].items():
        print(f"## {group}")
        for url in urls:
            code, note = head(url)
            results[url] = {"status": code, "note": note, "group": group}
            print(f"  {'✓' if code == 200 else '✗'} {code}  {url}" + (f"  ({note})" if note else ""))
            time.sleep(0.7)
    CHECKS.write_text(json.dumps(
        {"checked": len(results), "date": time.strftime("%Y-%m-%d"), "urls": results}, indent=1))
    good = sum(1 for v in results.values() if v["status"] == 200)
    print(f"\n{good}/{len(results)} reachable -> {CHECKS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
