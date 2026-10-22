import { L, lang } from "./i18n.js";
import { paraBlocks } from "./render/blocks.js";
import { forSection } from "./model.js";
import { S, cfg, rfcId, sb } from "./state.js";
import { buildForm, renderThreads, setQuote, setReply } from "./threads.js";
import { el, issueUrl, sectionKey, titleOf } from "./util.js";

export function paintCounts() {
  document.querySelectorAll(".lang h2[id] .cmt-btn").forEach(b => {
    const n = forSection(sectionKey(b.closest("h2"))).length;
    let c = b.querySelector(".cmt-n");
    if (!c) { c = el("span", "cmt-n"); b.append(c); }
    c.textContent = n ? String(n) : "";
    c.hidden = !n;
  });
  document.querySelectorAll(".cmt-pbtn").forEach(b => {
    const h = b.closest("section") && b.closest("section").querySelector("h2[id]");
    if (!h) return;
    const n = forSection(sectionKey(h), Number(b.dataset.i)).length;
    const c = b.querySelector(".cmt-n");
    c.textContent = n ? String(n) : "";
    c.hidden = !n;
    b.classList.toggle("has", !!n);
  });
}

/* Highlight commented passages in the active language, Confluence-style. */
export function paintMarks() {
  document.querySelectorAll("mark.cmt-mark").forEach(m => { const p = m.parentNode; m.replaceWith(...m.childNodes); p.normalize(); });
  if (!S.all) return;
  const cur = lang();
  for (const c of S.all) {
    if (!c.quote || c.parent_id || c.lang !== cur) continue;
    const h = document.getElementById(`${cur}-${c.section}`);
    const sec = h && h.closest("section");
    if (!sec) continue;
    const walker = document.createTreeWalker(sec, NodeFilter.SHOW_TEXT, {
      acceptNode: n => n.parentElement.closest("h2, .cmt-panel, pre, figure, mark") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT
    });
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const i = n.data.indexOf(c.quote);
      if (i < 0) continue;
      const r = document.createRange();
      r.setStart(n, i); r.setEnd(n, i + c.quote.length);
      const m = el("mark", "cmt-mark");
      m.dataset.id = c.id;
      m.title = `${c.author}: ${c.body.slice(0, 120)}`;
      r.surroundContents(m);
      m.addEventListener("click", () => openPanel(h, h.querySelector(".cmt-btn"), { focusId: c.id }));
      break;
    }
  }
}

/* ---------- one comment box per paragraph ---------- */
export function decoratePara() {
  if (!S.HAS_PARA) return;
  document.querySelectorAll(".lang section").forEach(sec => {
    const h = sec.querySelector("h2[id]");
    if (!h) return;
    const key = sectionKey(h);
    paraBlocks(sec).forEach((blk, i) => {
      if (blk._pb) return;
      blk._pb = true;
      const b = el("button", "cmt-pbtn"); b.type = "button"; b.dataset.i = String(i);
      b.title = L().paraBtn; b.setAttribute("aria-label", L().paraBtn); b.setAttribute("aria-expanded", "false");
      b.append(el("span", null, "💬"), el("span", "cmt-n"));
      b.addEventListener("click", () => openParaPanel(blk, key, i, b));
      blk.classList.add("cmt-pb");
      if (blk.matches(".tbl, .diagram, figure")) blk.classList.add("cmt-pb-in");
      blk.append(b);
    });
  });
  paintCounts();
}

export function openParaPanel(blk, key, idx, btn) {
  const inLi = blk.matches("li");
  const existing = inLi ? [...blk.children].find(c => c.classList.contains("cmt-panel"))
                        : (blk.nextElementSibling && blk.nextElementSibling.dataset.para !== undefined ? blk.nextElementSibling : null);
  if (existing) { existing.remove(); btn.setAttribute("aria-expanded", "false"); return; }
  const panel = el("div", "cmt-panel cmt-para-panel");
  panel.dataset.key = key; panel.dataset.para = String(idx);
  panel._form = buildForm(panel);
  panel.append(el("div", "cmt-list"), panel._form);
  renderThreads(panel);
  if (inLi) blk.append(panel); else blk.after(panel);
  btn.setAttribute("aria-expanded", "true");
}

export function flashPara(c) {
  const h = document.getElementById(`${lang()}-${c.section}`);
  const sec = h && h.closest("section");
  const blk = sec && paraBlocks(sec)[c.para];
  if (!blk) return;
  blk.scrollIntoView({ block: "center" });
  blk.classList.add("cmt-pflash");
  setTimeout(() => blk.classList.remove("cmt-pflash"), 1800);
}

/* ---------- panel ---------- */
export const giscusReady = () => cfg.repo && cfg.repo !== "OWNER/REPO" && cfg.giscus && cfg.giscus.repoId && cfg.giscus.categoryId;

export function openPanel(h, btn, opts) {
  opts = opts || {};
  const key = sectionKey(h);
  let panel = h.nextElementSibling;
  const isOpen = panel && panel.classList.contains("cmt-panel");
  if (isOpen && !opts.quote && !opts.focusId) { panel.remove(); btn.setAttribute("aria-expanded", "false"); return; }
  if (!isOpen) {
    panel = el("div", "cmt-panel");
    if (sb) {
      panel.dataset.key = key;
      panel._form = buildForm(panel);
      panel.append(el("div", "cmt-list"), panel._form);
      renderThreads(panel);
    } else if (giscusReady()) {
      const s = document.createElement("script");
      s.src = "https://giscus.app/client.js"; s.async = true; s.crossOrigin = "anonymous";
      const a = {
        repo: cfg.repo, "repo-id": cfg.giscus.repoId, category: cfg.giscus.category, "category-id": cfg.giscus.categoryId,
        mapping: "specific", term: `${rfcId}#${key}`, strict: "0", "reactions-enabled": "1", "emit-metadata": "0",
        "input-position": "top", theme: "preferred_color_scheme", lang: { pt: "pt", en: "en", zh: "zh-CN" }[lang()], loading: "lazy"
      };
      Object.entries(a).forEach(([k, v]) => s.setAttribute("data-" + k, v));
      panel.append(el("p", "cmt-note", L().need), s);
    } else {
      const p = el("p", "cmt-note");
      const link = el("a", null, L().fallback);
      link.href = issueUrl(key, titleOf(h)); link.target = "_blank"; link.rel = "noopener";
      p.append(link); panel.append(p);
    }
    h.after(panel);
    btn.setAttribute("aria-expanded", "true");
  }
  if (sb && opts.quote) { setReply(panel, null); setQuote(panel, opts.quote); }
  if (opts.focusId) {
    const item = panel.querySelector(`.cmt-item[data-id="${CSS.escape(opts.focusId)}"]`);
    if (item) { item.scrollIntoView({ block: "center" }); item.classList.add("cmt-flash"); setTimeout(() => item.classList.remove("cmt-flash"), 1600); }
  }
}

export function decorate() {
  document.querySelectorAll(".lang h2[id]").forEach(h => {
    if (h.querySelector(".cmt-btn")) return;
    const b = document.createElement("button");
    b.type = "button"; b.className = "cmt-btn"; b.setAttribute("aria-expanded", "false");
    b.innerHTML = '<span aria-hidden="true">💬</span> <span class="cmt-l"></span>';
    b.addEventListener("click", () => openPanel(h, b));
    h.append(b);
  });
  document.querySelectorAll(".cmt-btn .cmt-l").forEach(n => { n.textContent = L().btn; });
  if (sb) paintCounts();
}
