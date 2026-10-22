/* Images attached to an RFC created on the site. The browser reduces every image before it is sent (at most 1600 px wide, at most
   1 MB, metadata dropped by re-encoding) so the database stays small and the server has little to refuse. The server checks again
   (stage_rfc_asset: type, first bytes, size). */

export const ACCEPT = ["image/png", "image/jpeg", "image/webp"];
export const MAX_BYTES = 1048576;       // 1 MiB, the limit of the database column
export const MAX_IMAGES = 20;
export const MAX_WIDTH = 1600;
export const NAME_RE = /^[a-z0-9][a-z0-9._-]{0,59}$/;
const EXT = { "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp" };

export class ImageError extends Error {
  constructor(code) { super(code); this.code = code; }          // "type" | "decode" | "size"
}

/* A name the RFC text can use: lower case, only letters, digits, dot, dash and underscore, with the extension of the final type. */
export function slugName(filename, mime) {
  const base = String(filename).replace(/\.[A-Za-z0-9]+$/, "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/[^a-z0-9._-]+/g, "-").replace(/^[^a-z0-9]+|[-._]+$/g, "").slice(0, 50) || "imagem";
  return `${base}.${EXT[mime]}`;
}

function encode(canvas, mime, quality) {
  return new Promise(resolve => canvas.toBlob(b => resolve(b && b.type === mime ? b : null), mime, quality));
}

/* → { blob, mime, width, height } with blob.size <= MAX_BYTES. */
export async function shrinkImage(file) {
  if (!ACCEPT.includes(file.type)) throw new ImageError("type");
  let bmp;
  try { bmp = await createImageBitmap(file, { imageOrientation: "from-image" }); }
  catch (e) { throw new ImageError("decode"); }
  try {
    let scale = Math.min(1, MAX_WIDTH / bmp.width);
    for (let round = 0; round < 7; round++) {
      const w = Math.max(1, Math.round(bmp.width * scale)), h = Math.max(1, Math.round(bmp.height * scale));
      const canvas = document.createElement("canvas");
      canvas.width = w; canvas.height = h;
      const ctx = canvas.getContext("2d");
      if (file.type === "image/jpeg") { ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h); }     // no transparency in JPEG
      ctx.drawImage(bmp, 0, 0, w, h);
      // the original type first (a diagram stays a crisp PNG when it fits), then WebP at falling quality
      const attempts = [[file.type, file.type === "image/png" ? undefined : 0.9], ["image/webp", 0.85], ["image/webp", 0.7]];
      for (const [mime, quality] of attempts) {
        const blob = await encode(canvas, mime, quality);
        if (blob && blob.size <= MAX_BYTES) return { blob, mime, width: w, height: h };
      }
      scale *= 0.8;
    }
    throw new ImageError("size");
  } finally { bmp.close(); }
}

export function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result).split(",")[1]);
    r.onerror = () => reject(r.error);
    r.readAsDataURL(blob);
  });
}

export function base64ToBlob(b64, mime) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Blob([bytes], { type: mime });
}
