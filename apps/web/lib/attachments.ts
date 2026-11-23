/* Helpers of the attachments hub: sizes, file names for Storage, and editions (an attachment that replaces another is its newer edition; the list
   shows the latest of each chain and keeps the earlier ones under it). */
import type { Attachment } from "./db";

export const MAX_BYTES = 50 * 1024 * 1024;          // the bucket's limit; checked here first so nobody waits for an upload that will be refused

export function formatSize(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

/* a name Storage accepts in a path: letters, digits and . _ -; the extension is kept */
export function storageName(name: string): string {
  const clean = name.normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/[^A-Za-z0-9._-]+/g, "_").replace(/^[._]+/, "");
  const out = clean || "file";
  if (out.length <= 150) return out;
  const dot = out.lastIndexOf(".");
  const ext = dot > 0 && out.length - dot <= 12 ? out.slice(dot) : "";
  return out.slice(0, 150 - ext.length) + ext;
}

export const isHtml = (a: { content_type: string | null; name: string }) => /html/i.test(a.content_type ?? "") || /\.html?$/i.test(a.name);
/* what the page may show in place: pictures, audio and video; everything else (HTML above all) is offered as a download */
export const previewKind = (a: Attachment): "image" | "audio" | "video" | null => {
  if (a.kind !== "file" || isHtml(a)) return null;
  const c = a.content_type ?? "";
  return /^image\/(png|jpe?g|gif|webp)$/.test(c) ? "image" : c.startsWith("audio/") ? "audio" : c.startsWith("video/") ? "video" : null;
};

/* the latest edition of each chain, newest first, each with the editions before it (newest first) */
export function editions(rows: Attachment[]): { latest: Attachment; older: Attachment[] }[] {
  const byId = new Map(rows.map(r => [r.id, r]));
  const replaced = new Set(rows.map(r => r.replaces).filter(Boolean) as string[]);
  const out: { latest: Attachment; older: Attachment[] }[] = [];
  for (const r of rows) {
    if (replaced.has(r.id)) continue;
    const older: Attachment[] = [];
    for (let cur = r.replaces ? byId.get(r.replaces) : undefined, guard = 0; cur && guard < 50; cur = cur.replaces ? byId.get(cur.replaces) : undefined, guard++) older.push(cur);
    out.push({ latest: r, older });
  }
  return out.sort((a, b) => b.latest.created_at.localeCompare(a.latest.created_at));
}

export async function sha256(file: Blob): Promise<string | null> {
  try {
    const buf = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
    return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
  } catch { return null; }                          // an insecure origin has no crypto.subtle: the checksum is optional
}
