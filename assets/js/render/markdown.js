/* Markdown → RFC body HTML in the browser. A port of tools/rfc_md.py (render_body): same sections, directives, tables, diagrams
   and code figures, so an RFC looks the same whether the build or the browser renders it. tests/test_parity.py renders the same
   files with both and compares the result.

   Needs window.markdownit and window.markdownitContainer (assets/vendor/). */
import { CODE_LANGS, codeFigure, esc } from "./highlight.js";

export class RfcError extends Error {}

export const NOTE_LABELS = {
  note: { pt: "Nota", en: "Note", zh: "备注" },
  decision: { pt: "Decisão", en: "Decision", zh: "决定" },
  risk: { pt: "A confirmar", en: "To confirm", zh: "待确认" }
};
const TABLE_VARIANTS = ["changes", "num", "map"];
const CHIPS = { eq: "st eq", ch: "st ch", gap: "st gap", new: "st new", yes: "yes", no: "no", part: "part" };
const CHIP_RE = new RegExp("^\\[([^\\[\\]\\n]+)\\]\\{(" + Object.keys(CHIPS).join("|") + ")\\}");
const BR_RE = /^<br\s*\/?>/;
const METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const SLUG = /^[a-z0-9][a-z0-9-]*$/;
const ASSET = /^asset:([a-z0-9][a-z0-9._-]{0,59})$/;

function parser(html) {
  if (!window.markdownit || !window.markdownitContainer) throw new RfcError("markdown-it is not loaded");
  const md = window.markdownit("commonmark", { html }).enable("table");
  const container = (name, render) => md.use(window.markdownitContainer, name, { validate: params => params.trim().split(" ")[0] === name, render });

  const noteRender = name => (tokens, idx, options, env) => {
    const tok = tokens[idx];
    if (tok.nesting === 1) {
      const label = tok.info.trim().slice(name.length).trim() || NOTE_LABELS[name][env.lang];
      return `<div class="note-box${name === "note" ? "" : " " + name}"><span class="lbl">${esc(label)}</span>\n`;
    }
    return "</div>\n";
  };
  for (const name of ["note", "decision", "risk"]) container(name, noteRender(name));
  container("table", (tokens, idx, options, env) => {
    const tok = tokens[idx];
    if (tok.nesting === 1) {
      const variant = tok.info.trim().slice("table".length).trim();
      if (variant && !TABLE_VARIANTS.includes(variant)) throw new RfcError(`::: table ${variant}: unknown variant (use ${TABLE_VARIANTS.join(", ")})`);
      env.tbl = variant ? " " + variant : "";
    }
    return "";
  });
  for (const name of ["stats", "phases", "questions", "endpoints", "gallery", "screens", "legend", "caption"]) container(name, () => "");   // rewritten by the core rule below

  // [text]{eq}: a small coloured label; <br> is the only HTML a table cell may use (same as tools/rfc_md.py)
  md.inline.ruler.before("link", "rfc_chip", (state, silent) => {
    const m = state.src[state.pos] === "[" ? CHIP_RE.exec(state.src.slice(state.pos)) : null;
    if (!m) return false;
    if (!silent) { const tok = state.push("rfc_chip", "", 0); tok.content = m[1]; tok.meta = { kind: m[2] }; }
    state.pos += m[0].length;
    return true;
  });
  md.inline.ruler.before("html_inline", "rfc_br", (state, silent) => {
    const m = state.src[state.pos] === "<" ? BR_RE.exec(state.src.slice(state.pos)) : null;
    if (!m) return false;
    if (!silent) state.push("rfc_br", "br", 0);
    state.pos += m[0].length;
    return true;
  });
  md.renderer.rules.rfc_chip = (tokens, idx) => `<span class="${CHIPS[tokens[idx].meta.kind]}">${esc(tokens[idx].content)}</span>`;
  md.renderer.rules.rfc_br = () => "<br>";

  md.renderer.rules.table_open = (tokens, idx, options, env) => {
    const v = env.tbl || "";
    delete env.tbl;
    return `<div class="tbl${v}"><table>\n`;
  };
  md.renderer.rules.table_close = () => "</table></div>\n";

  md.renderer.rules.fence = (tokens, idx, options, env) => {
    const tok = tokens[idx];
    const info = tok.info.trim();
    const sp = info.search(/\s/);
    const lang = (sp === -1 ? info : info.slice(0, sp)).toLowerCase();
    const rest = sp === -1 ? "" : info.slice(sp).trim();
    if (lang === "mermaid") {
      const cap = rest ? `<p class="cap">${md.renderInline(rest, env)}</p>\n` : "";   // the caption may use inline Markdown
      return `<div class="diagram"><pre class="mermaid">\n${esc(tok.content)}</pre></div>\n${cap}`;
    }
    if (!CODE_LANGS.includes(lang)) throw new RfcError(`line ${tok.map[0] + 1}: code block needs a language (${CODE_LANGS.join(", ")} or mermaid), got '${lang}'`);
    return codeFigure(lang, tok.content);
  };

  // ![alt](asset:name.png) is an image attached to an RFC created on the site: the page fills in `src` after loading it from the database
  const defaultImage = md.renderer.rules.image;
  md.renderer.rules.image = (tokens, idx, options, env, slf) => {
    const tok = tokens[idx];
    const m = ASSET.exec(tok.attrGet("src") || "");
    if (!m) return defaultImage(tokens, idx, options, env, slf);
    const title = tok.attrGet("title");
    return `<img data-asset="${esc(m[1])}" alt="${esc(slf.renderInlineAsText(tok.children, options, env))}"${title ? ` title="${esc(title)}"` : ""} loading="lazy">`;
  };

  md.core.ruler.push("rfc_blocks", coreRule);
  return md;
}

