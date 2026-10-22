/* Reads and writes the RFCs that people create on the site (tables and functions of
   supabase/migrations/20261022000000_live_rfcs.sql) through Supabase's REST API with the public key. */
const cfg = (window.PHIZ_SITE || {}).comments || {};
const base = (cfg.supabaseUrl || "").replace(/\/+$/, "") + "/rest/v1/";
const headers = Object.assign({ apikey: cfg.supabaseKey || "" }, /^eyJ/.test(cfg.supabaseKey || "") ? { Authorization: "Bearer " + cfg.supabaseKey } : {});

export const enabled = !!(cfg.supabaseUrl && cfg.supabaseKey);

export class LiveError extends Error {
  constructor(message, code) { super(message); this.code = code; }
}

async function request(path, opts = {}) {
  let r;
  try { r = await fetch(base + path, Object.assign({}, opts, { headers: Object.assign({}, headers, opts.headers || {}) })); }
  catch (e) { throw new LiveError("network", "network"); }
  if (r.status === 429) throw new LiveError("rate limit", "rate");
  if (!r.ok) {
    let detail = "";
    try { detail = (await r.json()).message || ""; } catch (e) { /* not JSON */ }
    throw new LiveError(detail || `HTTP ${r.status}`, r.status === 400 ? "invalid" : "http");
  }
  return r.status === 204 ? null : r.json();
}

const q = s => encodeURIComponent(s);

export const listLive = () => request("rfc_live_current?select=*&order=rfc_id.desc");
export const getCurrent = async id => (await request(`rfc_live_current?select=*&rfc_id=eq.${q(id)}`))[0] || null;
export const listRevisions = id => request(`rfc_live_revisions?select=*&rfc_id=eq.${q(id)}&order=rev.desc`);
export const getRevision = async (id, version) =>
  (await request(`rfc_revisions?select=*&rfc_id=eq.${q(id)}&version=eq.${q(version)}`))[0] || null;
export const getLatestRevision = async id =>
  (await request(`rfc_revisions?select=*&rfc_id=eq.${q(id)}&order=rev.desc&limit=1`))[0] || null;

const post = (fn, body) => request(`rpc/${fn}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const createRfc = ({ meta, bundle, authors, collaborators, by }) =>
  post("create_rfc", { p_meta: meta, p_bundle: bundle, p_authors: authors, p_collaborators: collaborators, p_by: by });
export const addRevision = ({ id, meta, bundle, authors, collaborators, by, note }) =>
  post("add_rfc_revision", { p_rfc_id: id, p_meta: meta, p_bundle: bundle, p_authors: authors, p_collaborators: collaborators, p_by: by, p_note: note || null });
