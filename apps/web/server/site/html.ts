/* Small helpers shared by the page generators: the repository root, the site config, escaping and the three-language spans. */
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import siteConfig from "../../../../site.config.json" with { type: "json" };    // inlined by the bundler: a page rendered on demand runs where the repository is not on disk (docs/spec/v2/platform.md)

export const LANGS = ["pt", "en", "zh"] as const;
export type Lang = (typeof LANGS)[number];
export type Tri = Record<Lang, string>;

function findRoot(from: string): string | null {
  let dir = from;
  while (!existsSync(join(dir, "site.config.json"))) {
    const up = dirname(dir);
    if (up === dir) return null;
    dir = up;
  }
  return dir;
}

/* The repository root: templates/, skills/, assets/ and site.config.json live there, shared with the tools. It is found at build time; on a server that has only the
   bundle there is none, and that is fine for the routes rendered on demand (they never read it): so it does not throw. */
export const REPO_ROOT = findRoot(process.cwd()) ?? process.cwd();

type Config = { title: string; repo: string; giscus: Record<string, string>; comments?: Record<string, string>; google?: { clientId?: string } };
export const CFG: Config = siteConfig as Config;

export const liveConfig = () => ({ repo: CFG.repo, giscus: CFG.giscus, comments: CFG.comments ?? {} });
// the Google OAuth client of the export (docs/spec/v2/redesign.md, What PR 3 delivers); kept out of liveConfig, which the old pages carry byte for byte
export const googleClientId = () => CFG.google?.clientId ?? "";

// the same escaping as Python's html.escape
export const esc = (s: string) =>
  String(s).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#x27;");

export const spans = (d: Tri, cls = "") => LANGS.map(l => `<span data-l="${l}"${cls ? ` class="${cls}"` : ""}>${esc(d[l])}</span>`).join("");

/* JSON written the way Python's json.dumps writes it (", " and ": " separators; non-ASCII escaped unless asked not to), so the pages
   are byte for byte the ones the old build made. */
export function pyJson(value: unknown, ensureAscii = true): string {
  if (value === null || value === undefined) return "null";
  if (typeof value === "string") {
    const s = JSON.stringify(value);
    return ensureAscii ? s.replace(/[\u0080-\uffff]/g, c => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0")) : s;
  }
  if (typeof value === "number" || typeof value === "boolean") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(v => pyJson(v, ensureAscii)).join(", ") + "]";
  return "{" + Object.entries(value as Record<string, unknown>).map(([k, v]) => `${pyJson(k, ensureAscii)}: ${pyJson(v, ensureAscii)}`).join(", ") + "}";
}
