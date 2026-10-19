// Translates RFC comments into PT-BR, EN-US and Chinese with DeepL and stores the result in
// rfc_comments.translations / rfc_comments.src_lang.
//
// Called by a Supabase Database Webhook on INSERT into public.rfc_comments, with the header
//   x-webhook-secret: <TRANSLATE_WEBHOOK_SECRET>
// POST {"backfill": true} with the same header translates comments that have no translation yet
// (up to 200 per call).
//
// Secrets: DEEPL_API_KEY (free keys end with ":fx"), TRANSLATE_WEBHOOK_SECRET.
// SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are provided by Supabase.
import { createClient } from "jsr:@supabase/supabase-js@2";

const DEEPL_KEY = Deno.env.get("DEEPL_API_KEY") ?? "";
const SECRET = Deno.env.get("TRANSLATE_WEBHOOK_SECRET") ?? "";
const DEEPL_URL = Deno.env.get("DEEPL_API_URL") ??
  (DEEPL_KEY.endsWith(":fx") ? "https://api-free.deepl.com/v2/translate" : "https://api.deepl.com/v2/translate");
// English first: its result tells us the source language, so the matching target can be skipped.
const TARGETS: [string, string][] = [["en", "EN-US"], ["pt", "PT-BR"], ["zh", "ZH"]];
const SUPPORTED = new Set(TARGETS.map(([l]) => l));

const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
  auth: { persistSession: false },
});

type Row = { id: string; body: string; quote: string | null };
type Piece = { body: string; quote: string | null };

async function deepl(texts: string[], target: string) {
  const r = await fetch(DEEPL_URL, {
    method: "POST",
    headers: { Authorization: `DeepL-Auth-Key ${DEEPL_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ text: texts, target_lang: target, preserve_formatting: true }),
  });
  if (!r.ok) throw new Error(`DeepL ${r.status}: ${await r.text()}`);
  const json = await r.json();
  return json.translations as { text: string; detected_source_language: string }[];
}

async function translateRow(row: Row) {
  const texts = row.quote ? [row.body, row.quote] : [row.body];
  const out: Record<string, Piece> = {};
  let src = "";
  for (const [lang, target] of TARGETS) {
    if (lang === src) continue;
    const t = await deepl(texts, target);
    if (!src) src = (t[0].detected_source_language || "").toLowerCase().slice(0, 2);
    out[lang] = { body: t[0].text, quote: row.quote ? t[1].text : null };
  }
  const srcLang = SUPPORTED.has(src) ? src : null;
  if (srcLang) out[srcLang] = { body: row.body, quote: row.quote };   // the original stays as written
  const { error } = await db.from("rfc_comments").update({ translations: out, src_lang: srcLang }).eq("id", row.id);
  if (error) throw error;
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return new Response("method not allowed", { status: 405 });
  if (!SECRET || req.headers.get("x-webhook-secret") !== SECRET) return new Response("unauthorized", { status: 401 });
  if (!DEEPL_KEY) return new Response("DEEPL_API_KEY is not set", { status: 500 });
  const payload = await req.json().catch(() => ({}));
  try {
    if (payload.backfill) {
      const { data, error } = await db.from("rfc_comments").select("id,body,quote").is("translations", null)
        .order("created_at", { ascending: true }).limit(200);
      if (error) throw error;
      for (const row of data ?? []) await translateRow(row as Row);
      return Response.json({ translated: data?.length ?? 0 });
    }
    const row = payload.record as Row | undefined;
    if (payload.type !== "INSERT" || payload.table !== "rfc_comments" || !row?.id) return Response.json({ skipped: true });
    await translateRow(row);
    return Response.json({ ok: true, id: row.id });
  } catch (e) {
    console.error(e);
    return new Response(String(e), { status: 500 });
  }
});
