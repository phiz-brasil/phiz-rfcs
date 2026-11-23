"use client";
/* The attachments of a theme: files (straight to private Storage, up to 50 MB), Markdown notes and links, with editions. A file is opened through a
   signed address that expires; pictures, audio and video play in the page, everything else (HTML always) is offered as a download. */
import { useCallback, useEffect, useState } from "react";
import { STAGES, T, t, text } from "../lib/i18n";
import type { Attachment, Item, Theme } from "../lib/db";
import { MAX_BYTES, editions, formatSize, isHtml, previewKind, sha256, storageName } from "../lib/attachments";
import { useApp } from "./Shell";
import { Field, dateText, message } from "./ui";

export function Attachments({ theme, items }: { theme: Theme; items: Item[] }) {
  const { lang, db, reader } = useApp();
  const [rows, setRows] = useState<Attachment[] | null>(null);
  const [pictures, setPictures] = useState<{ name: string; rev: number; size: number }[]>([]);
  const [replaces, setReplaces] = useState("");
  const load = useCallback(async () => {
    try {
      const [a, p] = await Promise.all([db.attachments(theme.id), db.rfcPictures(theme.id).catch(() => [])]);
      setRows(a);
      setPictures(p);
    } catch { setRows([]); }
  }, [db, theme.id]);
  useEffect(() => { void load(); }, [load]);
  const groups = rows ? editions(rows) : [];
  const names = [...new Map(pictures.map(p => [p.name, p])).values()];
  return (
    <section className="panel" aria-label={T.attachments[lang]} id="attachments">
      <h2>{T.attachments[lang]}</h2>
      <p className="note">{T.attachmentsThemeLead[lang]}</p>
      {rows === null ? <p className="state">{T.loading[lang]}</p> : groups.length ? (
        <AttachmentTable groups={groups} items={items} showTheme={false} onChanged={load} onEdition={id => { setReplaces(id); document.getElementById("add-attachment")?.scrollIntoView(); }} />
      ) : <p className="empty">{T.attNone[lang]}</p>}
      {names.length ? (
        <details data-group="rfc-pictures">
          <summary>{T.attRfcPictures[lang]} ({names.length})</summary>
          <p className="note">{T.attRfcPicturesLead[lang]} <a href={`/rfc/?id=${theme.id}`}>{theme.id}</a></p>
          <ul className="plain">{names.map(p => <li key={p.name}>{p.name} · {formatSize(p.size)}</li>)}</ul>
        </details>
      ) : null}
      {!reader ? <AddAttachment key={replaces} theme={theme} items={items} rows={rows ?? []} initialReplaces={replaces} onAdded={() => { setReplaces(""); void load(); }} /> : null}
    </section>
  );
}

export function AttachmentTable({ groups, items, showTheme, onChanged, onEdition, themeTitles }: { groups: { latest: Attachment; older: Attachment[] }[]; items: Item[]; showTheme: boolean;
  onChanged: () => void; onEdition?: (id: string) => void; themeTitles?: Map<string, string> }) {
  const { lang } = useApp();
  return (
    <table className="stats attachments">
      <thead><tr>{showTheme ? <th>{T.attTheme[lang]}</th> : null}<th>{T.attKind[lang]}</th><th>{T.attName[lang]}</th><th>{T.attWho[lang]}</th><th>{T.attWhen[lang]}</th><th>{T.attSize[lang]}</th><th>{T.stage[lang]}</th><th /></tr></thead>
      <tbody>
        {groups.map(g => (
          <AttachmentRow key={g.latest.id} g={g} items={items} showTheme={showTheme} themeTitle={themeTitles?.get(g.latest.theme_id)} onChanged={onChanged} onEdition={onEdition} />
        ))}
      </tbody>
    </table>
  );
}

