"use client";
/* The executive view: every theme by front (Outros last) with the progress sentence, owner, status, estimate, milestones and what needs
   attention, and, on top, what needs the leadership. A click opens the theme. */
import { useCallback, useEffect, useMemo, useState } from "react";
import { STATUSES, T, t, text } from "../lib/i18n";
import type { Blocker, Decision, Front, Milestone, Theme } from "../lib/db";
import { isoWeek } from "../lib/week";
import { useApp } from "./Shell";
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
  const week = isoWeek();

  const load = useCallback(async () => {
    try {
      const [fronts, themes, weeks, blockers, decisions, milestones] = await Promise.all([db.fronts(), db.themes(), db.updateWeeks(), db.openBlockers(), db.openDecisions(), db.milestones()]);
      setData({ fronts, themes, weeks: new Set(weeks.map(w => `${w.theme_id}|${w.week}`)), blockers, decisions, milestones });
      setFailed(false);
    } catch { setFailed(true); }
  }, [db]);
  useEffect(() => { void load(); }, [load]);

  const tags = useMemo(() => [...new Set((data?.themes ?? []).flatMap(x => x.tags))].sort(), [data]);
  const owners = useMemo(() => [...new Set((data?.themes ?? []).map(x => x.owner).filter(Boolean) as string[])].sort(), [data]);

  if (failed) return <p className="state err">{T.failed[lang]}</p>;
  if (!data) return <p className="state">{T.loading[lang]}</p>;

  const open = (id: string) => ({
    blockers: data.blockers.filter(b => b.theme_id === id).length,
    decisions: data.decisions.filter(d => d.theme_id === id).length
  });
  const stale = (x: Theme) => x.status !== "done" && x.status !== "cancelled" && !data.weeks.has(`${x.id}|${week}`);
  const needsAttention = (x: Theme) => stale(x) || x.status === "at_risk" || x.status === "blocked" || open(x.id).blockers + open(x.id).decisions > 0;
  const shown = data.themes.filter(x => (status === "all" || x.status === status) && (!tag || x.tags.includes(tag)) && (!owner || x.owner === owner) && (!attention || needsAttention(x)));
  const title = (id: string) => data.themes.find(x => x.id === id)?.title;
  const leadership = [
    ...data.blockers.filter(b => b.needs_leadership).map(b => ({ kind: "blocker" as const, row: b })),
    ...data.decisions.filter(d => d.needs_leadership).map(d => ({ kind: "decision" as const, row: d }))
  ].sort((a, b) => (a.row.due_date ?? "9999").localeCompare(b.row.due_date ?? "9999"));

  return (
    <>
      <p className="eyebrow">{T.eyebrowTrack[lang]}</p>
      <h1>{T.executive[lang]}</h1>
      <p className="lead">{T.executiveLead[lang]}</p>
      <section className="kpis" aria-label={T.kpis[lang]}>
        {[
          { k: "active", n: data.themes.filter(x => x.status !== "done" && x.status !== "cancelled").length, on: () => { setStatus("all"); setAttention(false); } },
          { k: "on_track", n: data.themes.filter(x => x.status === "on_track").length, on: () => setStatus("on_track") },
          { k: "at_risk", n: data.themes.filter(x => x.status === "at_risk" || x.status === "blocked").length, tone: "warn", on: () => setStatus("at_risk") },
          { k: "stale", n: data.themes.filter(stale).length, tone: "warn", on: () => { setStatus("all"); setAttention(true); } },
          { k: "leadership", n: leadership.length, tone: "alert", on: () => document.getElementById("leadership")?.scrollIntoView({ behavior: "smooth" }) },
        ].map(c => (
          <button type="button" key={c.k} className="kpi" data-kpi={c.k} data-tone={c.n ? c.tone : undefined} onClick={c.on}>
            <span className="kpi-label">{T[`kpi_${c.k}`][lang]}</span>
            <span className="kpi-n">{c.n}</span>
          </button>
        ))}
      </section>
      <section className="alert" id="leadership" aria-label={T.leadership[lang]}>
        <h2>{T.leadership[lang]}</h2>
        {leadership.length ? (
          <ul>
            {leadership.map(({ kind, row }) => (
              <li key={row.id} data-kind={kind}>
                <span className="id">{kind === "blocker" ? T.blockers[lang] : T.decisions[lang]}</span>{" "}
                <Said value={row.what} lang={lang} machine={row.text_meta?.what} />{" — "}
                <a href={`/themes/${row.theme_id}/`}>{row.theme_id} <Said value={title(row.theme_id)} lang={lang} /></a>
                <span className="note">{("owner" in row ? row.owner : row.decider) ? ` · ${"owner" in row ? row.owner : row.decider}` : ""}{row.due_date ? ` · ${T.byWhen[lang]}: ${dateText(row.due_date)}` : ""}</span>
              </li>
            ))}
          </ul>
        ) : <p className="empty">{T.leadershipNone[lang]}</p>}
      </section>
      <div className="bar">
        <div className="filters" role="group" aria-label={T.status[lang]}>
          {["all", ...STATUSES].map(s => <button key={s} type="button" aria-pressed={status === s} onClick={() => setStatus(s)}>{s === "all" ? T.all[lang] : t(`status.${s}`, lang)}</button>)}
        </div>
        <div className="inline">
          <select aria-label={T.tag[lang]} value={tag} onChange={e => setTag(e.target.value)}><option value="">{T.tag[lang]}: {T.all[lang]}</option>{tags.map(x => <option key={x} value={x}>#{x}</option>)}</select>
          <select aria-label={T.owner[lang]} value={owner} onChange={e => setOwner(e.target.value)}><option value="">{T.owner[lang]}: {T.all[lang]}</option>{owners.map(x => <option key={x} value={x}>{x}</option>)}</select>
          <label className="checks"><input type="checkbox" checked={attention} onChange={e => setAttention(e.target.checked)} /> {T.onlyAttention[lang]}</label>
        </div>
      </div>
      {data.fronts.map(f => (
        <section className="front" key={f.key} id={`front-${f.key}`}>
          <h2>{text(f.name, lang)}</h2>
          <ul className="list">
            {shown.filter(x => x.front === f.key).map(x => {
              const c = open(x.id);
              const ms = data.milestones.filter(m => m.theme_id === x.id && m.col !== "done").slice(0, 3);
              return (
                <li className="card-li" key={x.id} data-theme={x.id}>
                  <a className="card" href={`/themes/${x.id}/`}>
                    <div className="top">
                      <span className="id">{x.id}</span>
                      <StatusBadge status={x.status} lang={lang} />
                      {x.stage ? <span className="ver">{t(`stage.${x.stage}`, lang)}</span> : null}
                      {stale(x) ? <span className="flag">{T.noUpdate[lang]}</span> : null}
                      {c.blockers ? <span className="flag lead">{c.blockers} {T.openBlockers[lang]}</span> : null}
                      {c.decisions ? <span className="flag lead">{c.decisions} {T.openDecisions[lang]}</span> : null}
                    </div>
                    <h3><Said value={x.title} lang={lang} machine={x.text_meta?.title} /></h3>
                    {text(x.progress, lang) ? <p className="progress"><Said value={x.progress} lang={lang} machine={x.text_meta?.progress} /></p> : null}
                    <div className="meta">
                      <span>{x.owner ?? "—"}</span>
                      <span>{T.due[lang]}: {dateText(x.due_date)}</span>
                      {ms.map(m => <span key={m.id}>◆ {m.title} {dateText(m.due_date)}</span>)}
                    </div>
                  </a>
                </li>
              );
            })}
          </ul>
          {!shown.some(x => x.front === f.key) ? <p className="empty">{T.noThemes[lang]}</p> : null}
        </section>
      ))}
    </>
  );
}
