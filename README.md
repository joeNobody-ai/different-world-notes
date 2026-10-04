# A Different World — Origin Notes

A fan page for the 2026 Netflix revival of **A Different World**. It exists to do one thing: for every
callback in the new season, show the exact moment in the **1987–1993 original** it points back to —
and say why it still matters in 2026.

Built to be **checked**, not believed. Every callback carries a tier, a confidence level and a source.
Where a claim is our reading, the page says *reading*. Where we could not source something — including
where a 2026 episode's politics could not be matched to a citable fact — the page says so.

---

## What's here

Two front ends over one dataset:

```
index.html               V1 — the text version: hub with episode grid, callback index, who's who,
                         timeline, glossary, method
ep01.html … ep10.html    V1 episode pages
v2/index.html            V2 — the Netflix-style browse: billboard + horizontal shelves
v2/ep01.html … ep10.html V2 episode pages: backdrop, callbacks as episode rows, panels
assets/styles.css        V1 skin (light + dark)
assets/app.js            V1 interactions
assets/v2/netflix.css    V2 skin (dark, cinematic, shelf layout)
assets/v2/netflix.js     V2 interactions (shelf scrolling, spoiler pill, expand-all, search)
assets/art/*.svg         35 generated artworks + manifest.json — ours, no licence needed
assets/img/commons/*     freely-licensed campus photos + CREDITS.json (attribution enforced)
data/                    all content as JSON (this is what you edit)
scripts/                 the pipeline (Python, plus two Node verifiers)
research/raw/            the raw sources we pulled, with MANIFEST.md recording the exact requests
vendor/                  the subtitle tool, cloned — not committed (see "The subtitle tool")
subtitles/               drop subtitle files here to get a full script panel (not committed)
```

## The three things on an episode page

1. **Callbacks** — the main content. One card per callback: *what you saw in 2026* → *the exact original
   episode* (season, number, title, air date) → *why it matters now*, plus tier/confidence badges and
   the source links.
2. **Politics & the moment** — collapsed by default. What the episode is about, what the original said
   in the same lane, and what is actually happening in Black America now (each item sourced), plus our
   reading, labelled as a reading.
3. **Full script** — collapsed by default, at the bottom. Renders the episode's subtitle text *if we
   have it*. We do not have any yet (see below), so for now it shows an honest notice instead of a
   pretend transcript.

---

## Quick start

Nothing to install to read either version — open `index.html` (text) or `v2/index.html` (browse).

To rebuild after editing anything in `data/`:

```bash
make build          # = python3 scripts/build_pages.py && python3 scripts/build_v2.py
```

To check your work before you say it's done (do this; it is the whole point of the project):

```bash
make verify         # all four checks
#   python3 scripts/verify_pages.py   — 175 structural checks (V1)
#   node    scripts/verify_pages.mjs  —  25 behaviour checks (V1, jsdom)
#   python3 scripts/verify_v2.py      — 363 structural checks (V2: shelves, ranks, images, credits)
#   node    scripts/verify_v2.mjs     —  26 behaviour checks (V2, jsdom)
bash scripts/check_images.sh          # SVG validity + hotlinked key art still returns 200
```

`verify_pages.py` is also where the citations are enforced: it refuses to build if a callback names an
original episode whose **title or air date** does not match the original-series episode list. That check
is why this page can be trusted.

## V2 — the Netflix-style view

V1 is words. V2 is the same content arranged the way a streaming service arranges it, because that is
the language an audience already knows how to read:

| Shelf | What's on it |
|---|---|
| Billboard | hero backdrop, the 39-years-to-the-day line, ▶ Start with episode 1 |
| Episodes | 10 cards: generated stills, hover-scale, callback count |
| **Top callbacks this season** | the 10 strongest, ranked 1–10 in outlined numerals, each deep-linking to its callback row |
| Who's who | cast tiles; returning originals carry a gold **1987** badge |
| The 1987–1993 era | the 12-episode starter path as a shelf |
| Politics & the moment | 10 cards, one per episode, linking to the collapsed section |
| The real campuses behind Hillman | 6 Commons photos, each with author + licence + link printed |
| Episode pages | backdrop hero + synopsis, then each callback as a Netflix-style episode row (thumbnail, title, "S/E — title · first aired" description, tier badges), then the collapsed politics and script panels, then a next-episode card |

