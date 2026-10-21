/* The single-file RFC (docs/spec/rfc-bundle.md): a metadata block, then one section per language.

   ---
   title_pt: …     title_en: …     title_zh: …
   summary_pt: …   summary_en: …   summary_zh: …
   systems: channel, card-vault
   ---
   <!-- lang:pt -->  …Markdown…
   <!-- lang:en -->  …Markdown…
   <!-- lang:zh -->  …Markdown… */
import { LANGS } from "./page.js";

const MARK = /^[ \t]*<!--\s*lang:\s*(pt|en|zh)\s*-->[ \t]*$/;

/* Reads a bundle. Never throws: problems go in `errors`, so a form can show them all at once. */
export function parseBundle(text) {
  const errors = [];
  // guidance comments may come before the metadata block
  const src = String(text).replace(/^\uFEFF/, "").replace(/\r\n?/g, "\n").replace(/^(?:\s*<!--[\s\S]*?-->)*\s*/, "");
  const m = /^---\n([\s\S]*?)\n---[ \t]*(?:\n|$)/.exec(src);
  const kv = {};
  if (!m) errors.push("The file must start with the metadata block between two '---' lines.");
  else {
    for (const line of m[1].split("\n")) {
      if (!line.trim() || line.trim().startsWith("#")) continue;
      const k = /^([a-z_]+):[ \t]*(.*)$/.exec(line);
      if (!k) errors.push(`Metadata line not understood: ${line.trim().slice(0, 60)}`);
      else kv[k[1]] = k[2].trim();
    }
  }
  if (/TODO:/.test(kv.systems || "")) errors.push("Metadata systems still has a TODO: marker (list the systems, or leave it empty).");
  const meta = { title: {}, summary: {}, systems: (kv.systems || "").split(",").map(s => s.trim()).filter(Boolean) };
  for (const l of LANGS) {
    for (const key of ["title", "summary"]) {
      const v = kv[`${key}_${l}`];
      if (!v) errors.push(`Metadata is missing ${key}_${l}.`);
      else if (/TODO:/.test(v)) errors.push(`Metadata ${key}_${l} still has a TODO: marker.`);
      meta[key][l] = v || "";
    }
  }
  const md = {};
  const lines = (m ? src.slice(m[0].length) : src).split("\n");
  let cur = null;
  const seen = [];
  const preamble = [];
  for (const line of lines) {
    const mm = MARK.exec(line);
    if (mm) {
      cur = mm[1];
      if (seen.includes(cur)) errors.push(`The language marker <!-- lang:${cur} --> appears more than once.`);
      seen.push(cur);
      md[cur] = [];
    } else if (cur) md[cur].push(line);
    else preamble.push(line);
  }
  const stray = preamble.join("\n").replace(/<!--[\s\S]*?-->/g, "").trim();     // guidance comments are fine, text is not
  if (stray) errors.push(`Text before the first language marker: ${stray.slice(0, 60)}`);
  for (const l of LANGS) {
    if (!md[l]) errors.push(`Missing the section <!-- lang:${l} -->.`);
    else md[l] = md[l].join("\n").trim() + "\n";
  }
  return { meta, md, errors };
}

/* The inverse: the file a person downloads to edit an existing RFC. */
export function buildBundle(meta, md) {
  const head = ["---", ...LANGS.map(l => `title_${l}: ${meta.title[l]}`), ...LANGS.map(l => `summary_${l}: ${meta.summary[l]}`),
    `systems: ${(meta.systems || []).join(", ")}`, "---", ""];
  return head.join("\n") + LANGS.map(l => `<!-- lang:${l} -->\n\n${md[l].trim()}\n`).join("\n");
}
