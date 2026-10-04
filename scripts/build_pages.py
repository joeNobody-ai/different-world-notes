#!/usr/bin/env python3
"""build_pages.py — render the whole site from data/.

Inputs (all in data/):  episodes.json, callbacks.json, characters.json, politics.json,
                        timeline.json, glossary.json, starter-path.json
Optional:               data/scripts/epNN.json   (transcripts -> the script panel)
                        data/candidates/*.json  (find_scenes.py output -> scene candidates)

Outputs: index.html + ep01.html .. ep10.html   (complete static HTML; no JS needed to read)

Usage:
  python3 scripts/build_pages.py            # build
  python3 scripts/build_pages.py --check    # validate data only, write nothing
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
EPISODE_COUNT = 10

# Source keys used in data files, mapped to URLs. Kept in one place so the "sources and method"
# section can list every reference automatically.
SOURCES = {
    "series-2026": "https://en.wikipedia.org/wiki/A_Different_World_(2026_TV_series)",
    "episodes-original": "https://en.wikipedia.org/wiki/List_of_A_Different_World_episodes",
    "context/original-series": "https://en.wikipedia.org/wiki/A_Different_World",
    "context/cosby-show": "https://en.wikipedia.org/wiki/The_Cosby_Show",
    "imdb-2026": "https://www.imdb.com/title/tt33081352/",
    "imdb-original": "https://www.imdb.com/title/tt0092339/",
}
SOURCE_LABELS = {
    "series-2026": "Wikipedia — A Different World (2026 TV series): cast, episode table, reception",
    "episodes-original": "Wikipedia — List of A Different World episodes: 1987–1993 titles, air dates, summaries",
    "context/original-series": "Wikipedia — A Different World (1987 series)",
    "context/cosby-show": "Wikipedia — The Cosby Show",
    "imdb-2026": "IMDb — tt33081352",
    "imdb-original": "IMDb — tt0092339",
}


def load(name: str, required: bool = True) -> dict | None:
    p = DATA / name
    if not p.exists():
        if required:
            sys.exit(f"missing {p}")
        return None
    return json.loads(p.read_text())


def e(x) -> str:
    return html.escape(str(x if x is not None else ""), quote=True)


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def src_links(keys: list[str]) -> str:
    out = []
    for k in keys:
        url = SOURCES.get(k)
        label = SOURCE_LABELS.get(k, k)
        if url:
            out.append(f'<a href="{e(url)}" rel="noopener">{e(label.split(":")[0])}</a>')
        else:
            out.append(e(label))
    return " · ".join(out)


# ----------------------------------------------------------------- data validation
def norm_date(raw: str) -> str:
    """The original-series list stores air dates as {{start date|1987|09|24}} — normalise to ISO."""
    m = re.search(r"start date\|(\d{4})\|(\d{1,2})\|(\d{1,2})", raw or "")
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw or "")
    return m.group(0) if m else (raw or "").strip()


def norm_title(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").replace("\u00a0", " ")).strip().strip('"').lower()


def check_data(episodes, callbacks, politics, characters, timeline, glossary, starter, orig_rows) -> list[str]:
    problems: list[str] = []
    cb = {c["id"]: c for c in callbacks["callbacks"]}

    if len(cb) != len(callbacks["callbacks"]):
        problems.append("duplicate callback ids")
    if len(episodes["episodes"]) != EPISODE_COUNT:
        problems.append(f"expected {EPISODE_COUNT} episodes, found {len(episodes['episodes'])}")

    numbers = [x["number"] for x in episodes["episodes"]]
    if numbers != list(range(1, EPISODE_COUNT + 1)):
        problems.append(f"episode numbers are not 1..{EPISODE_COUNT}: {numbers}")

    used = set()
    for ep in episodes["episodes"]:
        for cid in ep["callbacks"]:
            used.add(cid)
            if cid not in cb:
                problems.append(f"episode {ep['number']} references unknown callback {cid}")
            elif cb[cid]["episode"] != ep["number"]:
                problems.append(f"callback {cid} is filed under episode {cb[cid]['episode']} but listed on episode {ep['number']}")
        for field in ("title", "director", "writer", "released", "hook", "beat", "page"):
            if not ep.get(field):
                problems.append(f"episode {ep['number']} missing {field}")
    orphans = set(cb) - used
    if orphans:
        problems.append(f"callbacks not listed on any episode: {sorted(orphans)}")

    for cid, c in cb.items():
        if c.get("tier") not in callbacks["tiers"]:
            problems.append(f"{cid}: unknown tier {c.get('tier')!r}")
        if c.get("confidence") not in callbacks["confidence_levels"]:
            problems.append(f"{cid}: unknown confidence {c.get('confidence')!r}")
        if not c.get("sources"):
            problems.append(f"{cid}: has no sources")
        for k in c.get("sources", []):
            if k not in SOURCES:
                problems.append(f"{cid}: unknown source key {k!r}")
        o = c.get("origin") or {}
        n = o.get("episode")
        row = orig_rows.get(n)
        if row is None:
            problems.append(f"{cid}: origin episode {n} not found in the original-series list")
        else:
            if norm_title(o.get("title", "").split(" (")[0]) != norm_title(row["title"].split(" (")[0]):
                problems.append(f"{cid}: origin title {o.get('title')!r} != original list title {row['title']!r} for E{n}")
            if o.get("air_date") and o["air_date"] != norm_date(row["raw_date"]):
                problems.append(f"{cid}: origin air date {o['air_date']!r} != original list {norm_date(row['raw_date'])!r} (E{n})")
        if not c.get("scene_search"):
            problems.append(f"{cid}: no scene_search terms (find_scenes.py needs them)")

    ctx = {x["id"] for x in politics["context"]}
    for p in politics["episodes"]:
        if not 1 <= p["episode"] <= EPISODE_COUNT:
            problems.append(f"politics: bad episode {p['episode']}")
        for item in p["now"]:
            if item.get("context") and item["context"] not in ctx:
                problems.append(f"politics ep{p['episode']}: unknown context id {item['context']!r}")

    have = {x["episode"] for x in politics["episodes"]}
    missing = set(range(1, EPISODE_COUNT + 1)) - have
    if missing:
        problems.append(f"politics: no entry for episodes {sorted(missing)}")

    if len(starter["episodes"]) != 12:
        problems.append(f"starter path should have 12 entries, has {len(starter['episodes'])}")
    for s in starter["episodes"]:
        row = orig_rows.get(s["episode"])
        if not row or row["title"].strip() != s["title"].strip():
            problems.append(f"starter path: {s['season']}x{s['episode']} {s['title']!r} does not match the original episode list")

    if not timeline["events"] or not glossary["terms"]:
        problems.append("timeline or glossary is empty")
    for c in characters.get("main", []) + characters.get("special_guest", []) + characters.get("recurring", []):
        if not c.get("name_2026") or not c.get("actor"):
            problems.append(f"character record missing name/actor: {c}")
    return problems


# ----------------------------------------------------------------- page pieces
def head(title: str, desc: str, depth: int = 0) -> str:
    return f"""<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="color-scheme" content="light dark">
