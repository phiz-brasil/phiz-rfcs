/* The sign-in script of the pages (assets/auth.js, docs/spec/v2/login.md): it goes first in every layout and in every old page, configured with the Supabase address,
   the publishable key and the switch of site.config.json. */
import { authAttrs } from "../server/site/auth.ts";

export function AuthScript() {
  const a = authAttrs();
  // eslint-disable-next-line @next/next/no-sync-scripts
  return <script src="/assets/auth.js" data-url={a.url} data-key={a.key} data-required={a.required} />;
}
