/* The numbers the leadership pages share (overview and executive view), computed the same way on both. */
import type { Blocker, Decision, Theme } from "./db";

export type Portfolio = { themes: Theme[]; weeks: Set<string>; blockers: Blocker[]; decisions: Decision[] };

export const isOpen = (x: Theme) => x.status !== "done" && x.status !== "cancelled";
/* an open theme without a weekly update in the current ISO week */
export const isStale = (p: Portfolio, week: string) => (x: Theme) => isOpen(x) && !p.weeks.has(`${x.id}|${week}`);
/* an open theme whose estimated completion has passed */
export const isOverdue = (today: string) => (x: Theme) => isOpen(x) && !!x.due_date && x.due_date.slice(0, 10) < today;
export const atRisk = (x: Theme) => x.status === "at_risk" || x.status === "blocked";

export type LeadershipItem = { kind: "blocker" | "decision"; row: Blocker | Decision };
/* open blockers and decisions that need the leadership, earliest deadline first */
export const leadershipItems = (p: Portfolio): LeadershipItem[] => [
  ...p.blockers.filter(b => b.needs_leadership).map(b => ({ kind: "blocker" as const, row: b })),
  ...p.decisions.filter(d => d.needs_leadership).map(d => ({ kind: "decision" as const, row: d })),
].sort((a, b) => (a.row.due_date ?? "9999").localeCompare(b.row.due_date ?? "9999"));

export const KPI_KEYS = ["active", "on_track", "at_risk", "overdue", "stale", "leadership"] as const;
export type Kpi = (typeof KPI_KEYS)[number];
export function kpis(p: Portfolio, themes: Theme[], week: string, today: string): Record<Kpi, number> {
  const ids = new Set(themes.map(x => x.id));
  return {
    active: themes.filter(isOpen).length,
    on_track: themes.filter(x => x.status === "on_track").length,
    at_risk: themes.filter(atRisk).length,
    overdue: themes.filter(isOverdue(today)).length,
    stale: themes.filter(isStale(p, week)).length,
    leadership: leadershipItems(p).filter(l => ids.has(l.row.theme_id)).length,
  };
}
export const KPI_TONE: Partial<Record<Kpi, "warn" | "alert">> = { at_risk: "warn", overdue: "warn", stale: "warn", leadership: "alert" };
