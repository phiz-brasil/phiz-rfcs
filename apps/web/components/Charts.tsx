"use client";
/* Two small SVG charts for the metrics page (no chart library): stacked areas (cumulative flow) and bars (throughput). Every shape carries data-*
   attributes so the numbers behind a picture can be read and tested. */
import type { CfdRow } from "../lib/metrics";

const W = 720, H = 220, PAD = { l: 34, r: 8, t: 8, b: 22 };

export function StackedArea({ rows, keys, label, color, name }: { rows: CfdRow[]; keys: string[]; label: string; color: (k: string) => string; name: (k: string) => string }) {
  if (!rows.length) return null;
  const totals = rows.map(r => keys.reduce((a, k) => a + (r.counts[k] ?? 0), 0));
  const max = Math.max(1, ...totals);
  const x = (i: number) => PAD.l + (rows.length === 1 ? 0 : (i / (rows.length - 1)) * (W - PAD.l - PAD.r));
  const y = (v: number) => PAD.t + (1 - v / max) * (H - PAD.t - PAD.b);
  const lower = rows.map(() => 0);
  const bands = keys.map(k => {
    const top = rows.map((r, i) => lower[i] + (r.counts[k] ?? 0));
    const d = `M${rows.map((_, i) => `${x(i)},${y(top[i])}`).join(" L")} L${[...rows.keys()].reverse().map(i => `${x(i)},${y(lower[i])}`).join(" L")} Z`;
    const total = top.reduce((a, v, i) => a + (v - lower[i]), 0);
    for (let i = 0; i < rows.length; i++) lower[i] = top[i];
    return { k, d, total };
  });
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} data-days={rows.length} data-max={max}>
        <line x1={PAD.l} x2={W - PAD.r} y1={y(0)} y2={y(0)} stroke="currentColor" opacity=".3" />
        <text x={PAD.l - 4} y={PAD.t + 8} textAnchor="end" fontSize="10" fill="currentColor">{max}</text>
        <text x={PAD.l - 4} y={y(0)} textAnchor="end" fontSize="10" fill="currentColor">0</text>
        {bands.filter(b => b.total > 0).map(b => <path key={b.k} d={b.d} fill={color(b.k)} data-band={b.k} data-sum={b.total} opacity=".9"><title>{name(b.k)}</title></path>)}
        <text x={PAD.l} y={H - 6} fontSize="10" fill="currentColor">{rows[0].day}</text>
        <text x={W - PAD.r} y={H - 6} textAnchor="end" fontSize="10" fill="currentColor">{rows[rows.length - 1].day}</text>
      </svg>
      <figcaption className="legend">{bands.filter(b => b.total > 0).map(b => <span key={b.k}><i style={{ background: color(b.k) }} /> {name(b.k)}</span>)}</figcaption>
    </figure>
  );
}

export function Bars({ data, label }: { data: { key: string; value: number }[]; label: string }) {
  if (!data.length) return null;
  const max = Math.max(1, ...data.map(d => d.value));
  const bw = (W - PAD.l - PAD.r) / data.length;
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} data-max={max}>
        <line x1={PAD.l} x2={W - PAD.r} y1={H - PAD.b} y2={H - PAD.b} stroke="currentColor" opacity=".3" />
        <text x={PAD.l - 4} y={PAD.t + 8} textAnchor="end" fontSize="10" fill="currentColor">{max}</text>
        {data.map((d, i) => {
          const h = (d.value / max) * (H - PAD.t - PAD.b);
          return (
            <g key={d.key}>
              <rect x={PAD.l + i * bw + 2} y={H - PAD.b - h} width={Math.max(2, bw - 4)} height={h} fill="var(--accent)" data-week={d.key} data-value={d.value}><title>{`${d.key}: ${d.value}`}</title></rect>
              {data.length <= 14 || i % Math.ceil(data.length / 10) === 0 ? <text x={PAD.l + i * bw + bw / 2} y={H - 6} textAnchor="middle" fontSize="9" fill="currentColor">{d.key.slice(5)}</text> : null}
            </g>
          );
        })}
      </svg>
    </figure>
  );
}
