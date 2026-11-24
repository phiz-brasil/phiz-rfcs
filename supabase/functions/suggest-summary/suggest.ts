// What the "Suggest with AI" button of a theme does, without the network: which documents are read (the RFC, notes, text attachments, recent weekly
// updates), how they are put to the model, and how its answer is checked. Pure (no Deno, no fetch), so Node runs it in tests/test_suggest.py.
//
// The rule that matters: the model may only answer from the documents, and an answer is kept only if at least one quotation it gives is found
// WORD FOR WORD in the document it names. An answer without a verifiable quotation becomes "missing" with a sentence saying what is missing; nothing
// is ever invented to fill a gap. A person always confirms or edits what is kept.
export const FIELDS = ["problem", "solution", "success"] as const;
export type Field = typeof FIELDS[number];
export type Texts = Partial<Record<"pt" | "en" | "zh", string>>;
export type Source = { id: string; label: string; text: string };
export type Raw = {
  rfcBundle?: string | null;
  notes: { name: string; body: string }[];
  files: { name: string; text: string }[];
  updates: { week: string; progress?: Texts; advanced?: Texts; next_step?: Texts }[];
  theme: { title?: Texts; what_it_is?: Texts; progress?: Texts };
};
export type Cited = { label: string; quote: string };
export type Answer = { text: string | null; sources: Cited[]; missing: string | null };

export const MISSING: Record<Field, string> = {
  problem: "Os documentos não explicam qual problema este tema trata.",
  solution: "Os documentos não descrevem a solução proposta.",
  success: "Os documentos não dizem como o sucesso será medido.",
};
// The model reads at most 24 000 tokens (prompt + answer): about 36 000 characters of documents leave room for the instructions and the answer.
// Each kind of document has its own share, so a long RFC cannot push the notes and the weekly updates out.
const BUDGET = { rfc: 18_000, notes: 7_000, files: 6_000, rest: 5_000 }, PER_SOURCE_MAX = 8_000, PER_SOURCE_MIN = 600;
const MAX_PER_GROUP = { rfc: 20, notes: 8, files: 6, rest: 8 }, MAX_TEXT = 500, MAX_QUOTES = 3, MIN_QUOTE = 12;

const pick = (t?: Texts | null) => (t?.pt ?? t?.en ?? t?.zh ?? "").trim();
const clip = (s: string, n: number) => (s.length > n ? s.slice(0, n) : s);

