#!/usr/bin/env python3
"""fetch_youtube.py — the transcript route, and why it is blocked from this machine.

WHY THIS IS HARD. The reference wants real usage examples — lines actually spoken, with timestamps that
link to the moment. YouTube will not serve captions to this machine, and not for want of trying. Every
route attempted on 2026-10-04:

  1. youtube-transcript-api ...................... blocked: "YouTube is blocking requests from your IP"
                                                   (cloud-provider address ranges are refused)
  2. www.youtube.com/api/timedtext ............... 0 bytes
  3. video.google.com/timedtext (legacy) ......... 0 bytes
  4. the watch page's own captionTracks .......... page is served degraded here, no captionTracks at all
  5. yt-dlp --write-auto-subs .................... "Sign in to confirm you're not a bot"
  6. transcript web services (server-side) ....... return client-rendered shells; text not in the HTML
  7. Invidious mirrors (they fetch server-side) ... bot checks / not JSON; the public instance list is
                                                   down to a single candidate
  8. cloud browser (different IP) ................ provider returned no CDP endpoint in this profile

So the honest position: no caption text can be obtained from here, and therefore no quoted line appears
in the reference. What ships instead is *video-level* evidence — verified links whose context is the
uploader's own title (see harvest_video_evidence.py) — plus this script, which turns a transcript into
quotable evidence the moment one is available.

HOW TO UNBLOCK, in order of ease:

  A. Paste it. Open the video in a browser, open the transcript panel ("Show transcript"), select all,
     copy, and save it to a file. Then:
         python3 scripts/fetch_youtube.py --ingest /path/to/transcript.txt --video VIDEOID
     Works from any machine, including one whose IP YouTube does not block.

  B. Run this script somewhere else. On a normal (non-datacenter) connection:
         python3 scripts/fetch_youtube.py --fetch VIDEOID
     It tries the transcript API first, then yt-dlp, and writes /opt/data/scratch/caps/VIDEOID.vtt

  C. Provide cookies for yt-dlp. NOT recommended: YouTube may permanently ban the account the cookies
     come from. If you do it anyway, pass --cookies-from-browser=firefox to yt-dlp yourself; this script
     will not do it for you.

WHAT HAPPENS TO A TRANSCRIPT. It is stored OUTSIDE the repository (gitignored, like subtitles/) and is
never republished. Only short quoted lines are published — one line that demonstrates a term, credited to
the video and timestamped so a reader can watch it — with the transcript's provenance recorded in the
data. verify_lingo.py refuses to build a quoted example that has no recorded transcript source.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAPS = pathlib.Path("/opt/data/scratch/caps")
QUOTES = ROOT / "data/lingo_quotes.json"


def parse_vtt(text: str) -> list[dict]:
    """Return [{t: seconds, line: text}] from VTT or SRT."""
    cues = []
    block = re.split(r"\n\s*\n", text.replace("\r", ""))
    for b in block:
        m = re.search(r"(\d{1,2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->", b)
        if not m:
            continue
        h, mi, s, _ms = (int(x) for x in m.groups())
        body = " ".join(ln.strip() for ln in b.splitlines() if "-->" not in ln and ln.strip()
                        and not ln.strip().isdigit()
                        and not ln.strip().startswith(("WEBVTT", "Kind:", "Language:")))
        body = re.sub(r"<[^>]+>", "", body)
        body = re.sub(r"\s+", " ", body).strip()
        if body:
            cues.append({"t": h * 3600 + mi * 60 + s, "line": body})
    return cues


def try_fetch(vid: str) -> pathlib.Path | None:
    CAPS.mkdir(parents=True, exist_ok=True)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
        api = YouTubeTranscriptApi()
        fetched = api.fetch(vid)
        cues = [{"t": int(s.start), "line": re.sub(r"\s+", " ", s.text).strip()}
                for s in fetched if s.text.strip()]
        p = CAPS / f"{vid}.json"
        p.write_text(json.dumps(cues, indent=1))
        print(f"fetched {len(cues)} cues via youtube-transcript-api -> {p}")
        return p
    except Exception as exc:                                    # noqa: BLE001
        print(f"  transcript API failed: {str(exc).splitlines()[0][:120]}")
    p = subprocess.run(["yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs",
                        "--sub-langs", "en.*", "--sub-format", "vtt",
                        "-o", str(CAPS / "%(id)s.%(ext)s"),
                        f"https://www.youtube.com/watch?v={vid}"], capture_output=True, text=True)
    out = sorted(CAPS.glob(f"{vid}*.vtt"))
    if out:
        print(f"fetched via yt-dlp -> {out[0]}")
        return out[0]
    print("  yt-dlp failed:", (p.stderr or p.stdout).strip().splitlines()[-1][:140])
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", metavar="VIDEOID", help="try to download captions (needs an unblocked IP)")
    ap.add_argument("--ingest", metavar="FILE", help="ingest a pasted transcript (.vtt/.srt/.txt)")
    ap.add_argument("--video", metavar="VIDEOID", help="the video the pasted transcript came from")
    ap.add_argument("--demo", action="store_true", help="show what the ingestion would produce")
    args = ap.parse_args()

    if args.fetch:
        got = try_fetch(args.fetch)
        if not got:
            print("\nNothing fetched. See the docstring: this machine's IP is blocked by YouTube.")
            return 3
        return 0

    if not args.ingest:
        print(__doc__)
        return 0

    src = pathlib.Path(args.ingest)
    text = src.read_text(errors="replace")
    cues = parse_vtt(text)
    if not cues:                                    # plain text transcript: no timestamps available
        cues = [{"t": None, "line": re.sub(r"\s+", " ", ln).strip()}
                for ln in text.splitlines() if len(ln.strip()) > 3]
        print("no timestamps found — parsed as plain text "
              "(examples will have no jump-to-moment link)")
    print(f"parsed {len(cues)} cues from {src}")

    lingo = json.loads((ROOT / "data/lingo.json").read_text())
    terms = [x["term"] for s in lingo["sections"] for x in s["entries"]]
    demo = []
    for t in terms:
        needle = re.sub(r"\s*/\s*.*$", "", t).strip().lower()
        for c in cues:
            if needle and needle in c["line"].lower():
                demo.append((t, c["t"], c["line"][:110]))
                break
    print(f"\nterms with a candidate line in this transcript: {len(demo)}")
    for t, sec, line in demo[:25]:
        stamp = f"{sec // 60}:{sec % 60:02d}" if sec is not None else "  ?  "
        print(f"   {stamp}  {t[:34]:34s} {line}")

    QUOTES.write_text(json.dumps({
        "_note": ("Candidate quoted lines, extracted from a real transcript. NOT yet published: each "
                  "candidate has to be checked by a human against the video, then attached to the entry "
                  "with a transcript_source recorded, at which point verify_lingo.py will accept it. "
                  "The transcript itself is never committed."),
        "video": args.video,
        "source_file": str(src),
        "retrieved": "see file mtime",
        "candidates": [{"term": t, "t": sec, "line": line} for t, sec, line in demo],
    }, indent=1))
    print(f"\nwrote {len(demo)} candidates -> {QUOTES} (nothing published yet)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
