/* Reads and writes the themes of the database through Supabase's REST API with the public key, as the RFC pages do. Reads are tables
   (row security shows only what is not hidden); writes are the functions of supabase/migrations/20261124000000_themes.sql. */
export type Supabase = { url: string; key: string };
export type I18n = Partial<Record<"pt" | "en" | "zh", string>>;

export type AnswerState = { state: "suggested" | "confirmed" | "missing"; by?: string; at?: string; sources?: { label: string; quote: string }[]; missing?: string };
export type Suggestion = { text: string | null; sources: { label: string; quote: string }[]; missing: string | null };
export type Front = { key: string; name: I18n; scope: I18n; ord: number; is_other: boolean };
export type Theme = {
  id: string; kind: "project" | "task"; front: string; title: I18n; owner: string | null; status: string; stage: number | null; route: string;
  what_it_is: I18n; progress: I18n; problem: I18n; solution: I18n; success: I18n; start_date: string | null; due_date: string | null;
  tags: string[]; resolution: string | null; board_column: string | null; created_at: string; created_by: string | null; updated_at: string;
  text_meta?: Record<string, string[]> | null;        // per text field, the languages that are machine translations
  answers?: Record<string, AnswerState> | null;       // state of the three slide answers (problem, solution, success)
};
export type StageGate = { key: string; stage: number; position: number; title: I18n; owner_role: string | null; non_waivable: boolean };
export type BoardColumn = { id: string; board: string; name: I18n; position: number; stage: number; wip_limit: number | null; created_at: string };
export type GateCheck = { theme_id: string; gate_key: string; evidence: string; checked_by: string; checked_at: string };
export type StageEvent = { theme_id: string; at: string; field: string; new_value: unknown };
export type Attachment = {
  id: string; theme_id: string; item_id: string | null; kind: "file" | "note" | "link"; name: string; description: string; storage_path: string | null;
  content_type: string | null; size: number | null; checksum: string | null; body: string | null; url: string | null; stage: number | null; replaces: string | null;
  archive_version: string | null; archive_date: string | null; archive_note: I18n | null; created_at: string; created_by: string;
};
export type Item = { id: string; theme_id: string; title: string; owner: string | null; col: string; start_date?: string | null; due_date: string | null; milestone: boolean; created_at: string };
export type Urgency = "urgent" | "important" | "info";
export type Update = {
  id: string; theme_id: string; week: string; edited_by: string; created_at: string; progress: I18n; advanced: I18n; next_step: I18n;
  status_from: string | null; status_to: string | null; due_from: string | null; due_to: string | null; due_reason: string | null;
  text_meta?: Record<string, string[]> | null;
};
export type Blocker = {
  id: string; theme_id: string; item_id: string | null; what: I18n; owner: string | null; due_date: string | null; needs_leadership: boolean; urgency?: Urgency | null;
  state: "open" | "resolved"; how_resolved: I18n; resolved_at: string | null; resolved_by: string | null; created_at: string; created_by: string;
  text_meta?: Record<string, string[]> | null;
};
export type Decision = {
  id: string; theme_id: string; item_id: string | null; what: I18n; decider: string | null; due_date: string | null; needs_leadership: boolean; urgency?: Urgency | null;
  state: "open" | "decided" | "dropped"; decision: I18n; decided_at: string | null; decided_by: string | null; created_at: string; created_by: string;
  text_meta?: Record<string, string[]> | null;
};
export type Milestone = { id: string; theme_id: string; title: string; due_date: string | null; col: string };
export type Link = { theme_id: string; to_theme: string; kind: string };
export type Jira = { id: string; theme_id: string; item_id: string | null; url: string; label: string | null; issue_key: string | null };
export type EventRow = { id: string; theme_id: string; item_id: string | null; at: string; edited_by: string; field: string; old_value: unknown; new_value: unknown };

/* The FUP (docs/spec/v2/fup.md): the meeting keeps only its agenda, the records made in it and, once closed, the snapshot */
export type FupKind = "inform" | "discuss" | "decide";
export type FupAgenda = { theme: string; kind: FupKind; on: boolean; star: boolean };
export type FupRecord = { theme: string; type: "note" | "decision" | "action"; text: string; progress: "todo" | "doing" | "done"; due?: string | null; ref?: string | null };
export type Fup = {
  id: string; title: string; held_on: string; agenda: FupAgenda[]; log: FupRecord[]; closed_at: string | null;
  snapshot: { agenda: FupAgenda[]; log: FupRecord[]; statuses: Record<string, string>; closed_by: string } | null; created_by: string; created_at: string; updated_at: string;
};

