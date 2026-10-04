#!/usr/bin/env python3
"""make_art.py — generate every image the V2 (Netflix-style) pages need, as SVG.

Why generated art rather than scraped stills: we cannot lawfully redistribute Netflix's or IMDb's
key art, and we have no stills of our own. So we draw the artwork — cinematic dark backdrops,
episode "stills" with a motif per episode, cast tiles, and an original-era strip. Nothing here is
anyone else's image, so nothing here needs a licence note.

The one exception is the show's poster, which the V2 billboard *hotlinks* from IMDb's CDN (not
committed, not redistributed) with generated art layered behind it as the fallback. Switched off or
on in data/v2.json -> "poster_hotlink".

Outputs to assets/art/ :
    hero.svg                    billboard backdrop (2560x1440)
    ep01.svg … ep10.svg         episode stills (1280x720)
    cast-<slug>.svg             cast tiles (600x600)
    orig01.svg … orig12.svg     the original era (1280x720)
    politics.svg               row backdrop for the politics shelf (1280x720)
    logo.svg                    the site mark
Then assets/art/manifest.json records every file with its size + what drew it.

Usage:  python3 scripts/make_art.py [--force]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import textwrap

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "art"
DATA = ROOT / "data"

# Netflix-ish palette plus this project's gold
BG0, BG1, BG2 = "#0b0b0d", "#141418", "#1d1d23"
RED = "#e50914"
GOLD = "#c9a227"
PAPER = "#f5f2ea"
MUTE = "#9a958c"

# One motif per 2026 episode, drawn from what the episode is actually about.
MOTIFS = {
    1: "columns",     # Hillman / Gilbert Hall
    2: "tower",       # campus radio, the student's voice
    3: "beats",       # homecoming stepping
    4: "rings",       # cuffing season, interlocked
    5: "clock",       # finals, then the crisis
    6: "moon",        # insomnia, the night out
    7: "crown",       # Miss Gilbert Hall
    8: "storm",       # tornado warning
    9: "ledger",      # the budget crisis
    10: "frame",      # the gala / a gift & a curse
}


def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def svg_open(w: int, h: int, extra_defs: str = "") -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0.35" y2="1">
    <stop offset="0%" stop-color="{BG2}"/><stop offset="55%" stop-color="{BG1}"/><stop offset="100%" stop-color="{BG0}"/>
  </linearGradient>
  <linearGradient id="scrim" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="{BG0}" stop-opacity="0.96"/><stop offset="62%" stop-color="{BG0}" stop-opacity="0.45"/><stop offset="100%" stop-color="{BG0}" stop-opacity="0.05"/>
  </linearGradient>
  <linearGradient id="foot" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{BG0}" stop-opacity="0"/><stop offset="100%" stop-color="{BG0}" stop-opacity="0.92"/>
  </linearGradient>
  <radialGradient id="glow" cx="0.72" cy="0.28" r="0.75">
    <stop offset="0%" stop-color="{GOLD}" stop-opacity="0.30"/><stop offset="60%" stop-color="{RED}" stop-opacity="0.06"/><stop offset="100%" stop-color="{BG0}" stop-opacity="0"/>
  </radialGradient>
  {extra_defs}
</defs>
<rect width="{w}" height="{h}" fill="url(#sky)"/>
"""


