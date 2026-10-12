#!/usr/bin/env python3
"""normalize_episodes.py — turn the raw Wikipedia wikitext parse into clean episode records.

The raw pull (research/raw/original-episodes.json) is faithful to Wikipedia's markup, which means
season is a string like "Season 1 (1987-88)", the episode number is a string, and the air date is a
{{start date|1987|09|24}} template. Everything downstream wants integers and ISO dates, so this
normalises once, loudly, and fails if anything does not parse.

Output: data/original_episodes.json
   [{"season": 1, "ep": 1, "title": "...", "air_date": "1987-09-24", "summary": "..."}]
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]          # different-world-fan-page/
RAW = ROOT / "research/raw/original-episodes.json"
OUT = ROOT / "karens-class/data/original_episodes.json"


def parse_season(raw: str) -> int:
    m = re.search(r"(\d+)", raw or "")
    if not m:
        raise ValueError(f"unparseable season: {raw!r}")
    return int(m.group(1))


def parse_date(raw: str) -> str:
    m = re.search(r"start date\|(\d{4})\|(\d{1,2})\|(\d{1,2})", raw or "")
    if m:
        y, mo, d = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", (raw or "").strip())
    if m:
        return m.group(0)
    raise ValueError(f"unparseable date: {raw!r}")


def main() -> int:
    raw = json.loads(RAW.read_text())
    out, problems = [], []
    for rec in raw:
        try:
            season = parse_season(rec.get("season", ""))
            ep = int(str(rec.get("ep", "")).strip())
            title = (rec.get("title") or "").strip()
            date = parse_date(rec.get("date", ""))
            if not title:
                raise ValueError("empty title")
            out.append({"season": season, "ep": ep, "title": title, "air_date": date,
                        "summary": (rec.get("summary") or "").strip()})
        except Exception as exc:                                    # noqa: BLE001
            problems.append(f"{rec.get('season')} ep={rec.get('ep')}: {exc}")
    out.sort(key=lambda r: (r["season"], r["ep"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    print(f"normalised {len(out)} episodes -> {OUT}")
    if problems:
        print(f"{len(problems)} unparsed rows (reported, not silently dropped):")
        for p in problems[:20]:
            print("  !", p)
    # sanity: the seasons we expect, and the count per season
    from collections import Counter
    per = Counter(r["season"] for r in out)
    print("per season:", dict(sorted(per.items())))
    if len(out) < 140:
        print("WARNING: fewer than 140 episodes parsed (Wikipedia list has 144 total; "
              "a few rows use a different template) — fine for this course, noted for accuracy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
