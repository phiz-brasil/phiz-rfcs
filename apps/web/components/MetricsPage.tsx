"use client";
/* The flow metrics (docs/spec/v2/flow-and-metrics.md): computed in the browser from the event log by apps/web/lib/metrics.ts. Each block says
   how it is computed and lists the themes or items behind it. */
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { COLS, STAGES, STATUSES, T, t, text, type Lang } from "../lib/i18n";
import type { BoardColumn, Front, Theme } from "../lib/db";
import * as M from "../lib/metrics";
import { useApp } from "./Shell";
import { Bars, StackedArea } from "./Charts";
import { Said } from "./ui";

type Data = { fronts: Front[]; themes: Theme[]; events: M.MEvent[]; blockers: M.MBlocker[]; items: M.MItem[]; columns: BoardColumn[] };
const fmt = (x: number | null | undefined) => (x == null ? "—" : x.toFixed(1));
const stageColor = (k: string) => (k === "closed" ? "#9aa0a6" : `hsl(${200 + (Number(k) - 1) * 16} 55% ${62 - Number(k) * 2}%)`);
const itemColor = (k: string) => ({ todo: "#9aa0a6", doing: "#3b82f6", blocked: "#d9534f", done: "#25d366" } as Record<string, string>)[k] ?? "#999";

