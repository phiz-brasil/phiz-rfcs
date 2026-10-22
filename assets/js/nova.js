/* The page where anyone creates an RFC (/nova/) or adds a version to one (/nova/?edit=PHZ-1001): download the template, get an AI to
   fill it in, upload it, see the checks and a preview, say who wrote it, publish. */
import { ACCEPT, ImageError, MAX_IMAGES, NAME_RE, blobToBase64, shrinkImage, slugName } from "./images.js";
import { LATEST, LiveError, addRevision, createRfc, enabled, getAsset, getLatestRevision, listAssets, stageAsset } from "./live-api.js";
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
  badType: { pt: n => `“${n}” não é PNG, JPEG ou WebP.`, en: n => `“${n}” is not a PNG, JPEG or WebP.`, zh: n => `“${n}”不是 PNG、JPEG 或 WebP。` },
  badImage: { pt: n => `Não foi possível ler “${n}”.`, en: n => `Could not read “${n}”.`, zh: n => `无法读取“${n}”。` },
  bigImage: { pt: n => `“${n}” continua grande demais mesmo reduzida.`, en: n => `“${n}” is still too large even after reducing it.`, zh: n => `“${n}”即使缩小后仍然过大。` },
  tooMany: { pt: `No máximo ${MAX_IMAGES} imagens.`, en: `At most ${MAX_IMAGES} images.`, zh: `最多 ${MAX_IMAGES} 张图片。` },
  reducing: { pt: "Reduzindo as imagens…", en: "Reducing the images…", zh: "正在缩小图片…" },
  sending: { pt: (i, n) => `Enviando a imagem ${i} de ${n}…`, en: (i, n) => `Uploading image ${i} of ${n}…`, zh: (i, n) => `正在上传第 ${i} 张图片，共 ${n} 张…` },
  insert: { pt: "Inserir no texto", en: "Insert in the text", zh: "插入正文" },
  remove: { pt: "Remover", en: "Remove", zh: "移除" },
  already: { pt: "já enviada", en: "already sent", zh: "已上传" },
  describe: { pt: "descrição", en: "description", zh: "说明" },
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

/* ---------- images ---------- */
const attached = [];        // { name, mime, size, b64, preview } files attached now
let existing = [];          // names of the images the RFC already has (editing)
const escapeRe = s => s.replace(/[.*+?^$(){}|[\]\\]/g, "\\$&");
const assetNames = () => [...attached.map(a => a.name), ...existing];

function uniqueName(name, except) {
  const taken = new Set(assetNames().filter(n => n !== except));
  if (!taken.has(name)) return name;
  const m = /^(.*?)(\.[a-z0-9]+)$/.exec(name);
  for (let i = 2; ; i++) { const c = `${m[1].slice(0, 54)}-${i}${m[2]}`; if (!taken.has(c)) return c; }
}

function insertAtCursor(text) {
  const box = $("text");
  const at = box.selectionStart ?? box.value.length;
  const before = box.value.slice(0, at), after = box.value.slice(box.selectionEnd ?? at);
  const pad = s => (s && !s.endsWith("\n\n") ? (s.endsWith("\n") ? "\n" : "\n\n") : "");
  const lead = pad(before), tail = after && !after.startsWith("\n") ? "\n\n" : "";
  box.value = before + lead + text + tail + after;
  box.focus();
  box.dispatchEvent(new Event("input"));
}
const snippet = name => `![${say("describe")}](asset:${name})`;

function renderAssets() {
  const ul = $("assets");
  ul.replaceChildren();
  const row = (name, thumb, info, removable, onRename) => {
    const li = document.createElement("li");
    const img = document.createElement("img");
    if (thumb) img.src = thumb;
    img.alt = "";
    const body = document.createElement("div");
    const input = document.createElement("input");
    input.value = name; input.setAttribute("aria-label", "name"); input.maxLength = 60; input.readOnly = !removable;
    if (removable) input.addEventListener("change", () => onRename(input));
    const small = document.createElement("span"); small.className = "note"; small.textContent = info;
    const code = document.createElement("code"); code.textContent = snippet(name);
    const actions = document.createElement("div"); actions.className = "actions";
    const ins = document.createElement("button"); ins.type = "button"; ins.className = "btn"; ins.textContent = say("insert");
    ins.onclick = () => insertAtCursor(snippet(name));
    actions.append(ins);
    if (removable) {
      const rm = document.createElement("button"); rm.type = "button"; rm.className = "btn"; rm.textContent = say("remove");
      rm.onclick = () => { attached.splice(attached.findIndex(a => a.name === name), 1); renderAssets(); validate(); };
      actions.append(rm);
    }
    body.append(input, small, code, actions);
    li.append(img, body);
    ul.append(li);
  };
  for (const a of attached) {
    row(a.name, a.preview, `${Math.round(a.size / 1024)} KB`, true, input => {
      const old = a.name;
      const next = NAME_RE.test(input.value.trim().toLowerCase()) ? uniqueName(input.value.trim().toLowerCase(), old) : old;
      if (next !== old) {                  // keep the text in step with the new name
        a.name = next;
        $("text").value = $("text").value.replace(new RegExp(`asset:${escapeRe(old)}(?![a-z0-9._-])`, "g"), `asset:${next}`);
      }
      renderAssets(); validate();
    });
  }
  for (const name of existing) row(name, "", say("already"), false);
  $("imgs-note").textContent = attached.length ? `${attached.length}/${MAX_IMAGES}` : "";
}

