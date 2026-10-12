#!/usr/bin/env python3
"""attach_examples.py — merge the verified video evidence and the curated senses into data/lingo.json.

Two inputs, both machine-checkable:
  data/youtube_evidence.json  — video links verified through YouTube's oEmbed endpoint (uploader's own
                                title and channel). These become `examples` with kind="video-context":
                                the context recorded is the *uploader's framing*, never our paraphrase of
                                dialogue.
  data/lingo_senses.json      — curated multiple senses for terms that carry more than one meaning.

Idempotent: re-running replaces the generated fields rather than appending duplicates. A term with no
evidence keeps no examples — this script never invents one.
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINGO = ROOT / "data/lingo.json"
EVID = ROOT / "data/youtube_evidence.json"
SENSES = ROOT / "data/lingo_senses.json"

# terms whose evidence key differs from the entry term
KEY_ALIASES = {"cuff / cuffing season": "cuffing season"}


def main() -> int:
    lingo = json.loads(LINGO.read_text())
    evid = json.loads(EVID.read_text())["terms"]
    senses = json.loads(SENSES.read_text())["senses"]

    attached = 0
    terms_seen: set[str] = set()
    for section in lingo["sections"]:
        for x in section["entries"]:
            term = x["term"]
            terms_seen.add(term)
            key = KEY_ALIASES.get(term, term)
            vids = evid.get(key) or evid.get(term)
            if vids:
                x["examples"] = [{
                    "kind": "video-context",
                    "context": v["title"],                 # the uploader's own words
                    "channel": v["channel"],
                    "official": v["kind"] == "official",
                    "link": v["link"],
                } for v in vids]
                attached += 1
            else:
                x.pop("examples", None)
            if term in senses:
                x["senses"] = senses[term]
            else:
                x.pop("senses", None)

    # evidence keys that matched nothing are a signal the reference is missing a term
    missing = sorted(set(evid) - {KEY_ALIASES.get(t, t) for t in terms_seen} - terms_seen)
    if missing:
        print("  ! evidence exists for terms not in the reference:", missing)
        print("    (add the term, or the evidence will never be published)")

    LINGO.write_text(json.dumps(lingo, indent=1))
    n_ex = sum(len(x.get("examples", [])) for s in lingo["sections"] for x in s["entries"])
    n_senses = sum(1 for s in lingo["sections"] for x in s["entries"] if x.get("senses"))
    print(f"attached evidence to {attached} terms ({n_ex} verified video links) "
          f"and senses to {n_senses} terms")
    print(f"wrote {LINGO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
