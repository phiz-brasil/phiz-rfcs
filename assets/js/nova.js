/* The page where anyone creates an RFC (/nova/) or adds a version to one (/nova/?edit=PHZ-1001): download the template, get an AI to
   fill it in, upload it, see the checks and a preview, say who wrote it, publish. */
import { LiveError, addRevision, createRfc, enabled, getLatestRevision } from "./live-api.js";
import { checkBundle } from "./render/check.js";
import { BCP, heroHtml, pageBody } from "./render/page.js";
import { sanitize } from "./render/sanitize.js";

const $ = id => document.getElementById(id);
const LANGS = ["pt", "en", "zh"];
const lang = () => document.documentElement.dataset.lang || "pt";
const store = {
  get(k) { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode */ } }
};
const T = {
  ok: { pt: n => `Tudo certo: os 3 idiomas têm as mesmas ${n} seções.`, en: n => `All good: the 3 languages have the same ${n} sections.`, zh: n => `一切正常：三种语言都有相同的 ${n} 个章节。` },
  problems: { pt: "Corrija estes pontos e envie de novo:", en: "Fix these points and upload again:", zh: "请修正以下问题后重新上传：" },
  needName: { pt: "Informe o seu nome para publicar.", en: "Enter your name to publish.", zh: "请填写你的名字后再发布。" },
  publishing: { pt: "Publicando…", en: "Publishing…", zh: "正在发布…" },
  failed: { pt: "Não foi possível publicar. Tente de novo.", en: "Could not publish. Please try again.", zh: "无法发布，请重试。" },
  rate: { pt: "Muitas publicações seguidas. Espere um pouco e tente de novo.", en: "Too many publications in a row. Wait a little and try again.", zh: "发布过于频繁，请稍后再试。" },
  refused: { pt: "O servidor recusou o arquivo", en: "The server refused the file", zh: "服务器拒绝了该文件" },
  off: { pt: "O envio não está configurado neste site.", en: "Uploading is not set up on this site.", zh: "此站点未配置上传功能。" },
  noEdit: { pt: "RFC não encontrada para editar.", en: "RFC to edit not found.", zh: "未找到要编辑的 RFC。" },
  copied: { pt: "Copiado.", en: "Copied.", zh: "已复制。" },
  copyFail: { pt: "Não foi possível copiar. Baixe o .zip.", en: "Could not copy. Download the .zip instead.", zh: "无法复制，请下载 .zip。" },
  copyManual: { pt: "Selecione o texto e copie.", en: "Select the text and copy it.", zh: "请选中文字后复制。" },
  tooBig: { pt: "O arquivo é grande demais (limite de 600 KB).", en: "The file is too large (limit 600 KB).", zh: "文件过大（上限 600 KB）。" },
  empty: { pt: "Escolha o arquivo ou cole o conteúdo para verificar.", en: "Choose the file or paste the content to check it.", zh: "请选择文件或粘贴内容以进行检查。" }
};
const say = (key, ...a) => { const v = T[key][lang()]; return typeof v === "function" ? v(...a) : v; };

/* ---------- language of the page (same behaviour as the index) ---------- */
function setLang(l) {
  document.documentElement.dataset.lang = l;
  document.documentElement.lang = BCP[l];
  try { localStorage.setItem("phiz-rfc-lang", l); } catch (e) { /* ignore */ }
  document.querySelectorAll("[data-set-lang]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.setLang === l)));
  renderResult();
}
document.querySelectorAll("[data-set-lang]").forEach(b => { b.onclick = () => setLang(b.dataset.setLang); });
{
  const saved = store.get("phiz-rfc-lang");
  const nav = (navigator.language || "pt").slice(0, 2);
  setLang(LANGS.includes(saved) ? saved : LANGS.includes(nav) ? nav : "pt");
}

/* ---------- state ---------- */
const editId = (new URLSearchParams(location.search).get("edit") || "").toUpperCase();
let current = null;        // result of checkBundle for the text in the box
let previewLang = "pt";

function names(text) {
  return text.split(/[\n,]/).map(s => s.trim()).filter(Boolean).slice(0, 20);
}

/* ---------- step 2: the prompt ---------- */
fetch("../assets/templates/PROMPT.md").then(r => (r.ok ? r.text() : "")).then(t => { $("prompt").value = t; }).catch(() => {});
$("copy-prompt").onclick = async () => {
  try { await navigator.clipboard.writeText($("prompt").value); $("copied").textContent = say("copied"); }
  catch (e) { $("prompt").select(); $("copied").textContent = say("copyManual"); }
  setTimeout(() => { $("copied").textContent = ""; }, 2500);
};

$("copy-skill").onclick = async () => {
  try {
    const text = await (await fetch("../assets/skill/phiz-rfc-skill.md")).text();
    await navigator.clipboard.writeText(text);
    $("skill-copied").textContent = say("copied");
  } catch (e) { $("skill-copied").textContent = say("copyFail"); }
  setTimeout(() => { $("skill-copied").textContent = ""; }, 2500);
};

/* ---------- step 3: the file and its checks ---------- */
function renderResult() {
  const box = $("result");
  box.replaceChildren();
  const text = $("text").value;
  if (!text.trim()) { const p = document.createElement("p"); p.className = "note"; p.textContent = say("empty"); box.append(p); return; }
  if (!current) return;
  if (current.ok) {
    const p = document.createElement("p");
    p.className = "ok";
    p.textContent = say("ok", current.bodies.pt.ids.length);
    box.append(p);
  } else {
    const p = document.createElement("p");
    p.className = "bad";
    p.textContent = say("problems");
    const ul = document.createElement("ul");
    ul.className = "issues";
    for (const e of current.errors) { const li = document.createElement("li"); li.textContent = e; ul.append(li); }
    box.append(p, ul);
  }
}

let timer = null;
function validate() {
  const text = $("text").value;
  if (!text.trim()) current = null;
  else {
    try { current = checkBundle(text); }
    catch (e) { current = { ok: false, errors: [String(e.message || e)], bodies: {} }; }
  }
  renderResult();
  const ok = !!(current && current.ok);
  $("preview-bar").hidden = !ok;
  if (!ok) { $("preview").hidden = true; $("preview-langs").hidden = true; }
  else if (!$("preview").hidden) showPreview();
  updatePublish();
}
$("text").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(validate, 300); });
$("file").addEventListener("change", async e => {
  const f = e.target.files[0];
  if (!f) return;
  if (f.size > 600000) { current = { ok: false, errors: [say("tooBig")], bodies: {} }; $("text").value = ""; renderResult(); updatePublish(); return; }
  $("text").value = await f.text();
  validate();
});

