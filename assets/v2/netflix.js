/* V2 browse skin — interaction only. Every page is complete static HTML without this file.
   Adds: wheel-to-horizontal scrolling on shelves, drag-to-scroll, spoiler reveal, expand-all,
   transcript search, and remembering your "I've seen the original" choice. */

(function () {
  "use strict";
  const root = document.documentElement;
  const KEY = "dw-origin-notes-v2";

  function store(patch) {
    try { localStorage.setItem(KEY, JSON.stringify(Object.assign(load(), patch))); } catch (e) {}
  }
  function load() { try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { return {}; } }

  if (load().seenOriginal) root.classList.add("seen-original");

  function syncPills() {
    const on = root.classList.contains("seen-original");
    document.querySelectorAll('[data-action="toggle-spoilers"]').forEach(function (b) {
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.textContent = on ? "Spoilers shown" : "Reveal spoilers";
    });
  }

  /* ---- shelves: wheel scrolls sideways, drag scrolls, keyboard arrows work when focused ---- */
  document.querySelectorAll(".rail").forEach(function (rail) {
    rail.addEventListener("wheel", function (ev) {
      if (Math.abs(ev.deltaY) <= Math.abs(ev.deltaX)) return;   // already horizontal
      const before = rail.scrollLeft;
      rail.scrollLeft = before + ev.deltaY;
      if (rail.scrollLeft !== before) ev.preventDefault();
    }, { passive: false });

    let down = false, startX = 0, startLeft = 0;
    rail.addEventListener("pointerdown", function (ev) {
      if (ev.target.closest("a")) return;
      down = true; startX = ev.clientX; startLeft = rail.scrollLeft;
      rail.style.cursor = "grabbing";
    });
    window.addEventListener("pointerup", function () { down = false; rail.style.cursor = ""; });
    rail.addEventListener("pointermove", function (ev) {
      if (!down) return;
      rail.scrollLeft = startLeft - (ev.clientX - startX);
    });
  });

  /* ---- clicks ---- */
  document.addEventListener("click", function (ev) {
    const el = ev.target.closest("[data-action]");
    if (!el) return;
    const action = el.getAttribute("data-action");

    if (action === "toggle-spoilers") {
      const on = root.classList.toggle("seen-original");
      store({ seenOriginal: on });
      syncPills();
    }

    if (action === "expand-all") {
      const open = el.getAttribute("data-state") !== "open";
      document.querySelectorAll("details.nf").forEach(function (d) { d.open = open; });
      el.setAttribute("data-state", open ? "open" : "closed");
      el.textContent = open ? "Collapse" : "Expand all";
    }
  });

  /* ---- transcript search (same behaviour as V1) ---- */
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
      if (count) count.textContent = q ? hits + " lines" : cues.length + " lines";
    });
  }
  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, function (ch) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch];
    });
  }

  /* ---- deep link highlight ---- */
  if (location.hash) {
    const t = document.getElementById(location.hash.slice(1));
    if (t) {
      t.style.transition = "outline-color .4s ease";
      t.style.outline = "2px solid var(--red)";
      setTimeout(function () { t.style.outline = ""; }, 2400);
    }
  }

  syncPills();
})();