def motif(kind: str, w: int, h: int, dim: str = "#2a2a33") -> str:
    """Simple geometric glyphs — abstract, never a fake still of real footage."""
    cx, cy = w * 0.68, h * 0.46
    if kind == "columns":
        bars = "".join(
            f'<rect x="{cx - 210 + i * 62}" y="{cy - 210}" width="34" height="330" rx="3" fill="{dim}"/>'
            f'<rect x="{cx - 226 + i * 62}" y="{cy - 236}" width="66" height="22" rx="3" fill="{dim}"/>'
            f'<rect x="{cx - 226 + i * 62}" y="{cy + 100}" width="66" height="22" rx="3" fill="{dim}"/>'
            for i in range(7))
        return bars + f'<path d="M{cx - 250} {cy - 250} L {cx + 210} {cy - 250} L {cx + 250} {cy - 280} L {cx - 290} {cy - 280} Z" fill="{dim}"/>'
    if kind == "tower":
        return (f'<path d="M{cx} {cy + 180} L {cx - 16} {cy - 150} L {cx + 16} {cy - 150} Z" fill="{dim}"/>'
                f'<path d="M{cx - 90} {cy - 150} L {cx + 90} {cy - 150} L {cx + 46} {cy - 210} L {cx - 46} {cy - 210} Z" fill="{dim}"/>'
                + "".join(f'<circle cx="{cx + r[0]}" cy="{cy - 236}" r="{r[1]}" fill="none" stroke="{dim}" stroke-width="4" opacity="{0.75 - i * 0.16}"/>'
                          for i, r in enumerate([(0, 46), (0, 86), (0, 128), (0, 172)])))
    if kind == "beats":
        return "".join(f'<rect x="{cx - 200 + i * 46}" y="{cy - (26 + (i * 37) % 120)}" width="24" height="{52 + (i * 37) % 120}" rx="10" fill="{dim}" opacity="{0.55 + 0.05 * (i % 6)}"/>' for i in range(10))
    if kind == "rings":
        return "".join(f'<circle cx="{cx - 60 + i * 118}" cy="{cy}" r="{86 - i * 8}" fill="none" stroke="{dim}" stroke-width="18"/>' for i in range(3))
    if kind == "clock":
        return (f'<circle cx="{cx}" cy="{cy}" r="150" fill="none" stroke="{dim}" stroke-width="18"/>'
                f'<path d="M{cx} {cy} L {cx} {cy - 96}" stroke="{dim}" stroke-width="16" stroke-linecap="round"/>'
                f'<path d="M{cx} {cy} L {cx + 74} {cy + 44}" stroke="{red_soft()}" stroke-width="14" stroke-linecap="round"/>'
                + "".join(f'<circle cx="{cx + 150 * __import__("math").cos(a)}" cy="{cy + 150 * __import__("math").sin(a)}" r="9" fill="{dim}"/>'
                          for a in [i * 1.5708 for i in range(4)]))
    if kind == "moon":
        return (f'<circle cx="{cx}" cy="{cy}" r="132" fill="{dim}"/>'
                f'<circle cx="{cx + 54}" cy="{cy - 34}" r="132" fill="{BG1}"/>'
                + "".join(f'<circle cx="{cx - 250 + i * 84}" cy="{cy + 200 - (i % 3) * 44}" r="5" fill="{MUTE}" opacity="0.7"/>' for i in range(7)))
    if kind == "crown":
        return (f'<path d="M{cx - 180} {cy + 96} L {cx - 200} {cy - 96} L {cx - 74} {cy - 6} L {cx} {cy - 140} L {cx + 74} {cy - 6} L {cx + 200} {cy - 96} L {cx + 180} {cy + 96} Z" fill="{dim}"/>'
                f'<rect x="{cx - 186}" y="{cy + 104}" width="372" height="30" rx="8" fill="{GOLD}" opacity="0.55"/>')
    if kind == "storm":
        return "".join(f'<path d="M{cx} {cy} Q {cx + 120} {cy - 120} {cx} {cy - 220} Q {cx - 120} {cy - 320} {cx} {cy - 400}" fill="none" stroke="{dim}" stroke-width="16" stroke-linecap="round" transform="rotate({i * 120} {cx} {cy})"/>' for i in range(3)) + f'<circle cx="{cx}" cy="{cy}" r="26" fill="{GOLD}" opacity="0.7"/>'
    if kind == "ledger":
        return ("".join(f'<rect x="{cx - 210}" y="{cy - 170 + i * 52}" width="{330 - i * 26}" height="26" rx="6" fill="{dim}"/>' for i in range(7))
                + f'<path d="M{cx - 250} {cy + 210} L {cx + 120} {cy - 60} L {cx + 190} {cy + 210}" fill="none" stroke="{RED}" stroke-width="12" opacity="0.55"/>')
    if kind == "frame":
        return (f'<rect x="{cx - 220}" y="{cy - 150}" width="440" height="300" rx="10" fill="none" stroke="{dim}" stroke-width="22"/>'
                f'<rect x="{cx - 168}" y="{cy - 104}" width="336" height="208" rx="6" fill="{dim}" opacity="0.35"/>'
                f'<circle cx="{cx}" cy="{cy}" r="46" fill="{GOLD}" opacity="0.6"/>')
    return f'<circle cx="{cx}" cy="{cy}" r="120" fill="{dim}"/>'


