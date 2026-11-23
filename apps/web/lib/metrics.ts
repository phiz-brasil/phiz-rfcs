/* Flow metrics (docs/spec/v2/flow-and-metrics.md). Pure functions over the event log: nothing is typed by hand, and a theme's stage history is rebuilt
   by replaying its events. No imports, so Node runs this file in the tests (tests/test_metrics.py) with histories whose results were worked out by hand.

   Conventions (the definitions of the spec, made exact):
   - times are in calendar days with decimals (ms / 86 400 000); a "day" for the CFD is a UTC calendar day, counted at its last millisecond;
   - median = middle value (mean of the two middle ones when the count is even); 85th percentile = nearest rank, sorted[ceil(0.85 n) - 1];
   - a stage change is a `stage` event (the theme form) or a `move` event (the board) whose from and to stage differ; a move inside a stage is not a change;
   - a theme is *estimated* when part of its history was never recorded (it entered at a stage other than the first of its route, or it was closed without a
     resolution event): such themes are left out of the time metrics unless asked for. */
export type MTheme = { id: string; kind: string; front: string; owner: string | null; tags: string[]; route: string; stage: number | null; status: string;
  resolution: string | null; created_at: string };
export type MEvent = { theme_id: string; item_id: string | null; at: string; field: string; old_value: unknown; new_value: unknown };
export type MBlocker = { theme_id: string; created_at: string; resolved_at: string | null };
export type MItem = { id: string; theme_id: string; col: string; created_at: string };

export const DAY = 86_400_000;
export const ms = (iso: string) => Date.parse(iso);
export const days = (n: number) => n / DAY;
export const dayKey = (t: number) => new Date(t).toISOString().slice(0, 10);

export function median(xs: number[]): number | null {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}
export function p85(xs: number[]): number | null {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  return s[Math.ceil(0.85 * s.length) - 1];
}
export const summary = (xs: number[]) => ({ n: xs.length, median: median(xs), p85: p85(xs) });

/* ISO week ("2026-W08") of a timestamp, in UTC. */
export function isoWeekKey(t: number): string {
  const d = new Date(Date.UTC(new Date(t).getUTCFullYear(), new Date(t).getUTCMonth(), new Date(t).getUTCDate()));
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - day);
  const y = d.getUTCFullYear();
  const week = Math.ceil(((d.getTime() - Date.UTC(y, 0, 1)) / DAY + 1) / 7);
  return `${y}-W${String(week).padStart(2, "0")}`;
}

/* ---- themes -------------------------------------------------------------------------------------------------------------------------- */
export type Span = { stage: number; from: number; to: number | null };
export type Track = { theme: MTheme; createdAt: number; spans: Span[]; closedAt: number | null; closeKind: string | null; estimated: boolean };

export const firstStageOf = (route: string) => (route === "bug" ? 6 : route === "p0" ? 7 : 1);
const startOfCycle = (route: string) => (route === "bug" ? 6 : 7);

type Change = { at: number; from: number | null; to: number | null };
const num = (v: unknown) => (typeof v === "number" ? v : v == null || v === "" ? null : Number(v));

