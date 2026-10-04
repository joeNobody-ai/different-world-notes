# A Different World — Origin Notes

A fan page for the 2026 Netflix revival of **A Different World**. It exists to do one thing: for every
callback in the new season, show the exact moment in the **1987–1993 original** it points back to —
and say why it still matters in 2026.

Built to be **checked**, not believed. Every callback carries a tier, a confidence level and a source.
Where a claim is our reading, the page says *reading*. Where we could not source something — including
where a 2026 episode's politics could not be matched to a citable fact — the page says so.

---

## What's here

```
index.html               the hub: episode grid, callback index, who's who, timeline, glossary, method
ep01.html … ep10.html    one page per episode
assets/styles.css        the design (light + dark)
assets/app.js            interactions only — the pages read fine with JavaScript off
data/                    all content as JSON (this is what you edit)
scripts/                 the pipeline (Python, plus one Node verifier)
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

Nothing to install to read the site — open `index.html` in a browser.

To rebuild the pages after editing anything in `data/`:

```bash
python3 scripts/build_pages.py      # regenerates index.html + ep01..ep10.html
```

To check your work before you say it's done (do this; it is the whole point of the project):

```bash
python3 scripts/verify_pages.py     # 175 structural checks — citations, links, panels, tag balance
node scripts/verify_pages.mjs       # 25 behaviour checks in jsdom — filters, switches, collapse
```

Both must pass. `verify_pages.py` is also where the citations are enforced: it refuses to build if a
callback names an original episode whose **title or air date** does not match the original-series
episode list. That check is why this page can be trusted.

---

## The pipeline

| Script | What it does |
|---|---|
| `scripts/research_context.py` | Re-pulls the cited "what's happening now" items from Wikipedia (cached in `research/raw/context/`). |
| `scripts/import_subtitles.py` | Turns any subtitle file into one clean transcript per episode. |
| `scripts/find_scenes.py` | **The scene finder.** Scans a transcript for the things that matter (characters, Hillman lore, political language, sexual-health language, diaspora language, money) and returns ranked scene candidates with timecodes. |
| `scripts/build_pages.py` | Renders every page from `data/`. Also validates the data first (`--check`). |
| `scripts/verify_pages.py` | Structural verification; exits non-zero on any failure. |
| `scripts/verify_pages.mjs` | Behaviour verification in jsdom. |

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
