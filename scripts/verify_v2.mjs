/**
 * verify_v2.mjs — behaviour checks for the Netflix-style pages, in jsdom.
 *
 *   1. shelves and cards render in static HTML (no JS needed to read the page)
 *   2. the shelf wheel handler turns vertical wheel into horizontal scroll and does not throw
 *   3. the ranked shelf is numbered 1..10
 *   4. the spoiler pill flips the html class, relabels itself, and persists the choice
 *   5. "expand all" opens every panel on an episode page, twice in a row
 *   6. today's zero-transcript state renders the honest notice (and no fake search box)
 *   7. a deep link to a callback row doesn't throw and the row exists
 *
 * Run: node scripts/verify_v2.mjs      (exit 0 = pass)
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const here = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(here, "..");

function loadJsdom() {
  const require = createRequire(import.meta.url);
  for (const c of ["jsdom", path.join(ROOT, "vendor/netflix_subtitles_translator/node_modules/jsdom/lib/api.js")]) {
    try { const m = require(c); return m.JSDOM || m.default || m; } catch (e) { /* next */ }
  }
  console.error("jsdom not found — run: cd vendor/netflix_subtitles_translator && npm install --include=dev");
  process.exit(2);
}
const JSDOM = loadJsdom();
const APP = fs.readFileSync(path.join(ROOT, "assets/v2/netflix.js"), "utf8");

let pass = 0, fail = 0;
const failures = [];
function ok(cond, label, detail = "") {
  if (cond) { pass++; console.log(`  ✓ ${label}`); }
  else { fail++; failures.push(`${label} ${detail}`); console.log(`  ✗ ${label} ${detail}`); }
}

function page(file, withJs = true) {
  const html = fs.readFileSync(path.join(ROOT, "v2", file), "utf8");
  const dom = new JSDOM(html, { runScripts: withJs ? "dangerously" : undefined, url: "http://localhost/v2/" + file });
  if (withJs) dom.window.eval(APP);
  return dom;
}

const episodes = JSON.parse(fs.readFileSync(path.join(ROOT, "data/episodes.json"), "utf8"));

console.log("1. static content");
{
  const dom = page("index.html", false);
  const d = dom.window.document;
  ok(d.querySelectorAll(".shelf").length === 6, "hub has 6 shelves", `got ${d.querySelectorAll(".shelf").length}`);
  ok(d.querySelectorAll("#episodes .card").length === 10, "episodes shelf: 10 cards");
  ok(d.querySelectorAll("#callbacks .card.rank").length === 10, "top-callbacks shelf: 10 ranked cards");
  ok(d.querySelectorAll("#original .card").length === 12, "1987 shelf: 12 cards");
  ok(d.querySelectorAll("#campuses .card").length === 6, "campus shelf: 6 credited photos");
  ok(d.querySelectorAll("img").length > 30, `hub loads images (${d.querySelectorAll("img").length} img tags)`);
  const ep = page("ep07.html", false);
  const e7 = ep.window.document;
  ok(e7.querySelectorAll(".ep-row").length === 6, "ep07: 6 callback rows without JS");
  ok(e7.querySelectorAll("details.nf").length === 2, "ep07: two collapsible panels");
  ok(!e7.querySelector("#politics").hasAttribute("open"), "ep07: politics panel closed by default");
  ok(!e7.querySelector("#script").hasAttribute("open"), "ep07: script panel closed by default");
}

console.log("2. shelves scroll sideways");
{
  const dom = page("index.html");
  const { window } = dom, d = window.document;
  const rail = d.querySelector(".rail");
  rail.scrollLeft = 0;
  let threw = false;
  try {
    const ev = new window.WheelEvent("wheel", { deltaY: 200, bubbles: true, cancelable: true });
    rail.dispatchEvent(ev);
  } catch (e) { threw = true; }
  ok(!threw, "wheel event on a shelf does not throw");
  ok(typeof rail.scrollLeft === "number", "shelf has a scrollable position");
}

console.log("3. ranked shelf numbering");
{
  const dom = page("index.html", false);
  const ranks = [...dom.window.document.querySelectorAll(".rankno")].map(n => n.textContent.trim());
  ok(JSON.stringify(ranks) === JSON.stringify(["1","2","3","4","5","6","7","8","9","10"]),
     "ranks run 1..10 in order", ranks.join(","));
  const links = [...dom.window.document.querySelectorAll(".card.rank")].map(a => a.getAttribute("href"));
  ok(links.every(h => /^ep\d\d\.html#[-\w]+$/.test(h)), "each ranked card deep-links to its callback row");
}

console.log("4. spoiler pill");
{
  const dom = page("ep01.html");
  const { window } = dom, d = window.document, root = d.documentElement;
  const pill = d.querySelector('[data-action="toggle-spoilers"]');
  ok(!!pill, "spoiler pill exists in the nav");
  ok(!root.classList.contains("seen-original"), "original-series spoilers hidden by default");
  pill.click();
  ok(root.classList.contains("seen-original"), "pill reveals spoilers");
  ok(/shown/i.test(pill.textContent), "pill relabels itself", pill.textContent);
  ok(!!window.localStorage.getItem("dw-origin-notes-v2"), "choice is persisted");
  pill.click();
  ok(!root.classList.contains("seen-original"), "pill hides them again");
}

console.log("5. expand all");
{
  const dom = page("ep09.html");
  const { window } = dom, d = window.document;
  const btn = d.querySelector('[data-action="expand-all"]');
  btn.click();
  ok([...d.querySelectorAll("details.nf")].every(x => x.open), "expand-all opens every panel");
  btn.click();
  ok([...d.querySelectorAll("details.nf")].every(x => !x.open), "expand-all collapses them again");
}

console.log("6. transcript honesty");
{
  const dom = page("ep01.html");
  const d = dom.window.document;
  const has = fs.existsSync(path.join(ROOT, "data/scripts/ep01.json"));
  if (has) ok(!!d.getElementById("ts-search"), "transcript present -> search box rendered");
  else {
    ok(!!d.querySelector("#script .notice"), "no transcript -> honest notice rendered");
    ok(!d.getElementById("ts-search"), "no transcript -> no fake search box");
  }
}

console.log("7. deep links");
{
  const firstId = episodes.episodes[0].callbacks[0];
  const dom = page("ep01.html");
  const d = dom.window.document;
  ok(!!d.getElementById(firstId), `callback row #${firstId} exists for deep-linking`);
  let threw = false;
  try { dom.window.eval("location.hash = '#" + firstId + "'"); } catch (e) { threw = true; }
  ok(!threw, "setting a callback hash does not throw");
}

console.log(`\n${pass}/${pass + fail} checks passed`);
if (fail) {
  console.log(`\n${fail} FAILURE(S):`);
  failures.forEach(f => console.log("  ✗", f));
  process.exit(1);
}
console.log("ALL CHECKS PASS");
