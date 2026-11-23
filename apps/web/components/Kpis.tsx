"use client";
/* The band of big numbers (the reference layout's metric block): each number either filters the page it is on or leads to the executive view filtered. */
import { T, type Lang } from "../lib/i18n";
import { KPI_KEYS, KPI_TONE, type Kpi } from "../lib/portfolio";

export function Kpis({ values, lang, active, onPick, hrefOf }: { values: Record<Kpi, number>; lang: Lang; active?: Kpi | null;
  onPick?: (k: Kpi) => void; hrefOf?: (k: Kpi) => string }) {
  return (
    <section className="kpis" aria-label={T.kpis[lang]}>
      {KPI_KEYS.map(k => {
        const inner = <><span className="kpi-label">{T[`kpi_${k}`][lang]}</span><span className="kpi-n">{values[k]}</span></>;
        const props = { className: "kpi", "data-kpi": k, "data-tone": values[k] ? KPI_TONE[k] : undefined, "aria-pressed": onPick ? active === k : undefined };
        return hrefOf ? <a key={k} {...props} href={hrefOf(k)}>{inner}</a> : <button key={k} type="button" {...props} onClick={() => onPick?.(k)}>{inner}</button>;
      })}
    </section>
  );
}
