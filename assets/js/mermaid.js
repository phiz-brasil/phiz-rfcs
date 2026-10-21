import { dark } from "./util.js";

export function initMermaid() {
  if (!window.mermaid) return;
  window.mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: dark() ? "dark" : "neutral", flowchart: { htmlLabels: true } });
}
export async function renderMermaid() {
  if (!window.mermaid) return;
  const nodes = [...document.querySelectorAll(".lang.active pre.mermaid:not([data-processed])")];
  if (!nodes.length) return;
  try { await window.mermaid.run({ nodes }); } catch (e) { console.warn("mermaid", e); }
}
