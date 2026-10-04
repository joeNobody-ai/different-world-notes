#!/usr/bin/env python3
"""find_scenes.py — find the scenes that matter inside an episode transcript.

This is the working tool for the site: once an episode's subtitles are imported
(`scripts/import_subtitles.py`), this scans the cue stream for the things we care about —
characters, Hillman lore, and the political/social topics the show is speaking to — clusters
nearby hits into *scene candidates* with timecodes, and ranks them.

    python3 scripts/find_scenes.py --coverage                 # which episodes have transcripts
    python3 scripts/find_scenes.py --topics                   # the topic vocabulary and weights
    python3 scripts/find_scenes.py --episode 7                # all topics, episode 7, ranked
    python3 scripts/find_scenes.py --episode 7 --topic politics
    python3 scripts/find_scenes.py --all --out data/candidates  # write JSON for every episode
    python3 scripts/find_scenes.py --episode 3 --context 4     # print N lines around each hit

Topic vocabulary lives in data/scene_queries.json — edit that file (not this script) to teach it
new terms. Matching is case-insensitive, word-boundary aware, and multi-word phrases score higher.

Exit code 0 = ran; 2 = nothing to scan (no transcripts yet), with the exact next command printed.
"""
from __future__ import annotations

import argparse, json, pathlib, re, sys, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "data" / "scripts"
QUERIES = ROOT / "data" / "scene_queries.json"
CLUSTER_GAP_S = 45.0          # hits within this many seconds belong to the same scene


def load_queries() -> dict:
    if not QUERIES.exists():
        sys.exit(f"missing {QUERIES}")
    return json.loads(QUERIES.read_text())


def load_transcript(ep: int) -> dict | None:
    f = SCRIPTS / f"ep{ep:02d}.json"
    return json.loads(f.read_text()) if f.exists() else None


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).replace("\u2019", "'").replace("\u2014", " - ")
    return re.sub(r"[^a-z0-9' ]+", " ", s.lower())


def phrase_hits(text: str, phrase: str) -> int:
    """Count word-boundary occurrences of a phrase inside already-normalised text."""
    pat = r"\b" + re.escape(norm(phrase)).strip() + r"\b"
    return len(re.findall(pat, text))


def score_cues(cues: list[dict], terms: dict[str, float]) -> list[dict]:
    """Return per-cue hits: [{cue_i, term, weight, text, start_s, end_s}]."""
    hits = []
    for c in cues:
        hay = norm(c["plain"])
        for term, weight in terms.items():
            n = phrase_hits(hay, term)
            if n:
                hits.append({"cue_i": c["i"], "term": term, "weight": float(weight) * (1 + 0.25 * (len(term.split()) - 1)),
                             "count": n, "text": c["plain"], "start": c["start"], "end": c["end"],
                             "start_s": c["start_s"], "end_s": c["end_s"]})
    return hits


def cluster(hits: list[dict], gap: float = CLUSTER_GAP_S) -> list[dict]:
    """Group hits that happen within `gap` seconds of each other into scene candidates."""
    if not hits:
        return []
    hits = sorted(hits, key=lambda h: h["start_s"])
    groups: list[list[dict]] = [[hits[0]]]
    for h in hits[1:]:
        if h["start_s"] - groups[-1][-1]["start_s"] <= gap:
            groups[-1].append(h)
        else:
            groups.append([h])

    out = []
    for g in groups:
        terms = {}
        for h in g:
            terms[h["term"]] = terms.get(h["term"], 0) + h["count"]
        # score: distinct terms matter more than repeats; longer phrases already weighted
        distinct = len(terms)
        total = sum(h["weight"] * h["count"] for h in g)
        score = round(total + 1.5 * distinct, 2)
        # one line per cue, in cue order (a cue can match several terms; don't print it twice)
        lines, seen_cues = [], set()
        for h in sorted(g, key=lambda x: x["cue_i"]):
            if h["cue_i"] in seen_cues:
                continue
            seen_cues.add(h["cue_i"])
            lines.append(h["text"])
        out.append({
            "start": min(h["start"] for h in g), "end": max(h["end"] for h in g),
            "start_s": min(h["start_s"] for h in g), "end_s": max(h["end_s"] for h in g),
            "duration_s": round(max(h["end_s"] for h in g) - min(h["start_s"] for h in g), 1),
            "terms": sorted(terms, key=lambda t: (-terms[t], t)),
            "term_counts": terms, "hit_count": sum(h["count"] for h in g),
            "score": score,
            "cues": sorted({h["cue_i"] for h in g}),
            "lines": lines[:6],
        })
    return sorted(out, key=lambda s: -s["score"])


