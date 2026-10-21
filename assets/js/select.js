import { L } from "./i18n.js";
import { openPanel } from "./panels.js";
import { sb } from "./state.js";
import { el } from "./util.js";

export let fab = null;
export function hideFab() { if (fab) fab.hidden = true; }
export function onSelect() {
  if (!sb) return;
  const s = getSelection();
  if (!s || s.isCollapsed || !s.rangeCount) return hideFab();
  const text = s.toString().replace(/\s+/g, " ").trim();
  const range = s.getRangeAt(0);
  const anc = range.commonAncestorContainer;
  const node = anc.nodeType === 1 ? anc : anc.parentElement;
  const sec = node && node.closest(".lang.active section");
  if (!text || text.length > 500 || !sec || node.closest(".cmt-panel, h2, pre, .cmt-fab")) return hideFab();
  const h = sec.querySelector("h2[id]");
  if (!h) return hideFab();
  if (!fab) {
    fab = el("button", "cmt-fab"); fab.type = "button";
    fab.addEventListener("mousedown", e => e.preventDefault());
    document.body.append(fab);
  }
  fab.textContent = "💬 " + L().quote;
  const rect = range.getBoundingClientRect();
  fab.style.top = `${window.scrollY + rect.top - 42}px`;
  fab.style.left = `${Math.max(8, Math.min(window.scrollX + rect.left, window.scrollX + innerWidth - 220))}px`;
  fab.hidden = false;
  fab.onclick = () => { hideFab(); getSelection().removeAllRanges(); openPanel(h, h.querySelector(".cmt-btn"), { quote: text }); };
}
document.addEventListener("mouseup", () => setTimeout(onSelect, 0));
document.addEventListener("keyup", e => { if (e.shiftKey) onSelect(); });
document.addEventListener("selectionchange", () => { const s = getSelection(); if (!s || s.isCollapsed) hideFab(); });
