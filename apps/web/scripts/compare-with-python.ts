/* While the old static build (tools/build.py) still exists: the pages this app generates must be the ones it generated, byte for byte.
   Run `.venv/bin/python tools/build.py` first (it writes dist/), then `npm run check:pages`. Exit code 1 on any difference. */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { unzipSync, strFromU8 } from "fflate";
import { REPO_ROOT } from "../server/site/html.ts";
import { commentsPage, indexPage, newRfcPage, viewerPage } from "../server/site/pages.ts";
import { skillFiles, skillText, skillZip } from "../server/site/skill.ts";

const dist = (p: string) => readFileSync(join(REPO_ROOT, "dist", p), "utf-8");
const checks: [string, string, string][] = [
  ["index.html", indexPage(), dist("index.html")],
  ["rfc/index.html", viewerPage(), dist("rfc/index.html")],
  ["nova/index.html", newRfcPage(), dist("nova/index.html")],
  ["comments/index.html", commentsPage(), dist("comments/index.html")],
  ["assets/skill/phiz-rfc-skill.md", skillText(), dist("assets/skill/phiz-rfc-skill.md")],
];
const ours = unzipSync(skillZip(skillFiles()));
const theirs = unzipSync(readFileSync(join(REPO_ROOT, "dist", "assets", "skill", "phiz-rfc.zip")));
for (const name of new Set([...Object.keys(ours), ...Object.keys(theirs)])) {
  checks.push([`phiz-rfc.zip:${name}`, ours[name] ? strFromU8(ours[name]) : "(missing)", theirs[name] ? strFromU8(theirs[name]) : "(missing)"]);
}
let bad = 0;
for (const [name, a, b] of checks) {
  if (a === b) { console.log(`same      ${name}`); continue; }
  bad += 1;
  let i = 0;
  while (i < Math.min(a.length, b.length) && a[i] === b[i]) i += 1;
  console.log(`DIFFERENT ${name} at character ${i}\n  this app: ${JSON.stringify(a.slice(Math.max(0, i - 40), i + 60))}\n  old build: ${JSON.stringify(b.slice(Math.max(0, i - 40), i + 60))}`);
}
process.exit(bad ? 1 : 0);
