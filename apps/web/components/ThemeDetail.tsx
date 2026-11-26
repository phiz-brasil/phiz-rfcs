"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { COLS, STAGES, STATUSES, T, t, text, type Lang } from "../lib/i18n";
import type { Blocker, Decision, EventRow, Front, I18n, Item, Jira, Link, Theme, Update } from "../lib/db";
import { useApp } from "./Shell";
import { Field, Said, StatusBadge, dateText, message } from "./ui";
import { Records, WeeklyUpdate } from "./Updates";
import { Gates } from "./Gates";
import { Attachments } from "./Attachments";
import { Summary } from "./Summary";
import { PhaseIcon } from "./OverviewPage";
import { phaseOf } from "../lib/painel";

type Data = { theme: Theme; fronts: Front[]; items: Item[]; links: Link[]; linksTo: Link[]; jira: Jira[]; events: EventRow[]; rfc: { rfc_id: string; version: string } | null;
  updates: Update[]; blockers: Blocker[]; decisions: Decision[] };

export function ThemeDetail({ id }: { id: string }) {
  const { lang, db, reader, name } = useApp();
  const [data, setData] = useState<Data | null>(null);
  const [state, setState] = useState<"loading" | "missing" | "failed" | "ok">("loading");
  const [saved, setSaved] = useState(false);           // the form is redrawn from the saved data, so the "Saved." note lives here
  const [editing, setEditing] = useState(false);       // the theme's own data is shown read-only until someone presses "Edit"
  const load = useCallback(async () => {
    try {
      const theme = await db.theme(id);
      if (!theme) return setState("missing");
      const [fronts, items, links, linksTo, jira, events, rfc, updates, blockers, decisions] =
        await Promise.all([db.fronts(), db.items(id), db.links(id), db.linksTo(id), db.jira(id), db.events(id), db.rfc(id), db.updates(id), db.blockers(id), db.decisions(id)]);
      setData({ theme, fronts, items, links, linksTo, jira, events, rfc, updates, blockers, decisions });
      setState("ok");
    } catch { setState("failed"); }
  }, [db, id]);
  useEffect(() => { void load(); }, [load]);

  const [inlineNote, setInlineNote] = useState("");
  const saveTheme = async (p: Record<string, unknown>): Promise<boolean> => {
    if (!data) return false;
    if (!name.trim()) { setInlineNote(T.needName[lang]); return false; }
    try { await db.updateTheme(data.theme.id, p, name.trim()); setInlineNote(""); await load(); return true; }
    catch (e) { setInlineNote(message(e, lang)); await load(); return false; }
  };

  if (state === "loading") return <p className="state">{T.loading[lang]}</p>;
  if (state === "missing") return <><p><a href="/themes/">{T.back[lang]}</a></p><p className="state">{T.notFound[lang]}</p></>;
  if (state === "failed" || !data) return <p className="state err">{T.failed[lang]}</p>;
  const { theme } = data;
  const front = text(data.fronts.find(f => f.key === theme.front)?.name, lang);
  const today = new Date().toISOString().slice(0, 10);
  const overdue = !!theme.due_date && theme.due_date.slice(0, 10) < today && theme.status !== "done" && theme.status !== "cancelled";
  const sections: [string, string][] = [
    ["sec-summary", T.secSummary[lang]], ["sec-updates", T.weekly[lang]], ["sec-records", T.secRecords[lang]],
    ...(theme.kind === "project" ? [["sec-execution", T.secExecution[lang]] as [string, string]] : []),
    ["sec-attachments", T.attachments[lang]], ["sec-links", T.secLinks[lang]], ["sec-history", T.history[lang]],
  ];
  return (
    <>
      <p className="back"><a href="/themes/">{T.back[lang]}</a></p>
      <header className="theme-hero">
        <p className="eyebrow"><span className="id">{theme.id}</span> · {t(theme.kind, lang)} · {front}</p>
        <div className="theme-titleline">
          <PhaseIcon theme={theme} lang={lang} />
          {reader ? <h1><Said value={theme.title} lang={lang} machine={theme.text_meta?.title} /></h1>
            : <InlineText key={`t${theme.updated_at}${lang}`} tag="h1" field="title" value={text(theme.title, lang)} required onSave={v => saveTheme({ title: merge(theme.title, lang, v) })} />}
        </div>
        {reader ? (text(theme.what_it_is, lang) ? <p className="theme-what"><Said value={theme.what_it_is} lang={lang} machine={theme.text_meta?.what_it_is} /></p> : null)
          : <InlineText key={`w${theme.updated_at}${lang}`} tag="p" field="what_it_is" className="theme-what" value={text(theme.what_it_is, lang)} placeholder={T.addWhatItIs[lang]} onSave={v => saveTheme({ what_it_is: merge(theme.what_it_is, lang, v) })} />}
        {inlineNote ? <p className="state err" role="alert" data-note="inline">{inlineNote}</p> : null}
        <div className="facts" data-block="facts">
          <div><span className="kpi-label">{T.status[lang]}</span><StatusBadge status={theme.status} lang={lang} /></div>
          {theme.kind === "project" ? <div><span className="kpi-label">{T.stage[lang]}</span><strong>{theme.stage ? t(`stage.${theme.stage}`, lang) : "—"}</strong></div> : null}
          <div><span className="kpi-label">{T.owner[lang]}</span><strong>{theme.owner ?? "—"}</strong></div>
          <div><span className="kpi-label">{T.due[lang]}</span><strong className={overdue ? "overdue" : undefined}>{dateText(theme.due_date)}</strong></div>
          <div className="wide"><span className="kpi-label">{T.progress[lang].replace(/ \(.*\)$/, "")}</span><span>{text(theme.progress, lang) ? <Said value={theme.progress} lang={lang} machine={theme.text_meta?.progress} /> : "—"}</span></div>
        </div>
        <div className="actions">
          {data.rfc ? <a className="btn" href={`/rfc/?id=${theme.id}`}>{T.openRfc[lang]} (v{data.rfc.version})</a> : <span className="note">{T.noRfc[lang]}</span>}
          <a className="btn" href={`/slides/?theme=${theme.id}`}>{T.exportPptx[lang]}</a>
          {!reader ? <button type="button" className={editing ? "btn" : "btn primary"} aria-expanded={editing} onClick={() => { setEditing(e => !e); setSaved(false); }}>{editing ? T.doneEditing[lang] : T.editTheme[lang]}</button> : null}
        </div>
      </header>
      <nav className="secnav" aria-label={T.sections[lang]}>{sections.map(([id, label]) => <a key={id} href={`#${id}`}>{label}</a>)}</nav>

      <div className="theme-layout">
      <div className="theme-main">
      <div className="group" id="sec-summary">
        <h2 className="group-title" id="h-summary">{T.secSummary[lang]}</h2>
        {!reader && editing
          ? <ThemeForm key={theme.updated_at + lang} data={data} saved={saved} onSaved={() => { setSaved(true); void load(); }} onEdit={() => setSaved(false)} />
          : <ThemeReadOnly data={data} />}
        <Summary key={`s${theme.updated_at}${lang}`} theme={theme} onChanged={load} />
      </div>
      <div className="group" id="sec-updates">
        <h2 className="group-title" id="h-updates">{T.weekly[lang]}</h2>
        <WeeklyUpdate key={`u${data.updates.length}${lang}`} theme={theme} updates={data.updates} onChanged={load} />
      </div>
      <div className="group" id="sec-records">
        <h2 className="group-title" id="h-records">{T.secRecords[lang]}</h2>
        <div className="two">
          <Records kind="blocker" theme={theme} rows={data.blockers} items={data.items} onChanged={load} />
          <Records kind="decision" theme={theme} rows={data.decisions} items={data.items} onChanged={load} />
        </div>
      </div>
      {theme.kind === "project" ? (
        <div className="group" id="sec-execution">
          <h2 className="group-title" id="h-execution">{T.secExecution[lang]}</h2>
          <Items data={data} onChanged={load} />
          <Gates key={`g${theme.stage}${theme.route}${lang}`} theme={theme} />
        </div>
      ) : null}
      <div className="group" id="sec-history">
        <h2 className="group-title" id="h-history">{T.history[lang]}</h2>
        <History events={data.events} lang={lang} />
      </div>
      </div>
      <aside className="theme-side">
        <Properties key={`p${theme.updated_at}${lang}`} data={data} save={saveTheme} />
        <div className="group" id="sec-links">
          <h2 className="group-title" id="h-links">{T.secLinks[lang]}</h2>
          <div className="stack">
            <JiraLinks data={data} onChanged={load} />
            <Dependencies data={data} onChanged={load} />
          </div>
        </div>
        <div className="group" id="sec-attachments">
          <h2 className="group-title" id="h-attachments">{T.attachments[lang]}</h2>
          <Attachments theme={theme} items={data.items} />
        </div>
      </aside>
      </div>
    </>
  );
}

