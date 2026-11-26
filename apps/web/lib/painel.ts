/* The Painel (docs/spec/v2/redesign.md, "Painel"): pure rules, run in the browser and by Node in the tests (tests/test_painel_rules.py).
   Dates are calendar days ("2026-12-15"), compared as strings and read in UTC, as in roadmap.ts. */
import type { I18n } from "./db";

export type Quarter = { key: string; year: number; q: number; start: string; end: string };
export type Urgency = "urgent" | "important" | "info";
export const URGENCIES: Urgency[] = ["urgent", "important", "info"];

const pad = (n: number) => String(n).padStart(2, "0");
const lastDay = (y: number, m: number) => new Date(Date.UTC(y, m, 0)).getUTCDate();          // m: 1–12

/* The quarter a day falls in. */
export function quarterOf(day: string): Quarter {
  const y = Number(day.slice(0, 4)), m = Number(day.slice(5, 7));
  const q = Math.floor((m - 1) / 3) + 1;
  const m0 = (q - 1) * 3 + 1, m1 = m0 + 2;
  return { key: `${y}-Q${q}`, year: y, q, start: `${y}-${pad(m0)}-01`, end: `${y}-${pad(m1)}-${pad(lastDay(y, m1))}` };
}

/* `n` quarters from the one of `today` on (the columns of the timeline). */
export function quarters(today: string, n = 5): Quarter[] {
  const out: Quarter[] = [];
  let cur = quarterOf(today);
  for (let i = 0; i < n; i++) {
    out.push(cur);
    const ny = cur.q === 4 ? cur.year + 1 : cur.year, nq = cur.q === 4 ? 1 : cur.q + 1;
    cur = quarterOf(`${ny}-${pad((nq - 1) * 3 + 1)}-01`);
  }
  return out;
}

/* Index of the column a day falls in: -1 before the first, qs.length after the last. */
export function columnOf(qs: Quarter[], day: string): number {
  const d = day.slice(0, 10);
  if (d < qs[0].start) return -1;
  const i = qs.findIndex(q => d >= q.start && d <= q.end);
  return i < 0 ? qs.length : i;
}

/* Where a day falls along the timeline, 0–100 (for the "today" line). */
export function positionOf(qs: Quarter[], day: string): number {
  const ms = (d: string) => Date.parse(d + "T00:00:00Z");
  const from = ms(qs[0].start), to = ms(qs[qs.length - 1].end) + 86_400_000;
  return Math.max(0, Math.min(100, ((ms(day.slice(0, 10)) - from) / (to - from)) * 100));
}

export type Span = { start: string | null; due: string | null };
/* The bar of a period on the columns: [first, last] column, clipped to the timeline, or null when it has no date or falls outside. One date alone is a one-column bar. */
export function barOf(qs: Quarter[], s: Span): [number, number] | null {
  const a = s.start ?? s.due, b = s.due ?? s.start;
  if (!a || !b) return null;
  const i = columnOf(qs, a), j = columnOf(qs, b);
  if (j < 0 || i >= qs.length) return null;
  return [Math.max(0, i), Math.min(qs.length - 1, j)];
}

/* A click on column `i` of a period: the first click sets one quarter; a click before the start moves the start, any other moves the end. */
export function stretch(qs: Quarter[], s: Span, i: number): { start_date: string; due_date: string } {
  const bar = barOf(qs, s);
  if (!bar) return { start_date: qs[i].start, due_date: qs[i].end };
  const [a, b] = bar;
  if (i < a) return { start_date: qs[i].start, due_date: qs[b].end };
  return { start_date: qs[a].start, due_date: qs[i].end };
}

/* The period of a theme: the span of its deliveries' periods when any has a date, else its own start and estimate. */
export function themePeriod(theme: Span, items: Span[]): Span {
  const days = items.flatMap(x => [x.start, x.due]).filter((d): d is string => !!d).map(d => d.slice(0, 10)).sort();
  if (days.length) return { start: days[0], due: days[days.length - 1] };
  return { start: theme.start?.slice(0, 10) ?? null, due: theme.due?.slice(0, 10) ?? null };
}

/* The phase shown by the icon: from the PDLC B2B stage (01–02 discovery, 03–06 definition, 07–08 build, 09–10 launched); a task has none. */
export type Phase = "discovery" | "definition" | "build" | "launched";
export function phaseOf(stage: number | null): Phase | null {
  if (!stage) return null;
  return stage <= 2 ? "discovery" : stage <= 6 ? "definition" : stage <= 8 ? "build" : "launched";
}
export const PHASE_FILL: Record<Phase, number> = { discovery: 0, definition: 0.25, build: 0.5, launched: 1 };

