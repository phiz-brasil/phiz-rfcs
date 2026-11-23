/* The phiz-rfc skill people download from the new-RFC page: a zip (unzip into ~/.claude/skills or upload it as a skill) and the whole
   skill as one text, to paste as instructions into any AI. The zip has fixed dates, so the same sources give the same bytes. */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { zipSync, strToU8 } from "fflate";
import { SKILL_FILES } from "./constants.ts";
import { REPO_ROOT } from "./html.ts";

export function skillFiles(): Record<string, string> {
  const src = join(REPO_ROOT, "skills", "phiz-rfc");
  const files: Record<string, string> = {
    "SKILL.md": readFileSync(join(src, "site", "SKILL.md"), "utf-8"),
    "assets/RFC.md": readFileSync(join(REPO_ROOT, "templates", "bundle", "RFC.md"), "utf-8"),
  };
  for (const rel of SKILL_FILES) files[rel] = readFileSync(join(src, rel), "utf-8");
  return files;
}

export function skillZip(files = skillFiles()): Uint8Array {
  const mtime = new Date(2026, 0, 1, 0, 0, 0);
  const entries: Record<string, [Uint8Array, { mtime: Date; os: number; attrs: number }]> = {};
  for (const [rel, text] of Object.entries(files)) entries[`phiz-rfc/${rel}`] = [strToU8(text), { mtime, os: 3, attrs: 0o644 << 16 }];
  return zipSync(entries, { level: 6 });
}

export function skillText(files = skillFiles()): string {
  const parts = [files["SKILL.md"].trim()];
  for (const rel of [...SKILL_FILES, "assets/RFC.md"]) parts.push(`\n\n---\n\n# File: ${rel}\n\n` + files[rel].trim());
  return parts.join("\n") + "\n";
}