/* the pt (or else en, zh) section of an RFC bundle, split at its "## " headings: one source per section, so a citation says where in the RFC */
export function rfcSections(bundle: string): { heading: string; text: string }[] {
  const text = bundle.replace(/\r\n?/g, "\n");
  const marks = [...text.matchAll(/^[ \t]*<!--\s*lang:\s*(pt|en|zh)\s*-->[ \t]*$/gm)];
  if (!marks.length) return [];
  const body = (lang: string) => {
    const i = marks.findIndex(m => m[1] === lang);
    if (i < 0) return null;
    const start = marks[i].index! + marks[i][0].length;
    const end = i + 1 < marks.length ? marks[i + 1].index! : text.length;
    return text.slice(start, end);
  };
  const md = body("pt") ?? body("en") ?? body("zh") ?? "";
  const out: { heading: string; text: string }[] = [];
  let heading = "Introdução", buf: string[] = [];
  const flush = () => { const t = buf.join("\n").trim(); if (t) out.push({ heading, text: t }); };
  for (const line of md.split("\n")) {
    const h = /^##\s+(.*)$/.exec(line);
    if (h) {
      flush();
      heading = h[1].replace(/\s*\{[^}]*\}\s*$/, "").replace(/[*_`#]/g, "").trim() || "Seção";          // "Resumo {summary}": the {id} is an anchor, not a title
      buf = [];
    } else buf.push(line);
  }
  flush();
  return out;
}

export function buildSources(raw: Raw): Source[] {
  const groups: { budget: number; max: number; items: { label: string; text: string }[] }[] = [
    { budget: BUDGET.rfc, max: MAX_PER_GROUP.rfc, items: rfcSections(raw.rfcBundle ?? "").map(s => ({ label: `RFC — ${s.heading}`, text: s.text })) },
    { budget: BUDGET.notes, max: MAX_PER_GROUP.notes, items: raw.notes.map(n => ({ label: `Nota — ${n.name}`, text: n.body })) },
    { budget: BUDGET.files, max: MAX_PER_GROUP.files, items: raw.files.map(f => ({ label: `Anexo — ${f.name}`, text: f.text })) },
    { budget: BUDGET.rest, max: MAX_PER_GROUP.rest, items: [] },
  ];
  const th = [pick(raw.theme.what_it_is), pick(raw.theme.progress)].filter(Boolean).join("\n");
  if (th) groups[3].items.push({ label: "Tema — o que é e andamento", text: th });
  for (const u of raw.updates) {
    const t = [pick(u.progress), pick(u.advanced), pick(u.next_step)].filter(Boolean).join("\n");
    if (t) groups[3].items.push({ label: `Atualização semanal ${u.week}`, text: t });
  }
  const list: { label: string; text: string }[] = [];
  for (const g of groups) {
    const items = g.items.filter(s => s.text.trim()).slice(0, g.max);
    const cap = Math.max(PER_SOURCE_MIN, Math.min(PER_SOURCE_MAX, Math.floor(g.budget / Math.max(1, items.length))));
    let left = g.budget;
    for (const s of items) {
      if (left <= 0) break;
      const text = clip(s.text.trim(), Math.min(cap, left));
      list.push({ label: s.label, text });
      left -= text.length;
    }
  }
  return list.map((s, i) => ({ id: `S${i + 1}`, label: s.label, text: s.text }));
}

export function buildPrompt(title: string, sources: Source[]): { system: string; user: string } {
  const system = [
    "Você resume temas de trabalho para a liderança, SOMENTE a partir dos documentos fornecidos.",
    "Responda três perguntas: problem (que problema o tema trata), solution (qual é a solução proposta, em resumo) e success (o que é sucesso e como saberemos que foi atingido).",
    "Regras: use apenas o que está escrito nos documentos; não invente nem complete com conhecimento próprio.",
    `Cada resposta tem no máximo ${MAX_TEXT} caracteres, em português do Brasil, objetiva.`,
    `Cada resposta traz de 1 a ${MAX_QUOTES} citações COPIADAS LITERALMENTE de um documento, no formato {"source":"S2","quote":"trecho exato"}.`,
    'Se os documentos não permitem responder, use "text": null, "quotes": [] e, em "missing", uma frase dizendo o que falta.',
    'Responda APENAS com JSON: {"problem":{"text":...,"quotes":[...],"missing":...},"solution":{...},"success":{...}}.',
  ].join("\n");
  const docs = sources.map(s => `### ${s.id} · ${s.label}\n${s.text}`).join("\n\n");
  return { system, user: `Tema: ${title}\n\nDocumentos:\n\n${docs}` };
}

/* the first JSON object in the model's answer (models like to wrap it in prose or a code fence) */
export function parseModelJson(raw: unknown): unknown {
  if (raw && typeof raw === "object") return raw;
  if (typeof raw !== "string") return null;
  const s = raw.replace(/```(?:json)?/gi, "");
  for (let i = s.indexOf("{"); i >= 0; i = s.indexOf("{", i + 1)) {
    let depth = 0, inStr = false, esc = false;
    for (let j = i; j < s.length; j++) {
      const c = s[j];
      if (inStr) { if (esc) esc = false; else if (c === "\\") esc = true; else if (c === '"') inStr = false; continue; }
      if (c === '"') inStr = true; else if (c === "{") depth++; else if (c === "}" && --depth === 0) {
        try { return JSON.parse(s.slice(i, j + 1)); } catch { break; }
      }
    }
  }
  return null;
}

const norm = (s: string) => s.toLowerCase().replace(/[*_`#>\[\]()"'“”‘’«»]/g, "").replace(/\s+/g, " ").trim();

export function validate(parsed: unknown, sources: Source[]): Record<Field, Answer> {
  const out = {} as Record<Field, Answer>;
  const byId = new Map(sources.map(s => [s.id, { s, n: norm(s.text) }]));
  for (const f of FIELDS) {
    const a = ((parsed as Record<string, unknown> | null)?.[f] ?? {}) as { text?: unknown; quotes?: unknown; missing?: unknown };
    const said = typeof a.missing === "string" ? clip(a.missing.trim(), 300) : "";
    const text = typeof a.text === "string" ? a.text.trim() : "";
    const cited: Cited[] = [];
    if (text && Array.isArray(a.quotes)) {
      for (const q of a.quotes as { source?: unknown; quote?: unknown }[]) {
        const hit = typeof q?.source === "string" ? byId.get(q.source) : undefined;
        const quote = typeof q?.quote === "string" ? q.quote.trim() : "";
        if (!hit || norm(quote).length < MIN_QUOTE || !hit.n.includes(norm(quote))) continue;      // not found word for word in that document: dropped
        if (!cited.some(c => c.quote === quote && c.label === hit.s.label)) cited.push({ label: hit.s.label, quote: clip(quote, 400) });
        if (cited.length === MAX_QUOTES) break;
      }
    }
    out[f] = text && cited.length
      ? { text: clip(text, MAX_TEXT), sources: cited, missing: null }
      : { text: null, sources: [], missing: text ? `${said || MISSING[f]} (a resposta sugerida não tinha citação verificável nos documentos)` : said || MISSING[f] };
  }
  return out;
}

/* The same rule as public.is_member() in the database: an address of the company domain (docs/spec/v2/login.md). */
export const memberEmail = (email: unknown): boolean => typeof email === "string" && /^[^@\s]+@phizchat\.com$/i.test(email.trim());
