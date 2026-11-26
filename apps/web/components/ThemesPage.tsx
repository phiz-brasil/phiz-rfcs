"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { COLS, STATUSES, T, t, text, type Lang } from "../lib/i18n";
import type { Front, I18n, Theme } from "../lib/db";
import { useApp } from "./Shell";
import { Field, Said, StatusBadge, dateText, message } from "./ui";

export function ThemesPage() {
  const { lang, db, reader } = useApp();
  const [fronts, setFronts] = useState<Front[] | null>(null);
  const [themes, setThemes] = useState<Theme[]>([]);
  const [failed, setFailed] = useState(false);
  const [kind, setKind] = useState("all");
  const [status, setStatus] = useState("all");
  const [editing, setEditing] = useState(false);
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    try {
      const [f, th] = await Promise.all([db.fronts(), db.themes()]);
      setFronts(f);
      setThemes(th);
      setFailed(false);
    } catch { setFailed(true); }
  }, [db]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => { if (new URLSearchParams(location.search).get("new") === "1") setCreating(true); }, []);       // "New theme" on the Painel

  const shown = useMemo(() => themes.filter(x => (kind === "all" || x.kind === kind) && (status === "all" || x.status === status)), [themes, kind, status]);

  return (
    <>
      <p className="eyebrow">{T.eyebrowPortfolio[lang]}</p>
      <h1>{T.themes[lang]}</h1>
      <p className="lead">{T.lead[lang]}</p>
      <div className="bar">
        <div className="filters" role="group" aria-label={T.kind[lang]}>
          {["all", "project", "task"].map(k => (
            <button key={k} type="button" aria-pressed={kind === k} onClick={() => setKind(k)}>{k === "all" ? T.all[lang] : t(k, lang)}</button>
          ))}
        </div>
        <div className="filters" role="group" aria-label={T.status[lang]}>
          {["all", ...STATUSES].map(s => (
            <button key={s} type="button" aria-pressed={status === s} onClick={() => setStatus(s)}>{s === "all" ? T.all[lang] : t(`status.${s}`, lang)}</button>
          ))}
        </div>
        {!reader ? (
          <div className="actions">
            <button type="button" className="btn primary" onClick={() => setCreating(true)}>＋ {T.newTheme[lang]}</button>
            <button type="button" className="btn" onClick={() => setEditing(e => !e)}>{editing ? T.doneEditing[lang] : T.editFronts[lang]}</button>
          </div>
        ) : null}
      </div>
      {failed ? <p className="state err">{T.failed[lang]}</p> : fronts === null ? <p className="state">{T.loading[lang]}</p> : null}
      {creating && fronts && !reader ? <NewTheme fronts={fronts} onClose={() => setCreating(false)} onCreated={id => { window.location.href = `/themes/${id}/`; }} /> : null}
      {fronts?.map(f => (
        <section className="front" key={f.key} id={`front-${f.key}`}>
          {editing && !reader ? <EditFront front={f} onSaved={load} /> : (
            <>
              <h2>{text(f.name, lang)}</h2>
              <p className="scope">{text(f.scope, lang)}</p>
            </>
          )}
          {shown.some(x => x.front === f.key) ? (
            <div className="tablewrap">
              <table className="stats themes-table compact">
                <thead><tr><th>{T.colTheme[lang]}</th><th>{T.colKind[lang]}</th><th>{T.status[lang]}</th><th>{T.stage[lang]}</th><th>{T.owner[lang]}</th><th>{T.due[lang]}</th><th>{T.colTags[lang]}</th></tr></thead>
                <tbody>{shown.filter(x => x.front === f.key).map(x => <ThemeRow key={x.id} theme={x} lang={lang} />)}</tbody>
              </table>
            </div>
          ) : <p className="empty">{T.noThemes[lang]}</p>}
        </section>
      ))}
    </>
  );
}