def red_soft() -> str:
    return "#8f2b22"


def wrap(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width=width)[:3]


def hero(title: str, kicker: str, sub: str) -> str:
    w, h = 2560, 1440
    s = svg_open(w, h)
    s += f'<rect width="{w}" height="{h}" fill="url(#glow)"/>'
    s += motif("columns", w, h, "#23232c")
    s += f'<rect width="{w}" height="{h}" fill="url(#scrim)"/>'
    s += f'<rect x="0" y="{h - 560}" width="{w}" height="560" fill="url(#foot)"/>'
    s += f'<text x="170" y="330" fill="{RED}" font-family="Helvetica,Arial,sans-serif" font-size="34" letter-spacing="14" font-weight="700">{esc(kicker)}</text>'
    lines = wrap(title, 16)
    for i, line in enumerate(lines):
        s += f'<text x="164" y="{470 + i * 118}" fill="{PAPER}" font-family="Georgia,serif" font-size="104" font-weight="700">{esc(line)}</text>'
    for i, line in enumerate(wrap(sub, 62)[:2]):
        s += f'<text x="170" y="{500 + len(lines) * 118 + i * 42}" fill="{MUTE}" font-family="Helvetica,Arial,sans-serif" font-size="30">{esc(line)}</text>'
    s += f'<rect x="170" y="{300}" width="120" height="6" fill="{GOLD}"/>'
    return s + "</svg>\n"


def episode_still(ep: dict, total: int) -> str:
    w, h = 1280, 720
    kind = MOTIFS.get(ep["number"], "columns")
    s = svg_open(w, h)
    s += f'<rect width="{w}" height="{h}" fill="url(#glow)"/>'
    s += motif(kind, w, h, "#2b2b35")
    s += f'<rect width="{w}" height="{h}" fill="url(#scrim)"/>'
    s += f'<rect x="0" y="{h - 300}" width="{w}" height="300" fill="url(#foot)"/>'
    s += (f'<text x="72" y="470" fill="{GOLD}" font-family="Helvetica,Arial,sans-serif" font-size="26" letter-spacing="7" font-weight="700">'
          f'EPISODE {ep["number"]} OF {total}</text>')
    for i, line in enumerate(wrap(ep["title"], 26)):
        s += f'<text x="68" y="{545 + i * 62}" fill="{PAPER}" font-family="Georgia,serif" font-size="56" font-weight="700">{esc(line)}</text>'
    s += f'<text x="72" y="{h - 42}" fill="{MUTE}" font-family="Helvetica,Arial,sans-serif" font-size="24">dir. {esc(ep["director"])}  ·  written by {esc(ep["writer"])}</text>'
    return s + "</svg>\n"


def cast_tile(person: dict) -> str:
    w = h = 600
    initials = "".join(p[0] for p in re.split(r"[\s\-]+", person["name_2026"]) if p)[:2].upper()
    returning = bool(person.get("name_original"))
    s = svg_open(w, h)
    s += f'<rect width="{w}" height="{h}" fill="url(#glow)"/>'
    s += f'<circle cx="{w//2}" cy="{h*0.42:.0f}" r="150" fill="#22222b"/>'
    s += f'<text x="{w//2}" y="{h*0.47:.0f}" fill="{PAPER}" font-family="Georgia,serif" font-size="130" font-weight="700" text-anchor="middle">{esc(initials)}</text>'
    s += f'<rect x="0" y="{h-190}" width="{w}" height="190" fill="url(#foot)"/>'
    for i, line in enumerate(wrap(person["name_2026"], 18)):
        s += f'<text x="40" y="{h-118 + i*44}" fill="{PAPER}" font-family="Georgia,serif" font-size="40" font-weight="700">{esc(line)}</text>'
    s += (f'<text x="40" y="{h-40}" fill="{MUTE}" font-family="Helvetica,Arial,sans-serif" font-size="26">{esc(person["actor"])}</text>')
    if returning:
        s += f'<rect x="{w-134}" y="28" width="106" height="40" rx="6" fill="{GOLD}"/><text x="{w-81}" y="56" fill="{BG0}" font-family="Helvetica,Arial,sans-serif" font-size="20" font-weight="700" text-anchor="middle">1987</text>'
    return s + "</svg>\n"