**Where V2's images come from — three sources, deliberately separated:**

1. **Generated** (`assets/art/`, committed). `scripts/make_art.py` draws 35 SVGs: billboard backdrop, a
   still per episode with a motif drawn from what the episode is about (columns for the dorm, radio
   tower for student voice, crown for the pageant, storm for the tornado), cast tiles, the 1987 shelf,
   a politics backdrop, the logo. Ours, so no licence question — and `verify_v2.py` checks every one
   parses as XML.
2. **Commons, credited** (`assets/img/commons/`, committed). `scripts/fetch_commons.py` only accepts
   files whose licence it can read (Public domain / CC0 / CC BY / CC BY-SA / GFDL), downloads them,
   and writes `CREDITS.json`; the page prints author + licence + link under each photo. No licence,
   no photo — the script skips it.
3. **Hotlinked, not redistributed.** The show's key art and the cast headshots come from IMDb's image
   CDN (`m.media-amazon.com`) with `onerror` fallbacks so the generated art shows through if the CDN
   ever refuses. They are never downloaded and never committed. Turn the whole thing off with:

   ```bash
   python3 scripts/build_v2.py --no-poster
   ```

That is the honest version of "put images in it": generate what we own, credit what we borrow, and
never redistribute what we don't.


---

## The pipeline

| Script | What it does |
|---|---|
| `scripts/research_context.py` | Re-pulls the cited "what's happening now" items from Wikipedia (cached in `research/raw/context/`). |
| `scripts/probe_images.py` | Finds which image sources actually work and records them (`research/raw/image_sources.json`). |
| `scripts/make_art.py` | Draws every generated SVG (billboard, episode stills, cast tiles, the 1987 shelf, logo). |
| `scripts/fetch_commons.py` | Downloads only freely-licensed Commons photos, with credits. No licence, no download. |
| `scripts/import_subtitles.py` | Turns any subtitle file into one clean transcript per episode. |
| `scripts/find_scenes.py` | **The scene finder.** Scans a transcript for the things that matter (characters, Hillman lore, political language, sexual-health language, diaspora language, money) and returns ranked scene candidates with timecodes. |
| `scripts/build_pages.py` | Renders V1 from `data/`. Also validates the data first (`--check`). |
| `scripts/build_v2.py` | Renders V2 (the Netflix-style browse) from the same data. `--no-poster` drops the hotlinked key art. |
| `scripts/verify_pages.py` | V1 structural verification; exits non-zero on any failure. |
| `scripts/verify_pages.mjs` | V1 behaviour verification in jsdom. |
| `scripts/verify_v2.py` | V2 structural verification: shelves, ranked numbering, every image resolves or is a declared hotlink, credits are real, SVG validity. |
| `scripts/verify_v2.mjs` | V2 behaviour verification in jsdom. |
| `scripts/check_images.sh` | SVG XML validity + HTTP 200 on every hotlinked image + committed image weight. |
| `scripts/check_live.sh` | Checks the deployed GitHub Pages site (all pages 200, expected counts). |

### The scene finder, concretely

```bash
python3 scripts/find_scenes.py --coverage                    # which episodes have transcripts
python3 scripts/find_scenes.py --topics                      # the vocabulary it knows
python3 scripts/find_scenes.py --episode 7                   # all topics, ranked, episode 7
python3 scripts/find_scenes.py --episode 7 --topic politics
python3 scripts/find_scenes.py --all --out data/candidates   # write JSON for every episode
python3 scripts/find_scenes.py --episode 3 --context 4       # show 4 subtitles either side
```

It matches the vocabulary in `data/scene_queries.json` (edit that file, not the script), clusters
nearby hits into scenes, ranks them, and writes `data/candidates/epNN-<topic>.json`. Those candidates
then appear on the episode page under the script panel, with timecodes — so the "callbacks" can be
pinned to the second once a transcript exists.

---

## Getting the subtitles (the fiddly bit — read this)