async function addImages(files) {
  const note = $("imgs-note");
  let problem = "";                     // the last thing that went wrong stays visible after the list is redrawn
  for (const file of files) {
    if (attached.length >= MAX_IMAGES) { problem = say("tooMany"); break; }
    if (!ACCEPT.includes(file.type)) { problem = say("badType", file.name); continue; }
    note.textContent = say("reducing");
    try {
      const { blob, mime } = await shrinkImage(file);
      const b64 = await blobToBase64(blob);
      attached.push({ name: uniqueName(slugName(file.name, mime)), mime, size: blob.size, b64, preview: `data:${mime};base64,${b64}` });
    } catch (e) {
      problem = e instanceof ImageError && e.code === "size" ? say("bigImage", file.name) : say("badImage", file.name);
    }
  }
  renderAssets();
  if (problem) note.textContent = problem;
  validate();
}
$("imgs").addEventListener("change", async e => { const files = [...e.target.files]; e.target.value = ""; await addImages(files); });

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
  if (current.warnings && current.warnings.length) {
    const ul = document.createElement("ul");
    ul.className = "issues warn";
    for (const e of current.warnings) { const li = document.createElement("li"); li.textContent = e; ul.append(li); }
    box.append(ul);
  }
}

let timer = null;
function validate() {
  const text = $("text").value;
  if (!text.trim()) current = null;
  else {
    try { current = checkBundle(text, { assets: assetNames() }); }
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
async function fillImages(html) {
  const tpl = document.createElement("template");
  tpl.innerHTML = html;
  for (const img of tpl.content.querySelectorAll("img[data-asset]")) {
    const name = img.dataset.asset;
    const local = attached.find(a => a.name === name);
    let src = local ? local.preview : null;
    if (!src && existing.includes(name)) {
      try { const a = await getAsset(editId, name, LATEST); if (a) src = `data:${a.mime};base64,${a.data}`; } catch (e) { /* shown as a missing image */ }
    }
    if (src) { img.setAttribute("src", src); img.removeAttribute("loading"); }
  }
  return tpl.innerHTML;
}
async function previewDoc(l) {
  if (pageCss === null) pageCss = await (await fetch("../assets/page.css")).text();
  const meta = { id: editId || "PHZ-????", title: current.meta.title, summary: current.meta.summary, systems: current.meta.systems, status: "draft",
                 authors: [$("by").value.trim() || "—"], collaborators: names($("collabs").value), reviewers: [], created: new Date().toISOString().slice(0, 10) };
  const { html } = pageBody(current.bodies[l].body, l);
  const withImages = await fillImages(sanitize(html));
  const mermaid = new URL("../assets/mermaid.min.js", location.href).href;
  return `<!doctype html><html lang="${BCP[l]}"><head><meta charset="utf-8"><style>${pageCss}</style></head><body>` +
    `<div style="max-width:860px;margin:0 auto;padding:16px"><div class="lang active" data-lang="${l}" lang="${BCP[l]}">${heroHtml(meta, l)}${withImages}</div></div>` +
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
  clearTimeout(timer); validate();                                              // the text may have changed within the debounce delay
  if (!enabled) { note.textContent = say("off"); return; }
  if (!current || !current.ok) return;
  if (!by) { note.textContent = say("needName"); $("by").focus(); return; }
  store.set("phiz-rfc-author", by);
  $("publish").disabled = true;
  note.textContent = say("publishing");
  const args = { meta: current.meta, bundle: $("text").value, by, collaborators: names($("collabs").value) };
  try {
    const used = attached.filter(a => current.images.includes(a.name));        // images the text does not use are not sent
    if (used.length) {
      args.token = crypto.randomUUID();
      for (let i = 0; i < used.length; i++) {
        note.textContent = say("sending", i + 1, used.length);
        await stageAsset({ token: args.token, name: used[i].name, mime: used[i].mime, data: used[i].b64, by });
      }
      note.textContent = say("publishing");
    }
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
  try { existing = [...new Set((await listAssets(editId)).map(a => a.name))].sort(); } catch (e) { existing = []; }
  renderAssets();
  validate();
}
if (/^PHZ-\d{4}$/.test(editId) && enabled) loadForEdit();
else renderResult();
