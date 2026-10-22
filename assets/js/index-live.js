/* The index lists the RFCs of the repository (built into the page) and, here, the ones created on the site, read from the database. */
import { enabled, listLive } from "./live-api.js";
import { LANGS, STATUS } from "./render/page.js";

const personName = p => (typeof p === "string" ? p : (p && (p.name || p.pt)) || "");

function span(lang, text) {
  const s = document.createElement("span");
  s.dataset.l = lang;
  s.textContent = text;
  return s;
}
const spans = o => LANGS.map(l => span(l, o[l] || ""));

function card(row) {
  const li = document.createElement("li");
  li.className = "card-li";
  li.dataset.status = "draft";
  li.dataset.rfc = row.rfc_id;
  const a = document.createElement("a");
  a.className = "card";
  a.href = `rfc/?id=${encodeURIComponent(row.rfc_id)}`;
  const top = document.createElement("div");
  top.className = "top";
  const id = document.createElement("span"); id.className = "id"; id.textContent = row.rfc_id;
  const ver = document.createElement("span"); ver.className = "ver"; ver.textContent = `v${row.version}`;
  const badge = document.createElement("span"); badge.className = "badge"; badge.dataset.st = "draft"; badge.append(...spans(STATUS.draft));
  top.append(id, ver, badge);
  const h2 = document.createElement("h2"); h2.append(...spans(row.meta.title));
  const p = document.createElement("p"); p.append(...spans(row.meta.summary));
  const meta = document.createElement("div");
  meta.className = "meta";
  const authors = document.createElement("span"); authors.textContent = (row.authors || []).map(personName).join(", ") || "—";
  const revs = document.createElement("span"); revs.textContent = "Reviewers: —";
  const when = document.createElement("span"); when.textContent = (row.created_at || "").slice(0, 10);
  const cc = document.createElement("span"); cc.className = "cc"; cc.dataset.rfc = row.rfc_id; cc.hidden = true;
  meta.append(authors, revs, when, cc);
  a.append(top, h2, p, meta);
  li.append(a);
  return li;
}

async function start() {
  if (!enabled) return;
  let rows;
  try { rows = await listLive(); } catch (e) { return; }
  const list = document.querySelector(".list");
  if (!list || !rows.length) return;
  for (const row of rows) {
    if (list.querySelector(`.card-li[data-rfc="${row.rfc_id}"]`)) continue;
    const li = card(row);
    const after = [...list.querySelectorAll(".card-li")].find(x => x.dataset.rfc < row.rfc_id);     // newest id first
    list.insertBefore(li, after || null);
  }
  if (window.phizStatusIndexRefresh) window.phizStatusIndexRefresh();    // live status, and the status filters
  if (window.phizCountsRepaint) window.phizCountsRepaint();              // comment counters
}

start();