export function MetricsPage() {
  const { lang, db } = useApp();
  const [data, setData] = useState<Data | null>(null);
  const [failed, setFailed] = useState(false);
  const [f, setF] = useState({ period: 90, level: "both", front: "", tag: "", route: "", owner: "", estimated: false, project: "" });
  const now = useMemo(() => Date.now(), [data]);               // eslint-disable-line react-hooks/exhaustive-deps

  const load = useCallback(async () => {
    try {
      const [fronts, themes, events, blockers, items, columns] = await Promise.all([db.fronts(), db.themes(), db.metricEvents(), db.allBlockers(), db.allItems(), db.boardColumns()]);
      setData({ fronts, themes, events, blockers, items, columns });
      setFailed(false);
    } catch { setFailed(true); }
  }, [db]);
  useEffect(() => { void load(); }, [load]);

  const scoped = useMemo(() => (data?.themes ?? []).filter(x => (!f.front || x.front === f.front) && (!f.tag || x.tags.includes(f.tag)) && (!f.route || x.route === f.route) && (!f.owner || x.owner === f.owner)), [data, f]);
  const tracks = useMemo(() => (data ? M.tracksOf(scoped, data.events) : []), [data, scoped]);
  const since = f.period ? now - f.period * M.DAY : 0;
  const timed = useMemo(() => tracks.filter(x => f.estimated || !x.estimated), [tracks, f.estimated]);
  const finished = useMemo(() => timed.filter(x => x.closedAt != null && x.closedAt >= since), [timed, since]);
  const tags = useMemo(() => [...new Set((data?.themes ?? []).flatMap(x => x.tags))].sort(), [data]);
  const owners = useMemo(() => [...new Set((data?.themes ?? []).map(x => x.owner).filter(Boolean) as string[])].sort(), [data]);
  const projects = useMemo(() => scoped.filter(x => x.kind === "project"), [scoped]);
  const title = useCallback((id: string) => data?.themes.find(x => x.id === id)?.title, [data]);

  if (failed) return <p className="state err">{T.failed[lang]}</p>;
  if (!data) return <p className="state">{T.loading[lang]}</p>;

  const showThemes = f.level !== "items";
  const showItems = f.level !== "themes";
  const idsOf = (xs: { id: string; v: number | null }[]) => xs.filter(x => x.v != null) as { id: string; v: number }[];
  const timeBlock = (name: string, def: string, fn: (x: M.Track) => number | null) => {
    const rows = idsOf(finished.map(x => ({ id: x.theme.id, v: fn(x) })));
    return { name, def, rows, s: M.summary(rows.map(r => r.v)) };
  };
  const times = [timeBlock("leadTime", "def_lead", M.leadTime), timeBlock("deliveryTime", "def_delivery", M.deliveryTime), timeBlock("cycleTime", "def_cycle", M.cycleTime)];

  const stats = M.stageStats(timed.filter(x => x.closedAt != null), now);
  const wip = M.wipByStage(tracks);
  const limit = (s: number) => data.columns.filter(c => c.stage === s).reduce<number | null>((a, c) => (c.wip_limit == null ? a : (a ?? 0) + c.wip_limit), null);
  const weeks = M.throughputByWeek(finished);
  const weekKeys = Object.keys(weeks).sort();
  const aging = M.agingWip(timed, now);
  const cfdFrom = M.dayKey(Math.max(since, Math.min(now, ...tracks.map(x => x.createdAt))));
  const cfdRows = M.cfd(tracks, cfdFrom, M.dayKey(now));
  const blocked = idsOf(finished.map(x => { const b = M.blockedInCycle(x, data.blockers); return { id: x.theme.id, v: b ? b.days : null }; }));
  const shares = finished.map(x => M.blockedInCycle(x, data.blockers)?.share).filter((x): x is number => x != null);
  const inPeriod = (e: M.MEvent) => M.ms(e.at) >= since && scoped.some(x => x.id === e.theme_id);
  const gates = M.openGateMoves(data.events.filter(inPeriod));
  const tri = M.triage(timed.filter(x => M.ms(data.themes.find(y => y.id === x.theme.id)!.created_at) >= since));

  const ids = new Set(scoped.map(x => x.id));
  const itemTracks = M.itemTracks(data.items.filter(i => ids.has(i.theme_id)), data.events);
  const doneItems = itemTracks.filter(x => x.doneAt != null && x.doneAt >= since);
  const iLead = idsOf(doneItems.map(x => ({ id: x.item.id, v: M.itemLead(x) })));
  const iCycle = idsOf(doneItems.map(x => ({ id: x.item.id, v: M.itemCycle(x) })));
  const iWeeks = M.itemThroughputByWeek(doneItems);
  const iWip = M.itemWip(itemTracks);
  const iAging = M.itemAging(itemTracks, now);
  const projItems = f.project ? itemTracks.filter(x => x.item.theme_id === f.project) : [];
  const iCfd = f.project ? M.itemCfd(projItems, M.dayKey(Math.max(since, Math.min(now, ...projItems.map(x => x.createdAt)))), M.dayKey(now)) : [];

  const List = ({ rows, unit = true }: { rows: { id: string; v: number }[]; unit?: boolean }) => (
    <ul className="plain">{rows.map(r => <li key={r.id}><a href={`/themes/${r.id}/`}><span className="id">{r.id}</span> <Said value={title(r.id)} lang={lang} /></a> · {fmt(r.v)}{unit ? " d" : ""}</li>)}</ul>
  );
  const Note = ({ def, children }: { def: string; children?: ReactNode }) => (
    <details><summary>{T.howComputed[lang]}</summary><p className="note">{T[def][lang]}</p>{children}</details>
  );
  const Stats = ({ s }: { s: ReturnType<typeof M.summary> }) => (
    <><td data-k="n">{s.n}</td><td data-k="median">{fmt(s.median)}</td><td data-k="p85">{fmt(s.p85)}</td></>
  );
  const Head = () => <thead><tr><th /><th>{T.statN[lang]}</th><th>{T.statMedian[lang]}</th><th>{T.statP85[lang]}</th></tr></thead>;

  return (
    <>
      <h1>{T.metrics[lang]}</h1>
      <p className="lead">{T.metricsLead[lang]}</p>
      <div className="bar">
        <div className="fields">
          <label className="field"><span>{T.period[lang]}</span>
            <select value={f.period} onChange={e => setF({ ...f, period: Number(e.target.value) })}>
              {[30, 90, 180, 365].map(n => <option key={n} value={n}>{T.last[lang]} {n} {T.daysUnit[lang]}</option>)}<option value={0}>{T.allTime[lang]}</option>
            </select></label>
          <label className="field"><span>{T.level[lang]}</span>
            <select value={f.level} onChange={e => setF({ ...f, level: e.target.value })}>
              <option value="both">{T.levelBoth[lang]}</option><option value="themes">{T.levelThemes[lang]}</option><option value="items">{T.levelItems[lang]}</option>
            </select></label>
          <label className="field"><span>{T.front[lang]}</span>
            <select value={f.front} onChange={e => setF({ ...f, front: e.target.value })}><option value="">{T.all[lang]}</option>{data.fronts.map(x => <option key={x.key} value={x.key}>{text(x.name, lang)}</option>)}</select></label>
          <label className="field"><span>{T.tagFilter[lang]}</span>
            <select value={f.tag} onChange={e => setF({ ...f, tag: e.target.value })}><option value="">{T.all[lang]}</option>{tags.map(x => <option key={x} value={x}>#{x}</option>)}</select></label>
          <label className="field"><span>{T.route[lang]}</span>
            <select value={f.route} onChange={e => setF({ ...f, route: e.target.value })}><option value="">{T.all[lang]}</option>{["full", "bug", "p0"].map(x => <option key={x} value={x}>{x === "full" ? T.routeFull[lang] : x === "bug" ? "Bug" : "P0"}</option>)}</select></label>
          <label className="field"><span>{T.owner[lang]}</span>
            <select value={f.owner} onChange={e => setF({ ...f, owner: e.target.value })}><option value="">{T.all[lang]}</option>{owners.map(x => <option key={x} value={x}>{x}</option>)}</select></label>
        </div>
        <label className="checks"><input type="checkbox" checked={f.estimated} onChange={e => setF({ ...f, estimated: e.target.checked })} /> {T.includeEstimated[lang]}</label>
        <p className="note" data-estimated={tracks.filter(x => x.estimated).length}>{tracks.filter(x => x.estimated).length} {T.estimatedNote[lang]}.</p>
      </div>

      {showThemes ? (
        <>
          <section className="panel" aria-label={T.leadTime[lang]} data-block="times">
            <h2>{T.leadTime[lang]} · {T.deliveryTime[lang]} · {T.cycleTime[lang]}</h2>
            <table className="stats"><Head />
              <tbody>{times.map(b => <tr key={b.name} data-metric={b.name}><th>{T[b.name][lang]}</th><td data-k="n">{b.s.n}</td><td data-k="median">{fmt(b.s.median)}</td><td data-k="p85">{fmt(b.s.p85)}</td></tr>)}</tbody>
            </table>
            {times.map(b => <Note key={b.name} def={b.def}><p className="note"><strong>{T[b.name][lang]}</strong></p>{b.rows.length ? <List rows={b.rows} /> : <p className="empty">{T.nothing[lang]}</p>}</Note>)}
          </section>

          <section className="panel" aria-label={T.timeInStage[lang]} data-block="stages">
            <h2>{T.timeInStage[lang]}</h2>
            <table className="stats"><Head />
              <tbody>{STAGES.map(s => (
                <tr key={s} data-stage={s} data-over={limit(s) != null && (wip[s] ?? 0) > limit(s)! ? "1" : "0"}>
                  <th>{t(`stage.${s}`, lang)}</th><Stats s={stats[s]} /> <td data-k="wip">{wip[s] ?? 0}{limit(s) != null ? ` / ${limit(s)}` : ""}</td>
                </tr>))}</tbody>
            </table>
            <Note def="def_stage" />
          </section>

          <section className="panel" aria-label={T.throughput[lang]} data-block="throughput">
            <h2>{T.throughput[lang]}</h2>
            {weekKeys.length ? <Bars label={T.throughput[lang]} data={weekKeys.map(k => ({ key: k, value: weeks[k] }))} /> : <p className="empty">{T.nothing[lang]}</p>}
            <Note def="def_throughput"><ul className="plain">{Object.entries(M.countBy(finished.filter(x => x.closedAt != null), x => x.theme.front)).map(([k, n]) => <li key={k} data-front={k}>{text(data.fronts.find(y => y.key === k)?.name, lang)}: {n}</li>)}</ul></Note>
          </section>

          <section className="panel" aria-label={T.cfd[lang]} data-block="cfd">
            <h2>{T.cfd[lang]}</h2>
            {tracks.length ? <StackedArea rows={cfdRows} keys={[...STAGES.map(String), "closed"]} label={T.cfd[lang]} color={stageColor} name={k => (k === "closed" ? T.closedBand[lang] : t(`stage.${k}`, lang))} /> : <p className="empty">{T.nothing[lang]}</p>}
            <Note def="def_cfd" />
          </section>

          <section className="panel" aria-label={T.agingWip[lang]} data-block="aging">
            <h2>{T.agingWip[lang]}</h2>
            {aging.length ? (
              <table className="stats"><thead><tr><th /><th>{T.stage[lang]}</th><th>{T.inStageDays[lang]}</th><th>{T.sinceKickoff[lang]}</th><th>{T.statP85[lang]}</th></tr></thead>
                <tbody>{aging.map(a => (
                  <tr key={a.id} data-theme={a.id} data-over={a.over ? "1" : "0"}>
                    <th><a href={`/themes/${a.id}/`}><span className="id">{a.id}</span> <Said value={title(a.id)} lang={lang} /></a></th>
                    <td>{t(`stage.${a.stage}`, lang)}</td><td>{fmt(a.inStage)}{a.over ? <span className="flag lead"> {T.over85[lang]}</span> : null}</td><td>{fmt(a.sinceKickoff)}</td><td>{fmt(a.p85)}</td>
                  </tr>))}</tbody>
              </table>
            ) : <p className="empty">{T.nothing[lang]}</p>}
            <Note def="def_aging" />
          </section>

          <section className="panel" aria-label={T.blockedTime[lang]} data-block="blocked">
            <h2>{T.blockedTime[lang]}</h2>
            <table className="stats"><thead><tr><th /><th>{T.statN[lang]}</th><th>{T.statMedian[lang]}</th><th>{T.statP85[lang]}</th></tr></thead>
              <tbody>
                <tr data-metric="blockedDays"><th>{T.blockedDays[lang]}</th><td data-k="n">{blocked.length}</td><td data-k="median">{fmt(M.median(blocked.map(x => x.v)))}</td><td data-k="p85">{fmt(M.p85(blocked.map(x => x.v)))}</td></tr>
                <tr data-metric="blockedShare"><th>{T.blockedShare[lang]}</th><td data-k="n">{shares.length}</td><td data-k="median">{M.median(shares) == null ? "—" : `${(M.median(shares)! * 100).toFixed(0)}%`}</td><td data-k="p85">{M.p85(shares) == null ? "—" : `${(M.p85(shares)! * 100).toFixed(0)}%`}</td></tr>
              </tbody>
            </table>
            <Note def="def_blocked">{blocked.length ? <List rows={blocked} /> : null}</Note>
          </section>

          <section className="panel" aria-label={T.gateMoves[lang]} data-block="gates">
            <h2>{T.gateMoves[lang]}</h2>
            <p data-k="gates"><strong>{gates.total}</strong> {T.gateMovesOf[lang]} {gates.moves}</p>
            <ul className="plain">{Object.keys(gates.byStage).sort((a, b) => Number(a) - Number(b)).map(s => <li key={s} data-stage={s}>{t(`stage.${s}`, lang)}: {gates.byStage[Number(s)]}</li>)}</ul>
            <Note def="def_gates" />
          </section>

          <section className="panel" aria-label={T.triage[lang]} data-block="triage">
            <h2>{T.triage[lang]}</h2>
            <p data-k="triage">{tri.share == null ? "—" : <><strong>{(tri.share * 100).toFixed(0)}%</strong> ({tri.within} {T.gateMovesOf[lang]} {tri.n})</>}</p>
            <Note def="def_triage" />
          </section>
        </>
      ) : null}

      {showItems ? (
        <section className="panel" aria-label={T.itemsTitle[lang]} data-block="items">
          <h2>{T.itemsTitle[lang]}</h2>
          <table className="stats"><Head />
            <tbody>
              <tr data-metric="itemLead"><th>{T.itemLead[lang]}</th><Stats s={M.summary(iLead.map(x => x.v))} /></tr>
              <tr data-metric="itemCycle"><th>{T.itemCycle[lang]}</th><Stats s={M.summary(iCycle.map(x => x.v))} /></tr>
            </tbody>
          </table>
          <h3>{T.itemThroughput[lang]}</h3>
          {Object.keys(iWeeks).length ? <Bars label={T.itemThroughput[lang]} data={Object.keys(iWeeks).sort().map(k => ({ key: k, value: iWeeks[k] }))} /> : <p className="empty">{T.nothing[lang]}</p>}
          <h3>{T.itemWip[lang]}</h3>
          <p data-k="itemwip">{COLS.map(c => <span key={c} data-col={c} style={{ marginRight: 12 }}>{t(`col.${c}`, lang)}: {iWip[c] ?? 0}</span>)}</p>
          <h3>{T.itemAging[lang]}</h3>
          {iAging.length ? <ul className="plain">{iAging.map(a => <li key={a.id} data-item={a.id}><a href={`/themes/${a.theme_id}/`}>{a.theme_id}</a> · {t(`col.${a.col}`, lang)} · {fmt(a.inCol)} d</li>)}</ul> : <p className="empty">{T.nothing[lang]}</p>}
          <h3>{T.itemCfd[lang]}</h3>
          <label className="field"><span>{T.pickProject[lang]}</span>
            <select value={f.project} onChange={e => setF({ ...f, project: e.target.value })}>
              <option value="">—</option>{projects.map(p => <option key={p.id} value={p.id}>{p.id} {text(p.title, lang)}</option>)}
            </select></label>
          {f.project && projItems.length ? <StackedArea rows={iCfd} keys={[...M.ITEM_COLS]} label={T.itemCfd[lang]} color={itemColor} name={k => t(`col.${k}`, lang)} /> : null}
          <Note def="def_items" />
        </section>
      ) : null}
    </>
  );
}

export type { Lang };
