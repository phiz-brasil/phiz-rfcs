"use client";
import { useCallback, useEffect, useState } from "react";
import { COLS, STAGES, STATUSES, T, t, text, type Lang } from "../lib/i18n";
import type { Blocker, Decision, EventRow, Front, I18n, Item, Jira, Link, Theme, Update } from "../lib/db";
import { useApp } from "./Shell";
import { Field, Said, StatusBadge, dateText, message } from "./ui";
import { Records, WeeklyUpdate } from "./Updates";
import { Gates } from "./Gates";
import { Attachments } from "./Attachments";
import { Summary } from "./Summary";

type Data = { theme: Theme; fronts: Front[]; items: Item[]; links: Link[]; linksTo: Link[]; jira: Jira[]; events: EventRow[]; rfc: { rfc_id: string; version: string } | null;
  updates: Update[]; blockers: Blocker[]; decisions: Decision[] };

export function ThemeDetail({ id }: { id: string }) {
  const { lang, db, reader } = useApp();
  const [data, setData] = useState<Data | null>(null);
  const [state, setState] = useState<"loading" | "missing" | "failed" | "ok">("loading");
  const [saved, setSaved] = useState(false);           // the form is redrawn from the saved data, so the "Saved." note lives here
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

  if (state === "loading") return <p className="state">{T.loading[lang]}</p>;
  if (state === "missing") return <><p><a href="/themes/">{T.back[lang]}</a></p><p className="state">{T.notFound[lang]}</p></>;
  if (state === "failed" || !data) return <p className="state err">{T.failed[lang]}</p>;
  const { theme } = data;
  return (
    <>
      <p><a href="/themes/">{T.back[lang]}</a></p>
      <div className="top">
        <span className="id">{theme.id}</span>
        <span className="ver">{t(theme.kind, lang)}</span>
        <StatusBadge status={theme.status} lang={lang} />
        {theme.stage ? <span className="ver">{t(`stage.${theme.stage}`, lang)}</span> : null}
      </div>
      <h1><Said value={theme.title} lang={lang} machine={theme.text_meta?.title} /></h1>
      <section className="panel rfcbox">
        <h2>{T.rfc[lang]}</h2>
        {data.rfc ? <p><a className="btn" href={`/rfc/?id=${theme.id}`}>{T.openRfc[lang]} (v{data.rfc.version})</a></p> : <p className="empty">{T.noRfc[lang]}</p>}
      </section>
      {reader
        ? <ThemeReadOnly data={data} />
        : <ThemeForm key={theme.updated_at + lang} data={data} saved={saved} onSaved={() => { setSaved(true); void load(); }} onEdit={() => setSaved(false)} />}
      <Summary key={`s${theme.updated_at}${lang}`} theme={theme} onChanged={load} />
      <WeeklyUpdate key={`u${data.updates.length}${lang}`} theme={theme} updates={data.updates} onChanged={load} />
      <Records kind="blocker" theme={theme} rows={data.blockers} items={data.items} onChanged={load} />
      <Records kind="decision" theme={theme} rows={data.decisions} items={data.items} onChanged={load} />
      {theme.kind === "project" ? <Gates key={`g${theme.stage}${theme.route}${lang}`} theme={theme} /> : null}
      {theme.kind === "project" ? <Items data={data} onChanged={load} /> : null}
      <Attachments theme={theme} items={data.items} />
      <JiraLinks data={data} onChanged={load} />
      <Dependencies data={data} onChanged={load} />
      <History events={data.events} lang={lang} />
    </>
  );
}

function ThemeReadOnly({ data }: { data: Data }) {
  const { lang } = useApp();
  const { theme, fronts } = data;
  const rows: [string, React.ReactNode][] = [
    [T.front[lang], text(fronts.find(f => f.key === theme.front)?.name, lang)],
    [T.owner[lang], theme.owner ?? "—"],
    [T.start[lang], dateText(theme.start_date)],
    [T.due[lang], dateText(theme.due_date)],
    [T.tags[lang], theme.tags.length ? theme.tags.map(x => `#${x}`).join(" ") : "—"],
    [T.whatItIs[lang], <Said key="w" value={theme.what_it_is} lang={lang} machine={theme.text_meta?.what_it_is} />],
    [T.progress[lang], <Said key="p" value={theme.progress} lang={lang} machine={theme.text_meta?.progress} />],
    [T.problem[lang], <Said key="pr" value={theme.problem} lang={lang} machine={theme.text_meta?.problem} />],
    [T.solution[lang], <Said key="s" value={theme.solution} lang={lang} machine={theme.text_meta?.solution} />],
    [T.success[lang], <Said key="su" value={theme.success} lang={lang} machine={theme.text_meta?.success} />]
  ];
  return (
    <section className="panel" aria-label="theme">
      <dl className="pairs">{rows.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v || "—"}</dd></div>)}</dl>
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
  const run = async (fn: () => Promise<unknown>) => {
    if (!name.trim()) return setNote(T.needName[lang]);
    try { await fn(); setNote(""); onChanged(); } catch (e) { setNote(message(e, lang)); }
  };
  return (
    <section className="panel" aria-label={T.items[lang]}>
      <h2>{T.items[lang]}</h2>
      <div className="kanban">
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
      </div>
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