<link rel="stylesheet" href="assets/styles.css">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%2310203a'/%3E%3Ctext x='16' y='22' font-size='16' font-family='Georgia' fill='%23b8892b' text-anchor='middle'%3EDW%3C/text%3E%3C/svg%3E">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="masthead">
  <div class="wrap">
    <a class="brand" href="index.html">Origin<span>Notes</span> · A Different World</a>
    <nav>
      <a href="index.html#episodes">Episodes</a>
      <a href="index.html#callbacks">Callback index</a>
      <a href="index.html#who">Who's who</a>
      <a href="index.html#starter">Start the original</a>
      <a href="index.html#timeline">Timeline</a>
      <a href="index.html#method">Method</a>
    </nav>
    <div class="tools">
      <button class="toggle" data-action="toggle-spoilers" aria-pressed="false">Original series spoilers: hidden</button>
      <button class="toggle" data-action="toggle-theme">☾ Dark</button>
    </div>
  </div>
</header>
<main id="main">
"""


FOOT = """</main>
<footer class="site">
  <div class="wrap narrow">
    <h2>Sources &amp; method</h2>
    <p>Every fact on this page is drawn from published records, not from memory and not from a
    transcript we do not have. The 2026 episode table, cast and reception come from Wikipedia's
    article on the series; the original's episode numbers, titles, air dates and story summaries
    come from Wikipedia's episode list; the title IDs were confirmed through IMDb's suggestion API.
    Air dates for the original match the episode list to the day.</p>
    <ul>
      <li>Wikipedia — <a href="https://en.wikipedia.org/wiki/A_Different_World_(2026_TV_series)" rel="noopener">A Different World (2026 TV series)</a></li>
      <li>Wikipedia — <a href="https://en.wikipedia.org/wiki/List_of_A_Different_World_episodes" rel="noopener">List of A Different World episodes</a> (1987–1993)</li>
      <li>Wikipedia — <a href="https://en.wikipedia.org/wiki/A_Different_World" rel="noopener">A Different World</a> (1987 series) and <a href="https://en.wikipedia.org/wiki/The_Cosby_Show" rel="noopener">The Cosby Show</a></li>
      <li>IMDb — <a href="https://www.imdb.com/title/tt33081352/" rel="noopener">tt33081352</a> (2026) · <a href="https://www.imdb.com/title/tt0092339/" rel="noopener">tt0092339</a> (1987)</li>
    </ul>
    <p><b>What we would not do:</b> we do not quote dialogue, we do not invent episode numbers, and we
    do not claim the writers said anything they have not said. Where a callback is our reading rather
    than a documented fact, the card says <i>reading</i> and <i>interpretation</i>. Where we could not
    source something — including where a 2026 episode's politics could not be matched to a citable
    fact — we say so on the page instead of filling the gap with plausible-sounding prose.</p>
    <p class="fine">Fan project. Not affiliated with Netflix, NBC or the rights holders.
    Episode titles, air dates and summaries are referenced for commentary and identification.
    Verified against sources on 2026-10-04. Transcripts, when present, are kept privately and never
    republished whole.</p>
  </div>
