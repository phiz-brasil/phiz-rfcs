/* The header and the contents list of an RFC page. A port of hero_html and the TOC code in tools/rfc_md.py; the parity tests
   compare the two. */
import { esc } from "./highlight.js";

export const LANGS = ["pt", "en", "zh"];
export const BCP = { pt: "pt-BR", en: "en-US", zh: "zh-CN" };

export const STATUS = {
  "draft":       { pt: "Rascunho",     en: "Draft",       zh: "草稿" },
  "in-review":   { pt: "Em revisão",   en: "In review",   zh: "评审中" },
  "approved":    { pt: "Aprovada",     en: "Approved",    zh: "已批准" },
  "implemented": { pt: "Implementada", en: "Implemented", zh: "已实现" },
  "rejected":    { pt: "Rejeitada",    en: "Rejected",    zh: "已拒绝" },
  "superseded":  { pt: "Substituída",  en: "Superseded",  zh: "已被取代" }
};
const HERO = {
  pt: { status: "Status", author: "Autor", collaborators: "Colaboradores", date: "Data", reviewers: "Revisores", systems: "Sistemas", tbd: "A definir" },
  en: { status: "Status", author: "Author", collaborators: "Collaborators", date: "Date", reviewers: "Reviewers", systems: "Systems", tbd: "To be defined" },
  zh: { status: "状态", author: "作者", collaborators: "协作者", date: "日期", reviewers: "评审人", systems: "系统", tbd: "待定" }
};
const COUNTRY = { BR: { pt: "Brasil", en: "Brazil", zh: "巴西" }, CN: { pt: "China", en: "China", zh: "中国" } };

// a value that may be plain text (same in every language) or {pt, en, zh}
export function loc(value, lang) {
  if (value && typeof value === "object") return value[lang] || value.pt || Object.values(value)[0] || "";
  return value;
}

function reviewerText(r, lang) {
  if (r && typeof r === "object" && "name" in r) {
    const c = COUNTRY[r.country];
    if (c) return lang === "zh" ? `${r.name}（${c[lang]}）` : `${r.name} (${c[lang]})`;
    return r.name;
  }
  return loc(r, lang);
}

function dateText(iso, lang) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
  return m && lang === "pt" ? `${m[3]}/${m[2]}/${m[1]}` : (iso || "");
}

export function heroHtml(meta, lang, status) {
  const h = HERO[lang], st = status || meta.status;
  const label = esc(STATUS[st][lang]);
  const list = a => (a || []);
  const rows = [
    `<div><dt>${h.status}</dt><dd><span class="pill" data-st="${st}">${label}</span></dd></div>`,
    `<div><dt>${h.author}</dt><dd>${esc(list(meta.authors).map(a => loc(a, lang)).join(", ") || "—")}</dd></div>`,
    ...(list(meta.collaborators).length ? [`<div><dt>${h.collaborators}</dt><dd>${esc(meta.collaborators.map(c => loc(c, lang)).join(", "))}</dd></div>`] : []),
    `<div><dt>${h.date}</dt><dd>${esc(dateText(meta.created, lang))}</dd></div>`,
    `<div><dt>${h.reviewers}</dt><dd>${list(meta.reviewers).map(r => esc(reviewerText(r, lang))).join("<br>") || h.tbd}</dd></div>`
  ];
  for (const extra of list(meta.details)) rows.push(`<div><dt>${esc(loc(extra.label, lang))}</dt><dd>${loc(extra.value, lang)}</dd></div>`);
  if (list(meta.systems).length) rows.push(`<div><dt>${h.systems}</dt><dd>${esc(meta.systems.join(" · "))}</dd></div>`);
  return `<header class="hero">\n  <div class="eyebrow">RFC ${esc(meta.id)} · ${label}</div>\n  <h1>${esc(meta.title[lang])}</h1>\n` +
    `  <p class="lede">${esc(meta.summary[lang])}</p>\n  <dl class="meta">\n    ${rows.join("\n    ")}\n  </dl>\n</header>\n`;
}

/* `body` is renderBody()'s HTML with `§` ids: the page copy of it (ids prefixed by the language) and its contents list. */
export function pageBody(body, lang) {
  const html = body.replace(/id="§/g, `id="${lang}-`).replace(/href="#§/g, `href="#${lang}-`);
  const re = new RegExp(`<h2 id="${lang}-([^"]+)">([\\s\\S]*?)</h2>`, "g");
  const toc = [...html.matchAll(re)].map(m =>
    `<li><a href="#${lang}-${m[1]}">${m[2].replace(/<span class=.n.>[\s\S]*?<\/span>/g, "").replace(/<[^>]+>/g, "").trim()}</a></li>`).join("");
  return { html, toc };
}
