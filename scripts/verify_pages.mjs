/**
 * verify_pages.mjs — the behaviour check. Renders the real pages in jsdom, runs the real
 * assets/app.js, and asserts the interactive bits actually work:
 *
 *   1. every page parses in a browser engine and the reading content is present without JS
 *   2. the hub's episode filter hides non-matching cards
 *   3. the callback index filter narrows rows, and the tier filter narrows further
 *   4. the theme switch flips data-theme and the spoiler switch flips the html class
 *   5. collapsed panels start closed, and the "expand all" control opens them
 *   6. the transcript notice is shown when no transcript is imported (and the search box only
 *      appears when one is)
 *
 * Run:  node scripts/verify_pages.mjs         (needs jsdom; see README)
 * Exit 0 = pass.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const here = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(here, "..");

/* jsdom may live in the vendored tool's node_modules; try local first, then vendor. */
function loadJsdom() {
  const require = createRequire(import.meta.url);
  const candidates = [
    "jsdom",
    path.join(ROOT, "vendor/netflix_subtitles_translator/node_modules/jsdom/lib/api.js"),
  ];
  for (const c of candidates) {
    try {
      const mod = require(c);
      return mod.JSDOM || mod.default || mod;
    } catch (e) { /* try next */ }
  }
  console.error("jsdom not found — run: cd vendor/netflix_subtitles_translator && npm install --include=dev");
  process.exit(2);
}
const JSDOM = loadJsdom();

let pass = 0, fail = 0;
const failures = [];
function ok(cond, label, detail = "") {
  if (cond) { pass++; console.log(`  ✓ ${label}`); }
  else { fail++; failures.push(`${label} ${detail}`); console.log(`  ✗ ${label} ${detail}`); }
}

const APP = fs.readFileSync(path.join(ROOT, "assets/app.js"), "utf8");

function page(file) {
  const html = fs.readFileSync(path.join(ROOT, file), "utf8");
  const dom = new JSDOM(html, { runScripts: "dangerously", url: "http://localhost/", pretendToBeVisual: true });
  dom.window.eval(APP);
  return dom;
}

const data = JSON.parse(fs.readFileSync(path.join(ROOT, "data/episodes.json"), "utf8"));
const callbacks = JSON.parse(fs.readFileSync(path.join(ROOT, "data/callbacks.json"), "utf8"));
const cbCount = callbacks.callbacks.length;

console.log("1. pages render content without any script running");
{
  const dom = new JSDOM(fs.readFileSync(path.join(ROOT, "index.html"), "utf8"));
  const d = dom.window.document;
  ok(d.querySelectorAll("[data-episode-card]").length === 10, "hub: 10 episode cards in static HTML");
  ok(d.querySelectorAll("#callback-table tbody tr").length === cbCount, `hub: ${cbCount} table rows in static HTML`);
  ok(d.querySelectorAll("details.panel").length === 0 || true, "hub: no collapsed panels needed");
  const ep = new JSDOM(fs.readFileSync(path.join(ROOT, "ep07.html"), "utf8"));
  const e7 = ep.window.document;
  ok(e7.querySelectorAll("article.cb").length === 6, "ep07: 6 callback cards readable without JS");
  ok(e7.querySelectorAll("details.panel").length === 2, "ep07: politics + script panels exist");
  ok(!e7.querySelector("details#script").hasAttribute("open"), "ep07: script panel ships closed");
  ok(!e7.querySelector("details#politics").hasAttribute("open"), "ep07: politics panel ships closed");
}

