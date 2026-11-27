"use client";
/* The export (docs/spec/v2/redesign.md, What PR 3 delivers), in two modes:
   - Choose themes: pick themes (projects and standalone tasks) and download one .pptx with a slide each, in the language chosen here. A missing answer
     is written on the slide as "Not explained yet: …"; an AI suggestion nobody confirmed is marked as such (docs/spec/v2/slides.md).
   - Describe the material: a sentence goes to the Edge Function plan-deck, whose plan is cleaned (lib/deck-plan.ts) and shown as a preview; the theme
     slides, numbers and dates come from the database. Both modes can send the deck to Google Slides when the company's client id is set. */
import { useCallback, useEffect, useMemo, useState } from "react";
import { STATUSES, T, t, text, type Lang } from "../lib/i18n";
import type { Front, Theme } from "../lib/db";
import { slideOf, type Slide } from "../lib/slide-model";
import { buildPlanPptx, buildPptx } from "../lib/slides";
import { cleanPlan, planThemeIds, type Cleaned, type PlanSlide } from "../lib/deck-plan";
import { googleClientId, toGoogleSlides } from "../lib/google";
import { useApp } from "./Shell";
import { ANSWERS, answerState } from "./Summary";
import { Said, StatusBadge, message } from "./ui";

const LANG_NAME: Record<Lang, string> = { pt: "PT-BR", en: "EN-US", zh: "中文" };
const today = () => new Date().toISOString().slice(0, 10);

/* Opens the tab first (a tab opened after waiting for the upload would be blocked), then sends the deck and points the tab at it. */
async function sendToGoogle(clientId: string, make: () => Promise<Blob>, fileName: string, say: (s: string) => void, lang: Lang) {
  const tab = window.open("about:blank", "_blank");
  say(T.googleWorking[lang]);
  try {
    const address = await toGoogleSlides(clientId, await make(), fileName);
    if (tab) tab.location.href = address; else window.open(address, "_blank");
    say(T.googleDone[lang]);
  } catch {
    tab?.close();
    say(T.googleFailed[lang]);
  }
}

export function SlidesPage({ googleClientId: fromConfig = "" }: { googleClientId?: string }) {
  const { lang, db } = useApp();
  const [data, setData] = useState<{ themes: Theme[]; fronts: Front[] } | null>(null);
  const [failed, setFailed] = useState(false);
  const [mode, setMode] = useState<"pick" | "describe">("pick");
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [slideLang, setSlideLang] = useState<Lang | "">("");
  const [deck, setDeck] = useState(false);
  const [f, setF] = useState({ kind: "", front: "", status: "" });
  const [note, setNote] = useState("");
  const [clientId, setClientId] = useState("");
  useEffect(() => { setClientId(googleClientId(fromConfig)); }, [fromConfig]);
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
  const fileName = `PHIZ-slides-${today()}.pptx`;
  const pickedSlides = async () => {
    const d = await db.themeSlideData([...picked]);
    const order = new Map(data.themes.map((x, i) => [x.id, i]));
    return d.themes.sort((a, b) => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0)).map(x => slideOf(x, d.jira, d.fronts, out));
  };
  const run = async () => {
    if (!picked.size) return setNote(T.pickThemes[lang]);
    setNote(T.loading[lang]);
    try {
      await buildPptx(await pickedSlides(), out, fileName, { deck });
      setNote(T.slidesReady[lang]);
    } catch (e) { setNote(message(e, lang)); }
  };
  const google = () => {
    if (!picked.size) return setNote(T.pickThemes[lang]);
    void sendToGoogle(clientId, async () => (await buildPptx(await pickedSlides(), out, fileName, { deck, output: "blob" })) as Blob, fileName, setNote, lang);
  };
  const langSelect = (
    <label className="field"><span>{T.slideLang[lang]}</span>
      <select value={slideLang} onChange={e => setSlideLang(e.target.value as Lang | "")}>
        <option value="">{LANG_NAME[lang]}</option>
        {(["pt", "en", "zh"] as const).filter(l => l !== lang).map(l => <option key={l} value={l}>{LANG_NAME[l]}</option>)}
      </select></label>
  );
  return (
    <>
      <p className="eyebrow">{T.eyebrowPortfolio[lang]}</p>
      <h1>{T.slides[lang]}</h1>
      <div className="seg export-modes" role="group" aria-label={T.exportModes[lang]}>
        <button type="button" aria-pressed={mode === "pick"} onClick={() => { setMode("pick"); setNote(""); }}>{T.modePick[lang]}</button>
        <button type="button" aria-pressed={mode === "describe"} onClick={() => { setMode("describe"); setNote(""); }}>{T.modeDescribe[lang]}</button>
      </div>
      {mode === "describe" ? <Describe themes={data.themes} out={out} langSelect={langSelect} clientId={clientId} /> : <>
      <p className="lead">{T.slidesLead[lang]}</p>
      <div className="bar">
        <div className="fields">
          {langSelect}
          <label className="field"><span>{T.slidesDeck[lang]}</span>
            <input type="checkbox" checked={deck} onChange={e => setDeck(e.target.checked)} /></label>
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
          {clientId ? <button type="button" className="btn" onClick={google}>{T.toGoogle[lang]}</button> : null}
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
      </>}
    </>
  );
}

