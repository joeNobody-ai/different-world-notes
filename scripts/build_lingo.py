#!/usr/bin/env python3
"""build_lingo.py — build the Lingo & slang reference for both views.

  lingo.html      (V1, text version)
  v2/lingo.html   (V2, Netflix-style)

Reads data/lingo.json. Reuses the shared source registry in build_pages.py so every citation is a key,
not a loose URL, and the "sources" block on the page cannot drift from the rest of the site.

Validates the data before writing anything: a documented entry must cite an episode, every status must
be in the legend, and every source key must exist in SOURCES. Fails loudly rather than shipping a
reference with a broken claim in it.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_pages import load, e, SOURCES, SOURCE_LABELS, head, FOOT, src_links  # noqa: E402
import build_v2  # noqa: E402  (for the Netflix-style shell)

STATUS_CLASS = {
    "documented": "lg-doc",
    "era-lexicon": "lg-era",
    "handle-with-care": "lg-care",
    "project-jargon": "lg-jar",
}
STATUS_SHORT = {
    "documented": "documented",
    "era-lexicon": "era lexicon",
    "handle-with-care": "handle with care",
    "project-jargon": "project jargon",
}

INTRO = (
    "The vocabulary the two series run on, and the vocabulary the culture around them uses. Every entry "
    "carries a status, because this project does not pretend to know what was said on screen. "
    "<b>Documented</b> means the term appears in the material this site already verifies — an episode's "
    "published summary, or a 2026 episode title — and the citation is given. <b>Era lexicon</b> means the "
    "term is genuine vocabulary of that period, sourced to dictionaries and scholarship, but has not been "
    "verified as used on screen. <b>Handle with care</b> means racialised or derogatory vocabulary that "
    "belongs in analysis and never in speech."
)


def validate(lingo: dict) -> list[str]:
    problems: list[str] = []
    legend = set(lingo["legend"])
    seen: set[str] = set()
    if not lingo.get("sections"):
        problems.append("no sections")
    for s in lingo["sections"]:
        if not s.get("id") or not s.get("title"):
            problems.append("a section is missing id/title")
        for x in s.get("entries", []):
            term = (x.get("term") or "").strip()
            if not term:
                problems.append(f"entry with no term in section {s.get('id')}")
                continue
            if term.lower() in seen:
                problems.append(f"duplicate term: {term}")
            seen.add(term.lower())
            if not (x.get("gloss") or "").strip():
                problems.append(f"{term}: no gloss")
            if x.get("status") not in legend:
                problems.append(f"{term}: status {x.get('status')!r} not in the legend")
            if x.get("status") == "documented" and not x.get("evidence"):
                problems.append(f"{term}: documented but cites no evidence")
            if x.get("status") == "handle-with-care" and not x.get("evidence") and not x.get("sources"):
                problems.append(f"{term}: handle-with-care with no source or evidence")
            for k in x.get("sources", []):
                if k not in SOURCES:
                    problems.append(f"{term}: unknown source key {k}")
    return problems


def legend_html(lingo: dict) -> str:
    items = "".join(
        f'<li><span class="lg-tag {STATUS_CLASS.get(k, "")}">{e(STATUS_SHORT.get(k, k))}</span> {e(v)}</li>'
        for k, v in lingo["legend"].items())
    return f'<ul class="lg-legend">{items}</ul>'


def entries_html(entries: list[dict]) -> str:
    out = []
    for x in entries:
        st = x["status"]
        tag = (f'<span class="lg-tag {STATUS_CLASS.get(st, "")}">{e(STATUS_SHORT.get(st, st))}</span>')
        bits = [f'<dt id="lg-{e(x["term"].lower().replace(" ", "-").replace("/", "").replace("'", ""))[:60]}">'
                f'{e(x["term"])} {tag}</dt>', f'<dd>{e(x["gloss"])}']
        # multiple senses, where a term genuinely carries more than one meaning
        if x.get("senses"):
            items = "".join(f'<li><b>{e(s["label"])}</b> — {e(s["gloss"])}</li>' for s in x["senses"])
            bits.append(f'<ol class="lg-senses">{items}</ol>')
        # verified video evidence: the context shown is the uploader's own title, never our paraphrase
        if x.get("examples"):
            lis = []
            for ex in x["examples"]:
                badge = ("official" if ex.get("official") else "third-party clip")
                lis.append(
                    f'<li><a class="lg-watch" href="{e(ex["link"])}" target="_blank" rel="noopener">'
                    f'▶ {e(ex["context"])}</a> '
                    f'<span class="lg-chan">{e(ex["channel"])} · {badge}</span></li>')
            bits.append('<ul class="lg-examples">'
                        '<span class="lg-ex-head">Watch it — the link is the evidence, and the title is the '
                        'uploader\'s own:</span>' + "".join(lis) + "</ul>")
        if x.get("caution"):
            bits.append(f'<p class="lg-caution">{e(x["caution"])}</p>')
        if x.get("evidence"):
            bits.append(f'<p class="lg-ev"><b>Evidence:</b> {e(x["evidence"])}</p>')
        if x.get("sources"):
            bits.append(f'<p class="lg-src"><b>Sources:</b> {src_links(x["sources"])}</p>')
        bits.append("</dd>")
        out.append("".join(bits))
    return "".join(out)


def counts(lingo: dict) -> dict:
    c = {k: 0 for k in lingo["legend"]}
    for s in lingo["sections"]:
        for x in s["entries"]:
            c[x["status"]] = c.get(x["status"], 0) + 1
    c["total"] = sum(c.values())
    return c


def render_v1(lingo: dict, n: dict) -> str:
    toc = " · ".join(f'<a href="#{e(s["id"])}">{e(s["title"])}</a>' for s in lingo["sections"])
    body = [f"""<article class="wrap narrow">
