import { lang } from "./i18n.js";
import { cfg, rfcId } from "./state.js";

export const dark = () => matchMedia("(prefers-color-scheme: dark)").matches || document.documentElement.dataset.theme === "dark";

export const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
export function sectionKey(h) { return h.id.replace(/^(pt|en|zh)-/, ""); }
export function titleOf(h) { const c = h.cloneNode(true); c.querySelectorAll(".cmt-btn").forEach(x => x.remove()); c.querySelectorAll(".n").forEach(x => x.append(" ")); return c.textContent.replace(/\s+/g, " ").trim(); }
export function issueUrl(key, title) {
  const t = encodeURIComponent(`[${rfcId} · ${key}] `);
  const b = encodeURIComponent(`RFC: ${rfcId}\nSection: ${title}\nLink: ${location.href.split("#")[0]}#${key}\n\n`);
  return `https://github.com/${cfg.repo}/issues/new?labels=rfc-comment&title=${t}&body=${b}`;
}
export function when(iso) {
  const loc = { pt: "pt-BR", en: "en-US", zh: "zh-CN" }[lang()];
  try { return new Date(iso).toLocaleString(loc, { dateStyle: "medium", timeStyle: "short" }); } catch (e) { return iso; }
}
export const store = {
  get(k) { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
};

export const ts = iso => Date.parse(iso) || 0;