</footer>
<script src="assets/app.js" defer></script>
</body>
</html>
"""


def render_callback(c: dict, callbacks: dict) -> str:
    o = c["origin"]
    spoiler_cls = " spoiler" if c.get("spoiler") else ""
    tier = callbacks["tiers"].get(c["tier"], c["tier"])
    badge_tier = f'<span class="badge">{e(c["tier"])}</span>'
    badge_conf = f'<span class="badge {e(c["confidence"])}">{e(c["confidence"])}</span>'
    terms = " ".join(c.get("scene_search", []))
    return f"""<article class="cb" id="{e(c['id'])}" data-callback="{e(c['id'])}" data-tier="{e(c['tier'])}" data-search="{e(c['id'] + ' ' + c['scene_2026'] + ' ' + o.get('title','') + ' ' + terms)}">
  <div class="cb-head">{badge_tier}{badge_conf}</div>
  <dl>
    <dt>What you saw in 2026</dt>
    <dd class="scene">{e(c['scene_2026'])}</dd>
    <dt>Where it comes from</dt>
    <dd class="origin-line{spoiler_cls}"><b>Season {o['season']}, episode {o['episode']} — “{e(o['title'])}”</b> · first aired {e(o['air_date'])}<br>{e(o['what_happened'])}</dd>
    <dt>Why it matters now</dt>
    <dd class="why">{e(o['why_it_matters_now'])}</dd>
  </dl>
  <p class="srcs">Tier: {e(tier)} Sources: {src_links(c['sources'])}<br>
  <span class="srchint">Scene search terms for the transcript scanner: <code>{e(terms)}</code></span></p>
