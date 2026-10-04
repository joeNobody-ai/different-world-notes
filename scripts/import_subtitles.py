#!/usr/bin/env python3
"""import_subtitles.py — turn whatever subtitle material you have into one clean transcript per episode.

WHAT IT TAKES (drop the file in `subtitles/`, name it so the episode is obvious):

    ep01.srt            SubRip
    ep01.vtt            WebVTT
    ep01.ttml / .xml / .dfxp   Netflix's TTML subtitle XML (what the userscript intercepts)
    ep01.json           a localStorage dump from the Netflix Subtitle Translator userscript
                        (it caches the ORIGINAL + translated cues per episode URL)

WHAT IT MAKES:

    data/scripts/epNN.json   normalised cues: {i, start, end, start_s, end_s, text, plain}
    data/scripts/epNN.txt    plain transcript, one line per cue (what find_scenes.py reads)

USAGE

    python3 scripts/import_subtitles.py                 # import everything found in subtitles/
    python3 scripts/import_subtitles.py --list          # what is in subtitles/ and what it maps to
    python3 scripts/import_subtitles.py --check         # validate already-imported transcripts
    python3 scripts/import_subtitles.py --episode 3     # only ep03

Getting Netflix TTML without a browser download:
  Play the episode with the userscript installed, then in DevTools console run
      copy(JSON.stringify(localStorage))
  paste it into subtitles/ep01.json and run this script. The userscript caches the original
  (untranslated) cue text per episode URL, which is exactly what we need.

Stdlib only. No network access.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
DROPZONE = ROOT / "subtitles"
OUTDIR = ROOT / "data" / "scripts"

EP_RE = re.compile(r"(?:^|[^a-z0-9])ep(?:isode)?[ _-]?0?([1-9]|10)(?:[^0-9]|$)", re.I)
TS_RE = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})(?:[.,](\d{1,3}))?")


# ---------------------------------------------------------------- time helpers
def to_seconds(ts: str) -> float:
    m = TS_RE.search(ts.strip())
    if not m:
        raise ValueError(f"unparseable timestamp: {ts!r}")
    h, mi, s, ms = m.group(1), m.group(2), m.group(3), m.group(4)
    frac = float("0." + (ms or "0").ljust(3, "0"))
    return int(h or 0) * 3600 + int(mi) * 60 + int(s) + frac


def timecode(sec: float) -> str:
    sec = max(0.0, float(sec))
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}"


def tidy(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)             # strip inline tags
    text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
    text = re.sub(r"\{\\[^}]*\}", "", text)          # ASS karaoke junk
    return re.sub(r"\s+", " ", text).strip()


def cues_from_pairs(pairs: list[tuple[float, float, str]]) -> list[dict]:
    cues, seen = [], set()
    for start, end, raw in sorted(pairs, key=lambda p: (p[0], p[1])):
        text = tidy(raw)
        if not text or text in seen and False:
            continue
        cues.append({"i": len(cues) + 1, "start": timecode(start), "end": timecode(end),
                     "start_s": round(start, 3), "end_s": round(end, 3),
                     "text": text, "plain": tidy(text)})
        seen.add(text)
    return cues


# ---------------------------------------------------------------- per-format parsers
def parse_srt(raw: str) -> list[tuple[float, float, str]]:
    out = []
    for block in re.split(r"\n\s*\n", raw.replace("\r\n", "\n").replace("\r", "\n")):
        lines = [l for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        idx = 0
        if lines[0].strip().isdigit():
            idx = 1
        if idx >= len(lines) or "-->" not in lines[idx]:
            continue
        a, _, b = lines[idx].partition("-->")
        try:
            out.append((to_seconds(a), to_seconds(b.split()[0] if b.strip() else b), " ".join(lines[idx + 1:])))
        except ValueError:
            continue
    return out


def parse_vtt(raw: str) -> list[tuple[float, float, str]]:
    body = raw.replace("\r\n", "\n").replace("\r", "\n")
    body = re.sub(r"^WEBVTT[^\n]*\n", "", body, flags=re.I)
    out = []
    for block in re.split(r"\n\s*\n", body):
        lines = [l for l in block.split("\n") if l.strip()]
        ts_line = next((l for l in lines if "-->" in l), None)
        if not ts_line:
            continue
        a, _, b = ts_line.partition("-->")
        try:
            start = to_seconds(a)
            end = to_seconds(b.strip().split()[0] if b.strip() else b)
        except ValueError:
            continue
        text = " ".join(l for l in lines[lines.index(ts_line) + 1:] if l.strip())
        out.append((start, end, text))
    return out


def parse_ttml(raw: str) -> list[tuple[float, float, str]]:
    out = []
    raw = re.sub(r"^\s*<\?xml[^>]*\?>", "", raw.strip())
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        raise ValueError(f"TTML did not parse: {e}") from e
    for p in root.iter():
        if not p.tag.endswith("}p") and p.tag != "p":
            continue
        begin, end = p.get("begin"), p.get("end")
        if not begin or not end:
            continue
        parts = []
        for node in p.iter():
            if node is not p and (node.tag.endswith("}br") or node.tag == "br"):
                parts.append(" — ")                       # Netflix encodes speaker changes as <br>
        text = "".join(p.itertext())
        # keep the <br> separator where it belongs: rebuild from raw tail-order is messy, so
        # approximate by splitting the flat text evenly is wrong — instead join texts of children.
        kids = [ "".join(c.itertext()).strip() for c in list(p) if c.tag.endswith("}span") or c.tag == "span" ]
        if len(kids) > 1:
            text = " — ".join(k for k in kids if k)
        try:
            out.append((to_seconds(begin), to_seconds(end), text))
        except ValueError:
            continue
    if not out:
        raise ValueError("no <p> cues with begin/end found — is this really TTML?")
    return out


def _collect_userscript_strings(obj, acc: list[str]) -> None:
    """The userscript cache holds JSON blobs; we only want the original cue text lines."""
    if isinstance(obj, str):
        s = obj.strip()
        if s.startswith("{") or s.startswith("["):
            try:
                _collect_userscript_strings(json.loads(s), acc)
            except Exception:
                acc.append(obj)
        else:
            acc.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_userscript_strings(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _collect_userscript_strings(v, acc)


def parse_json_cache(raw: str) -> list[tuple[float, float, str]]:
    """Two shapes are accepted:
       (a) already-normalised: {"cues":[{"start_s":..,"end_s":..,"text":..}, ...]}
       (b) a raw localStorage dump from the userscript, which stores cue arrays with
           start/end/duration/text somewhere inside. We walk it and take cues that have both.
    """
    data = json.loads(raw)

    def norm_cues(cs):
        out = []
        for c in cs:
            if not isinstance(c, dict):
                continue
            st = c.get("start_s", c.get("start", c.get("startTime")))
            en = c.get("end_s", c.get("end", c.get("endTime")))
            txt = c.get("text") or c.get("plain") or c.get("original") or c.get("source") or ""
            if st is None or en is None or not str(txt).strip():
                continue
            out.append((float(st) if not isinstance(st, str) else to_seconds(st),
                        float(en) if not isinstance(en, str) else to_seconds(en),
                        str(txt)))
        return out

    if isinstance(data, dict):
        for key in ("cues", "lines", "subtitles", "captions"):
            if isinstance(data.get(key), list):
                got = norm_cues(data[key])
                if got:
                    return got
        # nested per-URL caches
        for v in data.values():
            if isinstance(v, dict):
                for key in ("cues", "lines"):
                    if isinstance(v.get(key), list):
                        got = norm_cues(v[key])
                        if got:
                            return got

    # last resort: flat string soup has no timing -> not usable
    strings: list[str] = []
    _collect_userscript_strings(data, strings)
    raise ValueError(
        "JSON contained no cue objects with timings. "
        f"Found {len(strings)} text strings but no start/end pairs. "
        "If this is a userscript dump, export the per-episode cache entry "
        "(localStorage key containing that episode URL) rather than the whole store."
    )


PARSERS = {".srt": parse_srt, ".vtt": parse_vtt,
           ".ttml": parse_ttml, ".xml": parse_ttml, ".dfxp": parse_ttml,
           ".json": parse_json_cache}


# ---------------------------------------------------------------- driver
def episode_of(path: pathlib.Path) -> int | None:
    m = EP_RE.search(path.stem)
    if not m:
        return None
    n = int(m.group(1))
    return n if 1 <= n <= 10 else None


def import_file(path: pathlib.Path, episode: int, quiet: bool = False) -> dict:
    ext = path.suffix.lower()
    parser = PARSERS.get(ext)
    if not parser:
        raise ValueError(f"unsupported extension {ext} (have: {', '.join(sorted(PARSERS))})")
    pairs = parser(path.read_text(encoding="utf-8", errors="replace"))
    cues = cues_from_pairs(pairs)
    if not cues:
        raise ValueError("parsed zero cues")
    rec = {"episode": episode, "source_file": path.name, "source_kind": ext.lstrip("."),
           "imported_on": date.today().isoformat(), "cue_count": len(cues),
           "duration": timecode(cues[-1]["end_s"]), "duration_s": cues[-1]["end_s"],
           "cues": cues}
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / f"ep{episode:02d}.json").write_text(json.dumps(rec, indent=1))
    (OUTDIR / f"ep{episode:02d}.txt").write_text("\n".join(c["plain"] for c in cues) + "\n")
    if not quiet:
        print(f"  ep{episode:02d}  <- {path.name:28s} {len(cues):5d} cues  {rec['duration']}  -> data/scripts/ep{episode:02d}.json")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="show what is in subtitles/ and where it maps")
    ap.add_argument("--check", action="store_true", help="validate imported transcripts")
    ap.add_argument("--episode", type=int, help="only this episode number")
    args = ap.parse_args()

    if args.check:
        files = sorted(OUTDIR.glob("ep*.json")) if OUTDIR.exists() else []
        if not files:
            print("no transcripts imported yet — data/scripts/ is empty.")
            print("drop files in subtitles/ and run: python3 scripts/import_subtitles.py")
            return 1
        bad = 0
        for f in files:
            rec = json.loads(f.read_text())
            ok = rec["cues"] and all(c.get("start_s") is not None and c.get("text") for c in rec["cues"])
            mono = all(rec["cues"][i]["start_s"] <= rec["cues"][i + 1]["start_s"] for i in range(len(rec["cues"]) - 1))
            print(f"  {f.name}: {rec['cue_count']} cues, {rec['duration']}, monotonic={mono}, complete={bool(ok)}")
            bad += 0 if (ok and mono) else 1
        print(f"{len(files)} transcript(s), {bad} problem(s)")
        return 1 if bad else 0

    if not DROPZONE.exists():
        DROPZONE.mkdir(parents=True)
        print(f"created {DROPZONE} — put ep01.srt / ep01.ttml / ep01.json in there and re-run.")
        return 1

    candidates = sorted(p for p in DROPZONE.iterdir() if p.is_file() and p.suffix.lower() in PARSERS)
    if not candidates:
        print(f"nothing to import in {DROPZONE}/")
        print("accepted: " + ", ".join(sorted(PARSERS)))
        return 1

    if args.list:
        for p in candidates:
            ep = episode_of(p)
            print(f"  {p.name:34s} -> {'ep%02d' % ep if ep else 'UNMAPPED (put ep01..ep10 in the name)'}")
        return 0

    print(f"importing from {DROPZONE}/")
    ok = fail = 0
    for p in candidates:
        ep = episode_of(p)
        if ep is None:
            print(f"  SKIP {p.name}: cannot tell which episode — name it ep01..ep10")
            fail += 1
            continue
        if args.episode and ep != args.episode:
            continue
        try:
            import_file(p, ep)
            ok += 1
        except Exception as e:
            print(f"  FAIL {p.name}: {e}")
            fail += 1
    print(f"\n{ok} imported, {fail} failed")
    if ok:
        print("next:  python3 scripts/find_scenes.py --coverage")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
