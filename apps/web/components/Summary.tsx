"use client";
/* The three answers that go on the executive slide (problem, solution, success), each with a state: missing, suggested by the AI (not confirmed) or
   confirmed by a person, plus the sources of a suggestion. "Suggest with AI" asks the Edge Function, which only answers from the theme's documents and
   quotes them; the page stores what came back (never over a confirmed answer: the database refuses) and a person confirms. Editing the text in the form
   above confirms it too. */
import { useState } from "react";
import { T, text } from "../lib/i18n";
import { DbError, type AnswerState, type Theme } from "../lib/db";
import { useApp } from "./Shell";
import { Said, dateText, message } from "./ui";

export const ANSWERS = ["problem", "solution", "success"] as const;
const QUESTION = { problem: "qProblem", solution: "qSolution", success: "qSuccess" } as const;

export function answerState(theme: Theme, f: (typeof ANSWERS)[number]): AnswerState["state"] | "empty" {
  const a = theme.answers?.[f];
  if (a) return a.state;
  return text(theme[f], "pt") || text(theme[f], "en") || text(theme[f], "zh") ? "confirmed" : "empty";        // a text a person wrote before states existed counts as confirmed
}

export function Summary({ theme, onChanged }: { theme: Theme; onChanged: () => void }) {
  const { lang, db, name, reader } = useApp();
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  if (theme.kind !== "project" && theme.kind !== "task") return null;
  const suggest = async () => {
    if (!name.trim()) return setNote(T.needName[lang]);
    setBusy(true);
    setNote(T.suggesting[lang]);
    try {
      const r = await db.suggest(theme.id, name.trim());
      await db.saveSuggestions(theme.id, r.suggestions, name.trim());
      setNote(T.suggestDone[lang]);
      onChanged();
    } catch (e) { setNote(e instanceof DbError && e.code === "rate" ? T.suggestLimit[lang] : e instanceof DbError && e.code === "http" ? T.suggestFailed[lang] : message(e, lang)); }
    setBusy(false);
  };
  const confirm = async (f: string) => {
    if (!name.trim()) return setNote(T.needName[lang]);
    try { await db.confirmAnswers(theme.id, [f], name.trim()); onChanged(); } catch (e) { setNote(message(e, lang)); }
  };
  return (
    <section className="panel" aria-label={T.summary[lang]} id="summary">
      <h2>{T.summary[lang]}</h2>
      <p className="note">{T.summaryLead[lang]}</p>
      {ANSWERS.map(f => {
        const st = answerState(theme, f);
        const a = theme.answers?.[f];
        return (
          <div className="row" key={f} data-answer={f} data-state={st}>
            <strong>{T[QUESTION[f]][lang]}</strong>
            <span className={st === "confirmed" ? "badge" : "flag"} data-s={st === "confirmed" ? "on_track" : undefined}>
              {st === "confirmed" ? T.stateConfirmed[lang] : st === "suggested" ? T.stateSuggested[lang] : st === "missing" ? T.stateMissing[lang] : T.stateEmpty[lang]}
            </span>
            {st === "empty" || st === "missing" ? (
              <p className="empty-line" data-k="missing">{T.notExplained[lang]}{a?.missing ? `: ${a.missing}` : ""}</p>
            ) : <p data-k="text"><Said value={theme[f]} lang={lang} machine={theme.text_meta?.[f]} /></p>}
            {st === "confirmed" && a?.by ? <p className="note">{T.confirmed[lang]} {a.by} · {dateText(a.at ?? null)}</p> : null}
            {a?.sources?.length ? (
              <details><summary>{T.sourcesOf[lang]} ({a.sources.length})</summary>
                <ul className="plain">{a.sources.map((s, i) => <li key={i} data-source><strong>{s.label}</strong> — “{s.quote}”</li>)}</ul></details>
            ) : null}
            {!reader && st === "suggested" ? <p><button type="button" className="btn" onClick={() => void confirm(f)}>{T.confirm[lang]}</button></p> : null}
          </div>
        );
      })}
      {!reader ? <p><button type="button" className="btn primary" disabled={busy} onClick={() => void suggest()}>{T.suggestAi[lang]}</button> <span className="note" role="status">{note}</span></p> : null}
      <p><a href={`/slides/?theme=${theme.id}`}>{T.exportPptx[lang]}</a></p>
    </section>
  );
}