function ThemeRow({ theme, lang }: { theme: Theme; lang: Lang }) {
  return (
    <tr className="theme-row" data-theme={theme.id} onClick={e => { if (!(e.target as Element).closest("a")) location.href = `/themes/${theme.id}/`; }}>
      <th><a href={`/themes/${theme.id}/`}><span className="id">{theme.id}</span> <Said value={theme.title} lang={lang} machine={theme.text_meta?.title} /></a>
        {text(theme.progress, lang) ? <div className="note"><Said value={theme.progress} lang={lang} machine={theme.text_meta?.progress} /></div> : null}</th>
      <td>{t(theme.kind, lang)}</td>
      <td><StatusBadge status={theme.status} lang={lang} /></td>
      <td className="stage">{theme.stage ? t(`stage.${theme.stage}`, lang) : "—"}</td>
      <td>{theme.owner ?? "—"}</td>
      <td className="date">{dateText(theme.due_date)}</td>
      <td>{theme.tags.map(tag => <span className="tag" key={tag}>#{tag} </span>)}</td>
    </tr>
  );
}

function NewTheme({ fronts, onClose, onCreated }: { fronts: Front[]; onClose: () => void; onCreated: (id: string) => void }) {
  const { lang, db, name } = useApp();
  const [kind, setKind] = useState("project");
  const [front, setFront] = useState(fronts[0]?.key ?? "");
  const [title, setTitle] = useState("");
  const [owner, setOwner] = useState("");
  const [note, setNote] = useState("");
  const submit = async () => {
    if (!name.trim()) return setNote(T.needName[lang]);
    if (!title.trim()) return setNote(T.error[lang]);
    setNote(T.saving[lang]);
    try {
      const r = await db.createTheme({ kind, front, title: { [lang]: title.trim() } satisfies I18n, owner: owner.trim() }, name.trim());
      onCreated(r.id);
    } catch (e) { setNote(message(e, lang)); }
  };
  return (
    <form className="panel" onSubmit={e => { e.preventDefault(); void submit(); }} aria-label={T.newTheme[lang]}>
      <h2>{T.newTheme[lang]}</h2>
      <div className="fields">
        <Field label={T.kind[lang]}>
          <select value={kind} onChange={e => setKind(e.target.value)}>{["project", "task"].map(k => <option key={k} value={k}>{t(k, lang)}</option>)}</select>
        </Field>
        <Field label={T.front[lang]}>
          <select value={front} onChange={e => setFront(e.target.value)}>{fronts.map(f => <option key={f.key} value={f.key}>{text(f.name, lang)}</option>)}</select>
        </Field>
        <Field label={`${T.title[lang]} (${T.writtenIn[lang]} ${lang.toUpperCase()})`}><input value={title} maxLength={200} onChange={e => setTitle(e.target.value)} /></Field>
        <Field label={T.owner[lang]}><input value={owner} maxLength={80} onChange={e => setOwner(e.target.value)} /></Field>
      </div>
      <p><button type="submit" className="btn primary">{T.create[lang]}</button> <button type="button" className="btn" onClick={onClose}>{T.cancel[lang]}</button> <span className="note" role="status">{note}</span></p>
    </form>
  );
}

function EditFront({ front, onSaved }: { front: Front; onSaved: () => void }) {
  const { lang, db, name } = useApp();
  const [nm, setNm] = useState<I18n>(front.name);
  const [scope, setScope] = useState<I18n>(front.scope);
  const [ord, setOrd] = useState(String(front.ord));
  const [note, setNote] = useState("");
  const save = async () => {
    if (!name.trim()) return setNote(T.needName[lang]);
    setNote(T.saving[lang]);
    try {
      const p: Record<string, unknown> = { name: nm, scope };
      if (!front.is_other) p.ord = Number(ord);
      await db.updateFront(front.key, p, name.trim());
      setNote(T.saved[lang]);
      onSaved();
    } catch (e) { setNote(message(e, lang)); }
  };
  return (
    <form className="panel" onSubmit={e => { e.preventDefault(); void save(); }} aria-label={`${T.editFronts[lang]}: ${front.key}`}>
      <div className="fields">
        {(["pt", "en", "zh"] as const).map(l => (
          <Field key={l} label={`${T.frontName[lang]} (${l.toUpperCase()})`}><input value={nm[l] ?? ""} maxLength={60} onChange={e => setNm({ ...nm, [l]: e.target.value })} /></Field>
        ))}
        {!front.is_other ? <Field label={T.frontOrder[lang]}><input type="number" min={1} max={50} value={ord} onChange={e => setOrd(e.target.value)} /></Field> : null}
      </div>
      <Field label={`${T.frontScope[lang]} (${lang.toUpperCase()})`}>
        <textarea rows={3} value={scope[lang] ?? ""} maxLength={1200} onChange={e => setScope({ ...scope, [lang]: e.target.value })} />
      </Field>
      <p><button type="submit" className="btn primary">{T.save[lang]}</button> <span className="note" role="status">{note}</span></p>
    </form>
  );
}