/* -- the three blocks ------------------------------------------------------------------------------------------------------------------------ */
type Open = { id: string; theme_id: string; what: I18n; due_date: string | null; needs_leadership: boolean; urgency?: Urgency | null; created_at: string };
export type Line = { key: string; theme: string; kind: "blocker" | "decision" | "milestone" | "due"; text: I18n | string; urgency: Urgency | "planned"; date: string | null };

const rank = (u: Line["urgency"]) => ({ urgent: 0, important: 1, info: 2, planned: 3 })[u];
const urg = (r: Open): Urgency => r.urgency ?? (r.needs_leadership ? "important" : "info");

/* "Needs you": open blockers and decisions that need the leadership or are urgent, urgent first, then by deadline, then oldest first. No names. */
export function needsYou(blockers: Open[], decisions: Open[], themes: Set<string>): Line[] {
  const pick = (kind: "blocker" | "decision") => (r: Open): Line => ({ key: r.id, theme: r.theme_id, kind, text: r.what, urgency: urg(r), date: r.due_date?.slice(0, 10) ?? null });
  const keep = (r: Open) => themes.has(r.theme_id) && (r.needs_leadership || urg(r) === "urgent");
  const all = [...blockers.filter(keep).map(pick("blocker")), ...decisions.filter(keep).map(pick("decision"))];
  const created = new Map([...blockers, ...decisions].map(r => [r.id, r.created_at]));
  return all.sort((a, b) => rank(a.urgency) - rank(b.urgency) || (a.date ?? "9999").localeCompare(b.date ?? "9999")
    || (created.get(a.key) ?? "").localeCompare(created.get(b.key) ?? ""));
}

/* "Latest decisions": the last ones decided, newest first. */
export function latestDecisions(decided: { id: string; theme_id: string; what: I18n; decision: I18n; decided_at: string | null; urgency?: Urgency | null }[],
  themes: Set<string>, n = 4): Line[] {
  return decided.filter(d => themes.has(d.theme_id) && d.decided_at).sort((a, b) => b.decided_at!.localeCompare(a.decided_at!)).slice(0, n)
    .map(d => ({ key: d.id, theme: d.theme_id, kind: "decision", text: Object.values(d.decision ?? {}).some(v => v?.trim()) ? d.decision : d.what, urgency: "info", date: d.decided_at!.slice(0, 10) }));
}

/* "Next milestones": open milestone items and open themes' estimates from today to `days` ahead, by date. */
export function nextMilestones(themes: { id: string; due_date: string | null; open: boolean }[], milestones: { id: string; theme_id: string; title: string; due_date: string | null; col: string }[],
  today: string, days = 90): Line[] {
  const until = new Date(Date.parse(today + "T00:00:00Z") + days * 86_400_000).toISOString().slice(0, 10);
  const ids = new Set(themes.filter(x => x.open).map(x => x.id));
  const inRange = (d: string | null) => !!d && d.slice(0, 10) >= today && d.slice(0, 10) <= until;
  return [
    ...milestones.filter(m => ids.has(m.theme_id) && m.col !== "done" && inRange(m.due_date))
      .map(m => ({ key: m.id, theme: m.theme_id, kind: "milestone" as const, text: m.title, urgency: "planned" as const, date: m.due_date!.slice(0, 10) })),
    ...themes.filter(x => x.open && inRange(x.due_date)).map(x => ({ key: "due-" + x.id, theme: x.id, kind: "due" as const, text: "", urgency: "planned" as const, date: x.due_date!.slice(0, 10) })),
  ].sort((a, b) => a.date.localeCompare(b.date));
}

/* -- filters --------------------------------------------------------------------------------------------------------------------------------- */
export type Filters = { front: string; owner: string; status: string; tag: string; kind: string; attention: boolean; stale: boolean };
export const NO_FILTERS: Filters = { front: "", owner: "", status: "", tag: "", kind: "", attention: false, stale: false };
type Row = { id: string; front: string; owner: string | null; status: string; tags: string[]; kind: string };
export function applyFilters<T extends Row>(rows: T[], f: Filters, flags: { attention: (x: T) => boolean; stale: (x: T) => boolean }): T[] {
  return rows.filter(x => (!f.front || x.front === f.front) && (!f.owner || x.owner === f.owner) && (!f.status || x.status === f.status)
    && (!f.tag || x.tags.includes(f.tag)) && (!f.kind || x.kind === f.kind) && (!f.attention || flags.attention(x)) && (!f.stale || flags.stale(x)));
}
