/* Swagger UI for RFCs that publish an OpenAPI spec (rfcs/<ID>/openapi_gen.py): the page defines window.PHIZ_SPECS and
   window.PHIZ_YAML ({pt, en, zh}); the reference is redrawn when the language changes. */
(function () {
  const COPY = { pt: ["Copiado", "Selecione e copie o texto abaixo"], en: ["Copied", "Select and copy the text below"], zh: ["已复制", "请选中下方文本并复制"] };
  const lang = () => document.documentElement.dataset.lang || "pt";
  let shown = null;

  function render() {
    const l = lang();
    const box = document.getElementById("swagger-ui");
    if (l === shown || !box || !window.SwaggerUIBundle || !window.PHIZ_SPECS) return;
    shown = l;
    box.innerHTML = "";
    window.SwaggerUIBundle({
      spec: window.PHIZ_SPECS[l], dom_id: "#swagger-ui", deepLinking: false,
      supportedSubmitMethods: [], defaultModelsExpandDepth: 0, docExpansion: "list", tryItOutEnabled: false
    });
  }

  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (e) { return false; }
  }

  const btn = document.getElementById("copy-yaml");
  if (btn) btn.addEventListener("click", async () => {
    const text = window.PHIZ_YAML[lang()];
    const note = document.getElementById("copy-note");
    const fb = document.getElementById("yaml-fallback");
    const ok = await copyText(text);
    if (ok) { note.textContent = COPY[lang()][0]; fb.hidden = true; }
    else { fb.value = text; fb.hidden = false; fb.select(); note.textContent = COPY[lang()][1]; }
    setTimeout(() => (note.textContent = ""), 2500);
  });

  new MutationObserver(render).observe(document.documentElement, { attributes: true, attributeFilter: ["data-lang"] });
  window.addEventListener("load", render);
  document.addEventListener("DOMContentLoaded", render);
  render();
})();
