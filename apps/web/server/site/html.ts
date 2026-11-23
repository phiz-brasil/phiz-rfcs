/* Small helpers shared by the page generators: the repository root, the site config, escaping and the three-language spans. */
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";

export const LANGS = ["pt", "en", "zh"] as const;
export type Lang = (typeof LANGS)[number];
export type Tri = Record<Lang, string>;

function findRoot(from: string): string {
  let dir = from;
  while (!existsSync(join(dir, "site.config.json"))) {
    const up = dirname(dir);
    if (up === dir) throw new Error(`site.config.json not found above ${from}`);
    dir = up;
  }
  return dir;
}

/* The repository root: templates/, skills/, assets/ and site.config.json live there, shared with the tools. */
export const REPO_ROOT = findRoot(process.cwd());

type Config = { title: string; repo: string; giscus: Record<string, string>; comments?: Record<string, string> };
export const CFG: Config = JSON.parse(readFileSync(join(REPO_ROOT, "site.config.json"), "utf-8"));

export const liveConfig = () => ({ repo: CFG.repo, giscus: CFG.giscus, comments: CFG.comments ?? {} });

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