</article>"""


def render_politics(p: dict, politics: dict) -> str:
    ctx = {x["id"]: x for x in politics["context"]}
    now = []
    for item in p["now"]:
        c = ctx.get(item.get("context")) if item.get("context") else None
        if c:
            now.append(f'<li class="politic-item">{e(item["note"])} <span class="srcs">Source: <a href="{e(c["source"])}" rel="noopener">context item “{e(c["id"])}”, verified {e(c["retrieved"])}</a></span></li>')
        else:
            now.append(f'<li class="politic-item">{e(item["note"])} <span class="srcs">No source attached — flagged, not asserted.</span></li>')
    pr = p["precedent"]
    return f"""<details class="panel" id="politics">
  <summary>Politics &amp; the moment<span class="hint">what the show is saying, and what the original said first</span></summary>
  <div class="panel-body">
    <div class="politic-item"><span class="tag">What the episode is about</span>{e(p['statement'])}</div>
    <div class="politic-item"><span class="tag">The original said it first — season {pr['season']}, episode {pr['episode']}: “{e(pr['title'])}” ({e(pr['air_date'])})</span>{e(pr['what'])}</div>
    <div class="politic-item"><span class="tag">What is happening now</span><ul>{''.join(now)}</ul></div>
    <div class="politic-item"><span class="tag">Our reading (interpretation, not fact)</span>{e(p['reading'])}</div>
  </div>
</details>"""


def render_script_panel(ep: dict, transcript: dict | None, candidates: list[dict]) -> str:
    rows = []
    if transcript:
        for cue in transcript["cues"]:
            rows.append(f'<div class="cue"><span class="tc">{e(cue["start"])}</span><span class="cue-text">{e(cue["plain"])}</span></div>')
        toolbar = ('<div class="ts-search"><input id="ts-search" type="search" placeholder="Search this episode\'s transcript…" aria-label="Search transcript">'
                   f'<span class="chip" id="ts-count">{len(transcript["cues"])} lines</span></div>')
        body = toolbar + '<div class="transcript">' + "".join(rows) + "</div>"
        hint = f'{transcript["cue_count"]} lines · {transcript["duration"]}'
    else:
        hint = "no transcript imported yet"
        body = ('<div class="notice"><b>Transcript not imported.</b> This panel is wired and waiting. '
                'For commentary we publish only short attributed excerpts, but if you want the full text '
                'readable locally (or if you decide to publish it), drop the episode\'s subtitle file in '
                '<code>subtitles/</code> and run:<br><br>'
                '<code>python3 scripts/import_subtitles.py</code><br><br>'
                'Accepted: <code>.srt</code>, <code>.vtt</code>, Netflix <code>.ttml</code>/<code>.dfxp</code>/<code>.xml</code>, '
                'or a <code>.json</code> export from the Netflix Subtitle Translator userscript cache. '
                'Name the file <code>ep%02d.*</code>. Then rebuild the pages. '
                'Nothing here claims to have read the episode: the sections that need a transcript say so.</div>' % ep["number"])

    cand_html = ""
    if candidates:
        items = []
        for cand in candidates:
            for scene in cand.get("scenes", [])[:6]:
                items.append(f'<li><code>{e(scene["start"])}–{e(scene["end"])}</code> '
                             f'<b>{e(cand["topic_label"])}</b> — {e(", ".join(scene["terms"][:5]))} '
                             f'<span class="srcs">(score {scene["score"]})</span></li>')
        if items:
            cand_html = ('<h3>Scene candidates the scanner found</h3>'
                         '<p class="section-sub">Output of <code>scripts/find_scenes.py</code> over the imported '
                         'transcript. Timecodes are where the topic language concentrates.</p><ul>' + "".join(items) + "</ul>")

    return f"""<details class="panel" id="script">
  <summary>Full script<span class="hint">{e(hint)}</span></summary>
  <div class="panel-body">
    <p class="section-sub">The episode's full subtitle text, if we have it. Kept collapsed by default,
    and never published wholesale — this is commentary material, and Netflix's subtitle text is theirs.</p>
    {cand_html}
    {body}
  </div>
