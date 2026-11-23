"use client";
/* The leadership's home: the numbers of the portfolio (each opens the executive view filtered), what needs attention (what needs the leadership first,
   then themes at risk, blocked or overdue), what is due in the next four weeks, each front in one line, and the themes updated this week. */
import { useCallback, useEffect, useState } from "react";
import { T, t, text } from "../lib/i18n";
import type { Blocker, Decision, Front, Milestone, Theme } from "../lib/db";
import { atRisk, isOpen, isOverdue, isStale, kpis, leadershipItems } from "../lib/portfolio";
import { isoWeek } from "../lib/week";
import { useApp } from "./Shell";
import { Kpis } from "./Kpis";
import { Said, StatusBadge, dateText } from "./ui";

type Data = { fronts: Front[]; themes: Theme[]; weeks: Set<string>; blockers: Blocker[]; decisions: Decision[]; milestones: Milestone[] };
const MIX = ["on_track", "at_risk", "blocked", "not_started", "paused", "done"] as const;

export function OverviewPage() {
  const { lang, db } = useApp();
  const [data, setData] = useState<Data | null>(null);
  const [failed, setFailed] = useState(false);
  const week = isoWeek();
  const today = new Date().toISOString().slice(0, 10);
  const horizon = new Date(Date.now() + 28 * 86_400_000).toISOString().slice(0, 10);

  const load = useCallback(async () => {
    try {
      const [fronts, themes, weeks, blockers, decisions, milestones] = await Promise.all([db.fronts(), db.themes(), db.updateWeeks(), db.openBlockers(), db.openDecisions(), db.milestones()]);
      setData({ fronts, themes, weeks: new Set(weeks.map(w => `${w.theme_id}|${w.week}`)), blockers, decisions, milestones });
      setFailed(false);
    } catch { setFailed(true); }
  }, [db]);
  useEffect(() => { void load(); }, [load]);

  if (failed) return <p className="state err">{T.failed[lang]}</p>;
  if (!data) return <p className="state">{T.loading[lang]}</p>;

  const stale = isStale(data, week);
  const overdue = isOverdue(today);
  const lead = leadershipItems(data);
  const title = (id: string) => data.themes.find(x => x.id === id)?.title;
  const watch = data.themes.filter(x => atRisk(x) || overdue(x)).sort((a, b) => Number(b.status === "blocked") - Number(a.status === "blocked") || (a.due_date ?? "9999").localeCompare(b.due_date ?? "9999"));
  const upcoming = [
    ...data.milestones.filter(m => m.col !== "done" && m.due_date && m.due_date >= today && m.due_date <= horizon).map(m => ({ date: m.due_date!, theme: m.theme_id, what: `◆ ${m.title}` })),
    ...data.themes.filter(x => isOpen(x) && x.due_date && x.due_date >= today && x.due_date <= horizon).map(x => ({ date: x.due_date!.slice(0, 10), theme: x.id, what: T.dueTheme[lang] })),
  ].sort((a, b) => a.date.localeCompare(b.date)).slice(0, 12);
  const updated = data.themes.filter(x => data.weeks.has(`${x.id}|${week}`));

  return (
    <>
      <p className="eyebrow">{T.eyebrowTrack[lang]}</p>
      <h1>{T.overview[lang]}</h1>
      <p className="lead">{T.overviewLead[lang]}</p>
      <Kpis values={kpis(data, data.themes, week, today)} lang={lang} hrefOf={k => `/executive/?f=${k}`} />

      <div className="ov-grid">
        <section className="panel" aria-label={T.attention[lang]} data-block="attention">
          <h2>{T.attention[lang]}</h2>
          <div className="alert" aria-label={T.leadership[lang]} role="region">
            <h3>{T.leadership[lang]}</h3>
            {lead.length ? (
              <ul>{lead.map(({ kind, row }) => (
                <li key={row.id} data-kind={kind}>
                  <span className="id">{kind === "blocker" ? T.blockers[lang] : T.decisions[lang]}</span>{" "}
                  <Said value={row.what} lang={lang} machine={row.text_meta?.what} />{" — "}
                  <a href={`/themes/${row.theme_id}/`}>{row.theme_id} <Said value={title(row.theme_id)} lang={lang} /></a>
                  <span className="note">{("owner" in row ? row.owner : row.decider) ? ` · ${"owner" in row ? row.owner : row.decider}` : ""}{row.due_date ? ` · ${T.byWhen[lang]}: ${dateText(row.due_date)}` : ""}</span>
                </li>
              ))}</ul>
            ) : <p className="empty">{T.leadershipNone[lang]}</p>}
          </div>
          {watch.length ? (
            <ul className="plain lines">{watch.map(x => (
              <li key={x.id} data-theme={x.id}>
                <a href={`/themes/${x.id}/`}><span className="id">{x.id}</span> <Said value={x.title} lang={lang} machine={x.text_meta?.title} /></a>
                <StatusBadge status={x.status} lang={lang} />
                {overdue(x) ? <span className="flag lead">{T.kpi_overdue[lang]} · {dateText(x.due_date)}</span> : null}
              </li>
            ))}</ul>
          ) : !lead.length ? <p className="empty">{T.attentionNone[lang]}</p> : null}
        </section>

        <section className="panel" aria-label={T.upcoming[lang]} data-block="upcoming">
          <h2>{T.upcoming[lang]}</h2>
          {upcoming.length ? (
            <ul className="plain lines">{upcoming.map((u, i) => (
              <li key={i} data-theme={u.theme}><time className="id">{u.date}</time> <a href={`/themes/${u.theme}/`}>{u.theme} <Said value={title(u.theme)} lang={lang} /></a> <span className="note">{u.what}</span></li>
            ))}</ul>
          ) : <p className="empty">{T.upcomingNone[lang]}</p>}
        </section>
      </div>

      <section className="fronts-sum" aria-label={T.frontSummary[lang]}>
        <table className="stats">
          <thead><tr><th>{T.frontSummary[lang]}</th><th>{T.kpi_active[lang]}</th><th>{T.kpi_at_risk[lang]}</th><th>{T.kpi_overdue[lang]}</th><th>{T.kpi_stale[lang]}</th><th>{T.statusMix[lang]}</th></tr></thead>
          <tbody>
            {data.fronts.map(f => {
              const mine = data.themes.filter(x => x.front === f.key);
              if (!mine.length) return null;
              const n = { active: mine.filter(isOpen).length, at_risk: mine.filter(atRisk).length, overdue: mine.filter(overdue).length, stale: mine.filter(stale).length };
              return (
                <tr key={f.key} data-front={f.key}>
                  <th><a href={`/executive/#front-${f.key}`}>{text(f.name, lang)}</a></th>
                  <td className="num" data-k="active">{n.active}</td>
                  <td className="num" data-k="at_risk" data-tone={n.at_risk ? "warn" : undefined}>{n.at_risk}</td>
                  <td className="num" data-k="overdue" data-tone={n.overdue ? "warn" : undefined}>{n.overdue}</td>
                  <td className="num" data-k="stale" data-tone={n.stale ? "warn" : undefined}>{n.stale}</td>
                  <td className="mix-cell"><span className="mix" role="img" aria-label={MIX.map(s => `${t(`status.${s}`, lang)}: ${mine.filter(x => x.status === s).length}`).join(", ")}>
                    {MIX.map(s => { const c = mine.filter(x => x.status === s).length; return c ? <i key={s} data-s={s} style={{ flexGrow: c }} title={`${t(`status.${s}`, lang)}: ${c}`} /> : null; })}
                  </span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <section className="panel" aria-label={T.thisWeek[lang]} data-block="updated">
        <h2>{T.thisWeek[lang]} <span className="note">{week}</span></h2>
        {updated.length ? (
          <ul className="plain lines">{updated.map(x => (
            <li key={x.id} data-theme={x.id}><a href={`/themes/${x.id}/`}><span className="id">{x.id}</span> <Said value={x.title} lang={lang} /></a> <StatusBadge status={x.status} lang={lang} />
              <span className="note"> {text(x.progress, lang) ? <Said value={x.progress} lang={lang} machine={x.text_meta?.progress} /> : null}</span></li>
          ))}</ul>
        ) : <p className="empty">{T.thisWeekNone[lang]}</p>}
        <p><a className="btn" href="/executive/">{T.seeExecutive[lang]} →</a></p>
      </section>
    </>
  );
}
