/* A Different World — Origin Notes
   Progressive enhancement only: every page is complete static HTML without this file.
   This adds: theme switch, "I've seen the original" spoiler switch, the callback-index
   filters, the transcript search, and anchor highlighting. */

(function () {
  "use strict";
  const root = document.documentElement;
  const KEY = "dw-origin-notes";

  function store(patch) {
    try {
      const cur = JSON.parse(localStorage.getItem(KEY) || "{}");
      localStorage.setItem(KEY, JSON.stringify(Object.assign(cur, patch)));
    } catch (e) { /* private mode: settings just don't persist */ }
  }
  function load() {
    try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { return {}; }
  }

  /* ---------- theme ---------- */
  const saved = load();
  if (saved.theme) root.setAttribute("data-theme", saved.theme);
  else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    root.setAttribute("data-theme", "dark");
  }

  /* ---------- spoilers ---------- */
  if (saved.seenOriginal) root.classList.add("seen-original");

  document.addEventListener("click", function (ev) {
    const el = ev.target.closest("[data-action]");
    if (!el) return;
    const action = el.getAttribute("data-action");

    if (action === "toggle-theme") {
      const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      store({ theme: next });
      document.querySelectorAll('[data-action="toggle-theme"]').forEach(function (b) {
        b.textContent = next === "dark" ? "☀︎ Light" : "☾ Dark";
      });
    }

    if (action === "toggle-spoilers") {
      const on = root.classList.toggle("seen-original");
      store({ seenOriginal: on });
      syncSpoilerButtons();
    }

    if (action === "expand-all") {
      const open = el.getAttribute("data-state") !== "open";
      document.querySelectorAll("details.panel").forEach(function (d) { d.open = open; });
      el.setAttribute("data-state", open ? "open" : "closed");
      el.textContent = open ? "Collapse all" : "Expand all";
    }
  });

  function syncSpoilerButtons() {
    const on = root.classList.contains("seen-original");
    document.querySelectorAll('[data-action="toggle-spoilers"]').forEach(function (b) {
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.textContent = on ? "✓ Original series spoilers: shown" : "Original series spoilers: hidden";
    });
    document.querySelectorAll('a[data-action="toggle-theme"], button[data-action="toggle-theme"]').forEach(function (b) {
      b.textContent = root.getAttribute("data-theme") === "dark" ? "☀︎ Light" : "☾ Dark";
    });
  }

  /* ---------- episode filter on the hub ---------- */
  const epFilter = document.getElementById("episode-filter");
  if (epFilter) {
    const cards = Array.prototype.slice.call(document.querySelectorAll("[data-episode-card]"));
    epFilter.addEventListener("input", function () {
      const q = epFilter.value.trim().toLowerCase();
      cards.forEach(function (c) {
        const hay = (c.getAttribute("data-search") || "").toLowerCase();
        c.style.display = (!q || hay.indexOf(q) !== -1) ? "" : "none";
      });
    });
  }

  /* ---------- callback index table ---------- */
  const cbTable = document.getElementById("callback-table");
  if (cbTable) {
    const rows = Array.prototype.slice.call(cbTable.querySelectorAll("tbody tr"));
    const text = document.getElementById("cb-filter-text");
    const tier = document.getElementById("cb-filter-tier");
    const status = document.getElementById("cb-filter-status");
    function apply() {
      const q = (text && text.value || "").trim().toLowerCase();
      const t = (tier && tier.value) || "";
      let shown = 0;
      rows.forEach(function (r) {
        const hay = (r.getAttribute("data-search") || "").toLowerCase();
        const ok = (!q || hay.indexOf(q) !== -1) && (!t || r.getAttribute("data-tier") === t);
        r.style.display = ok ? "" : "none";
        if (ok) shown++;
      });
      if (status) status.textContent = shown + " of " + rows.length + " shown";
    }
    if (text) text.addEventListener("input", apply);
    if (tier) tier.addEventListener("change", apply);
    apply();
  }

  /* ---------- transcript search ---------- */
  const tsSearch = document.getElementById("ts-search");
  if (tsSearch) {
    const cues = Array.prototype.slice.call(document.querySelectorAll(".transcript .cue"));
    const count = document.getElementById("ts-count");
    const raw = cues.map(function (c) { return c.querySelector(".cue-text").textContent; });
    tsSearch.addEventListener("input", function () {
      const q = tsSearch.value.trim().toLowerCase();
      let hits = 0;
      cues.forEach(function (c, i) {
        const target = c.querySelector(".cue-text");
        if (!q) { target.innerHTML = escapeHtml(raw[i]); c.style.display = ""; return; }
        const idx = raw[i].toLowerCase().indexOf(q);
        if (idx === -1) { c.style.display = "none"; return; }
        hits++;
        c.style.display = "";
        target.innerHTML = escapeHtml(raw[i].slice(0, idx)) + "<mark>" +
          escapeHtml(raw[i].slice(idx, idx + q.length)) + "</mark>" + escapeHtml(raw[i].slice(idx + q.length));
      });
      if (count) count.textContent = q ? hits + " matching lines" : cues.length + " lines";
    });
  }
  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, function (ch) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch];
    });
  }

  /* ---------- highlight a deep-linked callback ---------- */
  if (location.hash) {
    const t = document.getElementById(location.hash.slice(1));
    if (t) {
      t.style.transition = "box-shadow .4s ease";
      t.style.boxShadow = "0 0 0 3px var(--gold)";
      setTimeout(function () { t.style.boxShadow = ""; }, 2200);
    }
  }

  syncSpoilerButtons();
})();
