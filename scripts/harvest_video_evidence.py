#!/usr/bin/env python3
"""harvest_video_evidence.py — find and VERIFY real YouTube evidence for lingo terms.

Captions are blocked from this host (documented in scripts/fetch_youtube.py), so we cannot quote
dialogue. What we CAN do honestly:

  1. search YouTube for clips about each term,
  2. VERIFY every candidate exists via YouTube's oEmbed endpoint (returns the uploader's own title and
     channel — i.e. the evidence is the uploader's framing, not our paraphrase),
  3. prefer official channel clips (Netflix and the like) and label third-party clips as such,
  4. record video-level evidence with a clickable link — every one HTTP-verified, or it does not ship.

Output: data/youtube_evidence.json
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import urllib.parse

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36")
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/youtube_evidence.json"

# term -> search queries (a term may need several, to reach multi-sense evidence)
QUERIES: dict[str, list[str]] = {
    "cuffing season": ["A Different World cuffing season Netflix", "A Different World Those Who Can Cuff"],
    "stepping": ["A Different World stepping", "A Different World step show Hillman"],
    "signifying / signifyin'": ["A Different World reading someone", "A Different World Whitley reads"],
    "the dozens": ["A Different World the dozens", "A Different World playing the dozens"],
    "reading (someone)": ["Dwayne putting Whitley in Check A Different World", "A Different World Whitley read"],
    "throwing shade": ["A Different World shade", "Whitley Gilbert shady moments"],
    "bougie / bourgie": ["The Fabulous Whitley Gilbert", "Whitley Gilbert bougie moments"],
    "pageant (Miss Hillman, Mr. Hillman, Miss Gilbert Hall)": ["A Different World Mr Hillman pageant",
                                                              "A Different World Miss Hillman"],
    "pledge / pledging": ["A Different World It's Greek to Me pledge", "A Different World fraternity pledging"],
    "hazing": ["A Different World pledge hazing", "A Different World fraternity initiation"],
    "the Pit": ["A Different World The Pit Mr Gaines", "A Different World Mr Gaines"],
    "homecoming": ["A Different World homecoming", "A Different World Gilbert Hall steps"],
    "hook up": ["A Different World Dwayne Whitley romance", "A Different World dating"],
    "code-switching": ["A Different World Whitley telephone voice", "A Different World code switching"],
    "HBCU": ["A Different World HBCU impact", "HBCU campus tour A Different World"],
    "Mammy": ["A Different World Mammy Dearest", "A Different World images of black women exhibit"],
    "cuff / cuffing season": ["A Different World cast cuffing season", "A Different World season 1 clips Netflix"],
}
OFFICIAL_HINTS = ("netflix", "official", "nbc", "differentworld")


def curl(url: str) -> str:
    return subprocess.run(["curl", "-s", "-L", "-m", "30", "-A", UA, url],
                          capture_output=True, text=True).stdout


def search(q: str) -> list[tuple[str, str]]:
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(q)
    html = curl(url)
    out: list[tuple[str, str]] = []
    for m in re.finditer(r'"videoRenderer":\{"videoId":"([\w-]{11})".*?"title":\{"runs":\[\{"text":"(.*?)"\}', html):
        vid, title = m.group(1), m.group(2)
        if (vid, title) not in out:
            out.append((vid, title))
    return out[:8]


def oembed(vid: str) -> dict | None:
    """The verification step: does this video exist, what does the uploader call it, who uploaded it?"""
    u = ("https://www.youtube.com/oembed?format=json&url="
         + urllib.parse.quote(f"https://www.youtube.com/watch?v={vid}", safe=""))
    body = curl(u)
    try:
        d = json.loads(body)
    except Exception:
        return None
    if not d.get("title"):
        return None
    return {"id": vid, "title": d["title"], "channel": d.get("author_name", ""),
            "channel_url": d.get("author_url", ""), "link": f"https://youtu.be/{vid}"}


def main() -> int:
    result: dict[str, list[dict]] = {}
    for term, queries in QUERIES.items():
        found: list[dict] = []
        print(f"\n## {term}")
        for q in queries:
            for vid, title in search(q):
                if any(f["id"] == vid for f in found):
                    continue
                meta = oembed(vid)
                if not meta:
                    print(f"   ✗ dropped (oEmbed failed): {vid} {title[:60]}")
                    continue
                ch = meta["channel"].lower()
                meta["kind"] = "official" if any(h in ch for h in OFFICIAL_HINTS) else "third-party clip"
                found.append(meta)
                print(f"   ✓ {meta['id']} [{meta['kind']}] {meta['channel'][:22]:22s} {meta['title'][:62]}")
                if len(found) >= 4:
                    break
            if len(found) >= 4:
                break
        result[term] = found
    OUT.write_text(json.dumps({
        "_note": ("Video-level evidence for lingo terms. Every entry was verified through YouTube's oEmbed "
                  "endpoint, which returns the uploader's own title and channel — so the 'context' recorded "
                  "here is the uploader's framing, not our reading of dialogue. Captions are blocked from the "
                  "machine that built this, so no entry claims a quoted line; see scripts/fetch_youtube.py "
                  "for the transcript route and how quotes get promoted into the reference."),
        "verified_on": "2026-10-04",
        "method": "YouTube search -> oEmbed verification -> kind=official|third-party clip",
        "terms": result,
    }, indent=1))
    total = sum(len(v) for v in result.values())
    official = sum(1 for v in result.values() for x in v if x["kind"] == "official")
    print(f"\n{total} verified video links across {len(result)} terms ({official} official) -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
