/* What assets/auth.js needs to know, from site.config.json (docs/spec/v2/login.md): where Supabase is, the publishable key and whether sign-in is required. */
import { CFG, esc } from "./html.ts";

type AuthCfg = { comments?: { supabaseUrl?: string; supabaseKey?: string }; auth?: { required?: boolean } };

export function authAttrs() {
  const c = CFG as AuthCfg;
  return { url: c.comments?.supabaseUrl ?? "", key: c.comments?.supabaseKey ?? "", required: c.auth?.required ? "1" : "0" };
}

/* the same tag as a string, for the pages that are plain HTML text (the old pages) */
export function authScriptTag(): string {
  const a = authAttrs();
  return `<script src="/assets/auth.js" data-url="${esc(a.url)}" data-key="${esc(a.key)}" data-required="${a.required}"></script>`;
}