def original_still(n: int, item: dict) -> str:
    w, h = 1280, 720
    s = svg_open(w, h)
    s += f'<rect width="{w}" height="{h}" fill="url(#glow)"/>'
    s += motif(["columns", "tower", "beats", "rings", "clock", "moon", "crown", "storm", "ledger", "frame", "columns", "beats"][(n - 1) % 12], w, h, "#26262e")
    s += f'<rect width="{w}" height="{h}" fill="url(#scrim)"/>'
    s += f'<rect x="0" y="{h-280}" width="{w}" height="280" fill="url(#foot)"/>'
    s += f'<text x="72" y="452" fill="{GOLD}" font-family="Helvetica,Arial,sans-serif" font-size="24" letter-spacing="6" font-weight="700">ORIGINAL · S{item["season"]}E{item["episode"]} · {esc(item["air_date"])}</text>'
    for i, line in enumerate(wrap(item["title"], 28)):
        s += f'<text x="68" y="{516 + i * 56}" fill="{PAPER}" font-family="Georgia,serif" font-size="50" font-weight="700">{esc(line)}</text>'
    return s + "</svg>\n"


def politics_backdrop() -> str:
    w, h = 1280, 720
    s = svg_open(w, h)
    s += f'<rect width="{w}" height="{h}" fill="url(#glow)"/>'
    s += motif("ledger", w, h, "#2a2a33") + motif("crown", int(w * 0.6), h, "#26262f")
    s += f'<rect width="{w}" height="{h}" fill="url(#scrim)"/>'
    s += f'<text x="72" y="470" fill="{RED}" font-family="Helvetica,Arial,sans-serif" font-size="28" letter-spacing="8" font-weight="700">POLITICS &amp; THE MOMENT</text>'
    s += f'<text x="68" y="560" fill="{PAPER}" font-family="Georgia,serif" font-size="56" font-weight="700">What the show is saying</text>'
    return s + "</svg>\n"


def logo() -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512" role="img">'
            f'<rect width="512" height="512" rx="96" fill="{BG0}"/>'
            f'<rect x="64" y="150" width="384" height="12" rx="6" fill="{GOLD}"/>'
            f'<text x="256" y="330" fill="{PAPER}" font-family="Georgia,serif" font-size="150" font-weight="700" text-anchor="middle">DW</text>'
            f'<text x="256" y="400" fill="{RED}" font-family="Helvetica,Arial,sans-serif" font-size="38" letter-spacing="8" text-anchor="middle" font-weight="700">ORIGIN NOTES</text>'
            f'</svg>\n')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="redraw even if the files exist")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    episodes = json.loads((DATA / "episodes.json").read_text())
    characters = json.loads((DATA / "characters.json").read_text())
    starter = json.loads((DATA / "starter-path.json").read_text())
    manifest: dict[str, dict] = {}

    def write(name: str, content: str) -> None:
        p = OUT / name
        if args.force or not p.exists():
            p.write_text(content)
        manifest[name] = {"bytes": p.stat().st_size, "kind": "svg",
                          "generated_by": "scripts/make_art.py", "source": "original artwork"}

    write("hero.svg", hero("A Different World", "ORIGIN NOTES · 2026", "Every callback in the Netflix revival, with the 1987 episode it comes from."))
    total = len(episodes["episodes"])
    for ep in episodes["episodes"]:
        write(f"ep{ep['number']:02d}.svg", episode_still(ep, total))
    for person in characters["main"] + characters["special_guest"]:
        slug = re.sub(r"[^a-z0-9]+", "-", person["name_2026"].lower()).strip("-")
        write(f"cast-{slug}.svg", cast_tile(person))
    for i, item in enumerate(starter["episodes"], 1):
        write(f"orig{i:02d}.svg", original_still(i, item))
    write("politics.svg", politics_backdrop())
    write("logo.svg", logo())

    (OUT / "manifest.json").write_text(json.dumps(
        {"about": "All artwork on this site is generated by scripts/make_art.py — original SVG, no third-party images.",
         "count": len(manifest), "files": manifest}, indent=1))
    print(f"wrote {len(manifest)} SVG files + manifest.json to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