**Why we don't have them yet:** Netflix subtitle files come out of a logged-in Netflix session. There
is no honest way to fetch them from a machine without one, the pages are DRM-protected, and this repo
does not ship copyrighted subtitle text.

**The tool that does the work:** [`dariodf/netflix_subtitles_translator`](https://github.com/dariodf/netflix_subtitles_translator) —
a Tampermonkey userscript that intercepts Netflix's TTML subtitle stream in your browser. It is
installed here for development:

```bash
cd vendor && git clone https://github.com/dariodf/netflix_subtitles_translator.git
cd netflix_subtitles_translator && npm install --include=dev
```

> `--include=dev` matters: this box has `omit=dev` set in npm's environment config, so a plain
> `npm install` silently installs nothing (191 packages vs 0). Same flag needed for `jsdom` if you
> install verification deps at the repo root.

**Three routes to a transcript**, easiest first:

1. **Userscript cache export (no file wrangling).** Install the userscript, play an episode with
   subtitles on, then in the browser console:
   ```js
   copy(JSON.stringify(localStorage))
   ```
   Paste that into `subtitles/ep01.json`. The userscript caches the **original** (untranslated) cue
   text per episode, which is exactly what we need. Then:
   ```bash
   python3 scripts/import_subtitles.py
   ```
2. **A subtitle file you already have.** Save it as `subtitles/ep01.srt` / `.vtt` / `.ttml` / `.dfxp`
   (name it `ep01`…`ep10` so the importer knows which episode it is) and run the same command.
3. **The headless CLI in the vendored tool** (`cd vendor/netflix_subtitles_translator && make headless CONFIG=… EPISODE=…`),
   which expects TTML files in its own `episodes-local/`. Useful if you want its translation pipeline;
   overkill if you only want the text.

After importing: `python3 scripts/find_scenes.py --all --out data/candidates`, then
`python3 scripts/build_pages.py`, then both verifiers. The script panels fill themselves in.

**Copyright position:** full transcripts are `.gitignore`d (`data/scripts/`, `data/candidates/`) and are
never published. Locally they are readable; on the site we keep the panel honest and empty until Jason
decides otherwise. Short attributed excerpts inside commentary cards are a different question and are
already how the rest of the page is written.

---

## How to add season 2 (it's designed for this)

1. Re-pull the series data (see `research/raw/MANIFEST.md` for the exact `curl` commands) and add the
   new episodes to `data/episodes.json` (and `EPISODE_COUNT` in `scripts/build_pages.py`).
2. Add their callbacks to `data/callbacks.json` and their entry to `data/politics.json` (the validator
   refuses a callback whose origin episode doesn't match the original list — that's deliberate).
3. `python3 scripts/build_pages.py && python3 scripts/verify_pages.py && node scripts/verify_pages.mjs`.

## House rules (do not break these)

- **No invented callbacks.** A callback is *verified* only if it is a title echo, a returning actor, or a
  documented original episode. Everything else is labelled *interpretation*.
- **No dialogue quotes** unless a transcript exists, and then only briefly and attributed.
- **No claim about a line of dialogue we have not heard.** The pages state plainly that the writer has
  not watched the episodes.
- **No unsourced political assertions.** Unsourced context is flagged on the page as flagged.
- **Never publish a full transcript.**

## Credits & status

Fan project, unaffiliated with Netflix, NBC or the rights holders. Factual content verified against
Wikipedia and IMDb on **2026-10-04**; every source URL is listed on the site's "Sources & method"
section and in `research/raw/MANIFEST.md`.

## Related: the course built on this site

**[Karens-Class](https://github.com/joeNobody-ai/Karens-Class)** — a 15-session upper-division sociology
seminar, *A Different World*: Black Experience and American Society, taught from this site's documented
callback pairs. Each session pairs a 2026 episode with its 1987–1993 counterpart; the homework assigns
this site's callback cards as evidence to be checked. Syllabus, 15 assignments, midterm, final, rubrics
and instructor keys all included.

- Repository: https://github.com/joeNobody-ai/Karens-Class
- Course site: https://joenobody-ai.github.io/Karens-Class/
