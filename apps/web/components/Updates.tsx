"use client";
/* The weekly update of a theme, its history, and its blockers and decisions. Texts are written in the reader's language and kept per
   language (translations are filled in by the webhook). With reader mode on, only the records are shown, with no forms or buttons. */
import { useState } from "react";
import { STATUSES, T, t, text, type Lang } from "../lib/i18n";
import type { Blocker, Decision, I18n, Item, Theme, Update, Urgency } from "../lib/db";
import { useApp } from "./Shell";
import { Field, Said, StatusBadge, dateText, message } from "./ui";

const only = (lang: Lang, value: string): I18n => ({ [lang]: value.trim() });
const URGENCIES: Urgency[] = ["urgent", "important", "info"];

function useRun(onChanged: () => void) {
  const { lang, name } = useApp();
  const [note, setNote] = useState("");
  const run = async (fn: (by: string) => Promise<unknown>, done?: () => void) => {
    if (!name.trim()) { setNote(T.needName[lang]); return false; }
    setNote(T.saving[lang]);
    try { await fn(name.trim()); setNote(""); done?.(); onChanged(); return true; } catch (e) { setNote(message(e, lang)); return false; }
  };
  return { note, setNote, run };
}

export function WeeklyUpdate({ theme, updates, onChanged }: { theme: Theme; updates: Update[]; onChanged: () => void }) {
  const { lang, db, reader } = useApp();
  const { note, setNote, run } = useRun(onChanged);
  const [f, setF] = useState({ progress: "", advanced: "", next: "", status: theme.status, due: theme.due_date ?? "", reason: "" });
  const dueChanged = f.due !== (theme.due_date ?? "");
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const post = async () => {
    if (!f.progress.trim()) return setNote(T.needProgress[lang]);
    const p: Record<string, unknown> = { progress: only(lang, f.progress), status: f.status };
    if (f.advanced.trim()) p.advanced = only(lang, f.advanced);
    if (f.next.trim()) p.next_step = only(lang, f.next);
    if (dueChanged) { p.due_date = f.due || null; if (f.reason.trim()) p.due_reason = f.reason.trim(); }
    await run(by => db.postUpdate(theme.id, p, by), () => setF({ progress: "", advanced: "", next: "", status: f.status, due: f.due, reason: "" }));
  };
  return (
    <section className="panel" aria-label={T.weekly[lang]}>
      <h2>{T.weekly[lang]}</h2>
      {!reader ? (
        <form onSubmit={e => { e.preventDefault(); void post(); }}>
          <p className="note">{T.weeklyLead[lang]} {T.writtenIn[lang]} {lang.toUpperCase()}.</p>
          <Field label={T.progress[lang]}><input value={f.progress} maxLength={1200} onChange={set("progress")} /></Field>
          <Field label={T.advanced[lang]}><textarea rows={2} maxLength={2000} value={f.advanced} onChange={set("advanced")} /></Field>
          <Field label={T.nextStep[lang]}><textarea rows={2} maxLength={2000} value={f.next} onChange={set("next")} /></Field>
          <div className="fields">
            <Field label={T.status[lang]}><select value={f.status} onChange={set("status")}>{STATUSES.map(s => <option key={s} value={s}>{t(`status.${s}`, lang)}</option>)}</select></Field>
            <Field label={T.due[lang]}><input type="date" value={f.due} onChange={set("due")} /></Field>
            {dueChanged ? <Field label={T.dueReason[lang]}><input value={f.reason} maxLength={300} onChange={set("reason")} /></Field> : null}
          </div>
          <p><button type="submit" className="btn primary">{T.postUpdate[lang]}</button> <span className="note" role="status">{note}</span></p>
        </form>
      ) : null}
      <h3>{T.updatesHistory[lang]}</h3>
      {updates.length ? updates.map(u => (
        <article className="row" key={u.id}>
          <div className="meta"><span>{u.week}</span><time>{dateText(u.created_at)}</time><span>{T.by[lang]} {u.edited_by}</span>
            {u.status_to ? <span>{T.statusChanged[lang]}: {t(`status.${u.status_from}`, lang)} → {t(`status.${u.status_to}`, lang)}</span> : null}
            {u.due_to !== null || u.due_from !== null ? <span>{T.dueChanged[lang]}: {dateText(u.due_from)} → {dateText(u.due_to)}{u.due_reason ? ` (${u.due_reason})` : ""}</span> : null}</div>
          <div className="what"><Said value={u.progress} lang={lang} machine={u.text_meta?.progress} /></div>
          {text(u.advanced, lang) ? <dl className="pairs"><dt>{T.advanced[lang]}</dt><dd><Said value={u.advanced} lang={lang} machine={u.text_meta?.advanced} /></dd></dl> : null}
          {text(u.next_step, lang) ? <dl className="pairs"><dt>{T.nextStep[lang]}</dt><dd><Said value={u.next_step} lang={lang} machine={u.text_meta?.next_step} /></dd></dl> : null}
        </article>
      )) : <p className="empty">{T.none[lang]}</p>}
    </section>
  );
}

