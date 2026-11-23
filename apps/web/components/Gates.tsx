"use client";
/* The gate checklist of a project theme: the gates of its current stage and of the stages it passed on its route. A gate is ticked with an
   evidence; an open gate warns (a badge on the board card, a flag here) and never blocks a move. */
import { useCallback, useEffect, useState } from "react";
import { T, t, text } from "../lib/i18n";
import type { GateCheck, StageGate, Theme } from "../lib/db";
import { routeStages } from "../lib/board";
import { useApp } from "./Shell";
import { dateText, message } from "./ui";

export function Gates({ theme }: { theme: Theme }) {
  const { lang, db, name, reader } = useApp();
  const [gates, setGates] = useState<StageGate[] | null>(null);
  const [checks, setChecks] = useState<GateCheck[]>([]);
  const [note, setNote] = useState("");
  const load = useCallback(async () => {
    try { const [g, c] = await Promise.all([db.gates(), db.themeGateChecks(theme.id)]); setGates(g); setChecks(c); } catch { setNote(T.failed[lang]); }
  }, [db, theme.id, lang]);
  useEffect(() => { void load(); }, [load]);

  if (theme.stage == null) return null;
  const route = routeStages(theme.route);
  const stages = route.filter(s => s <= theme.stage!).reverse();       // current stage first
  const done = new Map(checks.map(c => [c.gate_key, c]));
  const change = async (gate: string, evidence: string | null) => {
    if (!name.trim()) return setNote(T.needName[lang]);
    if (evidence !== null && !evidence.trim()) return setNote(T.needEvidence[lang]);
    setNote(T.saving[lang]);
    try { await db.setGate(theme.id, gate, evidence, name.trim()); setNote(T.saved[lang]); await load(); } catch (e) { setNote(message(e, lang)); }
  };
  return (
    <section className="panel" aria-label={T.gates[lang]}>
      <h2>{T.gates[lang]}</h2>
      <p className="note">{T.gatesLead[lang]}</p>
      {gates === null ? <p className="state">{T.loading[lang]}</p> : stages.map(s => {
        const list = gates.filter(g => g.stage === s).sort((a, b) => a.position - b.position);
        return (
          <div key={s} data-stage={s}>
            <h3>{t(`stage.${s}`, lang)}</h3>
            {!list.length ? <p className="empty-line">{T.noStageGates[lang]}</p> : (
              <ul className="plain gates">
                {list.map(g => <GateRow key={g.key} gate={g} check={done.get(g.key)} passed={s < theme.stage!} readOnly={reader} onChange={change} />)}
              </ul>
            )}
          </div>
        );
      })}
      <p className="note" role="status">{note}</p>
    </section>
  );
}

function GateRow({ gate, check, passed, readOnly, onChange }: { gate: StageGate; check?: GateCheck; passed: boolean; readOnly: boolean;
  onChange: (gate: string, evidence: string | null) => void }) {
  const { lang } = useApp();
  const [evidence, setEvidence] = useState("");
  const title = text(gate.title, lang);
  return (
    <li className="gate" data-gate={gate.key} data-done={check ? "1" : "0"}>
      <div className="top">
        <span aria-hidden="true">{check ? "✔" : "○"}</span>
        <strong>{title}</strong>
        {gate.non_waivable ? <span className="flag lead">{T.nonWaivable[lang]}</span> : null}
        {!check && passed ? <span className="flag">{T.passedOpen[lang]}</span> : null}
      </div>
      {check ? (
        <p className="note">{T.evidence[lang]}: {check.evidence} · {check.checked_by} · {dateText(check.checked_at)}{" "}
          {!readOnly ? <button type="button" className="mini" onClick={() => onChange(gate.key, null)}>{T.unmark[lang]}</button> : null}</p>
      ) : !readOnly ? (
        <div className="inline">
          <input aria-label={`${T.evidence[lang]}: ${title}`} value={evidence} maxLength={500} placeholder={T.evidence[lang]} onChange={e => setEvidence(e.target.value)} />
          <button type="button" className="btn" onClick={() => { onChange(gate.key, evidence); setEvidence(""); }}>{T.mark[lang]}</button>
        </div>
      ) : null}
    </li>
  );
}
