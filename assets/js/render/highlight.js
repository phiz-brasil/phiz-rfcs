/* Code highlighting for the RFC page. A line-by-line port of tools/rfc_md.py (hl_json, hl_generic, code_figure): the two must
   produce the same markup, which tests/test_parity.py checks. */

export const CODE_LANGS = ["json", "bash", "http", "python", "yaml", "java", "javascript", "typescript", "dart", "kotlin", "go", "sql", "text"];

// same five entities as Python's html.escape
export function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
}

export function hlJson(src) {
  const out = [];
  const tok = /("(?:[^"\\]|\\.)*")(\s*:)?|(-?\b\d+(?:\.\d+)?\b)|\b(true|false|null)\b|([{}\[\],:])|(\s+)|([\s\S])/g;
  let m;
  while ((m = tok.exec(src)) !== null) {
    const [, s, colon, num, kw, punct, ws, other] = m;
    if (s !== undefined) out.push(`<span class="t-${colon ? "k" : "s"}">${esc(s)}</span>` + (colon ? esc(colon) : ""));
    else if (num !== undefined) out.push(`<span class="t-n">${num}</span>`);
    else if (kw !== undefined) out.push(`<span class="t-b">${kw}</span>`);
    else out.push(esc(punct || ws || other));
  }
  return out.join("");
}

const KEYWORDS = /\b(static|return|new|const|let|final|func|class|public|private|import|export|async|await|def|from)\b/g;
const COMMENTS = { bash: ["#"], yaml: ["#"], python: ["#"], http: ["#"], java: ["//"], javascript: ["//"], typescript: ["//"], dart: ["//"], kotlin: ["//"], go: ["//"], sql: ["--"] };
const KEYWORD_LANGS = ["java", "javascript", "typescript", "dart", "kotlin", "go"];
const HTTP_LINE = /^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|HTTP\/\d(?:\.\d)?)(\b.*)$/;
const HTTP_HEADER = /^([A-Za-z][A-Za-z0-9-]*)(:)( .*|)$/;

const span = (cls, text) => (text ? `<span class="t-${cls}">${esc(text)}</span>` : "");
const isSpace = ch => /\s/.test(ch);

function hlLine(line, lang) {
  const markers = COMMENTS[lang] || [];
  const out = [];
  let buf = [];
  const flush = () => {
    if (!buf.length) return;
    const text = buf.join("");
    if (KEYWORD_LANGS.includes(lang)) {
      let pos = 0;
      for (const m of text.matchAll(KEYWORDS)) {
        out.push(esc(text.slice(pos, m.index)) + span("k", m[0]));
        pos = m.index + m[0].length;
      }
      out.push(esc(text.slice(pos)));
    } else out.push(esc(text));
    buf = [];
  };
  let i = 0;
  const n = line.length;
  while (i < n) {
    const ch = line[i];
    const comment = markers.find(m => line.startsWith(m, i));
    if (comment && (comment !== "#" || i === 0 || isSpace(line[i - 1])) && !(comment === "//" && i > 0 && line[i - 1] === ":")) {
      flush();
      out.push(span("c", line.slice(i)));
      return out.join("");
    }
    if ("\"'`".includes(ch) && lang !== "http" && (lang === "javascript" || lang === "typescript" || ch !== "`")) {
      let j = line.indexOf(ch, i + 1);
      while (j !== -1 && line[j - 1] === "\\") j = line.indexOf(ch, j + 1);
      if (j !== -1) {
        flush();
        out.push(span("s", line.slice(i, j + 1)));
        i = j + 1;
        continue;
      }
    }
    buf.push(ch);
    i += 1;
  }
  flush();
  return out.join("");
}

export function hlGeneric(src, lang) {
  if (lang === "text" || !(lang in COMMENTS)) return esc(src);
  const out = [];
  for (const line of src.split("\n")) {
    if (lang === "http") {
      let m = HTTP_LINE.exec(line);
      if (m) { out.push(span("k", m[1]) + hlLine(m[2], lang)); continue; }
      m = HTTP_HEADER.exec(line);
      if (m) { out.push(span("h", m[1]) + esc(m[2]) + hlLine(m[3], lang)); continue; }
    }
    out.push(hlLine(line, lang));
  }
  return out.join("\n");
}

export function codeFigure(lang, src) {
  src = src.replace(/\n+$/, "");
  const body = lang === "json" ? hlJson(src) : hlGeneric(src, lang);
  return `<figure class="code"><figcaption><span>${esc(lang.toUpperCase())}</span><button type="button" class="copy" data-copy>COPY</button></figcaption><pre><code>${body}</code></pre></figure>\n`;
}
