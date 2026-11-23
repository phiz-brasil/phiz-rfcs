/* Fills public/ before `next dev` and `next build`: everything the pages load that is a file, not a route.
     assets/                        page scripts, styles and vendor files (the repository's assets/ folder)
     assets/templates/, page.css    the single-file template and the preview styles of the new-RFC page
     assets/skill/                  the phiz-rfc skill, zipped and as one text
     rfcs/<ID>/…                    the archived pages, the pictures they use and the OpenAPI reference, frozen in legacy/
     archive.json                   the archived versions the RFC page lists
   public/ is generated: never edit it, edit the sources. */
import { cpSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { REPO_ROOT } from "../server/site/html.ts";
import { skillFiles, skillText, skillZip } from "../server/site/skill.ts";

const WEB = join(import.meta.dirname, "..");
const PUBLIC = join(WEB, "public");

rmSync(PUBLIC, { recursive: true, force: true });
cpSync(join(REPO_ROOT, "assets"), join(PUBLIC, "assets"), { recursive: true });
cpSync(join(REPO_ROOT, "templates", "bundle"), join(PUBLIC, "assets", "templates"), { recursive: true });
cpSync(join(REPO_ROOT, "templates", "page.css"), join(PUBLIC, "assets", "page.css"));

const files = skillFiles();
mkdirSync(join(PUBLIC, "assets", "skill"), { recursive: true });
writeFileSync(join(PUBLIC, "assets", "skill", "phiz-rfc.zip"), skillZip(files));
writeFileSync(join(PUBLIC, "assets", "skill", "phiz-rfc-skill.md"), skillText(files));

cpSync(join(WEB, "legacy"), PUBLIC, { recursive: true });
console.log(`public/ ready (${PUBLIC})`);
