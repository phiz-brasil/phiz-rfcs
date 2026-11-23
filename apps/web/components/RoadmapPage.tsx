"use client";
/* The roadmap: every theme over time, built from its own dates (start, estimated completion) and its milestones, grouped by front. Themes
   with no dates are listed under the timeline. Nothing is stored here: a change on a theme shows on the next load. */
import { useCallback, useEffect, useMemo, useState } from "react";
import { STATUSES, T, t, text } from "../lib/i18n";
import type { Front, Milestone, Theme } from "../lib/db";
import { axisFor, isoDay, pct, widthPct } from "../lib/roadmap";
import { useApp } from "./Shell";
import { Said, StatusBadge, dateText } from "./ui";

type Data = { fronts: Front[]; themes: Theme[]; milestones: Milestone[] };
const MONTH_PX = 120;
const LABEL_PX = 240;

export function RoadmapPage() {
  const { lang, db } = useApp();
  const [data, setData] = useState<Data | null>(null);
  const [failed, setFailed] = useState(false);
  const [status, setStatus] = useState("all");
  const [tag, setTag] = useState("");
  const [owner, setOwner] = useState("");
  const [front, setFront] = useState("");
  const today = isoDay(Date.now());

  const load = useCallback(async () => {
    try {
      const [fronts, themes, milestones] = await Promise.all([db.fronts(), db.themes(), db.milestones()]);
      setData({ fronts, themes, milestones });
      setFailed(false);
    } catch { setFailed(true); }
  }, [db]);
  useEffect(() => { void load(); }, [load]);

  const tags = useMemo(() => [...new Set((data?.themes ?? []).flatMap(x => x.tags))].sort(), [data]);
  const owners = useMemo(() => [...new Set((data?.themes ?? []).map(x => x.owner).filter(Boolean) as string[])].sort(), [data]);
  const shown = useMemo(() => (data?.themes ?? []).filter(x =>
    (status === "all" || x.status === status) && (!tag || x.tags.includes(tag)) && (!owner || x.owner === owner) && (!front || x.front === front)), [data, status, tag, owner, front]);
  const msOf = useCallback((id: string) => (data?.milestones ?? []).filter(m => m.theme_id === id && m.due_date), [data]);
  const dated = shown.filter(x => x.start_date || x.due_date || msOf(x.id).length);
  const undated = shown.filter(x => !dated.includes(x));
  const axis = useMemo(() => axisFor(dated.flatMap(x => [x.start_date, x.due_date, ...msOf(x.id).map(m => m.due_date)]).filter(Boolean) as string[], today), [dated, msOf, today]);

  if (failed) return <p className="state err">{T.failed[lang]}</p>;
  if (!data) return <p className="state">{T.loading[lang]}</p>;
  const width = LABEL_PX + axis.months.length * MONTH_PX;
  const todayPct = pct(axis, today);

  return (
    <>
      <h1>{T.roadmap[lang]}</h1>
      <p className="lead">{T.roadmapLead[lang]}</p>
      <div className="bar">
        <div className="filters" role="group" aria-label={T.status[lang]}>
          {["all", ...STATUSES].map(s => <button key={s} type="button" aria-pressed={status === s} onClick={() => setStatus(s)}>{s === "all" ? T.all[lang] : t(`status.${s}`, lang)}</button>)}
        </div>
        <div className="inline">
          <select aria-label={T.front[lang]} value={front} onChange={e => setFront(e.target.value)}><option value="">{T.front[lang]}: {T.all[lang]}</option>{data.fronts.map(f => <option key={f.key} value={f.key}>{text(f.name, lang)}</option>)}</select>
          <select aria-label={T.tag[lang]} value={tag} onChange={e => setTag(e.target.value)}><option value="">{T.tag[lang]}: {T.all[lang]}</option>{tags.map(x => <option key={x} value={x}>#{x}</option>)}</select>
          <select aria-label={T.owner[lang]} value={owner} onChange={e => setOwner(e.target.value)}><option value="">{T.owner[lang]}: {T.all[lang]}</option>{owners.map(x => <option key={x} value={x}>{x}</option>)}</select>
        </div>
      </div>
      {!shown.length ? <p className="empty">{T.nothingToShow[lang]}</p> : null}
      {dated.length ? (
        <div className="boardwrap">
          <div className="rm" role="table" aria-label={T.roadmap[lang]} style={{ width }}>
            <div className="rm-row rm-head" role="row">
              <div />
              <div className="rm-track">
                {axis.months.map(m => <span className="rm-month" key={m.label} data-month={m.label} style={{ left: `${pct(axis, isoDay(m.start))}%` }}>{m.label}</span>)}
              </div>
            </div>
            {data.fronts.map(f => {
              const rows = dated.filter(x => x.front === f.key);
              if (!rows.length) return null;
              return (
                <div key={f.key} data-front={f.key}>
                  <h2 className="rm-front">{text(f.name, lang)}</h2>
                  {rows.map(x => <Row key={x.id} theme={x} milestones={msOf(x.id)} axis={axis} today={today} todayPct={todayPct} />)}
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
      {undated.length ? (
        <section className="panel" aria-label={T.noDates[lang]}>
          <h2>{T.noDates[lang]}</h2>
          <p className="note">{T.noDatesLead[lang]}</p>
          <ul className="plain">
            {undated.map(x => (
              <li key={x.id} data-theme={x.id}><a href={`/themes/${x.id}/`}><span className="id">{x.id}</span> <Said value={x.title} lang={lang} machine={x.text_meta?.title} /></a> <StatusBadge status={x.status} lang={lang} /></li>
            ))}
          </ul>
        </section>
      ) : null}
    </>
  );
}

function Row({ theme, milestones, axis, today, todayPct }: { theme: Theme; milestones: Milestone[]; axis: ReturnType<typeof axisFor>; today: string; todayPct: number }) {
  const { lang } = useApp();
  const { start_date: a, due_date: b } = theme;
  const overdue = !!b && b < today && theme.status !== "done" && theme.status !== "cancelled";
  const span = a && b && a <= b ? [a, b] : null;
  const single = !span ? (b ?? a) : null;                                 // only one date (or start after the estimate): a marker, not a bar
  return (
    <div className="rm-row" role="row" data-theme={theme.id}>
      <a className="rm-label" role="rowheader" href={`/themes/${theme.id}/`}>
        <span className="id">{theme.id}</span> <Said value={theme.title} lang={lang} machine={theme.text_meta?.title} />
        {overdue ? <span className="flag lead" data-flag="overdue">{T.overdue[lang]}</span> : null}
      </a>
      <div className="rm-track" role="cell">
        <span className="rm-today" data-today={today} style={{ left: `${todayPct}%` }} title={T.today[lang]} />
        {span ? (
          <span className="rm-bar" data-s={theme.status} data-from={span[0]} data-to={span[1]} title={`${dateText(span[0])} → ${dateText(span[1])}`}
            style={{ left: `${pct(axis, span[0])}%`, width: `${widthPct(axis, span[0], span[1])}%` }} />
        ) : null}
        {single ? <span className="rm-dot" data-s={theme.status} data-at={single} title={dateText(single)} style={{ left: `${pct(axis, single)}%` }} /> : null}
        {milestones.map(m => (
          <span className="rm-ms" key={m.id} data-done={m.col === "done" ? "1" : "0"} data-at={m.due_date!} title={`${T.milestone[lang]}: ${m.title} · ${dateText(m.due_date)}`}
            style={{ left: `${pct(axis, m.due_date!)}%` }}>◆</span>
        ))}
      </div>
    </div>
  );
}
