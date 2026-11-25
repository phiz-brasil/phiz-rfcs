"use client";
/* /fup/: the FUPs (newest first) and a form to start one with the suggested agenda (docs/spec/v2/fup.md). */
import { useEffect, useState } from "react";
import { T } from "../lib/i18n";
import type { Fup } from "../lib/db";
import { suggestAgenda } from "../lib/fup";
import { useApp } from "./Shell";
import { message } from "./ui";

export function FupList() {
  const { lang, db, name, reader } = useApp();
  const today = new Date().toISOString().slice(0, 10);
  const [fups, setFups] = useState<Fup[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [title, setTitle] = useState(`FUP ${today.slice(8, 10)}/${today.slice(5, 7)}`);
  const [day, setDay] = useState(today);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { db.fups().then(setFups, () => setFailed(true)); }, [db]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setNote(T.needName[lang]); return; }
    setBusy(true);
    try {
      const [fronts, themes, open] = await Promise.all([db.fronts(), db.themes(), db.openDecisions()]);
      const r = await db.saveFup(null, { title: title.trim(), held_on: day, agenda: suggestAgenda(fronts, themes, open) }, name.trim());
      location.href = `/fup/${r.id}/`;
    } catch (err) { setNote(message(err, lang)); setBusy(false); }
  }

  return (
    <div className="fup">
      <section className="fup-band">
        <h1>{T.fup[lang]}</h1>
        <p>{T.fupLead[lang]}</p>
      </section>
      {!reader && (
        <form className="fup-card fup-new" onSubmit={create} aria-label={T.fupNew[lang]}>
          <h2>{T.fupNew[lang]}</h2>
          <div className="fup-row2">
            <label><span>{T.fupTitle[lang]}</span><input value={title} maxLength={120} onChange={e => setTitle(e.target.value)} required /></label>
            <label><span>{T.fupDate[lang]}</span><input type="date" value={day} onChange={e => setDay(e.target.value)} required /></label>
          </div>
          <button className="fup-btn" disabled={busy}>{T.fupCreate[lang]}</button>
          {note && <p className="fup-note" role="status">{note}</p>}
        </form>
      )}
      {failed ? <p className="state err">{T.failed[lang]}</p> : !fups ? <p className="state">{T.loading[lang]}</p> : !fups.length ? <p className="state">{T.fupNone[lang]}</p> : (
        <ul className="fup-list">
          {fups.map(f => (
            <li key={f.id}>
              <a href={`/fup/${f.id}/`}>{f.title}</a>
              <span>{f.held_on.split("-").reverse().join("/")}</span>
              <span className={`fup-chip ${f.closed_at ? "k-inform" : "k-decide"}`}>{f.closed_at ? T.fupClosed[lang] : T.fupOpen[lang]}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
