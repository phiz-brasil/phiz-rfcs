import { openFromLink, paintAllBtn } from "./drawer.js";
import { paintCounts, paintMarks } from "./panels.js";
import { BASE_COLS, FULL_COLS, S, rfcId, sb } from "./state.js";
import { renderThreads } from "./threads.js";
import { store } from "./util.js";

export async function loadAll() {
  try {
    const q = c => `?select=${c}&rfc_id=eq.${encodeURIComponent(rfcId)}&order=created_at.asc&limit=2000`;
    let r = await fetch(sb.url + q(S.COLS), { headers: sb.headers });
    if (r.status === 400 && S.COLS === FULL_COLS) { S.COLS = BASE_COLS + ",translations,src_lang"; S.HAS_PARA = false; r = await fetch(sb.url + q(S.COLS), { headers: sb.headers }); }
    if (r.status === 400 && S.COLS !== BASE_COLS) { S.COLS = BASE_COLS; S.HAS_PARA = false; r = await fetch(sb.url + q(S.COLS), { headers: sb.headers }); }
    if (!r.ok) throw new Error("HTTP " + r.status);
    S.all = await r.json();
    S.loadFailed = false;
  } catch (e) {
    console.warn("comments", e);
    S.all = []; S.loadFailed = true;
  }
  if (!S.HAS_PARA) document.querySelectorAll(".cmt-pbtn, .cmt-para-panel").forEach(n => n.remove());   // database without the para column
  paintCounts(); paintMarks(); paintAllBtn();
  document.querySelectorAll(".cmt-panel[data-key]").forEach(renderThreads);
  openFromLink();
}

export async function hideComment(id) {
  const r = await fetch(sb.url.replace(/rfc_comments$/, "rpc/hide_rfc_comment"), {
    method: "POST",
    headers: Object.assign({ "Content-Type": "application/json" }, sb.headers),
    body: JSON.stringify({ p_id: id, p_by: store.get("phiz-rfc-author") || null })
  });
  if (r.status === 429) throw Object.assign(new Error("rate"), { code: "rate" });
  if (!r.ok) throw new Error("HTTP " + r.status);
}

export async function addComment(row) {
  const r = await fetch(sb.url + "?select=" + BASE_COLS + (S.HAS_PARA ? ",para" : ""), {
    method: "POST",
    headers: Object.assign({ "Content-Type": "application/json", Prefer: "return=representation" }, sb.headers),
    body: JSON.stringify(row)
  });
  if (r.status === 429) throw Object.assign(new Error("rate"), { code: "rate" });
  if (!r.ok) throw new Error("HTTP " + r.status);
  const rows = await r.json();
  return rows[0];
}