</details>"""


def render_episode_page(ep, callbacks, politics, transcripts, candidates, episodes) -> str:
    cb_index = {c["id"]: c for c in callbacks["callbacks"]}
    # render in the narrative order declared by episodes.json (not the file order in callbacks.json)
    cbs = [cb_index[cid] for cid in ep["callbacks"] if cid in cb_index]
    pol = next(p for p in politics["episodes"] if p["episode"] == ep["number"])
    prev_ep = next((x for x in episodes["episodes"] if x["number"] == ep["number"] - 1), None)
    next_ep = next((x for x in episodes["episodes"] if x["number"] == ep["number"] + 1), None)

    nav_bits = []
    if prev_ep:
        nav_bits.append(f'<a href="{e(prev_ep["page"])}">← Episode {prev_ep["number"]}: {e(prev_ep["title"])}</a>')
    else:
        nav_bits.append('<a href="index.html">← All episodes</a>')
    if next_ep:
        nav_bits.append(f'<a href="{e(next_ep["page"])}">Episode {next_ep["number"]}: {e(next_ep["title"])} →</a>')
    else:
        nav_bits.append(f'<a href="index.html#callbacks">All {len(callbacks["callbacks"])} callbacks →</a>')

    cards = "\n".join(render_callback(c, callbacks) for c in cbs)
    page_title = f"Episode {ep['number']}: {ep['title']} — A Different World Origin Notes"
    return head(page_title, ep["hook"]) + f"""
<section class="hero">
  <div class="wrap">
    <p class="kicker">Season 1 · Episode {ep['number']} of 10 · released {e(ep['released'])} on Netflix</p>
    <h1>{e(ep['title'])}</h1>
    <p class="lede">{e(ep['hook'])}</p>
    <div class="meta">
      <span class="chip">Directed by {e(ep['director'])}</span>
      <span class="chip">Written by {e(ep['writer'])}</span>
      <span class="chip key">{len(cbs)} documented callbacks</span>
    </div>
  </div>
</section>

<section class="block">
  <div class="wrap">
    <h2 class="section-title">The episode</h2>
    <p class="section-sub">Official summary beats — the basis for every callback below. We did not watch
    this episode to write this page; that is stated honestly and it is why nothing here quotes dialogue.</p>
    <p>{e(ep['beat'])}</p>
  </div>
</section>

<section class="block" id="callbacks">
  <div class="wrap">
    <h2 class="section-title">Callbacks in this episode</h2>
    <p class="section-sub">Each card: the 2026 moment, the exact original episode behind it, and why it
    matters. Badges show the tier and whether the link is verified or our reading.
    <button class="toggle" data-action="expand-all" data-state="closed">Expand all panels</button></p>
    {cards}
  </div>
</section>

<section class="block">
  <div class="wrap">
    <h2 class="section-title">The show's statements</h2>
    <p class="section-sub">Collapsed by default. What this episode argues about the world, what the
    original argued in the same lane, and what is actually happening in Black America now — sourced.</p>
    {render_politics(pol, politics)}
  </div>
</section>

<section class="block">
  <div class="wrap">
    <h2 class="section-title">The script</h2>
    <p class="section-sub">Collapsed by default, at the bottom, where it belongs.</p>
    {render_script_panel(ep, transcripts.get(ep['number']), candidates.get(ep['number'], []))}
  </div>
</section>

<nav class="epnav wrap">{' '.join(nav_bits)}</nav>
""" + FOOT


def render_glossary(glossary: dict) -> str:
    out = []
    for t in glossary["terms"]:
        src = f' <span class="srcs">{e(t["source"])}</span>' if t.get("source") else ""
        out.append(f'<dt>{e(t["term"])}</dt><dd>{e(t["definition"])}{src}</dd>')
    return "".join(out)


def render_index(episodes, callbacks, politics, characters, timeline, glossary, starter, transcripts) -> str:
    ep_cards = []
    for ep in episodes["episodes"]:
        mine = [c for c in callbacks["callbacks"] if c["episode"] == ep["number"]]
        n = len(mine)
        # the card is searchable by everything its episode's callbacks talk about, so
        # "pageant" or "HIV" finds the right episode from the hub
        extra = " ".join(f"{c['scene_2026']} {c['origin']['title']} {' '.join(c.get('scene_search', []))}" for c in mine)
        search = f"{ep['title']} {ep['hook']} {ep['beat']} {ep['director']} {ep['writer']} {extra}"
        ep_cards.append(f"""<a class="ep-card" href="{e(ep['page'])}" data-episode-card data-search="{e(search)}">
  <span class="num">Episode {ep['number']}</span>
  <h3>{e(ep['title'])}</h3>
  <p>{e(ep['hook'])}</p>
  <span class="count">{n} callbacks · dir. {e(ep['director'])}</span>