export function trackOf(theme: MTheme, events: MEvent[]): Track {
  const mine = events.filter(e => e.theme_id === theme.id && !e.item_id).map((e, i) => ({ e, i, at: ms(e.at) })).sort((a, b) => a.at - b.at || a.i - b.i);
  const changes: Change[] = [];
  let closedAt: number | null = null;
  let closeKind: string | null = null;
  let resolutionEvent = false;
  for (const { e, at } of mine) {
    if (e.field === "stage") changes.push({ at, from: num(e.old_value), to: num(e.new_value) });
    else if (e.field === "move") {
      const v = (e.new_value ?? {}) as { from_stage?: number | null; to_stage?: number | null };
      if (v.from_stage !== v.to_stage) changes.push({ at, from: num(v.from_stage), to: num(v.to_stage) });
    } else if (e.field === "resolution") {
      resolutionEvent = true;
      closeKind = typeof e.new_value === "string" && e.new_value ? e.new_value : null;
      closedAt = closeKind ? at : null;
    }
  }
  const createdAt = ms(theme.created_at);
  const initial = changes.length ? changes[0].from : theme.stage;
  const spans: Span[] = [];
  if (theme.kind === "project") {
    let cur: Span | null = initial != null ? { stage: initial, from: createdAt, to: null } : null;
    if (cur) spans.push(cur);
    for (const c of changes) {
      if (cur) cur.to = c.at;
      cur = c.to != null ? { stage: c.to, from: c.at, to: null } : null;
      if (cur) spans.push(cur);
    }
  }
  let estimated = false;
  if (theme.resolution && !resolutionEvent) {
    closeKind = theme.resolution;
    closedAt = mine.length ? mine[mine.length - 1].at : createdAt;
    estimated = true;
  }
  if (theme.kind === "project" && !changes.length && initial != null && initial !== firstStageOf(theme.route)) estimated = true;
  if (closedAt != null) for (const s of spans) if (s.to == null) s.to = closedAt;
  return { theme, createdAt, spans, closedAt, closeKind, estimated };
}

export const tracksOf = (themes: MTheme[], events: MEvent[]) => themes.filter(t => t.kind === "project").map(t => trackOf(t, events));

/* the first time the theme was in a stage at or beyond `stage` */
export const firstEntry = (t: Track, stage: number): number | null => {
  const hit = t.spans.filter(s => s.stage >= stage).map(s => s.from);
  return hit.length ? Math.min(...hit) : null;
};

const doneAt = (t: Track) => (t.closeKind === "done" ? t.closedAt : null);
export const leadTime = (t: Track): number | null => (doneAt(t) != null ? days(doneAt(t)! - t.createdAt) : null);
export function deliveryTime(t: Track): number | null {
  if (doneAt(t) == null || t.theme.route === "bug" || t.theme.route === "p0") return null;
  const a = firstEntry(t, 4);
  return a == null ? null : days(doneAt(t)! - a);
}
export function cycleTime(t: Track): number | null {
  if (doneAt(t) == null) return null;
  const a = firstEntry(t, startOfCycle(t.theme.route));
  return a == null ? null : days(doneAt(t)! - a);
}

/* days spent in each stage, every period added up (a re-entry adds); an open period runs to `now` */
export function timeInStage(t: Track, now: number): Record<number, number> {
  const out: Record<number, number> = {};
  for (const s of t.spans) out[s.stage] = (out[s.stage] ?? 0) + days((s.to ?? now) - s.from);
  return out;
}
export function stageStats(tracks: Track[], now: number): Record<number, ReturnType<typeof summary>> {
  const out: Record<number, ReturnType<typeof summary>> = {};
  for (let s = 1; s <= 10; s++) out[s] = summary(tracks.map(t => timeInStage(t, now)[s]).filter(x => x != null && x > 0));
  return out;
}

export function throughputByWeek(tracks: Track[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const t of tracks) if (doneAt(t) != null) { const k = isoWeekKey(doneAt(t)!); out[k] = (out[k] ?? 0) + 1; }
  return out;
}
export function countBy<T>(xs: T[], key: (x: T) => string): Record<string, number> {
  const out: Record<string, number> = {};
  for (const x of xs) { const k = key(x); out[k] = (out[k] ?? 0) + 1; }
  return out;
}

export const isOpen = (t: Track) => t.closedAt == null && t.spans.length > 0;
export const currentSpan = (t: Track) => t.spans.find(s => s.to == null) ?? null;
/* themes open in each stage right now */
export function wipByStage(tracks: Track[]): Record<number, number> {
  const out: Record<number, number> = {};
  for (const t of tracks) if (isOpen(t)) { const c = currentSpan(t); if (c) out[c.stage] = (out[c.stage] ?? 0) + 1; }
  return out;
}