<p class="eyebrow">Reference · tiered and sourced</p>
<h1>Lingo &amp; slang</h1>
<p class="lede">{INTRO}</p>
<p class="fine">{n['total']} entries: {n['documented']} documented · {n['era-lexicon']} era lexicon ·
{n['handle-with-care']} handle with care · {n['project-jargon']} project jargon.
Last updated {e(lingo['updated'])}.</p>
{legend_html(lingo)}
<h2>How to use this list</h2>
<ul>{"".join(f"<li>{t}</li>" for t in lingo["how_to_use"])}</ul>
<p class="fine">Jump to: {toc}</p>"""]
    for s in lingo["sections"]:
        body.append(f"""<section class="block" id="{e(s['id'])}">
<h2>{e(s['title'])}</h2>
<p>{e(s['blurb'])}</p>
<dl class="lingo">{entries_html(s['entries'])}</dl>
</section>""")
    body.append("""<section class="block" id="method">
<h2>Method, and what this page will not claim</h2>
<p>This project has not watched either series. So the honest split is: a term appears in a documented
summary or a 2026 episode title, or it does not. The first kind is marked <b>documented</b> with its
citation. Everything else is <b>era lexicon</b> — real vocabulary of the period, taken from dictionaries
and scholarship on African American English, and explicitly not asserted as dialogue. When the transcript
pipeline in this project is fed real subtitles, entries can be promoted from era lexicon to documented,
one line at a time, with the line recorded.</p>
<p>Definitions of contemporary vocabulary move fast and are contested. Where a term's meaning is still
settling, the gloss says what the term does in use rather than pretending to a settled definition. The
dictionaries and scholarly sources this page draws on are listed below, and every one of them was
HTTP-checked on the date at the foot of the page.</p>
</section>""")
    body.append("</article>")
    return head("Lingo & slang — A Different World", 
                "Tiered, sourced reference to the vocabulary of A Different World (2026) and the 1987-1993 original: "
                "campus and Greek-life terms, verbal traditions, period slang, and the project's own jargon.") \
        + "\n".join(body) + FOOT


def render_v2(lingo: dict, n: dict) -> str:
    toc = "".join(f'<a class="lg-jump" href="#{e(s["id"])}">{e(s["title"])}</a>' for s in lingo["sections"])
    body = [f"""<div class="lingo-page">
<section class="meth" id="top">
  <h2>Lingo &amp; slang</h2>
  <p class="lg-lede">{INTRO}</p>
  <p class="lg-meta">{n['total']} entries · {n['documented']} documented · {n['era-lexicon']} era lexicon ·
  {n['handle-with-care']} handle with care · {n['project-jargon']} project jargon</p>
  {legend_html(lingo)}
  <div class="lg-toc">{toc}</div>
</section>"""]
    for s in lingo["sections"]:
        body.append(f"""<section class="meth" id="{e(s['id'])}">
  <h2>{e(s['title'])}</h2>
  <p>{e(s['blurb'])}</p>
  <dl class="lingo">{entries_html(s['entries'])}</dl>
</section>""")
    body.append("""<section class="meth" id="method">
  <h2>Method</h2>
  <p>This project has not watched either series, so nothing here claims a line of dialogue. Terms are
  <b>documented</b> (cited to a published summary or a 2026 episode title) or <b>era lexicon</b> (real
  vocabulary of the period, from dictionaries and scholarship — not verified on screen). When real
  subtitles are fed into the project's transcript pipeline, entries can be promoted one line at a time.
  See the <a href="../index.html#glossary">text version</a> for the culture glossary, and
  <a href="../index.html#method">method section</a> for how the rest of the site is verified.</p>
</section>
</div>""")
    return build_v2.head("Lingo & slang — Origin Notes",
                         "Tiered, sourced reference to the vocabulary of A Different World (2026) and the "
                         "1987-1993 original.") + build_v2.nav("../index.html") + "\n".join(body) + build_v2.FOOT


def main() -> int:
    lingo = load("lingo.json")
    assert lingo, "data/lingo.json is missing"
    problems = validate(lingo)
    if problems:
        print("LINGO DATA INVALID:", file=sys.stderr)
        for p in problems:
            print("  ✗", p, file=sys.stderr)
        return 2
    n = counts(lingo)
    (ROOT / "lingo.html").write_text(render_v1(lingo, n))
    (ROOT / "v2" / "lingo.html").write_text(render_v2(lingo, n))
    print(f"built lingo.html and v2/lingo.html — {n['total']} entries "
          f"({n['documented']} documented, {n['era-lexicon']} era lexicon, "
          f"{n['handle-with-care']} handle with care, {n['project-jargon']} project jargon)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
