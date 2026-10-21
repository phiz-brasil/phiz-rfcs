/* Hosted-RFC enhancements: Mermaid rendering for the active language, comments (per section, per paragraph, reactions),
   the comments drawer and the language-aware wiring. Comments use Supabase when site.config.json has comments.supabaseUrl and
   comments.supabaseKey (stored on the page, no GitHub login); otherwise giscus, otherwise a pre-filled GitHub issue.
   Modules: state (config and shared values) · i18n · util · api (Supabase) · model (what a comment is) ·
   threads (lists, form, reactions, delete) · panels (section and paragraph boxes, counters, highlights) · drawer · select · mermaid. */
import { loadAll } from "./api.js";
import { paintAllBtn, renderDrawer } from "./drawer.js";
import { lang } from "./i18n.js";
import { initMermaid, renderMermaid } from "./mermaid.js";
import { decorate, decoratePara, openPanel, paintMarks } from "./panels.js";
import { S, frozen, sb } from "./state.js";
import { renderThreads, setQuote, setReply } from "./threads.js";
import { when } from "./util.js";

/* ---------- wiring ---------- */
export function refresh() {
  if (!frozen) { decorate(); if (sb) decoratePara(); }
  renderMermaid();
  if (sb) {
    // open panels live under one language's copy of the section: move them (with any draft) to the active language
    const cur = lang();
    document.querySelectorAll(".cmt-panel[data-key]").forEach(p => {
      if (p.dataset.para !== undefined) {       // a paragraph box closes when the language changes
        if (!p.closest(`.lang[data-lang="${cur}"]`)) { p.remove(); document.querySelectorAll(".cmt-pbtn[aria-expanded=true]").forEach(b => b.setAttribute("aria-expanded", "false")); }
        return;
      }
      const h = p.previousElementSibling;
      if (!h || h.id.startsWith(cur + "-")) return;
      const f = p.querySelector("form");
      const draft = f ? { parent: f.dataset.parent, quote: f.dataset.quote, body: f.querySelector("textarea").value } : null;
      p.remove();
      const ob = h.querySelector(".cmt-btn"); if (ob) ob.setAttribute("aria-expanded", "false");
      const nh = document.getElementById(`${cur}-${p.dataset.key}`);
      if (!nh || (nh.nextElementSibling && nh.nextElementSibling.classList.contains("cmt-panel"))) return;
      openPanel(nh, nh.querySelector(".cmt-btn"));
      const np = nh.nextElementSibling;
      if (draft && np && np.querySelector("form")) {
        np.querySelector("textarea").value = draft.body;
        if (draft.quote) setQuote(np, draft.quote);
        const parent = draft.parent && (S.all || []).find(c => c.id === draft.parent);
        if (parent) setReply(np, parent);
      }
    });
    paintMarks(); paintAllBtn(); if (S.drawer) renderDrawer();
    document.querySelectorAll(".cmt-panel[data-key]").forEach(renderThreads);   // comments follow the page language
  }
}

// close the version history when clicking elsewhere
document.addEventListener("click", e => { document.querySelectorAll("details.vers[open]").forEach(d => { if (!d.contains(e.target)) d.open = false; }); });

initMermaid();
new MutationObserver(refresh).observe(document.documentElement, { attributes: true, attributeFilter: ["data-lang"] });
window.addEventListener("load", refresh);
document.addEventListener("DOMContentLoaded", refresh);
if (document.readyState !== "loading") refresh();
if (sb) loadAll();