/* ---------- preview (a sandboxed frame: the page's own CSS, no access to this page) ---------- */
let pageCss = null;
async function previewDoc(l) {
  if (pageCss === null) pageCss = await (await fetch("../assets/page.css")).text();
  const meta = { id: editId || "PHZ-????", title: current.meta.title, summary: current.meta.summary, systems: current.meta.systems, status: "draft",
                 authors: [$("by").value.trim() || "—"], collaborators: names($("collabs").value), reviewers: [], created: new Date().toISOString().slice(0, 10) };
  const { html } = pageBody(current.bodies[l].body, l);
  const mermaid = new URL("../assets/mermaid.min.js", location.href).href;
  return `<!doctype html><html lang="${BCP[l]}"><head><meta charset="utf-8"><style>${pageCss}</style></head><body>` +
    `<div style="max-width:860px;margin:0 auto;padding:16px"><div class="lang active" data-lang="${l}" lang="${BCP[l]}">${heroHtml(meta, l)}${sanitize(html)}</div></div>` +
    `<script src="${mermaid}"></script><script>if(window.mermaid){mermaid.initialize({startOnLoad:false,securityLevel:"strict",theme:"neutral"});mermaid.run({nodes:[...document.querySelectorAll("pre.mermaid")]});}</script></body></html>`;
}
async function showPreview() {
  const frame = $("preview");
  frame.srcdoc = await previewDoc(previewLang);
  frame.hidden = false;
  $("preview-langs").hidden = false;
}
$("preview-toggle").onclick = () => { if ($("preview").hidden) showPreview(); else { $("preview").hidden = true; $("preview-langs").hidden = true; } };
document.querySelectorAll("[data-pl]").forEach(b => {
  b.onclick = () => {
    previewLang = b.dataset.pl;
    document.querySelectorAll("[data-pl]").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
    if (current && current.ok) showPreview();
  };
});

/* ---------- step 4: who, and publish ---------- */
$("by").value = store.get("phiz-rfc-author");
function updatePublish() {
  $("publish").disabled = !(current && current.ok);
}
$("by").addEventListener("input", () => { $("publish-note").textContent = ""; });

$("publish").onclick = async () => {
  const note = $("publish-note");
  const by = $("by").value.trim();
  if (!enabled) { note.textContent = say("off"); return; }
  if (!current || !current.ok) return;
  if (!by) { note.textContent = say("needName"); $("by").focus(); return; }
  store.set("phiz-rfc-author", by);
  $("publish").disabled = true;
  note.textContent = say("publishing");
  const args = { meta: current.meta, bundle: $("text").value, by, collaborators: names($("collabs").value) };
  try {
    const res = editId
      ? await addRevision({ ...args, id: editId, authors: names($("authors").value).length ? names($("authors").value) : [by], note: $("note").value.trim() })
      : await createRfc({ ...args, authors: [by] });
    location.href = `../rfc/?id=${encodeURIComponent(res.rfc_id)}`;
  } catch (e) {
    $("publish").disabled = false;
    note.textContent = e instanceof LiveError && e.code === "rate" ? say("rate")
      : e instanceof LiveError && e.code === "invalid" ? `${say("refused")}: ${e.message}` : say("failed");
  }
};

/* ---------- editing an existing RFC ---------- */
async function loadForEdit() {
  document.querySelectorAll(".only-new").forEach(n => { n.hidden = true; });
  document.querySelectorAll(".only-edit").forEach(n => { n.hidden = false; });
  $("edit-id").textContent = editId;
  let row = null;
  try { row = await getLatestRevision(editId); } catch (e) { /* shown below */ }
  if (!row) { $("result").textContent = say("noEdit"); return; }
  $("text").value = row.bundle;
  $("authors").value = (row.authors || []).join("\n");
  $("collabs").value = (row.collaborators || []).join("\n");
  const dl = $("dl-current");
  dl.href = URL.createObjectURL(new Blob([row.bundle], { type: "text/markdown" }));
  dl.download = `${editId}.md`;
  dl.hidden = false;
  validate();
}
if (/^PHZ-\d{4}$/.test(editId) && enabled) loadForEdit();
else renderResult();