const htmlBlock = (state, text) => {
  const t = new state.Token("html_block", "", 0);
  t.content = text;
  return t;
};
const renderInlineTokens = (state, inline) => state.md.renderer.renderInline(inline.children || [], state.md.options, state.env);

// the inline token of each list item found in `inner`
function listItems(inner) {
  return inner.filter((t, i) => t.type === "inline" && i > 0 && inner[i - 1].type === "paragraph_open" &&
    inner.slice(Math.max(0, i - 2), i).some(x => x.type === "list_item_open"));
}

function coreRule(state) {
  if (state.inlineMode) return;       // md.renderInline() (captions, endpoint descriptions) runs the core rules too
  const toks = state.tokens, env = state.env;
  if (!env.ids) env.ids = [];
  const out = [];
  let i = 0, inSection = false, number = 0;
  const line = t => (t.map ? t.map[0] + 1 : "?");
  while (i < toks.length) {
    const t = toks[i];
    if (t.type === "heading_open" && t.tag === "h2") {
      const inline = toks[i + 1];
      const m = /\s*\{#([^}\s]*)\}\s*$/.exec(inline.content);
      if (!m || !SLUG.test(m[1])) throw new RfcError(`line ${line(t)}: a level-2 heading needs a lowercase id, e.g. '## Summary {#summary}'`);
      const sid = m[1];
      if (env.ids.includes(sid)) throw new RfcError(`line ${line(t)}: duplicate section id '${sid}'`);
      inline.content = inline.content.slice(0, m.index);
      for (const child of [...(inline.children || [])].reverse()) {
        if (child.type === "text") { child.content = child.content.replace(/\s*\{#[^}\s]*\}\s*$/, ""); break; }
      }
      number += 1;
      env.ids.push(sid);
      out.push(htmlBlock(state, (inSection ? "</section>\n" : "") + `<section>\n<h2 id="§${sid}"><span class="n">${String(number).padStart(2, "0")}</span>`),
        inline, htmlBlock(state, "</h2>\n"));
      inSection = true;
      i += 3;
      continue;
    }
    if (!inSection) {
      if (t.type === "html_block" && t.content.trim().startsWith("<!--")) { i += 1; continue; }
      throw new RfcError(`line ${line(t)}: content before the first '##' section heading`);
    }
    const m = /^container_(stats|phases|questions|endpoints|gallery|screens|legend|caption)_open$/.exec(t.type);
    if (m) {
      const name = m[1];
      let j = i + 1;
      while (j < toks.length && toks[j].type !== `container_${name}_close`) j += 1;
      if (j >= toks.length) throw new RfcError(`line ${line(t)}: ':::' ${name} block is not closed`);
      out.push(...directive(state, name, toks.slice(i + 1, j), line(t), t.info));
      i = j + 1;
      continue;
    }
    out.push(t);
    i += 1;
  }
  if (inSection) out.push(htmlBlock(state, "</section>\n"));
  state.tokens = out;
}

function directive(state, name, inner, line, info = "") {
  if (name === "questions") {
    const lists = inner.filter(t => t.type === "ordered_list_open");
    if (!lists.length) throw new RfcError(`line ${line}: ::: questions needs a numbered list`);
    lists[0].attrSet("class", "qs");
    return inner;
  }
  if (name === "gallery") {
    // a list; each item is an attached image followed by its caption: '- ![alt](asset:b01.png) **B01.** Caption'
    const items = listItems(inner);
    if (!items.length) throw new RfcError(`line ${line}: ::: gallery needs a list like '- ![alt](asset:name.png) **A1.** Caption'`);
    const variant = info.trim().slice("gallery".length).trim();
    if (variant !== "" && variant !== "phones") throw new RfcError(`line ${line}: ::: gallery ${variant}: unknown variant (use phones, or nothing)`);
    const render = kids => state.md.renderer.renderInline(kids, state.md.options, state.env);
    const shots = items.map(it => {
      const kids = it.children || [];
      const at = kids.findIndex(c => c.type === "image");
      if (at === -1) throw new RfcError(`line ${line}: each gallery item starts with an image: '- ![alt](asset:name.png) Caption'`);
      const cap = render([...kids.slice(0, at), ...kids.slice(at + 1)]).trim();
      return `<div class="shot">${render([kids[at]])}` + (cap ? `<p class="cap">${cap}</p>` : "") + "</div>";
    });
    return [htmlBlock(state, `<div class="shots${variant ? " phones" : ""}">\n` + shots.join("\n") + "\n</div>\n")];
  }
  if (name === "caption") {       // a note under a table or a code block; it takes no comment number
    const inlines = inner.filter(t => t.type === "inline");
    if (inlines.length !== 1) throw new RfcError(`line ${line}: ::: caption holds one paragraph`);
    return [htmlBlock(state, `<p class="cap">${renderInlineTokens(state, inlines[0])}</p>\n`)];
  }
  if (name === "legend") {
    const items = listItems(inner);
    if (!items.length) throw new RfcError(`line ${line}: ::: legend needs a list like '- [same]{eq} what it means'`);
    return [htmlBlock(state, '<div class="legend">' + items.map(it => `<span>${renderInlineTokens(state, it)}</span>`).join("") + "</div>\n")];
  }
  if (name === "screens") {
    // '##### Title | Where it shows' headings, each followed by a list: a card per menu item
    const out = [];
    let open = false, k = 0;
    while (k < inner.length) {
      const t = inner[k];
      if (t.type === "heading_open" && t.tag === "h5") {
        const text = inner[k + 1].content, cut = text.indexOf(" | ");
        const title = cut === -1 ? text : text.slice(0, cut), path = cut === -1 ? "" : text.slice(cut + 3);
        out.push(htmlBlock(state, (open ? "</div>\n" : "") + `<div class="screen"><h5>${esc(title.trim())}</h5>` +
          (path.trim() ? `<span class="path">${esc(path.trim())}</span>` : "") + "\n"));
        open = true;
        k += 3;
        continue;
      }
      if (!open) throw new RfcError(`line ${line}: ::: screens must start with a '##### Title | Where it shows' heading`);
      out.push(t);
      k += 1;
    }
    if (!open) throw new RfcError(`line ${line}: ::: screens needs at least one '##### Title | Where it shows' heading`);
    return [htmlBlock(state, '<div class="screens">\n'), ...out, htmlBlock(state, "</div>\n</div>\n")];
  }
  if (name === "stats") {
    const items = listItems(inner);
    if (!items.length) throw new RfcError(`line ${line}: ::: stats needs a list like '- **8** integrations today'`);
    const rows = items.map(it => {
      const m = /^<strong>(.*?)<\/strong>\s*(.*)$/s.exec(renderInlineTokens(state, it));
      if (!m) throw new RfcError(`line ${line}: each stat starts with a bold number: '- **8** text'`);
      return `<div class="stat"><b>${m[1]}</b><span>${m[2]}</span></div>`;
    });
    return [htmlBlock(state, '<div class="stats">\n' + rows.join("\n") + "\n</div>\n")];
  }
  if (name === "endpoints") {
    const items = listItems(inner);
    if (!items.length) throw new RfcError(`line ${line}: ::: endpoints needs a list like '- POST /v1/payment — what it does'`);
    const re = new RegExp("^(" + METHODS.join("|") + ")\\s+`?([^\\s`]+)`?\\s+[—–-]+\\s+(.+)$", "s");
    const rows = items.map(it => {
      const m = re.exec(it.content.trim());
      if (!m) throw new RfcError(`line ${line}: endpoint items look like 'POST /v1/payment — what it does', got '${it.content.trim().slice(0, 50)}'`);
      const desc = state.md.renderInline(m[3], state.env);
      return `<div class="ep"><span class="m m-${m[1].toLowerCase()}">${m[1]}</span><code class="p">${esc(m[2])}</code><span class="d">${desc}</span></div>`;
    });
    return [htmlBlock(state, '<div class="eps">\n' + rows.join("\n") + "\n</div>\n")];
  }
  // phases: each '##### TAG: Name' heading opens a card that runs until the next one
  const out = [];
  let open = false, first = true, k = 0;
  while (k < inner.length) {
    const t = inner[k];
    if (t.type === "heading_open" && t.tag === "h5") {
      const m = /^(.*?)\s*[:：]\s*(.+)$/.exec(inner[k + 1].content);
      if (!m) throw new RfcError(`line ${line}: phase headings look like '##### PHASE 1: Name'`);
      out.push(htmlBlock(state, (open ? "</div>\n" : "") +
        `<div class="phase${first ? " first" : ""}"><span class="tag">${esc(m[1])}</span><h5>${esc(m[2])}</h5>\n`));
      open = true; first = false;
      k += 3;
      continue;
    }
    if (!open) throw new RfcError(`line ${line}: ::: phases must start with a '##### PHASE 0: Name' heading`);
    out.push(t);
    k += 1;
  }
  if (!open) throw new RfcError(`line ${line}: ::: phases needs at least one '##### PHASE N: Name' heading`);
  return [htmlBlock(state, '<div class="phases">\n'), ...out, htmlBlock(state, "</div>\n</div>\n")];
}

// CommonMark does not close `**bold：**中文` when punctuation touches a CJK letter: turn the `**…**` pairs left over in running
// text (never inside <pre> or <code>) into <strong>, block by block
function cjkBold(body) {
  const keep = [];
  body = body.replace(/<pre\b[\s\S]*?<\/pre>|<code\b[\s\S]*?<\/code>/g, m => { keep.push(m); return `\x00${keep.length - 1}\x00`; });
  const parts = body.split(/(<\/?(?:p|li|td|th|h[1-6]|div|ul|ol|tr|section|table|thead|tbody|figure|blockquote|dd|dt)\b[^>]*>)/);
  for (let i = 0; i < parts.length; i += 2) parts[i] = parts[i].replace(/\*\*([^*\n]+?)\*\*/g, "<strong>$1</strong>");
  return parts.join("").replace(/\x00(\d+)\x00/g, (m, d) => keep[Number(d)]);
}

// Without raw HTML, an HTML comment would show up as text. Comments (the template's guidance, for instance) are dropped,
// except inside fenced code.
function stripComments(text) {
  const keep = [];
  text = text.replace(/^(`{3,}|~{3,})[^\n]*\n[\s\S]*?^\1[ \t]*$/gm, m => { keep.push(m); return `\x00${keep.length - 1}\x00`; });
  text = text.replace(/<!--[\s\S]*?-->/g, "");
  return text.replace(/\x00(\d+)\x00/g, (m, d) => keep[Number(d)]);
}

/* Markdown → { body, ids }. `html` lets raw HTML through: only for files that live in the repository (trusted). Anything a
   visitor submits is rendered with html:false and sanitized (sanitize.js). */
export function renderBody(text, lang, { html = false } = {}) {
  if (!html) text = stripComments(text);
  const md = parser(html);
  const env = { lang, ids: [] };
  let body = md.render(text, env);
  const ids = env.ids;
  if (!ids.length) throw new RfcError("no '##' sections found");
  body = body.replace(/href="#([a-z0-9-]+)"/g, (m, sid) => {
    if (!ids.includes(sid)) throw new RfcError(`link to #${sid} does not match any section id (${ids.join(", ")})`);
    return `href="#§${sid}"`;
  });
  return { body: cjkBold(body), ids };
}
