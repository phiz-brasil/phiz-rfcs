/* The FUP's rules that do not need the page (docs/spec/v2/fup.md): the suggested agenda and the minutes. */
import type { Decision, Front, FupAgenda, FupKind, FupRecord, Theme } from "./db";
import { text, type Lang, type Tri } from "./i18n";

const CLOSED = new Set(["done", "cancelled"]);
const DAY = 86400000;

/* Every active theme, grouped by front in the fronts' order. On the agenda: at risk or blocked, with an open decision, or not updated
   for more than 7 days. Kind: decide when it has an open decision, discuss when it is at risk or blocked, inform otherwise. */
export function suggestAgenda(fronts: Front[], themes: Theme[], open: Decision[], now = Date.now()): FupAgenda[] {
  const order = new Map(fronts.map(f => [f.key, f.is_other ? 9999 : f.ord]));
  const withDecision = new Set(open.map(d => d.theme_id));
  return themes
    .filter(t => !CLOSED.has(t.status))
    .sort((a, b) => (order.get(a.front) ?? 9998) - (order.get(b.front) ?? 9998) || a.id.localeCompare(b.id))
    .map(t => {
      const risk = t.status === "at_risk" || t.status === "blocked";
      const stale = now - Date.parse(t.updated_at) > 7 * DAY;
      const kind: FupKind = withDecision.has(t.id) ? "decide" : risk ? "discuss" : "inform";
      return { theme: t.id, kind, on: risk || withDecision.has(t.id) || stale, star: false };
    });
}

export const fmtDay = (d: string) => `${d.slice(8, 10)}/${d.slice(5, 7)}`;

type Words = Record<"title" | "status" | "decisions" | "actions" | "open" | "favourites" | "none" | "nothing" | "until" | "note" | "decision" | "action", string> &
  { progress: Record<FupRecord["progress"], string>; statusOf: (s: string) => string };

/* The minutes as plain text: per theme on the agenda its status and records, then every decision, every action, the points still open
   and the favourites. */
export function minutes(f: { title: string; held_on: string; agenda: FupAgenda[]; log: FupRecord[] }, themes: Map<string, Theme>, open: Map<string, Tri[]>,
                        statuses: Record<string, string>, w: Words, lang: Lang): string {
  const name = (id: string) => `${id} ${text(themes.get(id)?.title, lang)}`.trim();
  const on = f.agenda.filter(a => a.on);
  const out = [`${f.title} · ${f.held_on.split("-").reverse().join("/")}`, ""];
  const type = { note: w.note, decision: w.decision, action: w.action };
  for (const a of on) {
    out.push(`■ ${name(a.theme)}`);
    const st = statuses[a.theme] ?? themes.get(a.theme)?.status;
    if (st) out.push(`  ${w.status}: ${w.statusOf(st)}`);
    const recs = f.log.filter(r => r.theme === a.theme);
    for (const r of recs) out.push(`  ${type[r.type]} [${w.progress[r.progress]}]: ${r.text}${r.due ? ` (${w.until} ${fmtDay(r.due)})` : ""}`);
    if (!recs.length) out.push(`  ${w.nothing}`);
    out.push("");
  }
  const list = (title: string, rows: string[]) => { out.push(title.toUpperCase()); out.push(...(rows.length ? rows.map(r => `- ${r}`) : [`- ${w.none}`])); out.push(""); };
  list(w.decisions, f.log.filter(r => r.type === "decision").map(r => `${name(r.theme)}: ${r.text}`));
  list(w.actions, f.log.filter(r => r.type === "action").map(r => `[${w.progress[r.progress]}] ${r.text}${r.due ? ` · ${fmtDay(r.due)}` : ""} (${r.theme})`));
  list(w.open, on.flatMap(a => (open.get(a.theme) ?? []).map(q => `${name(a.theme)}: ${text(q, lang)}`)));
  list(w.favourites, f.agenda.filter(a => a.star).map(a => name(a.theme)));
  return out.join("\n").trim();
}
