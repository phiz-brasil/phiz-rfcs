"use client";
/* The Painel (docs/spec/v2/redesign.md, "Painel"): the leadership's home. On top, the numbers (each opens the executive view filtered) and three
   blocks — what needs you, the latest decisions, the next milestones — where each line shows the theme, then what to communicate, then its
   urgency, and never a person's name. Below, the open themes by front, as a List (status, owner and forecast edited in place) or as a Timeline
   by quarter (title and "what it is" edited in place; a click on a quarter sets the period or the forecast; the deliveries open under the theme). */
import { useCallback, useEffect, useMemo, useState, type FocusEvent, type KeyboardEvent } from "react";
import { STATUSES, T, t, text, type Lang } from "../lib/i18n";
import type { Blocker, Decision, Front, I18n, Item, Milestone, Theme } from "../lib/db";
import { atRisk, isOpen, isOverdue, isStale, kpis } from "../lib/portfolio";
import { isoWeek } from "../lib/week";
import { NO_FILTERS, PHASE_FILL, applyFilters, barOf, columnOf, latestDecisions, needsYou, nextMilestones, phaseOf, positionOf, quarters, stretch, themePeriod,
  type Filters, type Line, type Quarter } from "../lib/painel";
import { useApp } from "./Shell";
import { Kpis } from "./Kpis";
import { Said, StatusBadge, message } from "./ui";

type Data = { fronts: Front[]; themes: Theme[]; weeks: Set<string>; blockers: Blocker[]; decisions: Decision[]; decided: Decision[]; milestones: Milestone[]; items: Item[] };
type View = "list" | "timeline";
const VIEW_KEY = "phiz-painel-view";
const MIX = ["on_track", "at_risk", "blocked", "not_started", "paused", "done"] as const;
const merge = (old: I18n, lang: Lang, value: string): I18n => ({ ...old, [lang]: value });
const qLabel = (q: Quarter) => `Q${q.q} ${q.year}`;
const enter = (e: KeyboardEvent<HTMLInputElement>) => { if (e.key === "Enter") e.currentTarget.blur(); };

