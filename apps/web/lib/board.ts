/* The rules of the B2B board that both the page and the tests rely on; they mirror supabase/migrations/20261127000000_board_columns.sql
   (move_theme_card): the same route stages, the same "needs a reason" test, the same current column. */
import type { BoardColumn, GateCheck, StageEvent, StageGate, Theme } from "./db";

export const routeStages = (route: string): number[] =>
  route === "bug" ? [6, 7, 8, 9, 10] : route === "p0" ? [7, 8, 9, 10] : [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

export const sortedColumns = (cols: BoardColumn[]) =>
  [...cols].sort((a, b) => a.position - b.position || a.created_at.localeCompare(b.created_at) || a.id.localeCompare(b.id));

/* The column a card is in: the stored one while it still points at the theme's stage, otherwise the first column of that stage
   (the stage may have been changed on the theme page, or the column deleted). */
export function currentColumn(theme: Theme, cols: BoardColumn[]): BoardColumn | undefined {
  if (theme.stage == null) return undefined;
  const sorted = sortedColumns(cols);
  return sorted.find(c => c.id === theme.board_column && c.stage === theme.stage) ?? sorted.find(c => c.stage === theme.stage);
}

/* Skipping a stage of the route, or leaving the route, needs a written reason (the standard asks for an approval). */
export function needsReason(theme: Theme, dest: BoardColumn): boolean {
  const route = routeStages(theme.route);
  const from = theme.stage ?? 0;
  const skipped = dest.stage > from && route.some(s => s > from && s < dest.stage);
  return skipped || !route.includes(dest.stage);
}

/* The gates of the theme's current stage that nobody has ticked. */
export function openGates(theme: Theme, gates: StageGate[], checks: GateCheck[]): StageGate[] {
  if (theme.stage == null) return [];
  const done = new Set(checks.filter(c => c.theme_id === theme.id).map(c => c.gate_key));
  return gates.filter(g => g.stage === theme.stage && !done.has(g.key)).sort((a, b) => a.position - b.position);
}

/* When the theme entered its current stage: the last stage change (a move to another stage, or a direct edit of the stage), else when it was created. */
export function stageSince(theme: Theme, events: StageEvent[]): string {
  let best = theme.created_at;
  for (const e of events) {
    if (e.theme_id !== theme.id || e.at <= best) continue;
    if (e.field === "stage") best = e.at;
    else if (e.field === "move") {
      const v = e.new_value as { from_stage?: number | null; to_stage?: number } | null;
      if (v && v.from_stage !== v.to_stage) best = e.at;
    }
  }
  return best;
}

export const daysSince = (iso: string, now = Date.now()) => Math.max(0, Math.floor((now - Date.parse(iso)) / 86_400_000));
