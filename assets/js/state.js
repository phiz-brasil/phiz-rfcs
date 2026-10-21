/* Configuration and the values the modules share. `S` is the only mutable state: comments of this RFC and what the
   drawer and the panels need to know about them. */
export const cfg = window.PHIZ_SITE || {};
export const rfcId = window.PHIZ_RFC_ID || "RFC";
export const frozen = !!window.PHIZ_FROZEN;   // archived version: read-only, no new comments

export const sb = !frozen && cfg.comments && cfg.comments.supabaseUrl && cfg.comments.supabaseKey ? {
  url: cfg.comments.supabaseUrl.replace(/\/+$/, "") + "/rest/v1/rfc_comments",
  // new publishable keys (sb_publishable_…) go only in "apikey"; legacy anon keys are JWTs and also go in Authorization
  headers: Object.assign({ apikey: cfg.comments.supabaseKey },
    /^eyJ/.test(cfg.comments.supabaseKey) ? { Authorization: "Bearer " + cfg.comments.supabaseKey } : {})
} : null;

export const BASE_COLS = "id,rfc_id,section,parent_id,author,body,quote,lang,created_at";
export const FULL_COLS = BASE_COLS + ",para,translations,src_lang";

export const S = {
  all: null,            // comments of this RFC; null while loading
  loadFailed: false,
  COLS: FULL_COLS,      // falls back step by step if the newer columns do not exist yet
  HAS_PARA: true,
  seenAt: 0,            // when this browser last opened the comments list (set by drawer.js)
  newIds: new Set(),    // "new" at the moment the drawer was opened
  drawer: null,
  dFilter: "all",
  linkDone: false
};
