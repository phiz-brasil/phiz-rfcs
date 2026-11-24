/* The page of an RFC created on the site: /rfc/?id=PHZ-1001[&v=1.2]. It reads the revision from the database, turns the
   single-file RFC into the same page the build produces for repository RFCs (assets/js/render/, no raw HTML, sanitized) and then
   starts the usual page scripts: comments, reactions, status, versions. */
import { base64ToBlob } from "./images.js";
import { LiveError, enabled, getAssetRow, getLatestRevision, getRevision, getTheme, listArchived, listAssets, listRevisions } from "./live-api.js";
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
const THEME_STATUS = {
  not_started: { pt: "Não iniciado", en: "Not started", zh: "未开始" }, on_track: { pt: "No prazo", en: "On track", zh: "按计划" },
  at_risk: { pt: "Em risco", en: "At risk", zh: "有风险" }, blocked: { pt: "Bloqueado", en: "Blocked", zh: "受阻" },
  paused: { pt: "Pausado", en: "Paused", zh: "已暂停" }, done: { pt: "Concluído", en: "Done", zh: "已完成" },
  cancelled: { pt: "Cancelado", en: "Cancelled", zh: "已取消" }
};
const STAGE = {
  1: { pt: "01 Solicitação", en: "01 Request", zh: "01 需求提出" }, 2: { pt: "02 Pesquisa", en: "02 Research", zh: "02 需求调研" },
  3: { pt: "03 Decisão", en: "03 Decision", zh: "03 立项决策" }, 4: { pt: "04 PRD e início", en: "04 PRD and kickoff", zh: "04 PRD 与启动" },
  5: { pt: "05 Revisão da solução", en: "05 Solution review", zh: "05 方案评审" }, 6: { pt: "06 Planejamento", en: "06 Planning", zh: "06 项目排期" },
  7: { pt: "07 Desenvolvimento", en: "07 Build", zh: "07 开发" }, 8: { pt: "08 Testes", en: "08 QA", zh: "08 测试验收" },
  9: { pt: "09 Publicação", en: "09 Release", zh: "09 发布准备" }, 10: { pt: "10 Lançamento", en: "10 Launch", zh: "10 上线收口" }
};
/* The status of an RFC that is a theme: the theme's status and, for projects, its stage (the old status picker goes away). */
const themeLabel = theme => Object.fromEntries(LANGS.map(l => [l, THEME_STATUS[theme.status][l] + (theme.stage ? ` · ${STAGE[theme.stage][l]}` : "")]));
const spans = (o, cls) => LANGS.map(l => `<span data-l="${l}"${cls ? ` class="${cls}"` : ""}>${esc(o[l])}</span>`).join("");
const main = () => document.querySelector("main");

function message(key) {
  main().innerHTML = `<p class="live-state">${spans(T[key])}</p>`;
  window.phizApplyLang && window.phizApplyLang();
}

const LOCALES = { pt: "pt-BR", en: "en-US", zh: "zh-CN" };
/* The moment a version was published, in the reader's time zone and language. Versions imported from the repository only know the
   day (they were stored at 12:00 UTC as a placeholder), so they show the date alone. */
function stamp(iso) {
  const d = new Date(iso);
  if (!iso || isNaN(d)) return "";
  const dayOnly = /T12:00:00(\.0+)?(Z|\+00:00)$/.test(iso);
  const out = {};
  for (const l of LANGS) out[l] = d.toLocaleString(LOCALES[l], dayOnly ? { dateStyle: "medium", timeZone: "UTC" } : { dateStyle: "medium", timeStyle: "short" });
  return spans(out);
}

function versionsHtml(revs, shown, rfcId, archived = []) {
  const latest = revs[0].version;
  const items = revs.map(r => {
    const cur = r.version === latest;
    const head = `<a href="?id=${esc(rfcId)}&v=${esc(r.version)}"><b>v${esc(r.version)}</b>${cur ? spans(T.current, "vtag") : ""}<time datetime="${esc(r.created_at || "")}">${stamp(r.created_at)}</time></a>`;
    const who = `<div class="vnote-wrap"><span class="vnote">${esc(r.edited_by)}${r.note ? " · " + esc(r.note) : ""}</span></div>`;
    return `<li${r.version === shown ? ' aria-current="true"' : ""}>${head}${who}</li>`;
  }).join("") + archived.map(a =>
    `<li><a href="../${esc(a.href)}"><b>v${esc(a.version)}</b><time>${esc(a.date || "")}</time></a><div class="vnote-wrap">${spans(a.note || {}, "vnote")}</div></li>`).join("");
  return `<details class="vers"><summary class="rfcno ver" aria-label="Version">v${esc(shown)}</summary><div class="vers-pop"><h3>${spans(T.versions)}</h3><ul>${items}</ul>` +
    `<p class="vnote-wrap"><a href="../nova/?edit=${esc(rfcId)}">${spans(T.newVersion)}</a></p></div></details>`;
}

/* The images of the RFC: `![alt](asset:name)` renders as <img data-asset="name">. Reading an image is what costs egress (its bytes travel as base64), so
   (docs/spec/v2/quota.md) an image is read only when it is about to be seen — its language is on screen and it is near the viewport — and once read it is kept in
   the browser under the row that answered (`<rfc>/<name>@<rev>`; a row never changes, a new revision is a new row), so a reload, another language or another
   version that uses the same row reads nothing. The list of rows (names and revisions, no bytes) is read once to know which row answers for a version.
   A click opens the image full size. */
