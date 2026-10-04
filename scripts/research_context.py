#!/usr/bin/env python3
"""research_context.py — pull *cited* 2026 context for the "Politics & the moment" sections.

Why this exists: the fan page puts the show's political/social statements next to what is
actually happening in Black American life in 2026. Those claims have to be checkable, so every
item is stored with the article URL and the date it was retrieved.

Method: Wikipedia search -> article intro, fetched with `curl` (the API rate-limits urllib from
this host; curl with a browser UA goes through), one request at a time, cached per topic so a
re-run never refetches what we already have.

Usage:
  python3 scripts/research_context.py            # fetch anything not yet cached, then merge
  python3 scripts/research_context.py --show     # print what we have
  python3 scripts/research_context.py --topic hbcu-funding
"""
from __future__ import annotations

import argparse, datetime, json, pathlib, subprocess, sys, time, urllib.parse

API = "https://en.wikipedia.org/w/api.php"
UA = ("DifferentWorldNotes/0.1 (+https://github.com/joeNobody-ai/different-world-notes) "
      "python-urllib/curl")
ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "research/raw/context"
OUT = ROOT / "research/raw/context-2026.json"

# Curated by exact article title (fewer requests than search, and we control the framing).
# label -> Wikipedia article title
TOPICS = {
    "hbcu": "Historically black colleges and universities",
    "affirmative-action": "Students for Fair Admissions v. Harvard",
    "affirmative-action-us": "Affirmative action in the United States",
    "dei": "Diversity, equity, and inclusion",
    "economic-blackout": "Economic Blackout",
    "black-wealth-gap": "Racial inequality in the United States",
    "hiv-black-america": "HIV/AIDS in the United States",
    "black-maternal-health": "Maternal mortality in the United States",
    "police-violence": "Police use of deadly force in the United States",
    "original-series": "A Different World",
    "cosby-show": "The Cosby Show",
}
PACE_S = 9.0   # Wikipedia throttles bursts hard from this host; one request every ~9s keeps up.


def curl_json(params: dict) -> dict:
    """One API call via curl. Retries on 429/503 with backoff."""
    url = f"{API}?" + urllib.parse.urlencode({**params, "format": "json", "formatversion": "2"})
    delay = 3.0
    for attempt in range(1, 5):
        p = subprocess.run(["curl", "-s", "-m", "30", "-A", UA, url],
                           capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip():
            try:
                return json.loads(p.stdout)
            except json.JSONDecodeError:
                pass
        print(f"    retry {attempt}/4 in {delay:.0f}s ({p.returncode=} {p.stdout[:80]!r})")
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"curl/API failed for {params}")


def fetch_topic(topic: str, title: str) -> dict:
    """Fetch one article's intro by exact title (one API request), cached to disc."""
    cache_file = CACHE / f"{topic}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    d = curl_json({"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
                   "redirects": 1, "titles": title})
    page = d.get("query", {}).get("pages", [{}])[0]
    real = page.get("title") or title
    rec = {"topic": topic, "requested_title": title,
           "article": {"title": real,
                       "url": "https://en.wikipedia.org/wiki/" + real.replace(" ", "_"),
                       "intro": (page.get("extract") or "").strip()[:2000]},
           "retrieved": datetime.date.today().isoformat()}
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(rec, indent=1))
    time.sleep(PACE_S)          # pace between *network* requests only; cache hits are instant
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--topic")
    args = ap.parse_args()

    if args.show and OUT.exists():
        for item in json.loads(OUT.read_text())["items"]:
            a = item["article"]
            print(f"## {item['topic']}\n   {a['title']}\n   {a['url']}\n   {(a['intro'] or '')[:300]}...\n")
        return 0

    topics = {args.topic: TOPICS[args.topic]} if args.topic else TOPICS
    items = []
    for topic, title in topics.items():
        cached = (CACHE / f"{topic}.json").exists()
        rec = fetch_topic(topic, title)
        items.append(rec)
        print(f"[{'cached' if cached else 'fetched'}] {topic} <- {rec['article']['title']}")

    # merge: keep every cached topic, not just the ones in this run
    merged = {}
    for f in sorted(CACHE.glob("*.json")):
        r = json.loads(f.read_text())
        merged[r["topic"]] = r
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"retrieved": datetime.date.today().isoformat(),
                              "endpoint": API, "items": list(merged.values())}, indent=1))
    print(f"\nwrote {OUT}  ({len(merged)} topics cached)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