</a>""")

    rows = []
    tier_order = list(callbacks["tiers"].keys())
    for c in sorted(callbacks["callbacks"], key=lambda x: (x["episode"], tier_order.index(x["tier"]))):
        o = c["origin"]
        search = f"{c['id']} {c['scene_2026']} {o['title']} {c['tier']} {' '.join(c.get('scene_search', []))}"
        rows.append(f"""<tr data-tier="{e(c['tier'])}" data-search="{e(search)}">
  <td><a href="ep{c['episode']:02d}.html#{e(c['id'])}">Ep {c['episode']}</a></td>
  <td>{e(c['scene_2026'][:110])}</td>
  <td>S{o['season']}·E{o['episode']} <b>{e(o['title'])}</b><br><span class="srcs">{e(o['air_date'])}</span></td>
  <td class="tier"><span class="badge">{e(c['tier'])}</span><br><span class="badge {e(c['confidence'])}">{e(c['confidence'])}</span></td>
</tr>""")

    people = []
    for group, label in (("main", "2026 main cast"), ("special_guest", "Special guest stars — returning originals"), ("recurring", "Recurring")):
        people.append(f"<h3>{e(label)}</h3>")
        for c in characters.get(group, []):
            orig = f' — <b>{e(c["name_original"])}</b> ({e(c["years_original"])})' if c.get("name_original") else ""
            people.append(f'<dt>{e(c["name_2026"])} <span class="srcs">played by {e(c["actor"])}, {e(c["role_2026"])}</span>{orig}</dt><dd>{e(c.get("note",""))}</dd>')

    starter_items = []
    for i, s in enumerate(starter["episodes"], 1):
        illum = " ".join(f'<a href="ep{n:02d}.html">episode {n}</a>' for n in s["illuminates"])
        starter_items.append(f"""<li><b>{e(s['title'])}</b> <span class="srcs">— season {s['season']}, episode {s['episode']}, aired {e(s['air_date'])}</span>
      <p>{e(s['why'])}</p><span class="ep-ref">Explains: {illum}</span></li>""")

    tl_items = "".join(f'<li><time datetime="{e(ev["date"])}">{e(ev["date"])}</time><div><b>{e(ev["label"])}</b><br>{e(ev["note"])} <span class="srcs"><a href="{e(ev["source"])}" rel="noopener">{e(ev["source_label"])}</a></span></div></li>' for ev in timeline["events"])
    gl_items = render_glossary(glossary)
    ctx_items = "".join(f'<li><b>{e(c["id"])}</b> — {e(c["note"])} <span class="srcs"><a href="{e(c["source"])}" rel="noopener">source</a>, retrieved {e(c["retrieved"])}</span></li>' for c in politics["context"])
    tier_items = "".join(f'<li><b>{e(k)}</b> — {e(v)}</li>' for k, v in callbacks["tiers"].items())
    conf_items = "".join(f'<li><b>{e(k)}</b> — {e(v)}</li>' for k, v in callbacks["confidence_levels"].items())

    return head("A Different World (2026) — Origin Notes: every callback, and where it comes from",
                "A fan-made guide to the 2026 Netflix revival that shows new viewers the exact 1987–1993 origin of each callback, and why it matters now.") + f"""
