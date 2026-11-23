"use client";
/* The B2B board: the project themes of every front on the columns of the board (each column maps to one V4 stage), a swimlane per front.
   A card moves by drag or by its "Move to" menu (keyboard and phone); open gates warn and never block. */
import { useCallback, useEffect, useMemo, useState } from "react";
import { STAGES, STATUSES, T, t, text } from "../lib/i18n";
import { DbError, type Blocker, type BoardColumn, type Decision, type Front, type GateCheck, type StageEvent, type StageGate, type Theme } from "../lib/db";
import { currentColumn, daysSince, needsReason, openGates, sortedColumns, stageSince } from "../lib/board";
import { useApp } from "./Shell";
import { Field, Said, StatusBadge, message } from "./ui";

type Data = { fronts: Front[]; themes: Theme[]; columns: BoardColumn[]; gates: StageGate[]; checks: GateCheck[]; events: StageEvent[];
  items: { theme_id: string; col: string }[]; jira: { theme_id: string; issue_key: string | null }[]; blockers: Blocker[]; decisions: Decision[] };

export function BoardPage() {
  const { lang, db, name, reader } = useApp();
  const [data, setData] = useState<Data | null>(null);
  const [failed, setFailed] = useState(false);
  const [note, setNote] = useState("");
  const [pending, setPending] = useState<{ theme: Theme; col: BoardColumn } | null>(null);
  const [reason, setReason] = useState("");
  const [configuring, setConfiguring] = useState(false);
  const [f, setF] = useState({ front: "all", tag: "all", owner: "", status: "all", blocked: false, aging: 0 });

  const load = useCallback(async () => {
    try {
      const [fronts, themes, columns, gates, checks, events, items, jira, blockers, decisions] =
        await Promise.all([db.fronts(), db.themes(), db.boardColumns(), db.gates(), db.gateChecks(), db.stageEvents(), db.itemCols(), db.jiraKeys(), db.openBlockers(), db.openDecisions()]);
      setData({ fronts, themes, columns, gates, checks, events, items, jira, blockers, decisions });
      setFailed(false);
    } catch { setFailed(true); }
  }, [db]);
  useEffect(() => { void load(); }, [load]);

  const cards = useMemo(() => (data?.themes ?? []).filter(x => x.kind === "project" && !x.resolution && x.stage != null), [data]);
  const cols = useMemo(() => sortedColumns(data?.columns ?? []), [data]);
  const colOf = useCallback((th: Theme) => (data ? currentColumn(th, data.columns) : undefined), [data]);
  const blockedIds = useMemo(() => new Set((data?.blockers ?? []).map(b => b.theme_id)), [data]);
  const tags = useMemo(() => [...new Set(cards.flatMap(x => x.tags))].sort(), [cards]);
  const shown = useMemo(() => {
    if (!data) return [];
    const now = Date.now();
    return cards.filter(x =>
      (f.front === "all" || x.front === f.front) && (f.tag === "all" || x.tags.includes(f.tag)) && (f.status === "all" || x.status === f.status) &&
      (!f.owner.trim() || (x.owner ?? "").toLowerCase().includes(f.owner.trim().toLowerCase())) && (!f.blocked || blockedIds.has(x.id)) &&
      (!f.aging || daysSince(stageSince(x, data.events), now) > f.aging));
  }, [cards, data, f, blockedIds]);

  const send = async (theme: Theme, col: BoardColumn, why: string) => {
    if (!name.trim()) return setNote(T.needName[lang]);
    setNote(T.saving[lang]);
    try {
      const r = await db.moveCard(theme.id, col.id, name.trim(), why.trim());
      setPending(null);
      setReason("");
      await load();
      setNote(r.open_gates?.length ? `${T.movedOpen[lang]} ${r.open_gates.length}` : T.moved[lang]);
    } catch (e) { setNote(e instanceof DbError && e.code === "invalid" && /reason/.test(e.message) ? T.skipReason[lang] : message(e, lang)); }
  };
  const request = (theme: Theme, col: BoardColumn) => {
    if (colOf(theme)?.id === col.id) return;
    if (needsReason(theme, col)) { setPending({ theme, col }); setReason(""); setNote(""); } else void send(theme, col, "");
  };

  if (failed) return <p className="state err">{T.failed[lang]}</p>;
  if (!data) return <p className="state">{T.loading[lang]}</p>;
  const lanes = data.fronts.filter(fr => f.front === "all" || fr.key === f.front);
  const count = (c: BoardColumn) => cards.filter(x => colOf(x)?.id === c.id).length;

  return (
    <>
      <p className="eyebrow">{T.eyebrowTrack[lang]}</p>
      <h1>{T.board[lang]}</h1>
      <p className="lead">{T.boardLead[lang]}</p>
      <div className="bar">
        <div className="fields">
          <Field label={T.front[lang]}>
            <select value={f.front} onChange={e => setF({ ...f, front: e.target.value })}>
              <option value="all">{T.all[lang]}</option>{data.fronts.map(x => <option key={x.key} value={x.key}>{text(x.name, lang)}</option>)}
            </select>
          </Field>
          <Field label={T.tagFilter[lang]}>
            <select value={f.tag} onChange={e => setF({ ...f, tag: e.target.value })}>
              <option value="all">{T.all[lang]}</option>{tags.map(x => <option key={x} value={x}>#{x}</option>)}
            </select>
          </Field>
          <Field label={T.owner[lang]}><input value={f.owner} onChange={e => setF({ ...f, owner: e.target.value })} /></Field>
          <Field label={T.status[lang]}>
            <select value={f.status} onChange={e => setF({ ...f, status: e.target.value })}>
              <option value="all">{T.all[lang]}</option>{STATUSES.map(s => <option key={s} value={s}>{t(`status.${s}`, lang)}</option>)}
            </select>
          </Field>
          <Field label={T.aging[lang]}>
            <select value={f.aging} onChange={e => setF({ ...f, aging: Number(e.target.value) })}>
              <option value={0}>{T.anyAge[lang]}</option>{[7, 14, 30].map(n => <option key={n} value={n}>{n} {T.daysUnit[lang]}</option>)}
            </select>
          </Field>
        </div>
        <label className="checks"><input type="checkbox" checked={f.blocked} onChange={e => setF({ ...f, blocked: e.target.checked })} /> {T.onlyBlocked[lang]}</label>
        {!reader ? <div className="actions"><button type="button" className="btn" onClick={() => setConfiguring(c => !c)}>{configuring ? T.doneConfig[lang] : T.configColumns[lang]}</button></div> : null}
      </div>
      {configuring && !reader ? <ColumnsEditor columns={cols} onChanged={load} /> : null}
      {pending ? (
        <form className="panel" aria-label={T.skipReason[lang]} onSubmit={e => { e.preventDefault(); if (reason.trim()) void send(pending.theme, pending.col, reason); }}>
          <p><strong>{pending.theme.id}</strong> → {text(pending.col.name, lang)}</p>
          <Field label={T.skipReason[lang]}><input value={reason} maxLength={300} onChange={e => setReason(e.target.value)} /></Field>
          <p><button type="submit" className="btn primary" disabled={!reason.trim()}>{T.confirmMove[lang]}</button> <button type="button" className="btn" onClick={() => setPending(null)}>{T.cancel[lang]}</button></p>
        </form>
      ) : null}
      <p className="note" role="status">{note}</p>
      <div className="boardwrap">
        <div className="board" role="table" aria-label={T.board[lang]} style={{ gridTemplateColumns: `repeat(${cols.length}, 250px)` }}>
          {cols.map(c => {
            const n = count(c);
            return (
              <div className="bhead" role="columnheader" key={c.id} data-column={c.id} data-over={c.wip_limit != null && n > c.wip_limit ? "1" : "0"}>
                <strong>{text(c.name, lang)}</strong>
                <span className="note">{n}{c.wip_limit != null ? ` / ${c.wip_limit}` : ""}{c.wip_limit != null ? ` (${T.wipLimit[lang]})` : ""}</span>
              </div>
            );
          })}
          {lanes.map(fr => {
            const mine = shown.filter(x => x.front === fr.key);
            if (!cards.some(x => x.front === fr.key)) return null;
            return (
              <Lane key={fr.key} front={fr} cols={cols}>
                {cols.map(c => (
                  <div className="cell" role="cell" key={c.id} data-column={c.id}
                    onDragOver={e => { if (!reader) e.preventDefault(); }}
                    onDrop={e => {
                      if (reader) return;
                      e.preventDefault();
                      const th = cards.find(x => x.id === e.dataTransfer.getData("text/plain"));
                      if (th) request(th, c);
                    }}>
                    {mine.filter(x => colOf(x)?.id === c.id).map(x => (
                      <Card key={x.id} theme={x} data={data} cols={cols} onMove={request} />
                    ))}
                  </div>
                ))}
              </Lane>
            );
          })}
        </div>
      </div>
      {!shown.length ? <p className="empty">{T.noProjects[lang]}</p> : null}
    </>
  );
}

function Lane({ front, cols, children }: { front: Front; cols: BoardColumn[]; children: React.ReactNode }) {
  const { lang } = useApp();
  return (
    <>
      <div className="lane" role="row" style={{ gridColumn: `1 / ${cols.length + 1}` }} data-front={front.key}><h2>{text(front.name, lang)}</h2></div>
      {children}
    </>
  );
}

function Card({ theme, data, cols, onMove }: { theme: Theme; data: Data; cols: BoardColumn[]; onMove: (th: Theme, c: BoardColumn) => void }) {
  const { lang, reader } = useApp();
  const open = openGates(theme, data.gates, data.checks);
  const items = data.items.filter(i => i.theme_id === theme.id);
  const keys = data.jira.filter(j => j.theme_id === theme.id).map(j => j.issue_key).filter(Boolean) as string[];
  const hasJira = data.jira.some(j => j.theme_id === theme.id);
  const nb = data.blockers.filter(b => b.theme_id === theme.id).length;
  const nd = data.decisions.filter(d => d.theme_id === theme.id).length;
  const days = daysSince(stageSince(theme, data.events));
  const cur = currentColumn(theme, data.columns);
  const red = open.some(g => g.non_waivable);
  return (
    <article className="kcard" data-theme={theme.id} draggable={!reader} onDragStart={e => e.dataTransfer.setData("text/plain", theme.id)}>
      <div className="top"><a className="id" href={`/themes/${theme.id}/`}>{theme.id}</a><StatusBadge status={theme.status} lang={lang} /></div>
      <a className="ktitle" href={`/themes/${theme.id}/`}><Said value={theme.title} lang={lang} machine={theme.text_meta?.title} /></a>
      <div className="meta">
        <span>{theme.owner ?? "—"}</span>
        <span>{days} {T.daysIn[lang]}</span>
        {items.length ? <span>{items.filter(i => i.col === "done").length}/{items.length} {T.itemsDone[lang]}</span> : null}
        {keys.map(k => <span className="jira" key={k}>{k}</span>)}
      </div>
      <div className="flags">
        {open.length ? <span className={red ? "flag lead" : "flag"} data-flag="gates">{open.length} {T.gatesOpen[lang]} · {t(`stage.${theme.stage}`, lang).slice(0, 2)}</span> : null}
        {nb ? <span className="flag lead" data-flag="blockers">{nb} {T.openBlockers[lang]}</span> : null}
        {nd ? <span className="flag" data-flag="decisions">{nd} {T.openDecisions[lang]}</span> : null}
        {theme.stage! >= 4 && !hasJira ? <span className="flag" data-flag="jira">{T.noJira[lang]}</span> : null}
      </div>
      {!reader ? (
        <label className="moveto"><span>{T.moveTo[lang]}</span>
          <select aria-label={`${T.moveTo[lang]} ${theme.id}`} value={cur?.id ?? ""} onChange={e => { const c = cols.find(x => x.id === e.target.value); if (c) onMove(theme, c); }}>
            {cols.map(c => <option key={c.id} value={c.id}>{text(c.name, lang)}</option>)}
          </select>
        </label>
      ) : null}
    </article>
  );
}

function ColumnsEditor({ columns, onChanged }: { columns: BoardColumn[]; onChanged: () => void }) {
  const { lang, db, name } = useApp();
  const [note, setNote] = useState("");
  const guard = async (fn: () => Promise<unknown>) => {
    if (!name.trim()) return setNote(T.needName[lang]);
    setNote(T.saving[lang]);
    try { await fn(); setNote(T.saved[lang]); onChanged(); } catch (e) { setNote(e instanceof DbError && /in use/.test(e.message) ? T.stageInUse[lang] : message(e, lang)); }
  };
  const renumber = (order: BoardColumn[]) => guard(async () => {
    for (const [i, c] of order.entries()) if (c.position !== i + 1) await db.saveColumn(c.id, { position: i + 1 }, name.trim());
  });
  const swap = (i: number, d: number) => {
    const next = [...columns];
    [next[i], next[i + d]] = [next[i + d], next[i]];
    void renumber(next);
  };
  return (
    <section className="panel" aria-label={T.configColumns[lang]}>
      <h2>{T.configColumns[lang]}</h2>
      <p className="note">{T.columnsLead[lang]}</p>
      {columns.map((c, i) => (
        <ColumnForm key={c.id + JSON.stringify(c.name) + c.stage + c.wip_limit} column={c} index={i} last={i === columns.length - 1}
          onSave={p => guard(() => db.saveColumn(c.id, p, name.trim()))} onDelete={() => guard(() => db.deleteColumn(c.id, name.trim()))}
          onUp={() => swap(i, -1)} onDown={() => swap(i, 1)} />
      ))}
      <ColumnForm column={null} index={columns.length} last onSave={p => guard(() => db.saveColumn(null, p, name.trim()))} />
      <p className="note" role="status">{note}</p>
    </section>
  );
}

function ColumnForm({ column, index, last, onSave, onDelete, onUp, onDown }: { column: BoardColumn | null; index: number; last: boolean;
  onSave: (p: Record<string, unknown>) => void; onDelete?: () => void; onUp?: () => void; onDown?: () => void }) {
  const { lang } = useApp();
  const [nm, setNm] = useState(column?.name ?? {});
  const [stage, setStage] = useState(String(column?.stage ?? 1));
  const [wip, setWip] = useState(column?.wip_limit != null ? String(column.wip_limit) : "");
  const label = column ? `${T.columnName[lang]} ${index + 1}` : T.addColumn[lang];
  return (
    <form className="panel" aria-label={label} onSubmit={e => { e.preventDefault(); onSave({ name: nm, stage: Number(stage), wip_limit: wip.trim() ? Number(wip) : null }); if (!column) setNm({}); }}>
      <div className="fields">
        {(["pt", "en", "zh"] as const).map(l => (
          <Field key={l} label={`${T.columnName[lang]} (${l.toUpperCase()})`}><input value={nm[l] ?? ""} maxLength={60} onChange={e => setNm({ ...nm, [l]: e.target.value })} /></Field>
        ))}
        <Field label={T.columnStage[lang]}><select value={stage} onChange={e => setStage(e.target.value)}>{STAGES.map(s => <option key={s} value={s}>{t(`stage.${s}`, lang)}</option>)}</select></Field>
        <Field label={T.columnWip[lang]}><input type="number" min={1} max={999} value={wip} onChange={e => setWip(e.target.value)} /></Field>
      </div>
      <p>
        <button type="submit" className="btn primary">{column ? T.save[lang] : T.create[lang]}</button>{" "}
        {column ? <>
          <button type="button" className="btn" disabled={index === 0} onClick={onUp}>{T.up[lang]}</button>{" "}
          <button type="button" className="btn" disabled={last} onClick={onDown}>{T.down[lang]}</button>{" "}
          <button type="button" className="btn" onClick={onDelete}>{T.remove[lang]}</button>
        </> : null}
      </p>
    </form>
  );
}
