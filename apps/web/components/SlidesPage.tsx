"use client";
/* Pick themes (projects and standalone tasks) and download one .pptx with a slide each, in the language chosen here. A missing answer is written on the
   slide as "Not explained yet: …"; an AI suggestion nobody confirmed is marked as such. */
import { useCallback, useEffect, useMemo, useState } from "react";
import { STATUSES, T, t, text, type Lang } from "../lib/i18n";
import type { Front, Theme } from "../lib/db";
import { slideOf } from "../lib/slide-model";
import { buildPptx } from "../lib/slides";
import { useApp } from "./Shell";
import { ANSWERS, answerState } from "./Summary";
import { Said, StatusBadge, message } from "./ui";

export function SlidesPage() {
  const { lang, db } = useApp();
  const [data, setData] = useState<{ themes: Theme[]; fronts: Front[] } | null>(null);
  const [failed, setFailed] = useState(false);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [slideLang, setSlideLang] = useState<Lang | "">("");
  const [f, setF] = useState({ kind: "", front: "", status: "" });
  const [note, setNote] = useState("");
  const load = useCallback(async () => {
    try {
      const [themes, fronts] = await Promise.all([db.themes(), db.fronts()]);
      setData({ themes, fronts });
      const asked = new URLSearchParams(location.search).get("theme");
      if (asked && themes.some(x => x.id === asked)) setPicked(new Set([asked]));
      setFailed(false);
    } catch { setFailed(true); }
  }, [db]);
  useEffect(() => { void load(); }, [load]);
  const shown = useMemo(() => (data?.themes ?? []).filter(x => (!f.kind || x.kind === f.kind) && (!f.front || x.front === f.front) && (!f.status || x.status === f.status)), [data, f]);
  if (failed) return <p className="state err">{T.failed[lang]}</p>;
  if (!data) return <p className="state">{T.loading[lang]}</p>;
  const toggle = (id: string) => setPicked(p => { const n = new Set(p); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const out = (slideLang || lang) as Lang;
  const run = async () => {
    const ids = [...picked];
    if (!ids.length) return setNote(T.pickThemes[lang]);
    setNote(T.loading[lang]);
    try {
      const d = await db.themeSlideData(ids);
      const order = new Map(data.themes.map((x, i) => [x.id, i]));
      const slides = d.themes.sort((a, b) => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0)).map(x => slideOf(x, d.jira, d.fronts, out));
      await buildPptx(slides, out, `PHIZ-slides-${new Date().toISOString().slice(0, 10)}.pptx`);
      setNote(T.slidesReady[lang]);
    } catch (e) { setNote(message(e, lang)); }
  };
  return (
    <>
      <p className="eyebrow">{T.eyebrowPortfolio[lang]}</p>
      <h1>{T.slides[lang]}</h1>
      <p className="lead">{T.slidesLead[lang]}</p>
      <div className="bar">
        <div className="fields">
          <label className="field"><span>{T.slideLang[lang]}</span>
            <select value={slideLang} onChange={e => setSlideLang(e.target.value as Lang | "")}>
              <option value="">{lang === "pt" ? "PT-BR" : lang === "en" ? "EN-US" : "中文"}</option>
              {(["pt", "en", "zh"] as const).filter(l => l !== lang).map(l => <option key={l} value={l}>{l === "pt" ? "PT-BR" : l === "en" ? "EN-US" : "中文"}</option>)}
            </select></label>
          <label className="field"><span>{T.kind[lang]}</span>
            <select value={f.kind} onChange={e => setF({ ...f, kind: e.target.value })}><option value="">{T.all[lang]}</option><option value="project">{t("project", lang)}</option><option value="task">{t("task", lang)}</option></select></label>
          <label className="field"><span>{T.front[lang]}</span>
            <select value={f.front} onChange={e => setF({ ...f, front: e.target.value })}><option value="">{T.all[lang]}</option>{data.fronts.map(x => <option key={x.key} value={x.key}>{text(x.name, lang)}</option>)}</select></label>
          <label className="field"><span>{T.status[lang]}</span>
            <select value={f.status} onChange={e => setF({ ...f, status: e.target.value })}><option value="">{T.all[lang]}</option>{STATUSES.map(s => <option key={s} value={s}>{t(`status.${s}`, lang)}</option>)}</select></label>
        </div>
        <div className="actions">
          <button type="button" className="btn" onClick={() => setPicked(new Set([...picked, ...shown.map(x => x.id)]))}>{T.selectAll[lang]}</button>
          <button type="button" className="btn" onClick={() => setPicked(new Set())}>{T.clearAll[lang]}</button>
          <button type="button" className="btn primary" onClick={() => void run()}>{T.exportPptx[lang]} ({picked.size})</button>
        </div>
        <p className="note" role="status">{note}</p>
      </div>
      <ul className="list">
        {shown.map(x => (
          <li key={x.id} data-theme={x.id} className="card-li">
            <label className="card" style={{ display: "block", cursor: "pointer" }}>
              <div className="top">
                <input type="checkbox" aria-label={x.id} checked={picked.has(x.id)} onChange={() => toggle(x.id)} />
                <span className="id">{x.id}</span><span className="ver">{t(x.kind, lang)}</span><StatusBadge status={x.status} lang={lang} />
              </div>
              <h3><Said value={x.title} lang={lang} machine={x.text_meta?.title} /></h3>
              <div className="meta">
                {ANSWERS.map(a => { const st = answerState(x, a); return <span key={a} data-answer={a} data-state={st} className={st === "confirmed" ? "tag" : "flag"}>{a === "problem" ? "P" : a === "solution" ? "S" : "✓"} {st === "confirmed" ? T.stateConfirmed[lang] : st === "suggested" ? T.stateSuggested[lang] : st === "missing" ? T.stateMissing[lang] : T.stateEmpty[lang]}</span>; })}
              </div>
            </label>
          </li>
        ))}
      </ul>
    </>
  );
}