<section class="hero">
  <div class="wrap">
    <p class="kicker">Netflix 2026 · 10 episodes · renewed for season 2</p>
    <h1>Every callback in the new <i>A Different World</i>, with the 1987 episode it comes from.</h1>
    <p class="lede">You just binged the revival. This is the other end of the joke: what each nod points
    back to in the original series, what that episode actually did, and why it still matters in 2026 —
    sorted episode by episode, with the receipts.</p>
    <div class="meta">
      <span class="chip key">Premiered 24 Sep 2026 — 39 years to the day after 24 Sep 1987</span>
      <span class="chip">{len(callbacks['callbacks'])} documented callbacks</span>
      <span class="chip">10 episode pages</span>
      <span class="chip">Every claim sourced</span>
    </div>
  </div>
</section>

<section class="block">
  <div class="wrap narrow">
    <h2 class="section-title">Read this first (60 seconds)</h2>
    <p><b>Hillman College</b> is fictional — a historically Black college in Virginia, introduced on
    <i>The Cosby Show</i> and then given its own show in 1987. From 1987 to 1993, <i>A Different World</i>
    ran six seasons and 144 episodes from inside one dorm and one campus: dorm rooms, a campus radio
    station, a pageant, a step squad, a student sit-in, an HIV diagnosis, the LA uprising. It was a
    sitcom that kept deciding that its audience could handle the real thing.</p>
    <p>In 2026 Netflix brought it back for ten episodes, centred on Deborah Wayne — the daughter of
    Whitley Gilbert and Dwayne Wayne, the couple the original re-centred on after its first lead left.
    The revival premiered on the original's exact birthday, 39 years on, and the writers spent the
    season quoting their own inheritance. This site is the decoder ring.</p>
    <p class="section-sub">Not affiliated with anyone. No dialogue quoted. Nothing invented — if a claim
    is our interpretation it is labelled <i>reading</i>, and if we could not source something we say so.</p>
  </div>
</section>

<section class="block" id="episodes">
  <div class="wrap">
    <h2 class="section-title">The 10 episodes</h2>
    <p class="section-sub">One page per episode: callbacks, the show's political and social statements
    (collapsed), and the script (collapsed, bottom). Filter if you're looking for something.</p>
    <div class="filters"><input id="episode-filter" type="search" placeholder="Filter episodes — title, beat, actor, topic…" aria-label="Filter episodes"></div>
    <div class="grid">{''.join(ep_cards)}</div>
  </div>
</section>

<section class="block" id="who">
  <div class="wrap">
    <h2 class="section-title">Who's who — the bridge</h2>
    <p class="section-sub">The revival's cast list is the argument: the generation that ran the original's
    fights is still on campus, and one of them is a congresswoman.</p>
    <dl>{''.join(people)}</dl>
    <h3>Off screen, and load-bearing</h3>
    <p>{e(characters.get('offscreen',{}).get('denise_huxtable',''))}</p>
  </div>
</section>

<section class="block" id="callbacks">
  <div class="wrap">
    <h2 class="section-title">Callback index</h2>
    <p class="section-sub">All {len(callbacks['callbacks'])} callbacks across the season. Filter by keyword
    or tier. Every row links to the card, which carries the source.</p>
    <div class="filters">
      <input id="cb-filter-text" type="search" placeholder="Filter — e.g. pageant, budget, Freddie, HIV…" aria-label="Filter callbacks">
      <select id="cb-filter-tier" aria-label="Filter by tier">
        <option value="">All tiers</option>
        {''.join(f'<option value="{e(k)}">{e(k)}</option>' for k in callbacks['tiers'])}
      </select>
      <span class="chip" id="cb-filter-status"></span>
    </div>
    <div class="table-scroll">
      <table id="callback-table">
        <thead><tr><th>2026</th><th>What you saw</th><th>Where it comes from</th><th>Tier</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
  </div>
</section>

<section class="block" id="starter">
  <div class="wrap narrow">
    <h2 class="section-title">Never seen the original? Watch these 12.</h2>
    <p class="section-sub">{e(starter['disclaimer'])} Ordered by what they explain about the 2026 season,
    not by broadcast order.</p>
    <ol class="path-list">{''.join(starter_items)}</ol>
  </div>