export class DbError extends Error {
  constructor(message: string, readonly code: "rate" | "invalid" | "network" | "http") { super(message); }
}

export function client({ url, key }: Supabase) {
  const base = url.replace(/\/+$/, "") + "/rest/v1/";
  const storage = url.replace(/\/+$/, "") + "/storage/v1/";
  const headers: Record<string, string> = { apikey: key, ...(/^eyJ/.test(key) ? { Authorization: "Bearer " + key } : {}) };
  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    let r: Response;
    try { r = await fetch(base + path, { ...init, headers: { ...headers, ...(init.headers as Record<string, string> | undefined) } }); }
    catch { throw new DbError("network", "network"); }
    if (r.status === 429) throw new DbError("rate limit", "rate");
    if (!r.ok) {
      let detail = "";
      try { detail = (await r.json()).message ?? ""; } catch { /* not JSON */ }
      throw new DbError(detail || `HTTP ${r.status}`, r.status === 400 ? "invalid" : "http");
    }
    return (r.status === 204 ? null : await r.json()) as T;
  }
  const rpc = <T = unknown>(fn: string, body: unknown) =>
    request<T>(`rpc/${fn}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const q = encodeURIComponent;
  /* Supabase returns at most 1000 rows a request: read a long list page by page (the order must be total, so pages do not overlap) */
  const all = async <T>(path: string): Promise<T[]> => {
    const out: T[] = [];
    for (let offset = 0; ; offset += 1000) {
      const page = await request<T[]>(`${path}&limit=1000&offset=${offset}`);
      out.push(...page);
      if (page.length < 1000) return out;
    }
  };
  return {
    fronts: () => request<Front[]>("fronts?select=*&order=ord"),
    themes: () => request<Theme[]>("themes?select=*&order=id.desc"),
    theme: async (id: string) => (await request<Theme[]>(`themes?select=*&id=eq.${q(id)}`))[0] ?? null,
    items: (id: string) => request<Item[]>(`theme_items?select=*&theme_id=eq.${q(id)}&order=created_at`),
    links: (id: string) => request<Link[]>(`theme_links?select=*&theme_id=eq.${q(id)}`),
    linksTo: (id: string) => request<Link[]>(`theme_links?select=*&to_theme=eq.${q(id)}`),
    jira: (id: string) => request<Jira[]>(`theme_jira?select=*&theme_id=eq.${q(id)}&order=created_at`),
    events: (id: string) => request<EventRow[]>(`theme_events?select=*&theme_id=eq.${q(id)}&order=at.desc&limit=40`),
    rfc: async (id: string) => (await request<{ rfc_id: string; version: string }[]>(`rfc_live_current?select=rfc_id,version&rfc_id=eq.${q(id)}`))[0] ?? null,
    titles: (ids: string[]) => request<{ id: string; title: I18n }[]>(`themes?select=id,title&id=in.(${ids.map(q).join(",")})`),
    updates: (id: string) => request<Update[]>(`theme_updates?select=*&theme_id=eq.${q(id)}&order=created_at.desc&limit=30`),
    blockers: (id: string) => request<Blocker[]>(`theme_blockers?select=*&theme_id=eq.${q(id)}&order=created_at.desc`),
    decisions: (id: string) => request<Decision[]>(`theme_decisions?select=*&theme_id=eq.${q(id)}&order=created_at.desc`),
    // slides: "Suggest with AI" is an Edge Function that only reads and answers; the page stores what the person keeps
    suggest: async (theme: string, by: string) => {
      let r: Response;
      try { r = await fetch(`${url.replace(/\/+$/, "")}/functions/v1/suggest-summary`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ theme, by }) }); }
      catch { throw new DbError("network", "network"); }
      if (r.status === 429) throw new DbError("rate limit", "rate");
      if (!r.ok) throw new DbError(`HTTP ${r.status}`, "http");
      return (await r.json()) as { suggestions: Record<"problem" | "solution" | "success", Suggestion>; sources: { id: string; label: string }[] };
    },
    // export: "Describe the material" is the Edge Function plan-deck, which only reads and answers with a deck plan (the page cleans it, lib/deck-plan.ts)
    planDeck: async (request: string, lang: string, by: string) => {
      let r: Response;
      try { r = await fetch(`${url.replace(/\/+$/, "")}/functions/v1/plan-deck`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ request, lang, by }) }); }
      catch { throw new DbError("network", "network"); }
      if (r.status === 429) throw new DbError("rate limit", "rate");
      if (!r.ok) throw new DbError(`HTTP ${r.status}`, "http");
      return ((await r.json()) as { plan?: unknown }).plan;
    },
    saveSuggestions: (theme: string, p: Record<string, Suggestion>, by: string) => rpc<{ applied: string[] }>("suggest_theme_answers", { p_theme: theme, p, p_by: by }),
    confirmAnswers: (theme: string, fields: string[], by: string) => rpc("confirm_theme_answers", { p_theme: theme, p_fields: fields, p_by: by }),
    themeSlideData: async (ids: string[]) => {
      const list = ids.map(q).join(",");
      const [themes, jira, fronts] = await Promise.all([request<Theme[]>(`themes?select=*&id=in.(${list})`), request<Jira[]>(`theme_jira?select=*&theme_id=in.(${list})&order=created_at`), request<Front[]>("fronts?select=*&order=ord")]);
      return { themes, jira, fronts };
    },
    // attachments: rows are tables; files go straight to Storage (private bucket) and are read through signed addresses that expire
    attachments: (id: string) => request<Attachment[]>(`attachments?select=*&theme_id=eq.${q(id)}&order=created_at.desc`),
    allAttachments: () => all<Attachment>("attachments?select=*&order=created_at.desc,id.asc"),
    rfcPictures: (id: string) => request<{ name: string; rev: number; mime: string; size: number }[]>(`rfc_assets?select=name,rev,mime,size&rfc_id=eq.${q(id)}&order=rev.desc`),
    addAttachment: (theme: string, p: Record<string, unknown>, by: string) => rpc<{ id: string }>("add_attachment", { p_theme: theme, p, p_by: by }),
    hideAttachment: (id: string, by: string) => rpc("hide_attachment", { p_id: id, p_by: by }),
    upload: async (path: string, file: Blob, type: string) => {
      let r: Response;
      try { r = await fetch(`${storage}object/attachments/${path.split("/").map(encodeURIComponent).join("/")}`, { method: "POST", headers: { ...headers, "Content-Type": type, "x-upsert": "false" }, body: file }); }
      catch { throw new DbError("network", "network"); }
      if (!r.ok) throw new DbError(`HTTP ${r.status}`, r.status === 413 ? "invalid" : "http");
    },
    /* a time-limited address; `download` makes the browser save the file instead of showing it (always used for HTML) */
    signedUrl: async (path: string, download?: string) => {
      const r = await request<{ signedURL: string }>(`../../storage/v1/object/sign/attachments/${path.split("/").map(encodeURIComponent).join("/")}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ expiresIn: 300 }) });
      const u = storage.replace(/\/$/, "") + (r.signedURL.startsWith("/") ? "" : "/") + r.signedURL;
      return download ? u + (u.includes("?") ? "&" : "?") + "download=" + encodeURIComponent(download) : u;
    },
    // flow metrics: the whole event log of the stage changes, resolutions and item moves, the blockers and the items
    metricEvents: () => all<EventRow>("theme_events?select=theme_id,item_id,at,field,old_value,new_value&field=in.(stage,move,resolution,item_col)&order=at.asc,id.asc"),
    allBlockers: () => all<{ theme_id: string; created_at: string; resolved_at: string | null }>("theme_blockers?select=theme_id,created_at,resolved_at&order=created_at.asc,id.asc"),
    allItems: () => all<{ id: string; theme_id: string; col: string; created_at: string }>("theme_items?select=id,theme_id,col,created_at&order=created_at.asc,id.asc"),
    // the B2B board
    gates: () => request<StageGate[]>("stage_gates?select=*&order=stage"),
    boardColumns: () => request<BoardColumn[]>("board_columns?select=*&order=position"),
    gateChecks: () => request<GateCheck[]>("theme_gate_checks?select=*"),
    themeGateChecks: (id: string) => request<GateCheck[]>(`theme_gate_checks?select=*&theme_id=eq.${q(id)}`),
    stageEvents: () => request<StageEvent[]>("theme_events?select=theme_id,at,field,new_value&field=in.(move,stage)&order=at.desc&limit=5000"),
    itemCols: () => request<{ theme_id: string; col: string }[]>("theme_items?select=theme_id,col&limit=5000"),
    jiraKeys: () => request<{ theme_id: string; issue_key: string | null }[]>("theme_jira?select=theme_id,issue_key&limit=5000"),
    moveCard: (theme: string, column: string, by: string, reason?: string) =>
      rpc<{ moved: boolean; open_gates?: string[] }>("move_theme_card", { p_theme: theme, p_column: column, p_by: by, p_reason: reason || null }),
    setGate: (theme: string, gate: string, evidence: string | null, by: string) => rpc("set_theme_gate", { p_theme: theme, p_gate: gate, p_evidence: evidence, p_by: by }),
    saveColumn: (id: string | null, p: Record<string, unknown>, by: string) => rpc("save_board_column", { p_id: id, p, p_by: by }),
    deleteColumn: (id: string, by: string) => rpc("delete_board_column", { p_id: id, p_by: by }),
    // for the executive view: what it needs across every theme
    updateWeeks: () => request<{ theme_id: string; week: string }[]>("theme_updates?select=theme_id,week&order=created_at.desc&limit=3000"),
    openBlockers: () => request<Blocker[]>("theme_blockers?select=*&state=eq.open&order=created_at"),
    openDecisions: () => request<Decision[]>("theme_decisions?select=*&state=eq.open&order=created_at"),
    milestones: () => request<Milestone[]>("theme_items?select=id,theme_id,title,due_date,col&milestone=eq.true&order=due_date"),
    // the Painel (docs/spec/v2/redesign.md): every delivery with its period, and the latest decisions taken
    deliveries: () => all<Item>("theme_items?select=*&order=created_at.asc,id.asc"),
    decided: () => request<Decision[]>("theme_decisions?select=*&state=eq.decided&order=decided_at.desc&limit=40"),
    postUpdate: (theme: string, p: Record<string, unknown>, by: string) => rpc<{ id: string; week: string }>("post_theme_update", { p_theme: theme, p, p_by: by }),
    saveBlocker: (theme: string, id: string | null, p: Record<string, unknown>, by: string) => rpc("save_theme_blocker", { p_theme: theme, p_id: id, p, p_by: by }),
    resolveBlocker: (id: string, how: I18n, by: string) => rpc("resolve_theme_blocker", { p_id: id, p_how: how, p_by: by }),
    saveDecision: (theme: string, id: string | null, p: Record<string, unknown>, by: string) => rpc("save_theme_decision", { p_theme: theme, p_id: id, p, p_by: by }),
    decideDecision: (id: string, state: "decided" | "dropped", decision: I18n, by: string) => rpc("decide_theme_decision", { p_id: id, p_state: state, p_decision: decision, p_by: by }),
    createTheme: (p: Record<string, unknown>, by: string) => rpc<{ id: string }>("create_theme", { p, p_by: by }),
    updateTheme: (id: string, p: Record<string, unknown>, by: string) => rpc("update_theme", { p_id: id, p, p_by: by }),
    updateFront: (key: string, p: Record<string, unknown>, by: string) => rpc("update_front", { p_key: key, p, p_by: by }),
    saveItem: (theme: string, item: string | null, p: Record<string, unknown>, by: string) => rpc("save_theme_item", { p_theme: theme, p_item: item, p, p_by: by }),
    addJira: (theme: string, item: string | null, url: string, label: string, by: string) =>
      rpc("add_theme_jira", { p_theme: theme, p_item: item, p_url: url, p_label: label || null, p_by: by }),
    removeJira: (id: string, by: string) => rpc("remove_theme_jira", { p_id: id, p_by: by }),
    setLink: (theme: string, to: string, kind: string, on: boolean, by: string) => rpc("set_theme_link", { p_theme: theme, p_to: to, p_kind: kind, p_on: on, p_by: by }),
    // the FUP
    fups: () => request<Fup[]>("fup_meetings?select=*&order=held_on.desc,created_at.desc&limit=200"),
    fup: async (id: string) => (await request<Fup[]>(`fup_meetings?select=*&id=eq.${q(id)}`))[0] ?? null,
    saveFup: (id: string | null, p: Record<string, unknown>, by: string) => rpc<{ id: string }>("save_fup", { p_id: id, p, p_by: by }),
    closeFup: (id: string, by: string) => rpc<{ id: string; updates: number }>("close_fup", { p_id: id, p_by: by }),
  };
}
export type Db = ReturnType<typeof client>;