def context_lines(cues: list[dict], scene: dict, n: int) -> list[str]:
    """The scene's lines plus n cues either side, for eyeballing in the terminal."""
    idx = {c["i"]: k for k, c in enumerate(cues)}
    lo = max(0, idx[scene["cues"][0]] - n)
    hi = min(len(cues), idx[scene["cues"][-1]] + n + 1)
    return [f"      {c['start']}  {c['plain']}" for c in cues[lo:hi]]


def run_episode(ep: int, query: dict, min_score: float, limit: int, ctx: int, out: pathlib.Path | None) -> list[dict]:
    rec = load_transcript(ep)
    if not rec:
        return []
    cues = rec["cues"]
    terms = query.get("terms", {})
    scenes = [s for s in cluster(score_cues(cues, terms)) if s["score"] >= min_score]

    print(f"\n=== ep{ep:02d}  ({rec['cue_count']} cues, {rec['duration']})  topic: {query['label']}")
    if not scenes:
        print("    no scenes above the score threshold")
    for s in scenes[:limit]:
        print(f"  [{s['score']:6.2f}] {s['start']}–{s['end']}  ({s['duration_s']}s, "
              f"{len(s['cues'])} cues)  terms: {', '.join(s['terms'][:6])}")
        for line in s["lines"][:3]:
            print(f"      · {line[:120]}")
        if ctx:
            for line in context_lines(cues, s, ctx):
                print(line)

    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        payload = {"episode": ep, "topic": query["id"], "topic_label": query["label"],
                   "generated_for": rec["source_file"], "transcript_cues": rec["cue_count"],
                   "min_score": min_score, "scenes": scenes[:limit]}
        (out / f"ep{ep:02d}-{query['id']}.json").write_text(json.dumps(payload, indent=1))
    return scenes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--episode", type=int, help="episode number 1-10")
    ap.add_argument("--all", action="store_true", help="every episode that has a transcript")
    ap.add_argument("--topic", default="all", help="topic id from data/scene_queries.json, or 'all'")
    ap.add_argument("--topics", action="store_true", help="list the vocabulary")
    ap.add_argument("--coverage", action="store_true", help="which episodes have transcripts")
    ap.add_argument("--min-score", type=float, default=6.0)
    ap.add_argument("--limit", type=int, default=8, help="max scenes printed per episode/topic")
    ap.add_argument("--context", type=int, default=0, help="print N subtitles either side of a scene")
    ap.add_argument("--out", type=pathlib.Path, help="write JSON here (e.g. data/candidates)")
    args = ap.parse_args()

    queries = load_queries()

    if args.topics:
        for q in queries["queries"]:
            print(f"  {q['id']:12s} {q['label']}\n      terms: {', '.join(list(q['terms'])[:12])}")
        return 0

    eps = list(range(1, 11))
    have = [e for e in eps if (SCRIPTS / f"ep{e:02d}.json").exists()]

    if args.coverage:
        print("transcripts available:")
        for e in eps:
            rec = load_transcript(e)
            print(f"  ep{e:02d}: " + (f"{rec['cue_count']} cues, {rec['duration']}  ({rec['source_kind']})" if rec else "— none —"))
        print(f"{len(have)}/10 imported")
        if not have:
            print("\nnext: put subtitles in subtitles/ and run  python3 scripts/import_subtitles.py")
        return 0

    if not have:
        print("nothing to scan — no transcripts imported yet.")
        print("  1) python3 scripts/import_subtitles.py --list     # see what is in subtitles/")
        print("  2) python3 scripts/import_subtitles.py            # import them")
        return 2

    targets = [args.episode] if args.episode else (have if args.all else [])
    if not targets:
        print(f"transcripts exist for {have} — pass --episode N or --all")
        return 2

    chosen = queries["queries"] if args.topic == "all" else [q for q in queries["queries"] if q["id"] == args.topic]
    if not chosen:
        sys.exit(f"unknown topic {args.topic!r}; see --topics")

    for ep in targets:
        if not load_transcript(ep):
            print(f"  ep{ep:02d}: no transcript — skipping")
            continue
        for q in chosen:
            run_episode(ep, q, args.min_score, args.limit, args.context, args.out)
    if args.out:
        print(f"\nwrote candidates to {args.out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