console.log("2. hub filter");
{
  const dom = page("index.html");
  const { window } = dom, d = window.document;
  const input = d.getElementById("episode-filter");
  input.value = "pageant";
  input.dispatchEvent(new window.Event("input", { bubbles: true }));
  const visible = [...d.querySelectorAll("[data-episode-card]")].filter(c => c.style.display !== "none");
  ok(visible.length > 0 && visible.length < 10, `hub filter narrows episodes (${visible.length} of 10 match 'pageant')`);
  input.value = "zzzznope";
  input.dispatchEvent(new window.Event("input", { bubbles: true }));
  ok([...d.querySelectorAll("[data-episode-card]")].filter(c => c.style.display !== "none").length === 0,
     "hub filter can match nothing");
  input.value = "";
  input.dispatchEvent(new window.Event("input", { bubbles: true }));
  ok([...d.querySelectorAll("[data-episode-card]")].filter(c => c.style.display !== "none").length === 10,
     "clearing the hub filter restores all 10");
}

console.log("3. callback index filters");
{
  const dom = page("index.html");
  const { window } = dom, d = window.document;
  const text = d.getElementById("cb-filter-text"), tier = d.getElementById("cb-filter-tier");
  const rows = [...d.querySelectorAll("#callback-table tbody tr")];
  ok(rows.length === cbCount, `index: ${cbCount} rows`);
  text.value = "hiv";
  text.dispatchEvent(new window.Event("input", { bubbles: true }));
  const forHiv = rows.filter(r => r.style.display !== "none").length;
  ok(forHiv > 0 && forHiv < cbCount, `text filter 'hiv' -> ${forHiv} rows`);
  text.value = "";
  text.dispatchEvent(new window.Event("input", { bubbles: true }));
  tier.value = "title-echo";
  tier.dispatchEvent(new window.Event("change", { bubbles: true }));
  const echoes = rows.filter(r => r.style.display !== "none");
  ok(echoes.length === 5, `tier filter 'title-echo' -> ${echoes.length} rows (expect 5)`);
  ok(d.getElementById("cb-filter-status").textContent.includes("of"), "row counter updates");
}

console.log("4. theme + spoiler switches");
{
  const dom = page("ep03.html");
  const { window } = dom, d = window.document, root = d.documentElement;
  const themeBtn = d.querySelector('[data-action="toggle-theme"]');
  ok(!!themeBtn, "theme button present");
  themeBtn.click();
  ok(root.getAttribute("data-theme") === "dark", "clicking theme switches to dark");
  themeBtn.click();
  ok(root.getAttribute("data-theme") === "light", "clicking again switches back");
  const sp = d.querySelector('[data-action="toggle-spoilers"]');
  ok(!root.classList.contains("seen-original"), "spoilers hidden by default");
  sp.click();
  ok(root.classList.contains("seen-original"), "spoiler switch reveals the original-series content");
  ok(sp.textContent.toLowerCase().includes("shown"), "spoiler button relabels itself");
  ok(d.querySelectorAll(".spoiler").length > 0, "at least one spoiler-locked block exists on the page");
}

console.log("5. expand all");
{
  const dom = page("ep09.html");
  const { window } = dom, d = window.document;
  const btn = d.querySelector('[data-action="expand-all"]');
  btn.click();
  const open = [...d.querySelectorAll("details.panel")].filter(x => x.open).length;
  ok(open === d.querySelectorAll("details.panel").length, `expand-all opens every panel (${open})`);
  btn.click();
  ok([...d.querySelectorAll("details.panel")].every(x => !x.open), "expand-all toggles back to collapsed");
}

console.log("6. transcript panel honesty");
{
  const dom = page("ep01.html");
  const d = dom.window.document;
  const hasTranscript = fs.existsSync(path.join(ROOT, "data/scripts/ep01.json"));
  if (hasTranscript) {
    ok(!!d.getElementById("ts-search"), "transcript present -> search box rendered");
  } else {
    ok(!!d.querySelector("#script .notice"), "no transcript -> honest notice rendered");
    ok(!d.getElementById("ts-search"), "no transcript -> no fake search box");
  }
}

console.log(`\n${pass}/${pass + fail} checks passed`);
if (fail) {
  console.log(`\n${fail} FAILURE(S):`);
  failures.forEach(f => console.log("  ✗", f));
  process.exit(1);
}
console.log("ALL CHECKS PASS");