export type Aging = { id: string; stage: number; inStage: number; sinceKickoff: number | null; p85: number | null; over: boolean };
/* open themes: days in the current stage and since kickoff (first entry into 04), against the 85th percentile of the finished ones in that stage */
export function agingWip(tracks: Track[], now: number): Aging[] {
  const finished = tracks.filter(t => t.closedAt != null);
  const out: Aging[] = [];
  for (const t of tracks) {
    if (!isOpen(t)) continue;
    const c = currentSpan(t);
    if (!c) continue;
    const ref = p85(finished.map(f => timeInStage(f, now)[c.stage]).filter(x => x != null && x > 0));
    const k = firstEntry(t, 4);
    const inStage = days(now - c.from);
    out.push({ id: t.theme.id, stage: c.stage, inStage, sinceKickoff: k == null || t.theme.route === "bug" || t.theme.route === "p0" ? null : days(now - k), p85: ref, over: ref != null && inStage > ref });
  }
  return out.sort((a, b) => b.inStage - a.inStage);
}

/* the stage the theme was in at an instant (null before creation or after it closed), and "closed" band for the CFD */
export function stageAt(t: Track, at: number): number | "closed" | null {
  if (at < t.createdAt) return null;
  if (t.closedAt != null && at >= t.closedAt) return "closed";
  const s = t.spans.find(x => x.from <= at && (x.to == null || x.to > at));
  return s ? s.stage : null;
}
export type CfdRow = { day: string; counts: Record<string, number> };
/* for each UTC day from `from` to `to` (inclusive), how many themes were in each stage at the end of that day; closed ones in the band "closed" */
export function cfd(tracks: Track[], from: string, to: string): CfdRow[] {
  const rows: CfdRow[] = [];
  for (let d = Date.parse(from + "T00:00:00Z"); d <= Date.parse(to + "T00:00:00Z"); d += DAY) {
    const counts: Record<string, number> = {};
    for (const t of tracks) { const s = stageAt(t, d + DAY - 1); if (s != null) counts[String(s)] = (counts[String(s)] ?? 0) + 1; }
    rows.push({ day: dayKey(d), counts });
  }
  return rows;
}

/* milliseconds with at least one blocker open inside [from, to] (overlapping blockers count once) */
export function blockedMs(blockers: MBlocker[], from: number, to: number): number {
  const iv = blockers.map(b => [Math.max(ms(b.created_at), from), Math.min(b.resolved_at ? ms(b.resolved_at) : to, to)] as const).filter(([a, b]) => b > a).sort((x, y) => x[0] - y[0]);
  let total = 0, curA = -1, curB = -1;
  for (const [a, b] of iv) {
    if (a > curB) { if (curB > curA) total += curB - curA; curA = a; curB = b; } else curB = Math.max(curB, b);
  }
  return total + (curB > curA ? curB - curA : 0);
}
/* blocked days of a finished theme and their share of its cycle time */
export function blockedInCycle(t: Track, blockers: MBlocker[]): { days: number; share: number } | null {
  if (doneAt(t) == null) return null;
  const a = firstEntry(t, startOfCycle(t.theme.route));
  if (a == null) return null;
  const b = blockedMs(blockers.filter(x => x.theme_id === t.theme.id), a, doneAt(t)!);
  return { days: days(b), share: b / (doneAt(t)! - a) };
}

/* moves made with gates open, per stage left */
export function openGateMoves(events: MEvent[]): { byStage: Record<number, number>; total: number; moves: number } {
  const byStage: Record<number, number> = {};
  let total = 0, moves = 0;
  for (const e of events) {
    if (e.field !== "move") continue;
    const v = (e.new_value ?? {}) as { from_stage?: number | null; to_stage?: number | null; open_gates?: string[] };
    if (v.from_stage == null || v.to_stage == null || v.to_stage <= v.from_stage) continue;
    moves++;
    if (v.open_gates?.length) { byStage[v.from_stage] = (byStage[v.from_stage] ?? 0) + 1; total++; }
  }
  return { byStage, total, moves };
}

