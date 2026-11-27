// What plan-deck sends to the model and how it reads the answer. Pure, so Node runs it (tests/test_deck_plan.py). The model receives only the
// active themes (id, front, title, what it is, progress, status, dates, owner, open blockers and decisions, open milestones) and must answer with a deck
// plan whose every sentence names its theme; the page drops anything it cannot trace (apps/web/lib/deck-plan.ts).
export type Texts = Record<string, string | null | undefined> | null;
export type ThemeRow = { id: string; front: string; title: Texts; what_it_is: Texts; progress: Texts; status: string; start_date: string | null; due_date: string | null;
  owner: string | null };
export type OpenRow = { theme_id: string; what: Texts; urgency?: string | null; due_date: string | null; needs_leadership?: boolean };
export type Milestone = { theme_id: string; title: string; due_date: string | null };
export type Context = { themes: ThemeRow[]; blockers: OpenRow[]; decisions: OpenRow[]; milestones: Milestone[] };

export const MAX_REQUEST = 600;
const LANGS = ["pt", "en", "zh"];
const NAMES: Record<string, string> = { pt: "Brazilian Portuguese", en: "English", zh: "Simplified Chinese" };

export function said(t: Texts, lang: string): string {
  const v = t?.[lang]?.trim();
  if (v) return v;
  for (const l of LANGS) if (t?.[l]?.trim()) return t[l]!.trim();
  return "";
}

/* One compact block per theme, in the language of the deck when the text exists in it. */
export function contextText(c: Context, lang: string): string {
  return c.themes.map(t => {
    const lines = [`[${t.id}] ${said(t.title, lang)} — front ${t.front}, status ${t.status}, start ${t.start_date?.slice(0, 10) ?? "-"}, estimate ${t.due_date?.slice(0, 10) ?? "-"}, owner ${t.owner ?? "-"}`];
    const what = said(t.what_it_is, lang), prog = said(t.progress, lang);
    if (what) lines.push(`  what it is: ${what}`);
    if (prog) lines.push(`  progress: ${prog}`);
    for (const b of c.blockers.filter(x => x.theme_id === t.id)) lines.push(`  blocker (${b.urgency ?? "info"}${b.due_date ? `, by ${b.due_date.slice(0, 10)}` : ""}): ${said(b.what, lang)}`);
    for (const d of c.decisions.filter(x => x.theme_id === t.id)) lines.push(`  decision needed (${d.urgency ?? "info"}${d.due_date ? `, by ${d.due_date.slice(0, 10)}` : ""}): ${said(d.what, lang)}`);
    for (const m of c.milestones.filter(x => x.theme_id === t.id)) lines.push(`  milestone: ${m.title}${m.due_date ? ` on ${m.due_date.slice(0, 10)}` : ""}`);
    return lines.join("\n");
  }).join("\n");
}

export function buildPrompt(request: string, lang: string, c: Context): { system: string; user: string } {
  const system = [
    "You plan a short executive slide deck from a company's project tracker. You never invent facts.",
    "Answer with JSON only, no prose: {\"title\": string, \"slides\": [slide, ...]} with at most 12 slides.",
    "Each slide is one of: {\"kind\":\"cover\",\"title\",\"subtitle\"} · {\"kind\":\"numbers\",\"title\",\"themes\":[ids]} · {\"kind\":\"decisions\",\"title\",\"items\":[{\"theme\":id,\"text\"}]} · " +
      "{\"kind\":\"theme\",\"theme\":id} · {\"kind\":\"roadmap\",\"title\",\"themes\":[ids]} · {\"kind\":\"dates\",\"title\",\"items\":[{\"theme\":id,\"text\"}]}.",
    "Use only theme ids from the list (like PHZ-0001). Every item names the theme it comes from and says only what that theme's lines say.",
    "\"decisions\" is for open blockers and decisions; \"dates\" for estimates and milestones; \"theme\" shows the theme's own slide; " +
      "\"numbers\" and \"roadmap\" are drawn from the themes' own status and dates, so only list the ids.",
    `Write titles and sentences in ${NAMES[lang] ?? NAMES.pt}, short (at most 25 words a sentence).`,
  ].join("\n");
  const user = `Request: ${request.trim().slice(0, MAX_REQUEST)}\n\nActive themes:\n${contextText(c, lang) || "(none)"}`;
  return { system, user };
}

/* The model's answer as an object (it may come wrapped in ```json fences or with text around it). */
export function parseModelJson(answer: unknown): unknown {
  if (answer && typeof answer === "object") return answer;
  const s = String(answer ?? "");
  const fenced = s.match(/```(?:json)?\s*([\s\S]*?)```/);
  const body = fenced ? fenced[1] : s.slice(Math.max(0, s.indexOf("{")), s.lastIndexOf("}") + 1);
  try { return JSON.parse(body); } catch { return null; }
}

export function memberEmail(email: string | null | undefined): boolean {
  return /^[^@\s]+@phizchat\.com$/i.test(String(email ?? ""));
}