/* "Describe the material": the request goes to plan-deck; only what is traced to an active theme is shown and exported. */
function Describe({ themes, out, langSelect, clientId }: { themes: Theme[]; out: Lang; langSelect: React.ReactNode; clientId: string }) {
  const { lang, db, name } = useApp();
  const [request, setRequest] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [got, setGot] = useState<Cleaned | null>(null);
  const active = useMemo(() => themes.filter(x => x.status !== "done" && x.status !== "cancelled"), [themes]);
  const byId = useMemo(() => new Map(themes.map(x => [x.id, x])), [themes]);
  const title = (id: string) => `${id} · ${text(byId.get(id)?.title, lang) || id}`;
  const fileName = `PHIZ-material-${today()}.pptx`;

  const build = async () => {
    if (!request.trim()) return setNote(T.needRequest[lang]);
    setBusy(true); setGot(null); setNote(T.planning[lang]);
    try {
      const c = cleanPlan(await db.planDeck(request.trim(), out, name.trim()), active.map(x => x.id));
      if (!c.plan.slides.length) setNote(T.planEmpty[lang]);
      else { setGot(c); setNote(""); }
    } catch (e) { setNote(e instanceof Error && /rate/.test(e.message) ? message(e, lang) : T.planFailed[lang]); }
    finally { setBusy(false); }
  };
  const deck = async (output: "file" | "blob") => {
    if (!got) return;
    const ids = planThemeIds(got.plan);
    const d = ids.length ? await db.themeSlideData(ids) : { themes: [], jira: [], fronts: [] };
    const slides = new Map<string, Slide>(d.themes.map(x => [x.id, slideOf(x, d.jira, d.fronts, out)]));
    const starts = new Map(d.themes.map(x => [x.id, x.start_date ? x.start_date.slice(0, 10) : ""]));
    return buildPlanPptx(got.plan, { slides, starts }, out, fileName, { output });
  };
  const download = async () => {
    setNote(T.loading[lang]);
    try { await deck("file"); setNote(T.slidesReady[lang]); } catch (e) { setNote(message(e, lang)); }
  };
  const detail = (s: PlanSlide) => {
    switch (s.kind) {
      case "cover": return s.subtitle ? <p className="note">{s.subtitle}</p> : null;
      case "theme": return null;
      case "numbers": case "roadmap": return <p className="note">{s.themes.map(title).join(" · ")}</p>;
      default: return <ul>{s.items.map((i, k) => <li key={k} data-theme={i.theme}><b>{title(i.theme)}</b>: {i.text}</li>)}</ul>;
    }
  };
  const heading = (s: PlanSlide) => (s.kind === "theme" ? title(s.theme) : s.title || t(`kindDeck.${s.kind}`, lang));
  return (
    <>
      <p className="lead">{T.describeLead[lang]}</p>
      <div className="bar describe">
        <label className="field wide"><span>{T.describeLabel[lang]}</span>
          <textarea rows={3} maxLength={600} value={request} placeholder={T.describeHint[lang]} onChange={e => setRequest(e.target.value)} /></label>
        <div className="fields">{langSelect}</div>
        <div className="actions">
          <button type="button" className="btn primary" disabled={busy} onClick={() => void build()}>{T.makePreview[lang]}</button>
        </div>
        <p className="note" role="status">{note}</p>
      </div>
      {got ? (
        <section className="deck-preview" aria-label={T.preview[lang]}>
          <h2>{T.preview[lang]}{got.plan.title ? <span className="note"> · {got.plan.title}</span> : null}</h2>
          {got.dropped ? <p className="note" data-dropped={got.dropped}>{got.dropped} {T.droppedN[lang]}</p> : null}
          <ol className="deck-slides">
            {got.plan.slides.map((s, i) => (
              <li key={i} data-kind={s.kind} data-theme={s.kind === "theme" ? s.theme : undefined}>
                <span className="deck-kind">{t(`kindDeck.${s.kind}`, lang)}</span>
                <strong>{heading(s)}</strong>
                {detail(s)}
              </li>
            ))}
          </ol>
          <div className="actions">
            <button type="button" className="btn primary" onClick={() => void download()}>{T.downloadPptx[lang]}</button>
            {clientId ? <button type="button" className="btn" onClick={() => void sendToGoogle(clientId, async () => (await deck("blob")) as Blob, fileName, setNote, lang)}>{T.toGoogle[lang]}</button> : null}
          </div>
        </section>
      ) : null}
    </>
  );
}