export function OverviewPage() {
  const { lang, db, name, reader } = useApp();
  const [data, setData] = useState<Data | null>(null);
  const [failed, setFailed] = useState(false);
  const [view, setView] = useState<View>("list");
  const [f, setF] = useState<Filters>(NO_FILTERS);
  const [opened, setOpened] = useState<Set<string>>(new Set());
  const [note, setNote] = useState("");
  const week = isoWeek();
  const today = new Date().toISOString().slice(0, 10);
  const qs = useMemo(() => quarters(today, 5), [today]);

  const load = useCallback(async () => {
    try {
      const [fronts, themes, weeks, blockers, decisions, decided, milestones, items] = await Promise.all([
        db.fronts(), db.themes(), db.updateWeeks(), db.openBlockers(), db.openDecisions(), db.decided(), db.milestones(), db.deliveries()]);
      setData({ fronts, themes, weeks: new Set(weeks.map(w => `${w.theme_id}|${w.week}`)), blockers, decisions, decided, milestones, items });
      setFailed(false);
    } catch { setFailed(true); }
  }, [db]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    try { const v = localStorage.getItem(VIEW_KEY); if (v === "list" || v === "timeline") setView(v); } catch { /* blocked */ }
  }, []);
  const pickView = (v: View) => { setView(v); try { localStorage.setItem(VIEW_KEY, v); } catch { /* blocked */ } };

  /* every write: the name is required (as on the other pages); the page reads everything again after it */
  const write = async (fn: (by: string) => Promise<unknown>) => {
    if (!name.trim()) { setNote(T.needName[lang]); return; }
    try { await fn(name.trim()); setNote(""); await load(); } catch (e) { setNote(message(e, lang)); }
  };

  const owners = useMemo(() => [...new Set((data?.themes ?? []).map(x => x.owner).filter(Boolean) as string[])].sort(), [data]);
  const tags = useMemo(() => [...new Set((data?.themes ?? []).flatMap(x => x.tags))].sort(), [data]);

  if (failed) return <p className="state err">{T.failed[lang]}</p>;
  if (!data) return <p className="state">{T.loading[lang]}</p>;

  const stale = isStale(data, week);
  const overdue = isOverdue(today);
  const ids = new Set(data.themes.map(x => x.id));
  const byId = new Map(data.themes.map(x => [x.id, x]));
  const itemsOf = (id: string) => data.items.filter(i => i.theme_id === id);
  const openCount = (id: string) => data.blockers.filter(b => b.theme_id === id).length + data.decisions.filter(d => d.theme_id === id).length;
  const attention = (x: Theme) => stale(x) || atRisk(x) || overdue(x) || openCount(x.id) > 0;
  const closedPicked = f.status === "done" || f.status === "cancelled";
  const shown = applyFilters(data.themes.filter(x => closedPicked || isOpen(x)), f, { attention, stale });
  const groups = data.fronts.map(fr => ({ front: fr, rows: shown.filter(x => x.front === fr.key) })).filter(g => g.rows.length);
  const chosenFront = f.front ? data.fronts.find(x => x.key === f.front) : null;
  const filtered = JSON.stringify(f) !== JSON.stringify(NO_FILTERS);
  const staleCount = data.themes.filter(stale).length;

  const you = needsYou(data.blockers, data.decisions, ids);
  const latest = latestDecisions(data.decided, ids);
  const next = nextMilestones(data.themes.map(x => ({ id: x.id, due_date: x.due_date, open: isOpen(x) })), data.milestones, today, 90);
  const set = (k: keyof Filters, v: string | boolean) => setF({ ...f, [k]: v });

  return (
    <div className="painel">
      <p className="eyebrow">{T.eyebrowTrack[lang]}</p>
      <h1>{T.overview[lang]}</h1>
      <p className="lead">{T.painelLead[lang]}</p>
      <Kpis values={kpis(data, data.themes, week, today)} lang={lang} hrefOf={k => `/executive/?f=${k}`} compact />

      <div className="pn-blocks">
        <Block id="you" label={T.needsYou[lang]} empty={T.needsYouNone[lang]} lines={you} lang={lang} byId={byId} />
        <Block id="decisions" label={T.latestDecisions[lang]} empty={T.latestDecisionsNone[lang]} lines={latest} lang={lang} byId={byId} />
        <Block id="milestones" label={T.nextMilestones[lang]} empty={T.nextMilestonesNone[lang]} lines={next} lang={lang} byId={byId} />
      </div>

      <div className="pn-toolbar">
        <div className="pn-filters" role="group" aria-label={T.filters[lang]}>
          <select aria-label={T.front[lang]} value={f.front} onChange={e => set("front", e.target.value)}>
            <option value="">{T.front[lang]}: {T.all[lang]}</option>{data.fronts.map(x => <option key={x.key} value={x.key}>{text(x.name, lang)}</option>)}
          </select>
          <select aria-label={T.owner[lang]} value={f.owner} onChange={e => set("owner", e.target.value)}>
            <option value="">{T.owner[lang]}: {T.all[lang]}</option>{owners.map(x => <option key={x} value={x}>{x}</option>)}
          </select>
          <select aria-label={T.status[lang]} value={f.status} onChange={e => set("status", e.target.value)}>
            <option value="">{T.status[lang]}: {T.all[lang]}</option>{STATUSES.map(s => <option key={s} value={s}>{t(`status.${s}`, lang)}</option>)}
          </select>
          <select aria-label={T.tag[lang]} value={f.tag} onChange={e => set("tag", e.target.value)}>
            <option value="">{T.tag[lang]}: {T.all[lang]}</option>{tags.map(x => <option key={x} value={x}>#{x}</option>)}
          </select>
          <select aria-label={T.kind[lang]} value={f.kind} onChange={e => set("kind", e.target.value)}>
            <option value="">{T.kind[lang]}: {T.all[lang]}</option><option value="project">{T.project[lang]}</option><option value="task">{T.task[lang]}</option>
          </select>
          <button type="button" className="chip" aria-pressed={f.attention} onClick={() => set("attention", !f.attention)}>{T.onlyAttention[lang]}</button>
          <button type="button" className="chip" aria-pressed={f.stale} data-toggle="stale" onClick={() => set("stale", !f.stale)}>{staleCount} {T.staleToggle[lang]}</button>
          {filtered ? <button type="button" className="mini" onClick={() => setF(NO_FILTERS)}>{T.clearFilters[lang]}</button> : null}
        </div>
        <div className="seg" role="group" aria-label={T.views[lang]}>
          <button type="button" aria-pressed={view === "list"} onClick={() => pickView("list")}>{T.viewList[lang]}</button>
          <button type="button" aria-pressed={view === "timeline"} onClick={() => pickView("timeline")}>{T.viewTimeline[lang]}</button>
        </div>
        {!reader ? <a className="btn primary" href="/themes/?new=1">＋ {T.newTheme[lang]}</a> : null}
      </div>
      {chosenFront && text(chosenFront.scope, lang) ? <p className="pn-scope" data-scope={chosenFront.key}>{text(chosenFront.scope, lang)}</p> : null}
      {note ? <p className="state err" role="alert">{note}</p> : null}
      {!reader ? <p className="note pn-hint">{view === "timeline" ? T.timelineHint[lang] : T.editHint[lang]}</p> : null}

      {!groups.length ? <p className="empty">{T.noThemes[lang]}</p> : view === "list" ? (
        <div className="pn-list" data-view="list">
          {groups.map(({ front, rows }) => (
            <section key={front.key} className="pn-group" data-front={front.key} aria-label={text(front.name, lang)}>
              <FrontHead front={front} rows={rows} lang={lang} stale={stale} overdue={overdue} />
              {rows.map(x => (
                <div key={x.id} className="pn-row" data-theme={x.id}>
                  <PhaseIcon theme={x} lang={lang} />
                  <div className="pn-main">
                    <div className="pn-line">
                      <a className="pn-title" href={`/themes/${x.id}/`}><span className="id">{x.id}</span> <Said value={x.title} lang={lang} machine={x.text_meta?.title} /></a>
                      {text(x.what_it_is, lang) ? <span className="pn-what"><Said value={x.what_it_is} lang={lang} machine={x.text_meta?.what_it_is} /></span> : null}
                      {stale(x) ? <span className="flag">{T.noUpdate[lang]}</span> : null}
                    </div>
                    {text(x.progress, lang) ? <div className="pn-progress"><Said value={x.progress} lang={lang} machine={x.text_meta?.progress} /></div> : null}
                  </div>
                  {reader ? <StatusBadge status={x.status} lang={lang} /> : (
                    <select className="ed-select" aria-label={T.status[lang]} data-s={x.status} value={x.status}
                      onChange={e => void write(by => db.updateTheme(x.id, { status: e.target.value }, by))}>
                      {STATUSES.map(s => <option key={s} value={s}>{t(`status.${s}`, lang)}</option>)}
                    </select>
                  )}
                  {reader ? <span className="pn-owner">{x.owner ?? "—"}</span> : (
                    <input key={`${x.id}|${x.owner ?? ""}`} className="ed" aria-label={T.owner[lang]} list="pn-owners" defaultValue={x.owner ?? ""} placeholder="—" maxLength={80}
                      onKeyDown={enter} onBlur={(e: FocusEvent<HTMLInputElement>) => { const v = e.target.value.trim(); if (v !== (x.owner ?? "")) void write(by => db.updateTheme(x.id, { owner: v }, by)); }} />
                  )}
                  {reader ? <span className="pn-due">{x.due_date ? x.due_date.slice(0, 10) : T.noDate[lang]}</span> : (
                    <select className="ed-select" aria-label={T.forecast[lang]} value={x.due_date?.slice(0, 10) ?? ""}
                      onChange={e => void write(by => db.updateTheme(x.id, { due_date: e.target.value || null }, by))}>
                      <option value="">{T.noDate[lang]}</option>
                      {x.due_date && !qs.some(q => q.end === x.due_date!.slice(0, 10)) ? <option value={x.due_date.slice(0, 10)}>{x.due_date.slice(0, 10)}</option> : null}
                      {qs.map(q => <option key={q.key} value={q.end}>{qLabel(q)}</option>)}
                    </select>
                  )}
                </div>
              ))}
            </section>
          ))}
          <datalist id="pn-owners">{owners.map(o => <option key={o} value={o} />)}</datalist>
        </div>
      ) : (
        <Timeline groups={groups} qs={qs} today={today} lang={lang} reader={reader} itemsOf={itemsOf} opened={opened}
          setOpened={setOpened} write={write} db={db} stale={stale} overdue={overdue} />
      )}
    </div>
  );
}

function Block({ id, label, empty, lines, lang, byId }: { id: string; label: string; empty: string; lines: Line[]; lang: Lang; byId: Map<string, Theme> }) {
  return (
    <section className="pn-block" role="region" aria-label={label} data-block={id}>
      <h2>{label} <span className="note">{lines.length}</span></h2>
      {lines.length ? (
        <ul className="pn-lines">
          {lines.map(l => (
            <li key={l.key} data-theme={l.theme} data-urgency={l.urgency} data-kind={l.kind}>
              <a href={`/themes/${l.theme}/`}>
                <span className="pn-top">
                  <b className="pn-theme"><Said value={byId.get(l.theme)?.title} lang={lang} /></b>
                  {l.date ? <time className="pn-date">{l.date}</time> : null}
                  <span className="urg" data-u={l.urgency}>{t(`urg.${l.urgency}`, lang)}</span>
                </span>
                <span className="pn-msg">{typeof l.text === "string" ? (l.kind === "milestone" ? `◆ ${l.text}` : T.dueTheme[lang]) : <Said value={l.text} lang={lang} />}</span>
              </a>
            </li>
          ))}
        </ul>
      ) : <p className="empty">{empty}</p>}
    </section>
  );
}

/* The head of a front: its name and count, then the numbers the old front summary showed and the mix of statuses. */
function FrontHead({ front, rows, lang, stale, overdue }: { front: Front; rows: Theme[]; lang: Lang; stale: (x: Theme) => boolean; overdue: (x: Theme) => boolean }) {
  const n = { active: rows.filter(isOpen).length, at_risk: rows.filter(atRisk).length, overdue: rows.filter(overdue).length, stale: rows.filter(stale).length };
  return (
    <header className="pn-front">
      <h2>{text(front.name, lang)} <span className="note" data-k="count">{rows.length}</span></h2>
      <span className="pn-front-n">
        {(["at_risk", "overdue", "stale"] as const).map(k => n[k] ? <span key={k} className="flag" data-k={k}>{n[k]} {T[`kpi_${k}`][lang]}</span> : null)}
      </span>
      <span className="mix" role="img" aria-label={MIX.map(s => `${t(`status.${s}`, lang)}: ${rows.filter(x => x.status === s).length}`).join(", ")}>
        {MIX.map(s => { const c = rows.filter(x => x.status === s).length; return c ? <i key={s} data-s={s} style={{ flexGrow: c }} /> : null; })}
      </span>
    </header>
  );
}

/* The small icon of the phase (from the PDLC B2B stage), coloured by the theme's status. */
function PhaseIcon({ theme, lang }: { theme: Theme; lang: Lang }) {
  const ph = phaseOf(theme.kind === "project" ? theme.stage : null);
  const c = 2 * Math.PI * 3;
  return (
    <svg className="phase" data-s={theme.status} data-phase={ph ?? "task"} width="14" height="14" viewBox="0 0 14 14" role="img"
      aria-label={ph ? t(`phase.${ph}`, lang) : T.task[lang]}>
      <circle cx="7" cy="7" r="6" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray={ph === "discovery" ? "2 2" : undefined} />
      {ph && PHASE_FILL[ph] ? <circle cx="7" cy="7" r="3" fill="none" stroke="currentColor" strokeWidth="6" strokeDasharray={`${(PHASE_FILL[ph] * c).toFixed(2)} ${c.toFixed(2)}`} transform="rotate(-90 7 7)" /> : null}
    </svg>
  );
}

type TimelineProps = {
  groups: { front: Front; rows: Theme[] }[]; qs: Quarter[]; today: string; lang: Lang; reader: boolean; itemsOf: (id: string) => Item[];
  opened: Set<string>; setOpened: (s: Set<string>) => void; write: (fn: (by: string) => Promise<unknown>) => Promise<void>;
  db: ReturnType<typeof useApp>["db"]; stale: (x: Theme) => boolean; overdue: (x: Theme) => boolean;
};

function Timeline({ groups, qs, today, lang, reader, itemsOf, opened, setOpened, write, db, stale, overdue }: TimelineProps) {
  const n = qs.length;
  const nowAt = positionOf(qs, today);
  const projects = groups.flatMap(g => g.rows).filter(x => x.kind === "project").map(x => x.id);
  const allOpen = projects.length > 0 && projects.every(id => opened.has(id));
  const toggle = (id: string) => { const s = new Set(opened); if (s.has(id)) s.delete(id); else s.add(id); setOpened(s); };
  const span = (a: number, b: number) => ({ left: `${(a / n) * 100}%`, width: `${((b - a + 1) / n) * 100}%` });
  const [draft, setDraft] = useState<Record<string, string>>({});

  return (
    <div className="pn-tl" data-view="timeline" style={{ ["--cols" as string]: n }}>
      <div className="pn-tl-head">
        <span className="pn-tl-name">{T.themeAndDeliveries[lang]}
          {projects.length ? <button type="button" className="mini" onClick={() => setOpened(allOpen ? new Set() : new Set(projects))}>{allOpen ? T.closeAll[lang] : T.openAll[lang]}</button> : null}
        </span>
        <div className="pn-track pn-qs">
          {qs.map(q => <span key={q.key} className="pn-q" data-q={q.key}>{qLabel(q)}</span>)}
          <span className="pn-today" style={{ left: `${nowAt}%` }}>{T.today[lang]}</span>
        </div>
      </div>
      {groups.map(({ front, rows }) => (
        <section key={front.key} className="pn-group" data-front={front.key} aria-label={text(front.name, lang)}>
          <FrontHead front={front} rows={rows} lang={lang} stale={stale} overdue={overdue} />
          {rows.map(x => {
            const items = x.kind === "project" ? itemsOf(x.id) : [];
            const dated = items.some(i => i.start_date || i.due_date);
            const per = themePeriod({ start: x.start_date, due: x.due_date }, items.map(i => ({ start: i.start_date ?? null, due: i.due_date })));
            const bar = barOf(qs, per);
            const dueCol = x.due_date ? columnOf(qs, x.due_date) : -1;
            const isOpenRow = opened.has(x.id);
            const click = (i: number) => void write(by => dated
              ? db.updateTheme(x.id, { due_date: qs[i].end }, by)
              : db.updateTheme(x.id, stretch(qs, { start: x.start_date, due: x.due_date }, i), by));
            return (
              <div key={x.id} className="pn-tl-theme" data-theme={x.id}>
                <div className="pn-tl-row">
                  <div className="pn-tl-name">
                    {x.kind === "project" ? <button type="button" className="caret" aria-expanded={isOpenRow} aria-label={T.showDeliveries[lang]} onClick={() => toggle(x.id)}>{isOpenRow ? "▾" : "▸"}</button> : <span className="caret" />}
                    <PhaseIcon theme={x} lang={lang} />
                    <div className="pn-tl-text">
                      {reader ? (
                        <>
                          <a className="pn-title" href={`/themes/${x.id}/`}><Said value={x.title} lang={lang} machine={x.text_meta?.title} /></a>
                          <span className="pn-what"><Said value={x.what_it_is} lang={lang} machine={x.text_meta?.what_it_is} /></span>
                        </>
                      ) : (
                        <>
                          <input key={`t|${x.id}|${x.title[lang] ?? ""}`} className="ed pn-title" aria-label={T.title[lang]} defaultValue={x.title[lang] ?? text(x.title, lang)} maxLength={200}
                            onKeyDown={enter} onBlur={e => { const v = e.target.value.trim(); if (v && v !== (x.title[lang] ?? "")) void write(by => db.updateTheme(x.id, { title: merge(x.title, lang, v) }, by)); }} />
                          <input key={`w|${x.id}|${x.what_it_is[lang] ?? ""}`} className="ed pn-what" aria-label={T.whatItIs[lang]} defaultValue={x.what_it_is[lang] ?? ""} placeholder={T.whatItIs[lang]} maxLength={1200}
                            onKeyDown={enter} onBlur={e => { const v = e.target.value.trim(); if (v !== (x.what_it_is[lang] ?? "")) void write(by => db.updateTheme(x.id, { what_it_is: merge(x.what_it_is, lang, v) }, by)); }} />
                        </>
                      )}
                    </div>
                    {!reader ? <a className="pn-open" href={`/themes/${x.id}/`} aria-label={T.openTheme[lang]} title={T.openTheme[lang]}>↗</a> : null}
                  </div>
                  <div className="pn-track">
                    {qs.map((q, i) => reader ? <span key={q.key} className="pn-cell" /> : (
                      <button key={q.key} type="button" className="pn-cell" data-q={q.key} aria-label={`${dated ? T.forecastIn[lang] : T.periodTo[lang]} ${qLabel(q)}`} onClick={() => click(i)} />
                    ))}
                    <span className="pn-now" style={{ left: `${nowAt}%` }} />
                    {bar ? <span className="pn-bar" data-s={x.status} data-overdue={overdue(x) || undefined} style={span(bar[0], bar[1])}>{bar[1] > bar[0] ? text(x.title, lang) : ""}</span> : null}
                    {dueCol >= 0 && dueCol < n ? <span className="pn-diamond" title={`${T.forecast[lang]}: ${x.due_date!.slice(0, 10)}`} style={{ left: `${((dueCol + 1) / n) * 100}%` }} /> : null}
                  </div>
                </div>
                {isOpenRow ? (
                  <div className="pn-items" aria-label={T.deliveries[lang]}>
                    {items.map(it => {
                      const ib = barOf(qs, { start: it.start_date ?? null, due: it.due_date });
                      return (
                        <div key={it.id} className="pn-tl-row pn-item" data-item={it.id}>
                          <div className="pn-tl-name">
                            <span className="dot" data-col={it.col} title={t(`col.${it.col}`, lang)} />
                            {reader ? <span className="pn-item-title">{it.milestone ? "◆ " : ""}{it.title}</span> : (
                              <input key={`i|${it.id}|${it.title}`} className="ed pn-item-title" aria-label={T.deliveryName[lang]} defaultValue={it.title} maxLength={200}
                                onKeyDown={enter} onBlur={e => { const v = e.target.value.trim(); if (v && v !== it.title) void write(by => db.saveItem(x.id, it.id, { title: v }, by)); }} />
                            )}
                          </div>
                          <div className="pn-track">
                            {qs.map((q, i) => reader ? <span key={q.key} className="pn-cell" /> : (
                              <button key={q.key} type="button" className="pn-cell" data-q={q.key} aria-label={`${T.periodTo[lang]} ${qLabel(q)}`}
                                onClick={() => void write(by => db.saveItem(x.id, it.id, stretch(qs, { start: it.start_date ?? null, due: it.due_date }, i), by))} />
                            ))}
                            <span className="pn-now" style={{ left: `${nowAt}%` }} />
                            {ib ? <span className="pn-bar thin" data-col={it.col} style={span(ib[0], ib[1])} /> : null}
                          </div>
                        </div>
                      );
                    })}
                    {!reader ? (
                      <div className="pn-tl-row pn-item pn-new">
                        <div className="pn-tl-name">
                          <span className="dot add">+</span>
                          <input className="ed" aria-label={T.newDelivery[lang]} placeholder={T.newDelivery[lang]} maxLength={200} value={draft[x.id] ?? ""}
                            onChange={e => setDraft({ ...draft, [x.id]: e.target.value })}
                            onKeyDown={e => {
                              const v = (draft[x.id] ?? "").trim();
                              if (e.key === "Enter" && v) void write(by => db.saveItem(x.id, null, { title: v }, by)).then(() => setDraft(d => ({ ...d, [x.id]: "" })));
                            }} />
                        </div>
                        <div className="pn-track" />
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            );
          })}
        </section>
      ))}
    </div>
  );
}