const ASSET_CACHE = "phiz-rfc-assets-v1";
async function openAssetCache() {
  try { return await caches.open(ASSET_CACHE); } catch (e) { return null; }          // private mode, an old browser, or blocked: the page works, without the memory
}

async function hydrateAssets(root, rfcId, rev) {
  let index = [];
  try { index = await listAssets(rfcId); } catch (e) { /* every image is then shown as missing */ }
  const cache = await openAssetCache();
  const urls = new Map();                                                           // "<name>@<row rev>" -> Promise<blob address | null>
  const rowFor = name => index.filter(r => r.name === name && r.rev <= rev).sort((a, b) => b.rev - a.rev)[0] || null;
  const key = (name, row) => new Request(`${location.origin}/__rfc-asset/${rfcId}/${encodeURIComponent(name)}@${row.rev}`);

  async function addressOf(name) {
    const row = rowFor(name);
    if (!row) return null;
    const k = `${name}@${row.rev}`;
    if (!urls.has(k)) {
      urls.set(k, (async () => {
        try {
          const hit = cache ? await cache.match(key(name, row)).catch(() => null) : null;
          if (hit) return URL.createObjectURL(await hit.blob());
          const a = await getAssetRow(rfcId, name, row.rev);
          if (!a) return null;
          const blob = base64ToBlob(a.data, a.mime);
          if (cache) cache.put(key(name, row), new Response(blob, { headers: { "Content-Type": a.mime } })).catch(() => { /* quota or blocked: not remembered */ });
          return URL.createObjectURL(blob);
        } catch (e) { return null; }
      })());
    }
    return urls.get(k);
  }

  async function show(img) {
    const url = await addressOf(img.dataset.asset);
    if (!url) { img.classList.add("missing"); return; }
    img.src = url;
    img.classList.add("zoomable");
    img.addEventListener("click", () => window.open(url, "_blank", "noopener"));
  }

  const imgs = [...root.querySelectorAll("img[data-asset]")];
  if (typeof IntersectionObserver === "undefined") { imgs.forEach(show); return; }
  // a printout needs every image of the language on screen, seen or not
  window.addEventListener("beforeprint", () => imgs.filter(i => i.closest(".lang.active") && !i.classList.contains("missing")).forEach(i => {
    watcher.unobserve(i);
    i.loading = "eager";                                                          // the page's own `loading=lazy` would still hold the picture back
    if (!i.getAttribute("src")) void show(i);
  }));
  // an image in a hidden language has no box, so it is not "intersecting" until that language is chosen
  const watcher = new IntersectionObserver(entries => entries.forEach(e => {
    if (e.isIntersecting) { watcher.unobserve(e.target); void show(e.target); }
  }), { rootMargin: "600px 0px" });
  imgs.forEach(img => watcher.observe(img));
}

/* Versions that exist only as archived pages, older than what the database holds: attachments of the theme (phase 8). Each leads to the attachments of the theme. */
async function archivedVersions(revs) {
  try {
    const have = new Set(revs.map(x => x.version));
    const seen = new Set();
    return (await listArchived(id))
      .filter(a => !have.has(a.archive_version) && !seen.has(a.archive_version) && seen.add(a.archive_version))
      .map(a => ({ version: a.archive_version, date: a.archive_date, note: a.archive_note, href: `themes/${id}/#attachments` }))
      .sort((a, b) => b.version.localeCompare(a.version, undefined, { numeric: true }));
  } catch (e) { return []; }
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
  const theme = await getTheme(id).catch(() => null);
  if (theme && !THEME_STATUS[theme.status]) theme.status = "not_started";
  const meta = { id, title: row.meta.title, summary: row.meta.summary, systems: row.meta.systems || [], status: "draft",
                 authors: row.authors, collaborators: row.collaborators || [], reviewers: row.meta.reviewers || [],
                 created: row.meta.created || (revs[revs.length - 1].created_at || "").slice(0, 10) };
  if (theme) { meta.statusLabel = themeLabel(theme); meta.statusKey = theme.status; }
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
  const badge = theme
    ? `<a class="rfcno st theme-st" href="../themes/${esc(id)}/" data-st="${esc(theme.status)}">${LANGS.map(l => `<span class="lang-st" data-l="${l}">${esc(themeLabel(theme)[l])}</span>`).join("")}</a>`
    : `<span class="rfcno st" data-st="draft">${LANGS.map(l => `<span class="lang-st" data-l="${l}">${esc(STATUS.draft[l])}</span>`).join("")}</span>`;
  const edit = `<a class="rfcno newver" href="../nova/?edit=${esc(id)}">✎ ${spans(T.newVersion)}</a>`;      // always in sight, not only inside the history
  no.insertAdjacentHTML("afterend", badge + versionsHtml(revs, row.version, id, await archivedVersions(revs)) + edit);
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
  window.PHIZ_THEME_STATUS = !!theme;                           // status.js leaves the badge alone: the theme owns the status
  await import("./main.js");                                   // comments, reactions, paragraphs, Mermaid, drawer
  const s = document.createElement("script");                  // status badge and picker
  s.src = "../assets/status.js";
  document.body.append(s);
}

start();