/* weekdays (Mon–Fri) in (from, to]: the business days that went by */
export function businessDaysBetween(from: number, to: number): number {
  let n = 0;
  const a = Date.parse(dayKey(from) + "T00:00:00Z");
  for (let d = a + DAY; d <= Date.parse(dayKey(to) + "T00:00:00Z"); d += DAY) { const w = new Date(d).getUTCDay(); if (w !== 0 && w !== 6) n++; }
  return n;
}
/* of the themes that left stage 01 on a recorded move, the share that left within 2 business days of being created (UTC: the requester's zone is not known) */
export function triage(tracks: Track[]): { n: number; within: number; share: number | null } {
  let n = 0, within = 0;
  for (const t of tracks) {
    if (t.theme.route === "bug" || t.theme.route === "p0" || t.estimated) continue;
    const first = t.spans[0];
    if (!first || first.stage !== 1 || first.to == null || t.spans.length < 2) continue;
    n++;
    if (businessDaysBetween(t.createdAt, first.to) <= 2) within++;
  }
  return { n, within, share: n ? within / n : null };
}

/* ---- execution items (the project kanban: todo, doing, blocked, done) --------------------------------------------------------------- */
export const ITEM_COLS = ["todo", "doing", "blocked", "done"] as const;
export type ItemTrack = { item: MItem; createdAt: number; changes: { at: number; from: string; to: string }[]; initial: string; doneAt: number | null; firstDoing: number | null };

export function itemTrack(item: MItem, events: MEvent[]): ItemTrack {
  const ch = events.filter(e => e.item_id === item.id && e.field === "item_col").map((e, i) => ({ at: ms(e.at), i, from: String(e.old_value), to: String(e.new_value) }))
    .sort((a, b) => a.at - b.at || a.i - b.i);
  const initial = ch.length ? ch[0].from : item.col;
  const doneEvents = ch.filter(c => c.to === "done");
  const doing = ch.find(c => c.to === "doing");
  return { item, createdAt: ms(item.created_at), changes: ch.map(({ at, from, to }) => ({ at, from, to })), initial,
           doneAt: item.col === "done" ? (doneEvents.length ? doneEvents[doneEvents.length - 1].at : ms(item.created_at)) : null,
           firstDoing: doing ? doing.at : (initial === "doing" ? ms(item.created_at) : null) };
}
export const itemTracks = (items: MItem[], events: MEvent[]) => items.map(i => itemTrack(i, events));
export const itemLead = (t: ItemTrack) => (t.doneAt != null ? days(t.doneAt - t.createdAt) : null);
export const itemCycle = (t: ItemTrack) => (t.doneAt != null && t.firstDoing != null ? days(t.doneAt - t.firstDoing) : null);
export const itemThroughputByWeek = (ts: ItemTrack[]) => { const out: Record<string, number> = {}; for (const t of ts) if (t.doneAt != null) { const k = isoWeekKey(t.doneAt); out[k] = (out[k] ?? 0) + 1; } return out; };
export const itemWip = (ts: ItemTrack[]) => countBy(ts.filter(t => t.item.col !== "done"), t => t.item.col);
export function itemColAt(t: ItemTrack, at: number): string | null {
  if (at < t.createdAt) return null;
  let col = t.initial;
  for (const c of t.changes) if (c.at <= at) col = c.to;
  return col;
}
/* items of one project: how many were in each column at the end of each day */
export function itemCfd(ts: ItemTrack[], from: string, to: string): CfdRow[] {
  const rows: CfdRow[] = [];
  for (let d = Date.parse(from + "T00:00:00Z"); d <= Date.parse(to + "T00:00:00Z"); d += DAY) {
    const counts: Record<string, number> = {};
    for (const t of ts) { const c = itemColAt(t, d + DAY - 1); if (c) counts[c] = (counts[c] ?? 0) + 1; }
    rows.push({ day: dayKey(d), counts });
  }
  return rows;
}
/* open items in `doing`: days since they entered it */
export function itemAging(ts: ItemTrack[], now: number): { id: string; theme_id: string; col: string; inCol: number }[] {
  const out = [];
  for (const t of ts) {
    if (t.item.col === "done" || t.item.col === "todo") continue;
    const last = [...t.changes].reverse().find(c => c.to === t.item.col);
    out.push({ id: t.item.id, theme_id: t.item.theme_id, col: t.item.col, inCol: days(now - (last ? last.at : t.createdAt)) });
  }
  return out.sort((a, b) => b.inCol - a.inCol);
}
