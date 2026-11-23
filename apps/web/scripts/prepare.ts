/* Fills public/ before `next dev` and `next build`: everything the pages load that is a file, not a route.
     assets/                        page scripts, styles and vendor files (the repository's assets/ folder)
     assets/templates/, page.css    the single-file template and the preview styles of the new-RFC page
     assets/skill/                  the phiz-rfc skill, zipped and as one text
     rfcs/<ID>/…                    the pictures and files the archived pages use (from the repository's rfcs/)
     rfcs/<ID>/v*.html, openapi…    the archived pages and the OpenAPI reference, frozen in legacy/
     archive.json                   the archived versions the RFC page lists
   public/ is generated: never edit it, edit the sources. */
import { cpSync, existsSync, mkdirSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { basename, join } from "node:path";
import { REPO_ROOT } from "../server/site/html.ts";
import { skillFiles, skillText, skillZip } from "../server/site/skill.ts";

const WEB = join(import.meta.dirname, "..");
const PUBLIC = join(WEB, "public");
// what the old build did not publish from an RFC folder: its sources and older versions
const SKIP = (name: string) => name === "source.html" || name === "versions" || name === "openapi_gen.py" || name === "__pycache__" || /^rfc\..*\.md$/.test(name);

rmSync(PUBLIC, { recursive: true, force: true });
cpSync(join(REPO_ROOT, "assets"), join(PUBLIC, "assets"), { recursive: true });
cpSync(join(REPO_ROOT, "templates", "bundle"), join(PUBLIC, "assets", "templates"), { recursive: true });
cpSync(join(REPO_ROOT, "templates", "page.css"), join(PUBLIC, "assets", "page.css"));

const files = skillFiles();
mkdirSync(join(PUBLIC, "assets", "skill"), { recursive: true });
writeFileSync(join(PUBLIC, "assets", "skill", "phiz-rfc.zip"), skillZip(files));
writeFileSync(join(PUBLIC, "assets", "skill", "phiz-rfc-skill.md"), skillText(files));

const rfcs = join(REPO_ROOT, "rfcs");
for (const id of existsSync(rfcs) ? readdirSync(rfcs) : []) {
  const dir = join(rfcs, id);
  if (id.startsWith("_") || !existsSync(join(dir, "rfc.json"))) continue;       // drafts without rfc.json are not published
  cpSync(dir, join(PUBLIC, "rfcs", id), { recursive: true, filter: src => !SKIP(basename(src)) });
}
cpSync(join(WEB, "legacy"), PUBLIC, { recursive: true });
console.log(`public/ ready (${PUBLIC})`);