</section>

<section class="block" id="timeline">
  <div class="wrap">
    <h2 class="section-title">1984 → 2026</h2>
    <p class="section-sub">The chain, with the source for each date.</p>
    <ul class="tl">{tl_items}</ul>
  </div>
</section>

<section class="block" id="glossary">
  <div class="wrap narrow">
    <h2 class="section-title">Glossary</h2>
    <dl class="glossary">{gl_items}</dl>
  </div>
</section>

<section class="block" id="method">
  <div class="wrap">
    <h2 class="section-title">Method, tiers, and what we refuse to do</h2>
    <p class="section-sub">This is the part that makes the rest usable. Read it before quoting the page.</p>
    <p>{e(callbacks.get('method_note',''))}</p>
    <h3>Tiers</h3><ul>{tier_items}</ul>
    <h3>Confidence</h3><ul>{conf_items}</ul>
    <h3>Where “what's happening now” comes from</h3>
    <ul>{ctx_items}</ul>
    <h3>The pipeline (so you can check or rebuild)</h3>
    <ul>
      <li><code>python3 scripts/research_context.py</code> — re-pulls the cited context items above</li>
      <li><code>python3 scripts/import_subtitles.py</code> — normalises any subtitle file into a transcript</li>
      <li><code>python3 scripts/find_scenes.py --all --out data/candidates</code> — finds the scenes that matter in a transcript</li>
      <li><code>python3 scripts/build_pages.py</code> — rebuilds every page from the JSON</li>
      <li><code>python3 scripts/verify_pages.py &amp;&amp; node scripts/verify_pages.mjs</code> — the machine checks</li>
    </ul>
  </div>
</section>
""" + FOOT


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate data only")
    args = ap.parse_args()

    episodes = load("episodes.json")
    callbacks = load("callbacks.json")
    politics = load("politics.json")
    characters = load("characters.json")
    timeline = load("timeline.json")
    glossary = load("glossary.json")
    starter = load("starter-path.json")

    # the original-series list is the authority for every origin citation
    orig = json.loads((ROOT / "research/raw/original-episodes.json").read_text())
    orig_rows = {}
    for r in orig:
        m = re.search(r"\d+", str(r.get("ep", "")))
        if m:
            orig_rows[int(m.group(0))] = {"title": r["title"], "raw_date": r["date"], "season": r["season"]}

    problems = check_data(episodes, callbacks, politics, characters, timeline, glossary, starter, orig_rows)
    if problems:
        print(f"DATA PROBLEMS ({len(problems)}):")
        for p in problems:
            print("  ✗", p)
        return 1
    print(f"data OK: {len(episodes['episodes'])} episodes · {len(callbacks['callbacks'])} callbacks · "
          f"{len(politics['episodes'])} politics sections · {len(characters.get('recurring',[])) + len(characters['main']) + len(characters['special_guest'])} cast rows")
    if args.check:
        return 0

    # optional transcript + scene-candidate inputs
    transcripts = {}
    for n in range(1, EPISODE_COUNT + 1):
        f = DATA / "scripts" / f"ep{n:02d}.json"
        if f.exists():
            transcripts[n] = json.loads(f.read_text())
    candidates = {}
    cdir = DATA / "candidates"
    if cdir.exists():
        for f in sorted(cdir.glob("ep*-*.json")):
            m = re.match(r"ep(\d+)-", f.name)
            if m:
                candidates.setdefault(int(m.group(1)), []).append(json.loads(f.read_text()))

    (ROOT / "index.html").write_text(render_index(episodes, callbacks, politics, characters, timeline, glossary, starter, transcripts))
    for ep in episodes["episodes"]:
        (ROOT / ep["page"]).write_text(render_episode_page(ep, callbacks, politics, transcripts, candidates, episodes))
    print(f"built index.html + {len(episodes['episodes'])} episode pages"
          + (f" (transcripts: {sorted(transcripts)})" if transcripts else " (no transcripts imported yet)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
