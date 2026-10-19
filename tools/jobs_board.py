#!/usr/bin/env python3
"""Render job_scraper/seen_jobs.json as a self-contained HTML job board.

`/html-report` covers the application tracker - jobs already applied to. The
postings `/scrape` and `/rank` collect live only in seen_jobs.json, which is
unreadable at a glance once it holds a few dozen entries. This turns it into a
single offline page: filterable by fit, status and portal, searchable, with the
`/rank` score, strengths and gaps shown when an entry carries them.

Output is one .html file with inline CSS/JS and no external requests. State
values are embedded as JSON and rendered with textContent, so titles and
company names copied from postings can never inject markup. Only http(s) URLs
become links.

Usage:
  python3 tools/jobs_board.py
  python3 tools/jobs_board.py --open
  python3 tools/jobs_board.py --state job_scraper/seen_jobs.json --out reports/jobs-board.html

`--open` opens the written board in the default browser (what `/scrape` Step 5
runs at the end of every scrape).

Exit 0 when the board is written, 1 when the state file is missing or invalid.
"""

import argparse
import datetime
import json
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "job_scraper" / "seen_jobs.json"
OUT = ROOT / "reports" / "jobs-board.html"

FIELDS = (
    "title", "company", "location", "url", "first_seen", "posted_date", "deadline", "salary",
    "fit", "status", "portal", "source", "rank_score", "rank_verdict",
    "location_verdict", "language_gate", "language_note", "strengths", "gaps",
)


