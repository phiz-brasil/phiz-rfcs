"use client";
/* /fup/<id>/: one FUP in three tabs (docs/spec/v2/fup.md). Agenda: every active theme by front, on or off, kind and favourite. Presentation:
   one theme per screen; what is recorded goes straight to the theme (status, decisions, execution items) and is kept in the FUP's log.
   Minutes: generated from the FUP. Closing freezes it and writes one weekly update per theme with records (close_fup). */
import { useCallback, useEffect, useMemo, useState } from "react";
import { T, t, text, type Tri } from "../lib/i18n";
import type { Attachment, Decision, Front, Fup, FupAgenda, FupKind, FupRecord, Theme, Update } from "../lib/db";
import { fmtDay, minutes } from "../lib/fup";
import { useApp } from "./Shell";
import { Said, StatusBadge, message } from "./ui";

type Tab = "agenda" | "present" | "minutes";
type Detail = { update: Update | null; attachments: Attachment[]; decisions: Decision[] };
const KINDS: FupKind[] = ["inform", "discuss", "decide"];
const PROGRESS: FupRecord["progress"][] = ["todo", "doing", "done"];
const TYPES: FupRecord["type"][] = ["note", "decision", "action"];
const HEALTH = ["on_track", "at_risk", "blocked"];

export function FupMeeting({ id }: { id: string }) {
  const { lang, db, name, reader } = useApp();
  const [fup, setFup] = useState<Fup | null>(null);
  const [fronts, setFronts] = useState<Front[]>([]);
  const [themes, setThemes] = useState<Map<string, Theme>>(new Map());
  const [openAtLoad, setOpenAtLoad] = useState<Map<string, Decision[]>>(new Map());
  const [state, setState] = useState<"loading" | "failed" | "missing" | "ok">("loading");
  const [tab, setTab] = useState<Tab>("agenda");
  const [cur, setCur] = useState(0);
  const [details, setDetails] = useState<Record<string, Detail>>({});
  const [note, setNote] = useState("");
  const [rtype, setRtype] = useState<FupRecord["type"]>("note");
  const [rprog, setRprog] = useState<FupRecord["progress"]>("todo");
  const [rtext, setRtext] = useState("");
  const [rdue, setRdue] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [arming, setArming] = useState(false);
  const [copied, setCopied] = useState("");

  const load = useCallback(async () => {
    try {
      const [f, fr, th, open] = await Promise.all([db.fup(id), db.fronts(), db.themes(), db.openDecisions()]);
      if (!f) { setState("missing"); return; }
      setFup(f); setFronts(fr); setThemes(new Map(th.map(x => [x.id, x])));
      const by = new Map<string, Decision[]>();
      for (const d of open) by.set(d.theme_id, [...(by.get(d.theme_id) ?? []), d]);
      setOpenAtLoad(by);
      setState("ok");
    } catch { setState("failed"); }
  }, [db, id]);
  useEffect(() => { void load(); }, [load]);

  const closed = !!fup?.closed_at;
  const locked = closed || reader;
  const agenda = useMemo(() => (closed && fup?.snapshot ? fup.snapshot.agenda : fup?.agenda) ?? [], [fup, closed]);
  const log = useMemo(() => (closed && fup?.snapshot ? fup.snapshot.log : fup?.log) ?? [], [fup, closed]);
  const onAgenda = agenda.filter(a => a.on && themes.has(a.theme));
  const current = onAgenda[Math.min(cur, Math.max(0, onAgenda.length - 1))];
  const answeredRefs = new Set(log.filter(r => r.type === "decision" && r.ref).map(r => r.ref as string));
  const points = (theme: string) => openAtLoad.get(theme) ?? [];
  const answered = (theme: string) => points(theme).filter(d => answeredRefs.has(d.id)).length;

  // what the presentation shows of the current theme: its last update, attachments and decisions
  useEffect(() => {
    if (tab !== "present" || !current || details[current.theme]) return;
    const th = current.theme;
    Promise.all([db.updates(th), db.attachments(th), db.decisions(th)])
      .then(([u, a, d]) => setDetails(x => ({ ...x, [th]: { update: u[0] ?? null, attachments: a, decisions: d } })))
      .catch(() => setDetails(x => ({ ...x, [th]: { update: null, attachments: [], decisions: [] } })));
  }, [tab, current, details, db]);

  useEffect(() => {
    if (tab !== "present") return;
    const key = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest?.("input, textarea, select")) return;
      if (e.key === "ArrowRight") setCur(c => Math.min(c + 1, onAgenda.length - 1));
      if (e.key === "ArrowLeft") setCur(c => Math.max(c - 1, 0));
    };
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, [tab, onAgenda.length]);

  const by = () => {
    if (!name.trim()) { setNote(T.needName[lang]); return null; }
    return name.trim();
  };
  async function save(next: { agenda?: FupAgenda[]; log?: FupRecord[] }) {
    if (!fup) return false;
    const who = by();
    if (!who) return false;
    const before = fup;
    setFup({ ...fup, ...next });
    try { await db.saveFup(fup.id, next, who); setNote(""); return true; }
    catch (e) { setFup(before); setNote(message(e, lang)); return false; }
  }
  const setRow = (theme: string, patch: Partial<FupAgenda>) => void save({ agenda: agenda.map(a => (a.theme === theme ? { ...a, ...patch } : a)) });

  async function setStatus(theme: string, status: string) {
    const who = by();
    if (!who) return;
    try { await db.updateTheme(theme, { status }, who); setThemes(m => new Map(m).set(theme, { ...m.get(theme)!, status })); setNote(""); }
    catch (e) { setNote(message(e, lang)); }
  }

  async function record() {
    const who = by();
    const body = rtext.trim();
    if (!who || !body || !current) return;
    const th = themes.get(current.theme)!;
    const words: Tri = { [lang]: body };
    try {
      let ref: string | null = null;
      if (rtype === "decision") {
        ref = ((await db.saveDecision(th.id, null, { what: words }, who)) as { id: string }).id;
        await db.decideDecision(ref, "decided", words, who);
      } else if (rtype === "action") {
        ref = th.kind === "project"
          ? ((await db.saveItem(th.id, null, { title: body.slice(0, 200), col: rprog, due_date: rdue || null }, who)) as { id: string }).id
          : ((await db.saveDecision(th.id, null, { what: words, due_date: rdue || null }, who)) as { id: string }).id;
      }
      const rec: FupRecord = { theme: th.id, type: rtype, text: body.slice(0, 1200), progress: rprog, due: rtype === "action" && rdue ? rdue : null, ref };
      if (await save({ log: [...log, rec] })) { setRtext(""); setRdue(""); }
    } catch (e) { setNote(message(e, lang)); }
  }

  async function cycle(i: number) {
    const r = log[i];
    const next = PROGRESS[(PROGRESS.indexOf(r.progress) + 1) % 3];
    const who = by();
    if (!who) return;
    try {
      if (r.type === "action" && r.ref && themes.get(r.theme)?.kind === "project") await db.saveItem(r.theme, r.ref, { col: next }, who);
      await save({ log: log.map((x, j) => (j === i ? { ...x, progress: next } : x)) });
    } catch (e) { setNote(message(e, lang)); }
  }

  async function answer(d: Decision) {
    const who = by();
    if (!who || !fup) return;
    const typed = (answers[d.id] ?? "").trim();
    const reply: Tri = { [lang]: typed || `${T.fupAnsweredIn[lang]} ${fmtDay(fup.held_on)}` };
    try {
      await db.decideDecision(d.id, "decided", reply, who);
      const q = text(d.what, lang);
      await save({ log: [...log, { theme: d.theme_id, type: "decision", text: (typed ? `${q} — ${typed}` : q).slice(0, 1200), progress: "done", due: null, ref: d.id }] });
    } catch (e) { setNote(message(e, lang)); }
  }

  async function close() {
    if (!arming) { setArming(true); return; }
    const who = by();
    if (!who || !fup) return;
    try { await db.closeFup(fup.id, who); setArming(false); await load(); setTab("minutes"); }
    catch (e) { setNote(message(e, lang)); }
  }

  if (state === "loading") return <p className="state">{T.loading[lang]}</p>;
  if (state === "failed") return <p className="state err">{T.failed[lang]}</p>;
  if (state === "missing" || !fup) return <p className="state err">{T.fupNotFound[lang]}</p>;

  const frontName = (key: string) => text(fronts.find(f => f.key === key)?.name, lang) || key;
  const count = (k: FupKind) => onAgenda.filter(a => a.kind === k).length;
  const totalPoints = onAgenda.reduce((n, a) => n + points(a.theme).length, 0);
  const totalAnswered = onAgenda.reduce((n, a) => n + answered(a.theme), 0);
  const words = {
    title: T.fupTabMinutes[lang], status: T.fupThemeStatus[lang], decisions: T.fupMinDecisions[lang], actions: T.fupMinActions[lang], open: T.fupMinOpen[lang],
    favourites: T.fupMinFav[lang], none: T.fupMinNone[lang], nothing: T.fupMinNothing[lang], until: T.fupUntil[lang], note: T.fupType_note[lang],
    decision: T.fupType_decision[lang], action: T.fupType_action[lang],
    progress: { todo: T.fupProg_todo[lang], doing: T.fupProg_doing[lang], done: T.fupProg_done[lang] }, statusOf: (s: string) => t(`status.${s}`, lang),
  };
  const stillOpen = new Map(onAgenda.map(a => [a.theme, points(a.theme).filter(d => !answeredRefs.has(d.id)).map(d => d.what)]));
  const statuses = closed && fup.snapshot ? fup.snapshot.statuses : Object.fromEntries(onAgenda.map(a => [a.theme, themes.get(a.theme)?.status ?? ""]));
  const ata = minutes({ title: fup.title, held_on: fup.held_on, agenda, log }, themes, stillOpen, statuses, words, lang);

  return (
    <div className="fup">
      <section className="fup-band">
        <p className="fup-back"><a href="/fup/">{T.fup[lang]}</a></p>
        <h1>{fup.title} · {fup.held_on.split("-").reverse().join("/")}</h1>
        {closed ? <p>{T.fupClosedOn[lang]} {fup.closed_at!.slice(0, 10).split("-").reverse().join("/")}.</p> : <p>{T.fupLead[lang]}</p>}
        <div className="fup-tabs" role="tablist" aria-label={T.fupTabs[lang]}>
          {(["agenda", "present", "minutes"] as Tab[]).map(k => (
            <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}>{T[k === "agenda" ? "fupTabAgenda" : k === "present" ? "fupTabPresent" : "fupTabMinutes"][lang]}</button>
          ))}
        </div>
      </section>
      {note && <p className="fup-note" role="status">{note}</p>}

      {tab === "agenda" && (
        <section aria-label={T.fupTabAgenda[lang]}>
          <div className="fup-sum">
            <div><b>{onAgenda.length}</b><span>{T.fupCountOn[lang]}</span></div>
            <div><b>{count("decide")}</b><span>{T.fupCountDecide[lang]}</span></div>
            <div><b>{count("discuss")}</b><span>{T.fupCountDiscuss[lang]}</span></div>
            <div><b>{count("inform")}</b><span>{T.fupCountInform[lang]}</span></div>
            <div><b>{totalAnswered}/{totalPoints}</b><span>{T.fupCountPoints[lang]}</span></div>
            <div><b>{agenda.filter(a => a.star).length}</b><span>{T.fupCountStars[lang]}</span></div>
          </div>
          <p className="fup-legend">{KINDS.map(k => <span key={k}><span className={`fup-chip k-${k}`}>{T[`fupKind_${k}`][lang]}</span> {T[`fupKindHelp_${k}`][lang]}</span>)}<span>★ {T.fupFavourite[lang].toLowerCase()}</span></p>
          {fronts.map(f => {
            const rows = agenda.filter(a => themes.get(a.theme)?.front === f.key);
            if (!rows.length) return null;
            return (
              <div key={f.key}>
                <h2 className="fup-front">{text(f.name, lang)}</h2>
                {rows.map(a => {
                  const th = themes.get(a.theme)!;
                  const pts = points(a.theme).length;
                  return (
                    <div key={a.theme} className={`fup-row${a.on ? "" : " off"}`} data-theme={a.theme}>
                      <div>
                        <span className={`fup-chip k-${a.kind}`}>{T[`fupKind_${a.kind}`][lang]}</span> <span className="fup-meta">{th.id}</span>
                        <h3><Said value={th.title} lang={lang} /></h3>
                        {pts ? <p className="fup-meta">{T.fupPoints[lang]}: <b>{answered(a.theme)}/{pts}</b></p> : null}
                      </div>
                      <div className="fup-ctl">
                        {!locked && (
                          <select aria-label={`${T.fupKindOf[lang]} ${th.id}`} value={a.kind} onChange={e => setRow(a.theme, { kind: e.target.value as FupKind })}>
                            {KINDS.map(k => <option key={k} value={k}>{T[`fupKind_${k}`][lang]}</option>)}
                          </select>
                        )}
                        <button className="fup-tog star" aria-pressed={a.star} aria-label={`${T.fupStar[lang]} ${th.id}`} disabled={locked} onClick={() => setRow(a.theme, { star: !a.star })}>★</button>
                        <button className="fup-tog" aria-pressed={a.on} disabled={locked} onClick={() => setRow(a.theme, { on: !a.on })}>{a.on ? T.fupOnAgenda[lang] : T.fupOff[lang]}</button>
                        {a.on && <button className="fup-tog" onClick={() => { setCur(onAgenda.findIndex(x => x.theme === a.theme)); setTab("present"); }}>{T.fupOpenTheme[lang]}</button>}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </section>
      )}

      {tab === "present" && (!current ? <p className="state">{T.fupNoAgenda[lang]}</p> : (() => {
        const th = themes.get(current.theme)!;
        const d = details[th.id];
        const recs = log.map((r, i) => ({ r, i })).filter(x => x.r.theme === th.id);
        const pts = d ? d.decisions.filter(x => points(th.id).some(p => p.id === x.id)) : points(th.id);
        return (
          <section aria-label={T.fupTabPresent[lang]}>
            <div className="fup-nav">
              <button className="fup-btn ghost" onClick={() => setCur(c => Math.max(c - 1, 0))} disabled={cur === 0}>{T.fupPrev[lang]}</button>
              <span className="fup-pos">{Math.min(cur, onAgenda.length - 1) + 1} {T.fupOf[lang]} {onAgenda.length}</span>
              <button className="fup-btn" onClick={() => setCur(c => Math.min(c + 1, onAgenda.length - 1))} disabled={cur >= onAgenda.length - 1}>{T.fupNext[lang]}</button>
            </div>
            <div className="fup-pres">
              <article className="fup-card">
                <p className="fup-meta"><span className={`fup-chip k-${current.kind}`}>{T[`fupKind_${current.kind}`][lang]}</span> {frontName(th.front)} · {th.id} <StatusBadge status={th.status} lang={lang} />{current.star ? <span> ★ {T.fupFavourite[lang]}</span> : null}</p>
                <h2><a href={`/themes/${th.id}/`}><Said value={th.title} lang={lang} /></a></h2>
                {text(th.what_it_is, lang) && <p className="fup-lead"><Said value={th.what_it_is} lang={lang} /></p>}
                {d?.update && (
                  <div className="fup-upd">
                    <b>{T.fupLastUpdate[lang]} ({d.update.week})</b>
                    <p><Said value={d.update.progress} lang={lang} /></p>
                    {text(d.update.advanced, lang) && <p><span className="fup-meta">{T.fupAdvanced[lang]}:</span> <Said value={d.update.advanced} lang={lang} /></p>}
                    {text(d.update.next_step, lang) && <p><span className="fup-meta">{T.fupNextStep[lang]}:</span> <Said value={d.update.next_step} lang={lang} /></p>}
                  </div>
                )}
                {pts.length > 0 && (
                  <div className="fup-points">
                    <b>{T.fupPoints[lang]}</b>
                    <ul>
                      {pts.map(p => {
                        const done = answeredRefs.has(p.id) || p.state !== "open";
                        return (
                          <li key={p.id} data-done={done ? "1" : undefined}>
                            <span className="bx" aria-hidden="true" /> <span className="q"><Said value={p.what} lang={lang} /></span>
                            {!done && !locked && (
                              <span className="fup-answer">
                                <input aria-label={`${T.fupAnswer[lang]}: ${text(p.what, lang)}`} placeholder={T.fupAnswer[lang]} maxLength={1100} value={answers[p.id] ?? ""} onChange={e => setAnswers(x => ({ ...x, [p.id]: e.target.value }))} />
                                <button className="fup-tog" onClick={() => void answer(p)}>{T.fupMarkAnswered[lang]}</button>
                              </span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}
                {d && d.attachments.length > 0 && (
                  <div className="fup-links">
                    <b>{T.fupMaterials[lang]}</b>
                    <div>{d.attachments.map(a => a.kind === "link" && a.url
                      ? <a key={a.id} href={a.url} target="_blank" rel="noreferrer">{a.name} ↗</a>
                      : <a key={a.id} href={`/themes/${th.id}/#sec-attachments`}>{a.name}</a>)}</div>
                  </div>
                )}
              </article>
              <aside className="fup-card fup-cap" aria-label={T.fupRecordNow[lang]}>
                {!locked && (
                  <>
                    <h3>{T.fupRecordNow[lang]}</h3>
                    <span className="lbl">{T.fupThemeStatus[lang]}</span>
                    <div className="fup-seg" role="group" aria-label={T.fupThemeStatus[lang]}>
                      {HEALTH.map(s => <button key={s} aria-pressed={th.status === s} onClick={() => void setStatus(th.id, s)}>{t(`status.${s}`, lang)}</button>)}
                    </div>
                    <span className="lbl">{T.fupRecordType[lang]}</span>
                    <div className="fup-seg" role="group" aria-label={T.fupRecordType[lang]}>
                      {TYPES.map(k => <button key={k} aria-pressed={rtype === k} onClick={() => setRtype(k)}>{T[`fupType_${k}`][lang]}</button>)}
                    </div>
                    <span className="lbl">{T.fupProgress[lang]}</span>
                    <div className="fup-seg" role="group" aria-label={T.fupProgress[lang]}>
                      {PROGRESS.map(k => <button key={k} aria-pressed={rprog === k} onClick={() => setRprog(k)}>{T[`fupProg_${k}`][lang]}</button>)}
                    </div>
                    <label className="lbl" htmlFor="fup-text">{T.fupText[lang]}</label>
                    <textarea id="fup-text" placeholder={T.fupTextHint[lang]} maxLength={1200} value={rtext} onChange={e => setRtext(e.target.value)} />
                    {rtype === "action" && (<><label className="lbl" htmlFor="fup-due">{T.fupDue[lang]}</label><input id="fup-due" type="date" value={rdue} onChange={e => setRdue(e.target.value)} /></>)}
                    <button className="fup-btn wide" onClick={() => void record()}>{T.fupRecord[lang]}</button>
                  </>
                )}
                <h3 className="fup-sub">{T.fupRecords[lang]}</h3>
                <ul className="fup-log">
                  {recs.map(({ r, i }) => (
                    <li key={i}>
                      <span>
                        <button className={`fup-prog p-${r.progress}`} title={T.fupCycle[lang]} disabled={locked} onClick={() => void cycle(i)}>{T[`fupProg_${r.progress}`][lang]}</button>{" "}
                        <em>{T[`fupType_${r.type}`][lang]}</em> {r.text}{r.due ? ` · ${T.fupUntil[lang]} ${fmtDay(r.due)}` : ""}
                      </span>
                      {!locked && r.type === "note" && <button className="fup-x" aria-label={T.fupDelete[lang]} onClick={() => void save({ log: log.filter((_, j) => j !== i) })}>×</button>}
                    </li>
                  ))}
                </ul>
              </aside>
            </div>
          </section>
        );
      })())}

      {tab === "minutes" && (
        <section aria-label={T.fupTabMinutes[lang]}>
          <div className="fup-nav">
            <h2>{T.fupTabMinutes[lang]}</h2>
            <button className="fup-btn" onClick={async () => { try { await navigator.clipboard.writeText(ata); setCopied(T.fupCopied[lang]); } catch { setCopied(T.fupCopyFail[lang]); } }}>{T.fupCopy[lang]}</button>
          </div>
          <pre className="fup-ata" data-testid="fup-minutes">{ata}</pre>
          {copied && <p className="fup-meta" role="status">{copied}</p>}
          {!locked && (
            <div className="fup-close">
              <button className="fup-btn danger" onClick={() => void close()}>{T.fupClose[lang]}</button>
              {arming && <p className="fup-note">{T.fupCloseConfirm[lang]}</p>}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

