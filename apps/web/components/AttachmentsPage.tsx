"use client";
/* Every attachment of every theme in one table (latest editions), with filters. Adding is done on the theme page. */
import { useCallback, useEffect, useMemo, useState } from "react";
import { STAGES, T, t, text } from "../lib/i18n";
import type { Attachment, Front, Theme } from "../lib/db";
import { editions } from "../lib/attachments";
import { useApp } from "./Shell";
import { AttachmentTable } from "./Attachments";

export function AttachmentsPage() {
  const { lang, db } = useApp();
  const [data, setData] = useState<{ rows: Attachment[]; themes: Theme[]; fronts: Front[] } | null>(null);
  const [failed, setFailed] = useState(false);
  const [f, setF] = useState({ kind: "", front: "", stage: "", who: "", q: "" });
  const load = useCallback(async () => {
    try { const [rows, themes, fronts] = await Promise.all([db.allAttachments(), db.themes(), db.fronts()]); setData({ rows, themes, fronts }); setFailed(false); } catch { setFailed(true); }
  }, [db]);
  useEffect(() => { void load(); }, [load]);
  const titles = useMemo(() => new Map((data?.themes ?? []).map(x => [x.id, text(x.title, lang)])), [data, lang]);
  const whos = useMemo(() => [...new Set((data?.rows ?? []).map(r => r.created_by))].sort(), [data]);
  const groups = useMemo(() => {
    if (!data) return [];
    const front = new Map(data.themes.map(x => [x.id, x.front]));
    const q = f.q.trim().toLowerCase();
    return editions(data.rows).filter(({ latest: a }) => (!f.kind || a.kind === f.kind) && (!f.front || front.get(a.theme_id) === f.front) && (!f.stage || String(a.stage) === f.stage)
      && (!f.who || a.created_by === f.who) && (!q || `${a.name} ${a.description}`.toLowerCase().includes(q)));
  }, [data, f]);
  if (failed) return <p className="state err">{T.failed[lang]}</p>;
  if (!data) return <p className="state">{T.loading[lang]}</p>;
  return (
    <>
      <p className="eyebrow">{T.eyebrowDocs[lang]}</p>
      <h1>{T.attachments[lang]}</h1>
      <p className="lead">{T.attachmentsLead[lang]}</p>
      <div className="bar">
        <div className="fields">
          <label className="field"><span>{T.attSearch[lang]}</span><input value={f.q} onChange={e => setF({ ...f, q: e.target.value })} /></label>
          <label className="field"><span>{T.attKind[lang]}</span>
            <select value={f.kind} onChange={e => setF({ ...f, kind: e.target.value })}><option value="">{T.attAllKinds[lang]}</option>{["file", "note", "link"].map(k => <option key={k} value={k}>{t(`kind.${k}`, lang)}</option>)}</select></label>
          <label className="field"><span>{T.front[lang]}</span>
            <select value={f.front} onChange={e => setF({ ...f, front: e.target.value })}><option value="">{T.all[lang]}</option>{data.fronts.map(x => <option key={x.key} value={x.key}>{text(x.name, lang)}</option>)}</select></label>
          <label className="field"><span>{T.stage[lang]}</span>
            <select value={f.stage} onChange={e => setF({ ...f, stage: e.target.value })}><option value="">{T.all[lang]}</option>{STAGES.map(s => <option key={s} value={s}>{t(`stage.${s}`, lang)}</option>)}</select></label>
          <label className="field"><span>{T.attWho[lang]}</span>
            <select value={f.who} onChange={e => setF({ ...f, who: e.target.value })}><option value="">{T.all[lang]}</option>{whos.map(x => <option key={x} value={x}>{x}</option>)}</select></label>
        </div>
      </div>
      {groups.length ? <AttachmentTable groups={groups} items={[]} showTheme themeTitles={titles} onChanged={load} /> : <p className="empty">{T.attNone[lang]}</p>}
    </>
  );
}
