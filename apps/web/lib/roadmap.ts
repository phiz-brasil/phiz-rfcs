/* The geometry of the roadmap: a time axis in whole months that covers every date shown (and today), and the position of a date on it as a
   share of the axis. Dates are calendar days ("2026-12-15"), read in UTC so the position never depends on the reader's time zone. */
const DAY = 86_400_000;
export const toMs = (d: string) => Date.parse(d.slice(0, 10) + "T00:00:00Z");
export const isoDay = (ms: number) => new Date(ms).toISOString().slice(0, 10);

export type Axis = { from: number; to: number; months: { label: string; start: number }[] };

export function axisFor(dates: string[], today: string, minMonths = 3): Axis {
  const all = [...dates.map(toMs), toMs(today)];
  const lo = new Date(Math.min(...all));
  const hi = new Date(Math.max(...all));
  let start = Date.UTC(lo.getUTCFullYear(), lo.getUTCMonth(), 1);
  let end = Date.UTC(hi.getUTCFullYear(), hi.getUTCMonth() + 1, 1);                 // the first day after the last month
  const months: { label: string; start: number }[] = [];
  for (let m = new Date(start); m.getTime() < end || months.length < minMonths; m = new Date(Date.UTC(m.getUTCFullYear(), m.getUTCMonth() + 1, 1))) {
    months.push({ label: isoDay(m.getTime()).slice(0, 7), start: m.getTime() });
    end = Math.max(end, Date.UTC(m.getUTCFullYear(), m.getUTCMonth() + 1, 1));
  }
  start = months[0].start;
  return { from: start, to: end, months };
}

/* 0–100: where a day falls on the axis (its left edge). */
export const pct = (axis: Axis, day: string) => ((toMs(day) - axis.from) / (axis.to - axis.from)) * 100;
/* Width of the span start..end, both days included, as a share of the axis. */
export const widthPct = (axis: Axis, a: string, b: string) => ((toMs(b) - toMs(a) + DAY) / (axis.to - axis.from)) * 100;
