# research/raw — MANIFEST

Everything below was pulled **2026-10-04** during planning for the "Origin Notes" fan page.
Nothing here is hand-written: each file is the raw response to the `curl` command listed next to it.
Re-pull at any time with those commands; the parse rules live in `scripts/build-data.py` (Task 2).

| File | What it is | How it was made |
|---|---|---|
| `2026-article.txt` | Full plain-text article for the 2026 Netflix series (premise, cast, production, reception) | `action=query&prop=extracts&explaintext=1&redirects=1&titles=A Different World (2026 TV series)` |
| `2026-article-wikitext.json` | Raw wikitext of that article — the `{{Episode list}}` table with all 10 episodes, directors, writers, airdates, summaries | `action=parse&page=A Different World (2026 TV series)&prop=wikitext` |
| `2026-episodes.json` | The 10 season-1 episodes, parsed from the wikitext above: `ep,title,dir,writer,date,summary` | parsed (see parse note 1) |
| `original-episodes-wikitext.json` / `.txt` | Raw wikitext of `List of A Different World episodes` (all 6 seasons, 1987–1993) | `action=parse&page=List of A Different World episodes&prop=wikitext` |
| `original-episodes.json` | 141 original episodes: `season,ep,title,date,summary` | parsed from the file above (see parse note 2) |
| `original-episode-titles.json` | The bare 141 original titles, used for title-echo matching | derived from the same parse |

### Parse notes (carry these into `build-data.py`)

1. 2026 episodes come from `{{Episode list}}` blocks inside `==Episodes==`; `OriginalAirDate` is a `{{Start date|…}}` template to normalise to `YYYY-MM-DD`.
2. The Wikipedia list yields **141** rows of a stated **144** episodes (three rows use a different template). If a specific missing episode ever matters, reconcile it against that season's article — do not guess a number.
3. Season attribution in `original-episodes.json` comes from the nearest preceding `== Season N (YYYY–YY) ==` heading.
4. Summaries were stripped of wiki markup and wikilinks; they are **short by nature** — they are evidence that an episode exists and what it covers, not enough on their own to write a rich "why it matters now". Supplement from the season articles or from Jason's own rewatch notes.

### Endpoints that do NOT work from this box (don't waste time)

- `https://www.imdb.com/title/...` — bot challenge, returns **HTTP 202** with an empty body.
- `https://html.duckduckgo.com/html/?q=…` — HTTP 202 (blocked).
- `https://www.mojeek.com/search` — HTTP 403 (blocked).
- `web_search` / `web_extract` / cloud browser tools — not configured in this profile.

What **does** work: `https://en.wikipedia.org/w/api.php` (any query) and
`https://v3.sg.media-imdb.com/suggestion/x/<title-or-id>.json` (IMDb's suggestion API — how
`tt33081352` (2026 series) and `tt0092339` (1987 series) were confirmed).

### Licensing note for these snapshots

The Wikipedia material in this folder (article text, wikitext, episode tables) is **CC BY-SA 4.0**.
These are verbatim snapshots kept so that every citation on the site can be re-verified without
re-fetching. Each file is attributed to its source URL above, which is also where the licence and the
full edit history live. Nothing in `data/` copies Wikipedia prose: the site paraphrases, and the raw
snapshots stay here as evidence. IMDb is used only for title identifiers.
