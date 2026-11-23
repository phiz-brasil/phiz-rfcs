/* Reads and writes the themes of the database through Supabase's REST API with the public key, as the RFC pages do. Reads are tables
   (row security shows only what is not hidden); writes are the functions of supabase/migrations/20261124000000_themes.sql. */
export type Supabase = { url: string; key: string };
export type I18n = Partial<Record<"pt" | "en" | "zh", string>>;

export type Front = { key: string; name: I18n; scope: I18n; ord: number; is_other: boolean };
export type Theme = {
  id: string; kind: "project" | "task"; front: string; title: I18n; owner: string | null; status: string; stage: number | null; route: string;
  what_it_is: I18n; progress: I18n; problem: I18n; solution: I18n; success: I18n; start_date: string | null; due_date: string | null;
  tags: string[]; resolution: string | null; created_at: string; created_by: string | null; updated_at: string;
};
export type Item = { id: string; theme_id: string; title: string; owner: string | null; col: string; due_date: string | null; milestone: boolean; created_at: string };
export type Link = { theme_id: string; to_theme: string; kind: string };
export type Jira = { id: string; theme_id: string; item_id: string | null; url: string; label: string | null; issue_key: string | null };
export type EventRow = { id: string; theme_id: string; item_id: string | null; at: string; edited_by: string; field: string; old_value: unknown; new_value: unknown };

export class DbError extends Error {
  constructor(message: string, readonly code: "rate" | "invalid" | "network" | "http") { super(message); }
}

export function client({ url, key }: Supabase) {
  const base = url.replace(/\/+$/, "") + "/rest/v1/";
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
    createTheme: (p: Record<string, unknown>, by: string) => rpc<{ id: string }>("create_theme", { p, p_by: by }),
    updateTheme: (id: string, p: Record<string, unknown>, by: string) => rpc("update_theme", { p_id: id, p, p_by: by }),
    updateFront: (key: string, p: Record<string, unknown>, by: string) => rpc("update_front", { p_key: key, p, p_by: by }),
    saveItem: (theme: string, item: string | null, p: Record<string, unknown>, by: string) => rpc("save_theme_item", { p_theme: theme, p_item: item, p, p_by: by }),
    addJira: (theme: string, item: string | null, url: string, label: string, by: string) =>
      rpc("add_theme_jira", { p_theme: theme, p_item: item, p_url: url, p_label: label || null, p_by: by }),
    removeJira: (id: string, by: string) => rpc("remove_theme_jira", { p_id: id, p_by: by }),
    setLink: (theme: string, to: string, kind: string, on: boolean, by: string) => rpc("set_theme_link", { p_theme: theme, p_to: to, p_kind: kind, p_on: on, p_by: by }),
  };
}
export type Db = ReturnType<typeof client>;
