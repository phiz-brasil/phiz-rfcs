/* The page of an RFC created on the site: /rfc/?id=PHZ-1001[&v=1.2]. It reads the revision from the database, turns the
   single-file RFC into the same page the build produces for repository RFCs (assets/js/render/, no raw HTML, sanitized) and then
   starts the usual page scripts: comments, reactions, status, versions. */
import { base64ToBlob } from "./images.js";
import { LiveError, enabled, getAsset, getLatestRevision, getRevision, listRevisions } from "./live-api.js";
import { parseBundle } from "./render/bundle.js";
import { renderBody } from "./render/markdown.js";
import { BCP, LANGS, STATUS, heroHtml, pageBody } from "./render/page.js";
import { esc } from "./render/highlight.js";
import { sanitize } from "./render/sanitize.js";

const params = new URLSearchParams(location.search);
const id = (params.get("id") || "").toUpperCase();
const wanted = params.get("v");
const T = {
  loading: { pt: "Carregando a RFC…", en: "Loading the RFC…", zh: "正在加载 RFC…" },
  notFound: { pt: "RFC não encontrada.", en: "RFC not found.", zh: "未找到该 RFC。" },
  failed: { pt: "Não foi possível carregar a RFC. Tente de novo.", en: "Could not load the RFC. Please try again.", zh: "无法加载 RFC，请重试。" },
  broken: { pt: "Esta versão não pôde ser exibida: o arquivo dela tem um problema.", en: "This version cannot be shown: its file has a problem.", zh: "无法显示此版本：其文件有问题。" },
  versions: { pt: "Histórico de versões", en: "Version history", zh: "版本历史" },
  current: { pt: "atual", en: "current", zh: "当前" },
  newVersion: { pt: "Nova versão", en: "New version", zh: "新版本" },
  by: { pt: "por", en: "by", zh: "由" },
  archived: { pt: (v, c) => `Você está lendo a versão ${v}, arquivada e somente leitura. A versão atual é a ${c}.`,
              en: (v, c) => `You are reading version ${v}, archived and read-only. The current version is ${c}.`,
              zh: (v, c) => `你正在阅读已存档的只读版本 ${v}。当前版本为 ${c}。` },
  goCurrent: { pt: "Ver versão atual", en: "View current version", zh: "查看当前版本" }
};
const spans = (o, cls) => LANGS.map(l => `<span data-l="${l}"${cls ? ` class="${cls}"` : ""}>${esc(o[l])}</span>`).join("");
const main = () => document.querySelector("main");

function message(key) {
  main().innerHTML = `<p class="live-state">${spans(T[key])}</p>`;
  window.phizApplyLang && window.phizApplyLang();
}

function versionsHtml(revs, shown, rfcId) {
  const latest = revs[0].version;
  const items = revs.map(r => {
    const cur = r.version === latest;
    const head = `<a href="?id=${esc(rfcId)}&v=${esc(r.version)}"><b>v${esc(r.version)}</b>${cur ? spans(T.current, "vtag") : ""}<time>${esc((r.created_at || "").slice(0, 10))}</time></a>`;
    const who = `<div class="vnote-wrap"><span class="vnote">${esc(r.edited_by)}${r.note ? " · " + esc(r.note) : ""}</span></div>`;
    return `<li${r.version === shown ? ' aria-current="true"' : ""}>${head}${who}</li>`;
  }).join("");
  return `<details class="vers"><summary class="rfcno ver" aria-label="Version">v${esc(shown)}</summary><div class="vers-pop"><h3>${spans(T.versions)}</h3><ul>${items}</ul>` +
    `<p class="vnote-wrap"><a href="../nova/?edit=${esc(rfcId)}">${spans(T.newVersion)}</a></p></div></details>`;
}

/* The images of the RFC: `![alt](asset:name)` renders as <img data-asset="name">; each is read from the database (the newest of that
   name up to this version) and shown from a local blob. A click opens it full size. */
async function hydrateAssets(root, rfcId, rev) {
  const urls = new Map();
  const imgs = [...root.querySelectorAll("img[data-asset]")];
  await Promise.all(imgs.map(async img => {
    const name = img.dataset.asset;
    if (!urls.has(name)) {
      urls.set(name, getAsset(rfcId, name, rev).then(a => (a ? URL.createObjectURL(base64ToBlob(a.data, a.mime)) : null)).catch(() => null));
    }
    const url = await urls.get(name);
    if (!url) { img.classList.add("missing"); return; }
    img.src = url;
    img.classList.add("zoomable");
    img.addEventListener("click", () => window.open(url, "_blank", "noopener"));
  }));
}

async function start() {
  if (!/^PHZ-\d{4}$/.test(id) || !enabled) return message("notFound");
  message("loading");
  let revs, row;
  try {
    revs = await listRevisions(id);
    if (!revs.length) return message("notFound");
    row = wanted && wanted !== revs[0].version ? await getRevision(id, wanted) : await getLatestRevision(id);
  } catch (e) { return message(e instanceof LiveError && e.code === "invalid" ? "notFound" : "failed"); }
  if (!row) return message("notFound");
  const frozen = row.version !== revs[0].version;

  const parsed = parseBundle(row.bundle);
  if (parsed.errors.length) return message("broken");
  const meta = { id, title: row.meta.title, summary: row.meta.summary, systems: row.meta.systems || [], status: "draft",
                 authors: row.authors, collaborators: row.collaborators || [], reviewers: [], created: (revs[revs.length - 1].created_at || "").slice(0, 10) };
  const blocks = [], tocs = [];
  try {
    for (const l of LANGS) {
      const { body } = renderBody(parsed.md[l], l, { html: false });
      const page = pageBody(body, l);
      blocks.push(`<div class="lang" data-lang="${l}" lang="${BCP[l]}">${heroHtml(meta, l)}${sanitize(page.html)}</div>`);
      tocs.push(`<ol class="toc-list" data-lang="${l}" lang="${BCP[l]}">${sanitize(page.toc)}</ol>`);
    }
  } catch (e) { return message("broken"); }

  document.title = `RFC ${id} · ${meta.title.en}${frozen ? ` · v${row.version}` : ""}`;
  const no = document.querySelector(".rfcno");
  no.textContent = `RFC ${id}`;
  const badge = `<span class="rfcno st" data-st="draft">${LANGS.map(l => `<span class="lang-st" data-l="${l}">${esc(STATUS.draft[l])}</span>`).join("")}</span>`;
  no.insertAdjacentHTML("afterend", badge + versionsHtml(revs, row.version, id));
  if (frozen) {
    document.querySelector("header.bar").insertAdjacentHTML("afterend",
      `<div class="ver-banner" role="note">${LANGS.map(l => `<span data-l="${l}">${esc(T.archived[l](row.version, revs[0].version))}</span>`).join("")} ` +
      `<a href="?id=${esc(id)}">${spans(T.goCurrent)}</a></div>`);
  }
  main().innerHTML = blocks.join("\n");
  hydrateAssets(main(), id, row.rev);
  document.querySelector(".toc details").insertAdjacentHTML("beforeend", tocs.join("\n"));
  window.phizApplyLang();

  window.PHIZ_RFC_ID = id;
  window.PHIZ_FROZEN = frozen;
  await import("./main.js");                                   // comments, reactions, paragraphs, Mermaid, drawer
  const s = document.createElement("script");                  // status badge and picker
  s.src = "../assets/status.js";
  document.body.append(s);
}

start();