def load_jobs(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    jobs = []
    for key, entry in data.get("seen", {}).items():
        job = {f: entry.get(f) for f in FIELDS}
        # Legacy entries may carry a PASS/FAIL/FLAG verdict in `location`.
        if job["location"] in ("PASS", "FAIL", "FLAG"):
            job["location_verdict"] = job["location_verdict"] or job["location"]
            job["location"] = None
        url = job["url"] or ""
        job["url"] = url if url.startswith(("http://", "https://")) else None
        job["key"] = key
        jobs.append(job)
    return jobs


def render(jobs: list[dict], today: str) -> str:
    # "</" inside a <script> block would end it early; < keeps the JSON valid.
    payload = json.dumps(jobs, ensure_ascii=False).replace("<", "\\u003c")
    return TEMPLATE.replace("__DATA__", payload).replace("__DATE__", today)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--state", type=Path, default=STATE)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--open", action="store_true", help="open the board in the default browser")
    args = ap.parse_args()

    if not args.state.exists():
        print(f"state file not found: {args.state} - run /scrape first", file=sys.stderr)
        return 1
    try:
        jobs = load_jobs(args.state)
    except (json.JSONDecodeError, AttributeError) as exc:
        print(f"invalid state file {args.state}: {exc}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    args.out.write_text(render(jobs, stamp), encoding="utf-8")
    active = sum(1 for j in jobs if j["status"] not in ("skipped", "expired", "unreachable"))
    print(f"{args.out} - {len(jobs)} jobs ({active} active)")
    if args.open and not webbrowser.open(args.out.resolve().as_uri()):
        print("could not open a browser - open the file manually", file=sys.stderr)
    return 0


TEMPLATE = r"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Job Board</title>
<style>
:root{
  --high:#16a34a;--medium:#d97706;--low:#94a3b8;
  --bg:#f1f5f9;--card:#fff;--text:#0f172a;--muted:#64748b;--border:#e2e8f0;--stripe:#f8fafc;--accent:#2563eb;
}
@media (prefers-color-scheme: dark){
  :root{--bg:#0f172a;--card:#1e293b;--text:#e2e8f0;--muted:#94a3b8;--border:#334155;--stripe:#172033;--accent:#60a5fa}
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.45}
.wrap{max-width:1300px;margin:0 auto;padding:24px 16px}
header{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;margin-bottom:18px}
h1{font-size:1.6rem;margin:0}
.muted{color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin-bottom:18px}
.card{background:var(--card);border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.12);padding:12px 16px;border-left:5px solid var(--muted);cursor:pointer}
.card .n{font-size:1.8rem;font-weight:700}
.card .l{color:var(--muted);font-size:.85rem}
.panel{background:var(--card);border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.12);padding:16px}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px}
select,input[type=search]{font:inherit;padding:6px 8px;border:1px solid var(--border);border-radius:6px;background:var(--card);color:var(--text)}
input[type=search]{flex:1;min-width:200px}
label.chk{display:flex;gap:6px;align-items:center;font-size:.9rem}
.count{margin-left:auto;font-size:.9rem}
.tscroll{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th,td{text-align:left;padding:8px;border-bottom:1px solid var(--border);vertical-align:top}
th{cursor:pointer;user-select:none;white-space:nowrap}
th[data-k]:hover{color:var(--accent)}
tbody tr.job:nth-child(4n+1){background:var(--stripe)}
td.nowrap{white-space:nowrap}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:.78rem;font-weight:600;color:#fff;background:var(--low)}
.pill.high{background:var(--high)}.pill.medium{background:var(--medium)}
.st{font-size:.8rem;padding:1px 6px;border:1px solid var(--border);border-radius:4px;white-space:nowrap}
.st.new{border-color:var(--accent);color:var(--accent)}
a{color:var(--accent)}
.more{background:none;border:0;color:var(--accent);cursor:pointer;font:inherit;padding:0}
tr.detail td{background:var(--card);font-size:.85rem}
tr.detail ul{margin:4px 0 8px 18px;padding:0}
.empty{text-align:center;color:var(--muted);padding:28px 8px}
footer{color:var(--muted);font-size:.8rem;text-align:center;margin-top:24px}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Job Board</h1>
    <span class="muted">Stand: __DATE__ · Quelle: job_scraper/seen_jobs.json</span>
  </header>
  <section class="cards" id="cards"></section>
  <section class="panel">
    <div class="toolbar">
      <input id="q" type="search" placeholder="Titel, Firma, Ort…" aria-label="Suche">
      <select id="fFit" aria-label="Passung"><option value="">Alle Passungen</option><option value="high">Hoch</option><option value="medium">Mittel</option><option value="low">Niedrig</option></select>
      <select id="fStatus" aria-label="Status"><option value="">Alle Status</option></select>
      <select id="fPortal" aria-label="Portal"><option value="">Alle Portale</option></select>
      <label class="chk"><input id="hide" type="checkbox" checked> Übersprungene/abgelaufene ausblenden</label>
      <span class="count muted" id="count"></span>
    </div>
    <div class="tscroll">
      <table>
        <thead><tr>
          <th data-k="fit">Passung</th><th data-k="rank_score">Score</th><th data-k="title">Titel</th>
          <th data-k="company">Firma</th><th data-k="location">Ort</th><th data-k="posted_date">Veröffentlicht</th>
          <th data-k="deadline">Frist</th><th data-k="salary">Gehalt</th><th data-k="status">Status</th><th data-k="portal">Portal</th><th>Link</th>
        </tr></thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
  </section>
  <footer>Generated by Claude Code · ai-job-search · __DATE__ · neu erzeugen: <code>python tools/jobs_board.py</code></footer>
</div>
<script>
var JOBS = __DATA__;
var FIT = {high:3, medium:2, low:1};
var LABEL = {high:"Hoch", medium:"Mittel", low:"Niedrig"};
var HIDDEN = {skipped:1, expired:1, unreachable:1};
var sortKey = "fit", sortDir = -1;
var $ = function(id){ return document.getElementById(id); };

function el(tag, cls, text){
  var e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined && text !== null) e.textContent = text;
  return e;
}
function uniq(k){
  var s = {}; JOBS.forEach(function(j){ if (j[k]) s[j[k]] = 1; });
  return Object.keys(s).sort();
}
function fill(sel, vals){ vals.forEach(function(v){ var o = el("option", null, v); o.value = v; sel.appendChild(o); }); }

function cards(){
  var active = JOBS.filter(function(j){ return !HIDDEN[j.status]; });
  var defs = [
    ["Aktiv", active.length, "var(--accent)", ""],
    ["Hoch", active.filter(function(j){ return j.fit === "high"; }).length, "var(--high)", "high"],
    ["Mittel", active.filter(function(j){ return j.fit === "medium"; }).length, "var(--medium)", "medium"],
    ["Bewertet (/rank)", JOBS.filter(function(j){ return j.status === "ranked"; }).length, "var(--text)", null],
    ["Gesamt gesehen", JOBS.length, "var(--low)", null]
  ];
  var c = $("cards");
  defs.forEach(function(d){
    var card = el("div", "card"); card.style.borderLeftColor = d[2];
    card.appendChild(el("div", "n", d[1])); card.appendChild(el("div", "l", d[0]));
    if (d[3] !== null) card.onclick = function(){ $("fFit").value = d[3]; $("hide").checked = true; draw(); };
    c.appendChild(card);
  });
}

