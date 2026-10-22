/* What is checked in the browser before an RFC is uploaded (rules B01-B07 of docs/spec/rfc-bundle.md), and what the preview shows.
   The database function create_rfc repeats the size, metadata and marker checks for anyone who calls it directly. */
import { structure } from "./blocks.js";
import { parseBundle } from "./bundle.js";
import { RfcError, renderBody } from "./markdown.js";
import { LANGS } from "./page.js";

export const MAX_BUNDLE = 600000;

function todoErrors(md) {
  const errors = [];
  for (const l of LANGS) {
    const lines = (md[l] || "").split("\n");
    const hits = lines.map((x, i) => (x.includes("TODO:") ? i + 1 : 0)).filter(Boolean);
    if (hits.length) errors.push(`The ${l.toUpperCase()} section still has ${hits.length} TODO: marker${hits.length > 1 ? "s" : ""} (first at line ${hits[0]} of that section).`);
  }
  return errors;
}

// the image names (![alt](asset:name)) a rendered body uses
export function assetNames(bodyHtml) {
  const doc = new DOMParser().parseFromString(`<body>${bodyHtml}</body>`, "text/html");
  return [...new Set([...doc.body.querySelectorAll("img[data-asset]")].map(i => i.dataset.asset))].sort();
}

/* → { ok, errors, warnings, meta, md, bodies, images } ; `bodies[lang]` is { body, ids } with `§` ids when every language rendered.
   `assets` are the names of the images that will be available: the files attached now, plus the ones the RFC already has when editing. */
export function checkBundle(text, { assets = [] } = {}) {
  const errors = [];
  const warnings = [];
  if (String(text).length > MAX_BUNDLE) errors.push(`The file is too large (${Math.round(String(text).length / 1000)} KB; the limit is ${MAX_BUNDLE / 1000} KB).`);
  const { meta, md, errors: parseErrors } = parseBundle(text);
  errors.push(...parseErrors.filter(e => !/TODO:/.test(e)));
  errors.push(...parseErrors.filter(e => /TODO:/.test(e)));
  if (LANGS.every(l => md[l])) errors.push(...todoErrors(md));

  const bodies = {};
  if (LANGS.every(l => md[l])) {
    for (const l of LANGS) {
      try { bodies[l] = renderBody(md[l], l, { html: false }); }
      catch (e) {
        if (!(e instanceof RfcError)) throw e;
        errors.push(`${l.toUpperCase()}: ${e.message}`);
      }
    }
  }
  if (LANGS.every(l => bodies[l])) {
    const ids = l => bodies[l].ids;
    for (const l of ["en", "zh"]) {
      if (ids(l).join() !== ids("pt").join()) errors.push(`Section ids differ between PT and ${l.toUpperCase()}: PT has ${ids("pt").join(", ")}; ${l.toUpperCase()} has ${ids(l).join(", ")}.`);
    }
    if (ids("en").join() === ids("pt").join() && ids("zh").join() === ids("pt").join()) {
      const st = Object.fromEntries(LANGS.map(l => [l, structure(bodies[l].body)]));
      ids("pt").forEach((sid, k) => {
        const n = LANGS.map(l => st[l].blocks[k]);
        if (new Set(n).size > 1) errors.push(`Section "${sid}" has a different number of paragraphs, list items, tables, diagrams or code blocks: PT ${n[0]} · EN ${n[1]} · ZH ${n[2]} (comments on a paragraph use these numbers).`);
      });
      const d = LANGS.map(l => st[l].diagrams);
      if (new Set(d).size > 1) errors.push(`Different number of diagrams: PT ${d[0]} · EN ${d[1]} · ZH ${d[2]}.`);
      for (const l of ["en", "zh"]) {
        const a = st.pt.code.map(c => c.replace(/\s+/g, "")), b = st[l].code.map(c => c.replace(/\s+/g, ""));
        if (a.length !== b.length) errors.push(`Different number of code blocks: PT ${a.length} · ${l.toUpperCase()} ${b.length}.`);
        else if (a.join("\u0000") !== b.join("\u0000")) errors.push(`Code blocks in ${l.toUpperCase()} are not identical to PT (samples are shared across languages; comments in English).`);
      }
    }
  }
  let images = [];
  if (LANGS.every(l => bodies[l])) {
    const names = Object.fromEntries(LANGS.map(l => [l, assetNames(bodies[l].body)]));
    images = [...new Set(LANGS.flatMap(l => names[l]))].sort();
    if (LANGS.some(l => names[l].join() !== names.pt.join())) {
      errors.push(`The three languages must use the same images: PT uses ${names.pt.join(", ") || "none"}; EN ${names.en.join(", ") || "none"}; ZH ${names.zh.join(", ") || "none"}.`);
    }
    for (const n of images) if (!assets.includes(n)) errors.push(`The text uses the image "${n}" but it is not attached.`);
    for (const n of assets) if (!images.includes(n)) warnings.push(`The image "${n}" is attached but not used in the text, so it will not be sent.`);
  }
  return { ok: errors.length === 0, errors, warnings, meta, md, bodies, images };
}