function AttachmentRow({ g, items, showTheme, themeTitle, onChanged, onEdition }: { g: { latest: Attachment; older: Attachment[] }; items: Item[]; showTheme: boolean;
  themeTitle?: string; onChanged: () => void; onEdition?: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const { lang } = useApp();
  return (
    <>
      <Line a={g.latest} items={items} showTheme={showTheme} themeTitle={themeTitle} onChanged={onChanged} onEdition={onEdition}
        extra={g.older.length ? <button type="button" className="mini" aria-expanded={open} onClick={() => setOpen(o => !o)}>{g.older.length} {T.attEarlier[lang]}</button> : null} />
      {open ? g.older.map(a => <Line key={a.id} a={a} items={items} showTheme={showTheme} themeTitle={themeTitle} onChanged={onChanged} earlier />) : null}
    </>
  );
}

function Line({ a, items, showTheme, themeTitle, onChanged, onEdition, extra, earlier }: { a: Attachment; items: Item[]; showTheme: boolean; themeTitle?: string; onChanged: () => void;
  onEdition?: (id: string) => void; extra?: React.ReactNode; earlier?: boolean }) {
  const { lang, db, name, reader } = useApp();
  const [note, setNote] = useState("");
  const [preview, setPreview] = useState<{ kind: "image" | "audio" | "video"; url: string } | null>(null);
  const [showNote, setShowNote] = useState(false);
  const open = async () => {
    if (a.kind === "link") return void window.open(a.url!, "_blank", "noopener");
    if (a.kind === "note") return setShowNote(s => !s);
    try {
      const pk = previewKind(a);
      if (pk) {
        if (preview) return setPreview(null);
        return setPreview({ kind: pk, url: await db.signedUrl(a.storage_path!) });
      }
      const url = await db.signedUrl(a.storage_path!, a.name);            // anything that is not a picture, audio or video is saved, never shown on this origin
      const link = document.createElement("a");
      link.href = url; link.download = a.name; link.rel = "noopener"; document.body.appendChild(link); link.click(); link.remove();
    } catch (e) { setNote(message(e, lang)); }
  };
  const remove = async () => {
    if (!name.trim()) return setNote(T.needName[lang]);
    try { await db.hideAttachment(a.id, name.trim()); onChanged(); } catch (e) { setNote(message(e, lang)); }
  };
  const item = a.item_id ? items.find(i => i.id === a.item_id) : null;
  return (
    <>
      <tr data-attachment={a.id} data-kind={a.kind} data-name={a.name} data-earlier={earlier ? "1" : "0"}>
        {showTheme ? <td><a href={`/themes/${a.theme_id}/#attachments`}>{a.theme_id}</a>{themeTitle ? <span className="note"> {themeTitle}</span> : null}</td> : null}
        <td>{t(`kind.${a.kind}`, lang)}</td>
        <td><strong>{a.name}</strong>{a.description ? <span className="note"> — {a.description}</span> : null}{item ? <span className="note"> · {item.title}</span> : null}
          {a.kind === "file" && isHtml(a) ? <span className="note"> · {T.attHtmlNote[lang]}</span> : null}</td>
        <td>{a.created_by}</td><td>{dateText(a.created_at)}</td><td>{a.kind === "file" ? formatSize(a.size) : "—"}</td><td>{a.stage ? t(`stage.${a.stage}`, lang) : "—"}</td>
        <td className="acts">
          <button type="button" className="mini" onClick={() => void open()}>{a.kind === "file" && !previewKind(a) ? T.attDownload[lang] : T.attOpen[lang]}</button>{" "}
          {!reader && !earlier && onEdition ? <button type="button" className="mini" onClick={() => onEdition(a.id)}>{T.attNewEdition[lang]}</button> : null}{" "}
          {!reader && !earlier ? <button type="button" className="mini" onClick={() => void remove()}>{T.attRemove[lang]}</button> : null}{" "}{extra}
          {note ? <span className="note" role="status"> {note}</span> : null}
        </td>
      </tr>
      {showNote && a.body ? <tr data-note-of={a.id}><td colSpan={showTheme ? 8 : 7}><pre className="notebody">{a.body}</pre></td></tr> : null}
      {preview?.url ? (
        <tr data-preview-of={a.id}><td colSpan={showTheme ? 8 : 7}>
          {preview.kind === "image" ? <img src={preview.url} alt={a.name} style={{ maxWidth: "100%" }} /> : preview.kind === "audio" ? <audio controls src={preview.url} /> : <video controls src={preview.url} style={{ maxWidth: "100%" }} />}
        </td></tr>
      ) : null}
    </>
  );
}

function AddAttachment({ theme, items, rows, initialReplaces, onAdded }: { theme: Theme; items: Item[]; rows: Attachment[]; initialReplaces: string; onAdded: () => void }) {
  const { lang, db, name: who } = useApp();
  const [kind, setKind] = useState<"file" | "note" | "link">("file");
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [body, setBody] = useState("");
  const [url, setUrl] = useState("");
  const [stage, setStage] = useState("");
  const [item, setItem] = useState("");
  const [replaces, setReplaces] = useState(initialReplaces);
  const [status, setStatus] = useState("");
  const latest = editions(rows).map(g => g.latest);
  const submit = async () => {
    if (!who.trim()) return setStatus(T.needName[lang]);
    const nm = (name || file?.name || "").trim();
    if (!nm) return setStatus(T.attNeedName[lang]);
    const p: Record<string, unknown> = { kind, name: nm, description, stage: stage ? Number(stage) : null, item_id: item || null, replaces: replaces || null };
    try {
      if (kind === "file") {
        if (!file) return setStatus(T.attPickFile[lang]);
        if (file.size > MAX_BYTES) return setStatus(T.attTooBig[lang]);
        setStatus(T.attUploading[lang]);
        const path = `${theme.id}/${crypto.randomUUID()}/${storageName(file.name)}`;
        await db.upload(path, file, file.type || "application/octet-stream");
        p.path = path;
        p.checksum = await sha256(file);
      } else if (kind === "note") p.body = body;
      else p.url = url.trim();
      await db.addAttachment(theme.id, p, who.trim());
      setStatus(T.attAdded[lang]);
      setFile(null); setName(""); setDescription(""); setBody(""); setUrl(""); setStage(""); setItem(""); setReplaces("");
      onAdded();
    } catch (e) { setStatus(message(e, lang)); }
  };
  return (
    <form id="add-attachment" className="panel" aria-label={T.addAttachment[lang]} onSubmit={e => { e.preventDefault(); void submit(); }}>
      <h3>{T.addAttachment[lang]}</h3>
      <div className="fields">
        <Field label={T.attKind[lang]}><select value={kind} onChange={e => setKind(e.target.value as typeof kind)}>{(["file", "note", "link"] as const).map(k => <option key={k} value={k}>{t(`kind.${k}`, lang)}</option>)}</select></Field>
        {kind === "file" ? <Field label={T.attFile[lang]}><input type="file" onChange={e => { setFile(e.target.files?.[0] ?? null); }} /></Field> : null}
        <Field label={T.attName[lang]}><input value={name} maxLength={200} placeholder={file?.name ?? ""} onChange={e => setName(e.target.value)} /></Field>
        <Field label={T.attDescription[lang]}><input value={description} maxLength={1000} onChange={e => setDescription(e.target.value)} /></Field>
        {kind === "link" ? <Field label={T.attUrl[lang]}><input type="url" value={url} onChange={e => setUrl(e.target.value)} /></Field> : null}
        <Field label={T.attStage[lang]}><select value={stage} onChange={e => setStage(e.target.value)}><option value="">—</option>{STAGES.map(s => <option key={s} value={s}>{t(`stage.${s}`, lang)}</option>)}</select></Field>
        <Field label={T.attReplaces[lang]}><select value={replaces} onChange={e => setReplaces(e.target.value)}><option value="">—</option>{latest.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select></Field>
        {items.length ? <Field label={T.attItem[lang]}><select value={item} onChange={e => setItem(e.target.value)}><option value="">—</option>{items.map(i => <option key={i.id} value={i.id}>{i.title}</option>)}</select></Field> : null}
      </div>
      {kind === "note" ? <Field label={T.attNote[lang]}><textarea rows={6} value={body} maxLength={50000} onChange={e => setBody(e.target.value)} /></Field> : null}
      <p><button type="submit" className="btn primary">{T.attAdd[lang]}</button> <span className="note" role="status">{status}</span></p>
    </form>
  );
}

export { text };