function cmp(a, b){
  var x = sortKey === "fit" ? (FIT[a.fit] || 0) : a[sortKey];
  var y = sortKey === "fit" ? (FIT[b.fit] || 0) : b[sortKey];
  if (x === y || (x == null && y == null)) {
    // tie-break: newest posting first
    return String(b.posted_date || "").localeCompare(String(a.posted_date || ""));
  }
  if (x == null) return 1;
  if (y == null) return -1;
  return (x > y ? 1 : -1) * sortDir;
}

function detailRow(j){
  var tr = el("tr", "detail"); var td = el("td"); td.colSpan = 11;
  if (j.rank_verdict) td.appendChild(el("div", null, "Urteil: " + j.rank_verdict));
  [["Stärken", j.strengths], ["Lücken", j.gaps]].forEach(function(p){
    if (!p[1] || !p[1].length) return;
    td.appendChild(el("strong", null, p[0]));
    var ul = el("ul"); p[1].forEach(function(s){ ul.appendChild(el("li", null, s)); }); td.appendChild(ul);
  });
  var gates = [];
  if (j.location_verdict) gates.push("Ort: " + j.location_verdict);
  if (j.language_gate) gates.push("Sprache: " + j.language_gate + (j.language_note ? " – " + j.language_note : ""));
  if (gates.length) td.appendChild(el("div", "muted", gates.join(" · ")));
  tr.appendChild(td); tr.hidden = true;
  return tr;
}

function draw(){
  var q = $("q").value.toLowerCase(), fit = $("fFit").value, st = $("fStatus").value,
      po = $("fPortal").value, hide = $("hide").checked;
  var list = JOBS.filter(function(j){
    if (hide && HIDDEN[j.status] && st !== j.status) return false;
    if (fit && j.fit !== fit) return false;
    if (st && j.status !== st) return false;
    if (po && j.portal !== po) return false;
    if (q && [j.title, j.company, j.location].join(" ").toLowerCase().indexOf(q) < 0) return false;
    return true;
  }).sort(cmp);
  var body = $("rows"); body.textContent = "";
  $("count").textContent = list.length + " von " + JOBS.length;
  if (!list.length) {
    var tr = el("tr"), td = el("td", "empty", "Keine Stellen für diese Filter."); td.colSpan = 11;
    tr.appendChild(td); body.appendChild(tr); return;
  }
  list.forEach(function(j){
    var tr = el("tr", "job");
    var f = el("td"); f.appendChild(el("span", "pill " + (j.fit || ""), LABEL[j.fit] || "–")); tr.appendChild(f);
    tr.appendChild(el("td", "nowrap", j.rank_score != null ? j.rank_score : "–"));
    var t = el("td", null, j.title || "–");
    var hasDetail = j.rank_verdict || (j.strengths && j.strengths.length) || (j.gaps && j.gaps.length) || j.language_gate;
    var d = hasDetail ? detailRow(j) : null;
    if (d) { var b = el("button", "more", " Details"); b.onclick = function(){ d.hidden = !d.hidden; }; t.appendChild(b); }
    tr.appendChild(t);
    tr.appendChild(el("td", null, j.company || "–"));
    tr.appendChild(el("td", null, j.location || "–"));
    tr.appendChild(el("td", "nowrap", j.posted_date || "–"));
    tr.appendChild(el("td", "nowrap", j.deadline || "–"));
    tr.appendChild(el("td", "nowrap", j.salary || "–"));
    var s = el("td"); s.appendChild(el("span", "st " + (j.status || ""), j.status || "–")); tr.appendChild(s);
    tr.appendChild(el("td", "nowrap muted", j.portal || "–"));
    var l = el("td");
    if (j.url) { var a = el("a", null, "Öffnen"); a.href = j.url; a.target = "_blank"; a.rel = "noopener noreferrer"; l.appendChild(a); }
    else l.textContent = "–";
    tr.appendChild(l);
    body.appendChild(tr);
    if (d) body.appendChild(d);
  });
}

fill($("fStatus"), uniq("status"));
fill($("fPortal"), uniq("portal"));
cards();
["q", "fFit", "fStatus", "fPortal", "hide"].forEach(function(id){ $(id).addEventListener("input", draw); });
[].forEach.call(document.querySelectorAll("th[data-k]"), function(th){
  th.onclick = function(){
    var k = th.getAttribute("data-k");
    sortDir = sortKey === k ? -sortDir : (k === "title" || k === "company" || k === "location" ? 1 : -1);
    sortKey = k; draw();
  };
});
draw();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
