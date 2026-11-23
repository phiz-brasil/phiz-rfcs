"use client";
/* The executive view: every theme in one compact table, grouped by front (Outros last): status, stage, owner, the progress sentence, the estimate,
   the next milestone and the signals that need attention. The numbers on top filter the table; ?f=<number> opens it filtered (links from the overview). */
import { useCallback, useEffect, useMemo, useState } from "react";
import { STATUSES, T, t, text } from "../lib/i18n";
import type { Blocker, Decision, Front, Milestone, Theme } from "../lib/db";
import { KPI_KEYS, atRisk, isOpen, isOverdue, isStale, kpis, leadershipItems, type Kpi } from "../lib/portfolio";
import { isoWeek } from "../lib/week";
import { useApp } from "./Shell";
import { Kpis } from "./Kpis";
import { Said, StatusBadge, dateText } from "./ui";

type Data = { fronts: Front[]; themes: Theme[]; weeks: Set<string>; blockers: Blocker[]; decisions: Decision[]; milestones: Milestone[] };

export function ExecutivePage() {
  const { lang, db } = useApp();
  const [data, setData] = useState<Data | null>(null);
  const [failed, setFailed] = useState(false);
  const [status, setStatus] = useState("all");
  const [tag, setTag] = useState("");
  const [owner, setOwner] = useState("");
  const [attention, setAttention] = useState(false);
  const [focus, setFocus] = useState<Kpi | null>(null);
  const week = isoWeek();
  const today = new Date().toISOString().slice(0, 10);

  const load = useCallback(async () => {
    try {
      const [fronts, themes, weeks, blockers, decisions, milestones] = await Promise.all([db.fronts(), db.themes(), db.updateWeeks(), db.openBlockers(), db.openDecisions(), db.milestones()]);
      setData({ fronts, themes, weeks: new Set(weeks.map(w => `${w.theme_id}|${w.week}`)), blockers, decisions, milestones });
      setFailed(false);
    } catch { setFailed(true); }
  }, [db]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const f = new URLSearchParams(location.search).get("f");
    if (f && (KPI_KEYS as readonly string[]).includes(f)) setFocus(f as Kpi);
  }, []);

  const tags = useMemo(() => [...new Set((data?.themes ?? []).flatMap(x => x.tags))].sort(), [data]);
  const owners = useMemo(() => [...new Set((data?.themes ?? []).map(x => x.owner).filter(Boolean) as string[])].sort(), [data]);

  if (failed) return <p className="state err">{T.failed[lang]}</p>;
  if (!data) return <p className="state">{T.loading[lang]}</p>;

  const stale = isStale(data, week);
  const overdue = isOverdue(today);
  const lead = leadershipItems(data);
  const leadIds = new Set(lead.map(l => l.row.theme_id));
  const open = (id: string) => ({ blockers: data.blockers.filter(b => b.theme_id === id).length, decisions: data.decisions.filter(d => d.theme_id === id).length });
  const needsAttention = (x: Theme) => stale(x) || atRisk(x) || overdue(x) || open(x.id).blockers + open(x.id).decisions > 0;
  const byFocus: Record<Kpi, (x: Theme) => boolean> = { active: isOpen, on_track: x => x.status === "on_track", at_risk: atRisk, overdue, stale, leadership: x => leadIds.has(x.id) };
  const shown = data.themes.filter(x => (status === "all" || x.status === status) && (!tag || x.tags.includes(tag)) && (!owner || x.owner === owner)
    && (!attention || needsAttention(x)) && (!focus || byFocus[focus](x)));
  const next = (id: string) => data.milestones.find(m => m.theme_id === id && m.col !== "done");

  return (
    <>
      <p className="eyebrow">{T.eyebrowTrack[lang]}</p>
      <h1>{T.executive[lang]}</h1>
      <p className="lead">{T.executiveLead[lang]}</p>
      <Kpis values={kpis(data, data.themes, week, today)} lang={lang} active={focus} onPick={k => setFocus(f => (f === k ? null : k))} />
      <div className="bar">
        <div className="filters" role="group" aria-label={T.status[lang]}>
          {["all", ...STATUSES].map(s => <button key={s} type="button" aria-pressed={status === s} onClick={() => setStatus(s)}>{s === "all" ? T.all[lang] : t(`status.${s}`, lang)}</button>)}
        </div>
        <div className="inline">
          <select aria-label={T.tag[lang]} value={tag} onChange={e => setTag(e.target.value)}><option value="">{T.tag[lang]}: {T.all[lang]}</option>{tags.map(x => <option key={x} value={x}>#{x}</option>)}</select>
          <select aria-label={T.owner[lang]} value={owner} onChange={e => setOwner(e.target.value)}><option value="">{T.owner[lang]}: {T.all[lang]}</option>{owners.map(x => <option key={x} value={x}>{x}</option>)}</select>
          <label className="checks"><input type="checkbox" checked={attention} onChange={e => setAttention(e.target.checked)} /> {T.onlyAttention[lang]}</label>
          {focus ? <button type="button" className="mini" data-focus={focus} onClick={() => setFocus(null)}>{T[`kpi_${focus}`][lang]} ✕</button> : null}
        </div>
      </div>
      <div className="tablewrap">
        <table className="stats themes-table">
          <thead><tr>
            <th>{T.colTheme[lang]}</th><th>{T.status[lang]}</th><th>{T.stage[lang]}</th><th>{T.owner[lang]}</th><th>{T.progress[lang].replace(/ \(.*\)$/, "")}</th>
            <th>{T.due[lang]}</th><th>{T.colNext[lang]}</th><th>{T.colSignals[lang]}</th>
          </tr></thead>
          {data.fronts.map(f => {
            const rows = shown.filter(x => x.front === f.key);
            return (
              <tbody key={f.key} id={`front-${f.key}`} data-front={f.key}>
                <tr className="front-row"><th colSpan={8}>{text(f.name, lang)} <span className="note">{rows.length}</span></th></tr>
                {rows.map(x => {
                  const c = open(x.id);
                  const m = next(x.id);
                  return (
                    <tr key={x.id} className="theme-row" data-theme={x.id} onClick={e => { if (!(e.target as Element).closest("a")) location.href = `/themes/${x.id}/`; }}>
                      <th><a href={`/themes/${x.id}/`}><span className="id">{x.id}</span> <Said value={x.title} lang={lang} machine={x.text_meta?.title} /></a></th>
                      <td><StatusBadge status={x.status} lang={lang} /></td>
                      <td className="stage">{x.stage ? t(`stage.${x.stage}`, lang) : "—"}</td>
                      <td>{x.owner ?? "—"}</td>
                      <td className="progress">{text(x.progress, lang) ? <Said value={x.progress} lang={lang} machine={x.text_meta?.progress} /> : "—"}</td>
                      <td className={overdue(x) ? "date overdue" : "date"}>{dateText(x.due_date)}</td>
                      <td>{m ? `◆ ${m.title} ${dateText(m.due_date)}` : "—"}</td>
                      <td className="signals">
                        {stale(x) ? <span className="flag">{T.noUpdate[lang]}</span> : null}
                        {overdue(x) ? <span className="flag lead">{T.kpi_overdue[lang]}</span> : null}
                        {c.blockers ? <span className="flag lead">{c.blockers} {T.openBlockers[lang]}</span> : null}
                        {c.decisions ? <span className="flag lead">{c.decisions} {T.openDecisions[lang]}</span> : null}
                      </td>
                    </tr>
                  );
                })}
                {!rows.length ? <tr className="empty-row"><td colSpan={8} className="empty">{T.noThemes[lang]}</td></tr> : null}
              </tbody>
            );
          })}
        </table>
      </div>
    </>
  );
}