type Kind = "blocker" | "decision";

export function Records({ kind, theme, rows, items, onChanged }: { kind: Kind; theme: Theme; rows: (Blocker | Decision)[]; items: Item[]; onChanged: () => void }) {
  const { lang, db, reader } = useApp();
  const { note, run } = useRun(onChanged);
  const [what, setWhat] = useState("");
  const [who, setWho] = useState("");
  const [due, setDue] = useState("");
  const [lead, setLead] = useState(false);
  const [urgency, setUrgency] = useState<Urgency>("info");
  const [item, setItem] = useState("");
  const [closing, setClosing] = useState<string | null>(null);
  const [closingText, setClosingText] = useState("");
  const title = kind === "blocker" ? T.blockers[lang] : T.decisions[lang];
  const open = rows.filter(r => r.state === "open");
  const closed = rows.filter(r => r.state !== "open");
  const owner = (r: Blocker | Decision) => ("owner" in r ? r.owner : r.decider);
  const add = () => {
    if (!what.trim()) return;
    const p: Record<string, unknown> = { what: only(lang, what), needs_leadership: lead, urgency, item_id: item || null, due_date: due || null };
    p[kind === "blocker" ? "owner" : "decider"] = who.trim();
    void run(by => (kind === "blocker" ? db.saveBlocker(theme.id, null, p, by) : db.saveDecision(theme.id, null, p, by)),
      () => { setWhat(""); setWho(""); setDue(""); setLead(false); setUrgency("info"); setItem(""); });
  };
  const close = (r: Blocker | Decision, state: "resolved" | "decided" | "dropped") => {
    const body = closingText.trim() ? only(lang, closingText) : {};
    void run(by => (kind === "blocker" ? db.resolveBlocker(r.id, body, by) : db.decideDecision(r.id, state === "dropped" ? "dropped" : "decided", body, by)),
      () => { setClosing(null); setClosingText(""); });
  };
  return (
    <section className="panel" aria-label={title}>
      <h2>{title}</h2>
      {open.length ? open.map(r => (
        <article className="row" key={r.id} data-state="open">
          <div className="what"><Said value={r.what} lang={lang} machine={r.text_meta?.what} />{r.needs_leadership ? <span className="flag lead"> {T.needsLeadership[lang]}</span> : null}
            {reader ? <span className="urg" data-u={r.urgency ?? "info"}>{t(`urg.${r.urgency ?? "info"}`, lang)}</span>
              : <select className="urg" data-u={r.urgency ?? "info"} aria-label={`${T.urgency[lang]}: ${text(r.what, lang)}`} value={r.urgency ?? "info"}
                  onChange={e => void run(by => (kind === "blocker" ? db.saveBlocker(theme.id, r.id, { urgency: e.target.value }, by) : db.saveDecision(theme.id, r.id, { urgency: e.target.value }, by)))}>
                  {URGENCIES.map(u => <option key={u} value={u}>{t(`urg.${u}`, lang)}</option>)}
                </select>}</div>
          <div className="meta">{owner(r) ? <span>{owner(r)}</span> : null}{r.due_date ? <span>{T.byWhen[lang]}: {dateText(r.due_date)}</span> : null}
            {r.item_id ? <span>↳ {items.find(i => i.id === r.item_id)?.title}</span> : null}</div>
          {!reader ? (closing === r.id ? (
            <div className="inline">
              <input aria-label={kind === "blocker" ? T.howResolved[lang] : T.decisionText[lang]} placeholder={kind === "blocker" ? T.howResolved[lang] : T.decisionText[lang]} value={closingText} maxLength={1200} onChange={e => setClosingText(e.target.value)} />
              <button type="button" className="btn primary" onClick={() => close(r, kind === "blocker" ? "resolved" : "decided")}>{kind === "blocker" ? T.resolve[lang] : T.decide[lang]}</button>
              {kind === "decision" ? <button type="button" className="btn" onClick={() => close(r, "dropped")}>{T.dropDecision[lang]}</button> : null}
              <button type="button" className="btn" onClick={() => setClosing(null)}>{T.cancel[lang]}</button>
            </div>
          ) : <p><button type="button" className="mini" onClick={() => { setClosing(r.id); setClosingText(""); }}>{kind === "blocker" ? T.resolve[lang] : T.decide[lang]}</button></p>) : null}
        </article>
      )) : <p className="empty">{T.none[lang]}</p>}
      {closed.length ? (
        <details><summary>{kind === "blocker" ? T.resolved[lang] : T.decided[lang]} ({closed.length})</summary>
          {closed.map(r => (
            <article className="row" key={r.id} data-state="closed">
              <div className="what"><Said value={r.what} lang={lang} machine={r.text_meta?.what} />{"state" in r && r.state === "dropped" ? <span className="flag"> {T.dropped[lang]}</span> : null}</div>
              <div className="meta"><span>→ <Said value={"how_resolved" in r ? r.how_resolved : r.decision} lang={lang} /></span></div>
            </article>
          ))}
        </details>
      ) : null}
      {!reader ? (
        <form className="inline add" onSubmit={e => { e.preventDefault(); add(); }}>
          <input aria-label={kind === "blocker" ? T.blockerWhat[lang] : T.decisionWhat[lang]} placeholder={kind === "blocker" ? T.blockerWhat[lang] : T.decisionWhat[lang]} value={what} maxLength={1200} onChange={e => setWhat(e.target.value)} />
          <input aria-label={kind === "blocker" ? T.unblockOwner[lang] : T.decider[lang]} placeholder={kind === "blocker" ? T.unblockOwner[lang] : T.decider[lang]} value={who} maxLength={80} onChange={e => setWho(e.target.value)} />
          <input type="date" aria-label={T.byWhen[lang]} value={due} onChange={e => setDue(e.target.value)} />
          {items.length ? (
            <select aria-label={T.relatedItem[lang]} value={item} onChange={e => setItem(e.target.value)}>
              <option value="">{T.relatedItem[lang]}</option>{items.map(i => <option key={i.id} value={i.id}>{i.title}</option>)}
            </select>
          ) : null}
          <label className="checks"><input type="checkbox" checked={lead} onChange={e => { setLead(e.target.checked); if (e.target.checked && urgency === "info") setUrgency("important"); }} /> {T.needsLeadership[lang]}</label>
          <select aria-label={T.urgency[lang]} value={urgency} onChange={e => setUrgency(e.target.value as Urgency)}>
            {URGENCIES.map(u => <option key={u} value={u}>{t(`urg.${u}`, lang)}</option>)}
          </select>
          <button type="submit" className="btn">{T.add[lang]}</button> <span className="note" role="status">{note}</span>
        </form>
      ) : null}
    </section>
  );
}