function ThemeReadOnly({ data }: { data: Data }) {
  const { lang } = useApp();
  const { theme, fronts } = data;
  const said = (k: "what_it_is" | "problem" | "solution" | "success") =>
    text(theme[k], lang) ? <Said value={theme[k]} lang={lang} machine={theme.text_meta?.[k]} /> : null;
  // what the header above does not already show; fields nobody filled are left out
  const rows: [string, React.ReactNode][] = ([
    [T.front[lang], text(fronts.find(f => f.key === theme.front)?.name, lang) || "—"],
    [T.start[lang], theme.start_date ? dateText(theme.start_date) : null],
    [T.colTags[lang], theme.tags.length ? theme.tags.map(x => `#${x}`).join(" ") : null],
    [T.whatItIs[lang], said("what_it_is")],
    [T.problem[lang], said("problem")],
    [T.solution[lang], said("solution")],
    [T.success[lang], said("success")],
  ] as [string, React.ReactNode][]).filter(([, v]) => v);
  return (
    <section className="panel" aria-label="theme">
      <dl className="pairs grid">{rows.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
    </section>
  );
}

const merge = (old: I18n, lang: Lang, value: string): I18n => ({ ...old, [lang]: value });

function ThemeForm({ data, saved, onSaved, onEdit }: { data: Data; saved: boolean; onSaved: () => void; onEdit: () => void }) {
  const { lang, db, name } = useApp();
  const { theme, fronts } = data;
  const [f, setF] = useState({
    front: theme.front, status: theme.status, stage: theme.stage ? String(theme.stage) : "", owner: theme.owner ?? "",
    start_date: theme.start_date ?? "", due_date: theme.due_date ?? "", tags: theme.tags.join(", "),
    title: theme.title[lang] ?? "", what_it_is: theme.what_it_is[lang] ?? "", progress: theme.progress[lang] ?? "",
    problem: theme.problem[lang] ?? "", solution: theme.solution[lang] ?? "", success: theme.success[lang] ?? ""
  });
  const [note, setNote] = useState("");
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => { onEdit(); setF({ ...f, [k]: e.target.value }); };
  const save = async () => {
    if (!name.trim()) return setNote(T.needName[lang]);
    const p: Record<string, unknown> = {};
    if (f.front !== theme.front) p.front = f.front;
    if (f.status !== theme.status) p.status = f.status;
    if (theme.kind === "project" && f.stage !== (theme.stage ? String(theme.stage) : "")) p.stage = f.stage ? Number(f.stage) : null;
    if (f.owner.trim() !== (theme.owner ?? "")) p.owner = f.owner.trim();
    if (f.start_date !== (theme.start_date ?? "")) p.start_date = f.start_date || null;
    if (f.due_date !== (theme.due_date ?? "")) p.due_date = f.due_date || null;
    const tags = f.tags.split(",").map(x => x.trim().replace(/^#/, "")).filter(Boolean);
    if (tags.join("\n") !== theme.tags.join("\n")) p.tags = tags;
    for (const k of ["title", "what_it_is", "progress", "problem", "solution", "success"] as const) {
      if (f[k] !== (theme[k][lang] ?? "")) p[k] = merge(theme[k], lang, f[k]);
    }
    if (!Object.keys(p).length) return onSaved();
    setNote(T.saving[lang]);
    try { await db.updateTheme(theme.id, p, name.trim()); setNote(""); onSaved(); }
    catch (e) { setNote(message(e, lang)); }
  };
  const area = (k: "what_it_is" | "progress" | "problem" | "solution" | "success", label: string, rows = 2) => (
    <Field label={label}>
      {theme.text_meta?.[k]?.includes(lang) && theme[k][lang] ? <span className="from auto" title={T.machineNote[lang]}>{T.machine[lang]}</span> : null}
      <textarea rows={rows} maxLength={1200} value={f[k]} placeholder={theme[k][lang] ? "" : text(theme[k], lang)} onChange={set(k)} />
    </Field>
  );
  return (
    <form className="panel" onSubmit={e => { e.preventDefault(); void save(); }} aria-label="theme">
      <p className="note">{T.writtenIn[lang]} {lang.toUpperCase()}</p>
      <div className="fields">
        <Field label={T.title[lang]}><input value={f.title} maxLength={200} onChange={set("title")} placeholder={text(theme.title, lang)} /></Field>
        <Field label={T.front[lang]}>
          <select value={f.front} onChange={set("front")}>{fronts.map(x => <option key={x.key} value={x.key}>{text(x.name, lang)}</option>)}</select>
        </Field>
        <Field label={T.status[lang]}>
          <select value={f.status} onChange={set("status")}>{STATUSES.map(s => <option key={s} value={s}>{t(`status.${s}`, lang)}</option>)}</select>
        </Field>
        {theme.kind === "project" ? (
          <Field label={T.stage[lang]}>
            <select value={f.stage} onChange={set("stage")}>{STAGES.map(s => <option key={s} value={s}>{t(`stage.${s}`, lang)}</option>)}</select>
          </Field>
        ) : null}
        <Field label={T.owner[lang]}><input value={f.owner} maxLength={80} onChange={set("owner")} /></Field>
        <Field label={T.start[lang]}><input type="date" value={f.start_date} onChange={set("start_date")} /></Field>
        <Field label={T.due[lang]}><input type="date" value={f.due_date} onChange={set("due_date")} /></Field>
        <Field label={T.tags[lang]}><input value={f.tags} onChange={set("tags")} /></Field>
      </div>
      {area("what_it_is", T.whatItIs[lang])}
      {area("progress", T.progress[lang])}
      {area("problem", T.problem[lang], 3)}
      {area("solution", T.solution[lang], 3)}
      {area("success", T.success[lang], 3)}
      <p><button type="submit" className="btn primary">{T.save[lang]}</button> <span className="note" role="status">{note || (saved ? T.saved[lang] : "")}</span></p>
    </form>
  );
}

function Items({ data, onChanged }: { data: Data; onChanged: () => void }) {
  const { lang, db, name, reader } = useApp();
  const [title, setTitle] = useState("");
  const [itemDue, setItemDue] = useState("");
  const [milestone, setMilestone] = useState(false);
  const [note, setNote] = useState("");
  const [view, setView] = useState<"board" | "list">("board");
  useEffect(() => { try { if (localStorage.getItem("phiz-theme-items-view") === "list") setView("list"); } catch { /* no storage */ } }, []);
  const pick = (v: "board" | "list") => { setView(v); try { localStorage.setItem("phiz-theme-items-view", v); } catch { /* no storage */ } };
  const save = (i: Item, p: Record<string, unknown>) => run(() => db.saveItem(data.theme.id, i.id, p, name.trim()));
  const run = async (fn: () => Promise<unknown>) => {
    if (!name.trim()) return setNote(T.needName[lang]);
    try { await fn(); setNote(""); onChanged(); } catch (e) { setNote(message(e, lang)); }
  };
  return (
    <section className="panel" aria-label={T.items[lang]}>
      <div className="items-head">
        <h2>{T.items[lang]}</h2>
        <div className="seg" role="group" aria-label={T.views[lang]}>
          <button type="button" aria-pressed={view === "list"} onClick={() => pick("list")}>{T.viewList[lang]}</button>
          <button type="button" aria-pressed={view === "board"} onClick={() => pick("board")}>{T.viewBoard[lang]}</button>
        </div>
      </div>
      {view === "list" ? <ItemList items={data.items} save={save} /> : <div className="kanban">
        {COLS.map(c => (
          <div className="col" key={c} data-col={c}>
            <h3>{t(`col.${c}`, lang)}</h3>
            <ul>
              {data.items.filter(i => i.col === c).map(i => (
                <li key={i.id} className="item">
                  <span>{i.milestone ? "◆ " : ""}{i.title}{i.due_date ? <span className="note"> · {dateText(i.due_date)}</span> : null}</span>
                  {!reader ? <span className="moves">
                    {COLS.filter(x => x !== c).map(x => (
                      <button key={x} type="button" className="mini" title={t(`col.${x}`, lang)} aria-label={`${i.title} → ${t(`col.${x}`, lang)}`}
                        onClick={() => run(() => db.saveItem(data.theme.id, i.id, { col: x }, name.trim()))}>{t(`col.${x}`, lang)}</button>
                    ))}
                  </span> : null}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>}
      {!reader ? (
        <form className="inline" onSubmit={e => { e.preventDefault(); if (title.trim()) void run(async () => { await db.saveItem(data.theme.id, null, { title: title.trim(), due_date: itemDue || null, milestone }, name.trim()); setTitle(""); setItemDue(""); setMilestone(false); }); }}>
          <input aria-label={T.itemTitle[lang]} placeholder={T.itemTitle[lang]} value={title} maxLength={200} onChange={e => setTitle(e.target.value)} />
          <input type="date" aria-label={T.byWhen[lang]} value={itemDue} onChange={e => setItemDue(e.target.value)} />
          <label className="checks"><input type="checkbox" checked={milestone} onChange={e => setMilestone(e.target.checked)} /> {T.milestones[lang]}</label>
          <button type="submit" className="btn">{T.addItem[lang]}</button> <span className="note" role="status">{note}</span>
        </form>
      ) : null}
    </section>
  );
}

function JiraLinks({ data, onChanged }: { data: Data; onChanged: () => void }) {
  const { lang, db, name, reader } = useApp();
  const [url, setUrl] = useState("");
  const [label, setLabel] = useState("");
  const [note, setNote] = useState("");
  const run = async (fn: () => Promise<unknown>) => {
    if (!name.trim()) return setNote(T.needName[lang]);
    try { await fn(); setNote(""); onChanged(); } catch (e) { setNote(message(e, lang)); }
  };
  return (
    <section className="panel" aria-label={T.jira[lang]}>
      <h2>{T.jira[lang]}</h2>
      {data.jira.length ? (
        <ul className="plain">
          {data.jira.map(j => (
            <li key={j.id}>
              <a href={j.url} target="_blank" rel="noopener noreferrer" className="jira">{j.issue_key ?? j.label ?? j.url}</a>
              {j.label && j.issue_key ? <span className="note"> {j.label}</span> : null}{" "}
              {!reader ? <button type="button" className="mini" onClick={() => run(() => db.removeJira(j.id, name.trim()))}>{T.remove[lang]}</button> : null}
            </li>
          ))}
        </ul>
      ) : <p className="empty">{T.none[lang]}</p>}
      {!reader ? <form className="inline" onSubmit={e => { e.preventDefault(); if (url.trim()) void run(async () => { await db.addJira(data.theme.id, null, url.trim(), label.trim(), name.trim()); setUrl(""); setLabel(""); }); }}>
        <input aria-label={T.jiraUrl[lang]} placeholder={T.jiraUrl[lang]} value={url} onChange={e => setUrl(e.target.value)} />
        <input aria-label={T.jiraLabel[lang]} placeholder={T.jiraLabel[lang]} value={label} maxLength={80} onChange={e => setLabel(e.target.value)} />
        <button type="submit" className="btn">{T.add[lang]}</button> <span className="note" role="status">{note}</span>
      </form> : null}
    </section>
  );
}

function Dependencies({ data, onChanged }: { data: Data; onChanged: () => void }) {
  const { lang, db, name, reader } = useApp();
  const [to, setTo] = useState("");
  const [kind, setKind] = useState("depends_on");
  const [note, setNote] = useState("");
  const [titles, setTitles] = useState<Record<string, I18n>>({});
  const ids = [...new Set([...data.links.map(l => l.to_theme), ...data.linksTo.map(l => l.theme_id)])];
  const key = ids.join(",");
  useEffect(() => {
    if (!ids.length) return;
    void db.titles(ids).then(rows => setTitles(Object.fromEntries(rows.map(r => [r.id, r.title])))).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [db, key]);
  const run = async (fn: () => Promise<unknown>) => {
    if (!name.trim()) return setNote(T.needName[lang]);
    try { await fn(); setNote(""); onChanged(); } catch (e) { setNote(message(e, lang)); }
  };
  const label = (id: string) => <a href={`/themes/${id}/`}>{id} {text(titles[id], lang)}</a>;
  return (
    <section className="panel" aria-label={T.deps[lang]}>
      <h2>{T.deps[lang]}</h2>
      {data.links.length || data.linksTo.length ? (
        <ul className="plain">
          {data.links.map(l => (
            <li key={`${l.to_theme}${l.kind}`}>{t(l.kind, lang)} {label(l.to_theme)}{" "}
              {!reader ? <button type="button" className="mini" onClick={() => run(() => db.setLink(data.theme.id, l.to_theme, l.kind, false, name.trim()))}>{T.remove[lang]}</button> : null}</li>
          ))}
          {data.linksTo.map(l => <li key={`in${l.theme_id}${l.kind}`}>← {label(l.theme_id)} {t(l.kind, lang)}</li>)}
        </ul>
      ) : <p className="empty">{T.none[lang]}</p>}
      {!reader ? <form className="inline" onSubmit={e => { e.preventDefault(); if (to.trim()) void run(async () => { await db.setLink(data.theme.id, to.trim().toUpperCase(), kind, true, name.trim()); setTo(""); }); }}>
        <select value={kind} aria-label={T.deps[lang]} onChange={e => setKind(e.target.value)}>{["depends_on", "blocks", "related"].map(k => <option key={k} value={k}>{t(k, lang)}</option>)}</select>
        <input aria-label={T.otherTheme[lang]} placeholder={T.otherTheme[lang]} value={to} maxLength={8} onChange={e => setTo(e.target.value)} />
        <button type="submit" className="btn">{T.add[lang]}</button> <span className="note" role="status">{note}</span>
      </form> : null}
    </section>
  );
}

function History({ events, lang }: { events: EventRow[]; lang: Lang }) {
  const show = (e: EventRow) => {
    if (e.field === "move") {
      const v = (e.new_value ?? {}) as { from_stage?: number | null; to_stage?: number; reason?: string | null; open_gates?: string[] };
      const st = (n?: number | null) => (n ? t(`stage.${n}`, lang) : "—");
      return `${t("ev.move", lang)}: ${st(v.from_stage)} → ${st(v.to_stage)}${v.open_gates?.length ? ` (${v.open_gates.length} ${t("gatesOpen", lang)})` : ""}${v.reason ? ` — ${v.reason}` : ""}`;
    }
    if (e.field === "gate_checked" || e.field === "gate_unchecked") return `${t(`ev.${e.field}`, lang)}: ${String(e.new_value)}`;
    if (/^(jira|link|item|blocker|decision|attachment|answer|ai_)/.test(e.field) || e.field === "created" || e.field === "update_posted") return t(`ev.${e.field}`, lang);
    const v = (x: unknown) => (typeof x === "object" && x ? JSON.stringify(x).slice(0, 60) : String(x ?? "—"));
    return `${e.field}: ${v(e.old_value)} → ${v(e.new_value)}`;
  };
  return (
    <section className="panel" aria-label={T.history[lang]}>
      <h2>{T.history[lang]}</h2>
      <ul className="plain history">
        {events.map(e => <li key={e.id}><time>{dateText(e.at)}</time> {show(e)} <span className="note">{T.by[lang]} {e.edited_by}</span></li>)}
      </ul>
    </section>
  );
}

/* A text edited where it is shown: click, type, Enter (or leaving the field) saves, Escape gives the old text back. */
function InlineText({ tag, field, value, className, placeholder, required, onSave }: {
  tag: "h1" | "p"; field: string; value: string; className?: string; placeholder?: string; required?: boolean; onSave: (v: string) => Promise<boolean>;
}) {
  const ref = useRef<HTMLElement | null>(null);
  const Tag = tag as "h1";
  const done = () => {
    const el = ref.current;
    if (!el) return;
    const v = (el.textContent ?? "").replace(/\s+/g, " ").trim();
    if (v === value.trim() || (required && !v)) { el.textContent = value; return; }
    void onSave(v).then(ok => { if (!ok && ref.current) ref.current.textContent = value; });
  };
  return (
    <Tag ref={ref as React.Ref<HTMLHeadingElement>} className={`${className ?? ""} editable`.trim()} data-edit={field} contentEditable suppressContentEditableWarning spellCheck
      data-placeholder={placeholder} title={placeholder}
      onBlur={done}
      onKeyDown={e => {
        if (e.key === "Enter") { e.preventDefault(); (e.currentTarget as HTMLElement).blur(); }
        if (e.key === "Escape") { e.preventDefault(); (e.currentTarget as HTMLElement).textContent = value; (e.currentTarget as HTMLElement).blur(); }
      }}>{value}</Tag>
  );
}

/* The right column: the theme's properties, each changed where it is shown (read-only for readers). */
function Properties({ data, save }: { data: Data; save: (p: Record<string, unknown>) => Promise<boolean> }) {
  const { lang, reader } = useApp();
  const { theme, fronts } = data;
  const [owner, setOwner] = useState(theme.owner ?? "");
  const ph = phaseOf(theme.kind === "project" ? theme.stage : null);
  // a change that was not saved (no name, refused) puts the control back to what is saved
  const set = (el: HTMLInputElement | HTMLSelectElement, old: string, p: Record<string, unknown>) => void save(p).then(ok => { if (!ok) el.value = old; });
  const row = (k: string, label: string, view: React.ReactNode, edit: React.ReactNode) => (
    <div data-prop={k}><dt>{label}</dt><dd>{reader ? view : edit}</dd></div>
  );
  const date = (k: "start_date" | "due_date", label: string) => row(k, label, dateText(theme[k]),
    <input type="date" aria-label={label} defaultValue={theme[k]?.slice(0, 10) ?? ""} onChange={e => set(e.target, theme[k]?.slice(0, 10) ?? "", { [k]: e.target.value || null })} />);
  return (
    <section className="panel props" aria-label={T.properties[lang]} data-block="properties">
      <h2>{T.properties[lang]}</h2>
      <dl className="props-list">
        {row("status", T.status[lang], <StatusBadge status={theme.status} lang={lang} />,
          <select aria-label={T.status[lang]} defaultValue={theme.status} onChange={e => set(e.target, theme.status, { status: e.target.value })}>
            {STATUSES.map(x => <option key={x} value={x}>{t(`status.${x}`, lang)}</option>)}
          </select>)}
        {theme.kind === "project" ? <>
          {row("stage", T.stage[lang], theme.stage ? t(`stage.${theme.stage}`, lang) : "—",
            <select aria-label={T.stage[lang]} defaultValue={theme.stage ? String(theme.stage) : ""} onChange={e => set(e.target, theme.stage ? String(theme.stage) : "", { stage: e.target.value ? Number(e.target.value) : null })}>
              {!theme.stage ? <option value="">—</option> : null}
              {STAGES.map(x => <option key={x} value={x}>{t(`stage.${x}`, lang)}</option>)}
            </select>)}
          <div data-prop="phase"><dt>{T.phase[lang]}</dt><dd className="props-phase"><PhaseIcon theme={theme} lang={lang} /> {ph ? t(`phase.${ph}`, lang) : "—"}</dd></div>
        </> : null}
        <div data-prop="kind"><dt>{T.kind[lang]}</dt><dd>{t(theme.kind, lang)}</dd></div>
        {row("owner", T.owner[lang], theme.owner ?? "—",
          <input aria-label={T.owner[lang]} value={owner} maxLength={80} onChange={e => setOwner(e.target.value)}
            onBlur={() => { if (owner.trim() !== (theme.owner ?? "")) void save({ owner: owner.trim() }).then(ok => { if (!ok) setOwner(theme.owner ?? ""); }); }}
            onKeyDown={e => { if (e.key === "Enter") (e.currentTarget as HTMLInputElement).blur(); }} />)}
        {date("start_date", T.start[lang])}
        {date("due_date", T.due[lang])}
        {row("front", T.front[lang], text(fronts.find(f => f.key === theme.front)?.name, lang) || "—",
          <select aria-label={T.front[lang]} defaultValue={theme.front} onChange={e => set(e.target, theme.front, { front: e.target.value })}>
            {fronts.map(x => <option key={x.key} value={x.key}>{text(x.name, lang)}</option>)}
          </select>)}
        <div data-prop="id"><dt>ID</dt><dd className="id">{theme.id}</dd></div>
      </dl>
    </section>
  );
}

/* The deliveries as a list: every field changed where it is shown; a delivery is closed by moving it to Done, never deleted. */
function ItemList({ items, save }: { items: Item[]; save: (i: Item, p: Record<string, unknown>) => Promise<unknown> }) {
  const { lang, reader } = useApp();
  if (!items.length) return <p className="empty">{T.none[lang]}</p>;
  const order = (i: Item) => COLS.indexOf(i.col as (typeof COLS)[number]);
  const rows = [...items].sort((a, b) => order(a) - order(b) || (a.due_date ?? "9999").localeCompare(b.due_date ?? "9999"));
  return (
    <table className="items-list">
      <thead><tr><th>{T.deliveryName[lang]}</th><th>{T.column[lang]}</th><th>{T.start[lang]}</th><th>{T.due[lang]}</th><th>{T.owner[lang]}</th><th>{T.milestoneOne[lang]}</th></tr></thead>
      <tbody>
        {rows.map(i => reader ? (
          <tr key={i.id} data-item={i.id} data-col={i.col}>
            <td>{i.milestone ? "◆ " : ""}{i.title}</td><td>{t(`col.${i.col}`, lang)}</td><td>{dateText(i.start_date ?? null)}</td><td>{dateText(i.due_date)}</td>
            <td>{i.owner ?? "—"}</td><td>{i.milestone ? "◆" : ""}</td>
          </tr>
        ) : (
          <tr key={`${i.id}${i.title}${i.owner}${i.start_date}${i.due_date}${i.col}${i.milestone}`} data-item={i.id} data-col={i.col}>
            <td><input aria-label={`${T.deliveryName[lang]}: ${i.title}`} defaultValue={i.title} maxLength={200}
              onBlur={e => { const v = e.target.value.trim(); if (v && v !== i.title) void save(i, { title: v }); else e.target.value = i.title; }}
              onKeyDown={e => { if (e.key === "Enter") (e.currentTarget as HTMLInputElement).blur(); }} /></td>
            <td><select aria-label={`${T.column[lang]}: ${i.title}`} defaultValue={i.col} onChange={e => void save(i, { col: e.target.value })}>
              {COLS.map(c => <option key={c} value={c}>{t(`col.${c}`, lang)}</option>)}</select></td>
            <td><input type="date" aria-label={`${T.start[lang]}: ${i.title}`} defaultValue={i.start_date?.slice(0, 10) ?? ""} onChange={e => void save(i, { start_date: e.target.value || null })} /></td>
            <td><input type="date" aria-label={`${T.due[lang]}: ${i.title}`} defaultValue={i.due_date?.slice(0, 10) ?? ""} onChange={e => void save(i, { due_date: e.target.value || null })} /></td>
            <td><input aria-label={`${T.owner[lang]}: ${i.title}`} defaultValue={i.owner ?? ""} maxLength={80}
              onBlur={e => { const v = e.target.value.trim(); if (v !== (i.owner ?? "")) void save(i, { owner: v }); }}
              onKeyDown={e => { if (e.key === "Enter") (e.currentTarget as HTMLInputElement).blur(); }} /></td>
            <td><input type="checkbox" aria-label={`${T.milestoneOne[lang]}: ${i.title}`} defaultChecked={i.milestone} onChange={e => void save(i, { milestone: e.target.checked })} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
