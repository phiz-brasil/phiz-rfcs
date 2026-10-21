// Translates RFC comments into PT-BR, EN-US and Chinese with Cloudflare Workers AI (m2m100) and
// stores the result in rfc_comments.translations / rfc_comments.src_lang.
//
// Called by a Supabase Database Webhook on INSERT into public.rfc_comments, with the header
//   x-webhook-secret: <TRANSLATE_WEBHOOK_SECRET>
// POST {"backfill": true} with the same header translates comments that have no translation yet
// (up to 50 per call).
//
// Secrets: CF_ACCOUNT_ID, CF_API_TOKEN (permission "Workers AI"), TRANSLATE_WEBHOOK_SECRET.
// SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are provided by Supabase.
//
// m2m100 does not detect the source language, so detect() guesses it (CJK characters → zh;
// otherwise Portuguese vs English by accents and common words) and falls back to the language
// the page was in when the comment was written (rfc_comments.lang).
import { createClient } from "jsr:@supabase/supabase-js@2";

const ACCOUNT = Deno.env.get("CF_ACCOUNT_ID") ?? "";
const TOKEN = Deno.env.get("CF_API_TOKEN") ?? "";
const SECRET = Deno.env.get("TRANSLATE_WEBHOOK_SECRET") ?? "";
const MODEL = Deno.env.get("CF_TRANSLATE_MODEL") ?? "@cf/meta/m2m100-1.2b";
const ENDPOINT = `https://api.cloudflare.com/client/v4/accounts/${ACCOUNT}/ai/run/${MODEL}`;
const LANGS = ["pt", "en", "zh"] as const;
type Lang = typeof LANGS[number];

const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
  auth: { persistSession: false },
});

type Row = { id: string; body: string; quote: string | null; lang: string | null };
type Piece = { body: string; quote: string | null };

const PT_WORDS = /\b(que|não|nao|uma|para|com|como|mais|isso|esse|essa|está|sobre|também|então|pode|deve|seria|ainda|já|mas|por|dos|das|nos|nas|ao|se|é)\b/gi;
const EN_WORDS = /\b(the|and|that|this|with|for|not|are|is|was|would|should|could|can|will|have|has|from|but|what|how|why|it|of|to|in)\b/gi;

function detect(text: string): Lang | null {
  const letters = text.replace(/[\s\d\p{P}\p{S}]/gu, "");
  if (!letters) return null;
  const cjk = (letters.match(/[㐀-鿿]/g) ?? []).length;
  if (cjk / letters.length > 0.3) return "zh";
  const pt = (text.match(PT_WORDS) ?? []).length + (text.match(/[ãõçáéíóúâêô]/gi) ?? []).length * 2;
  const en = (text.match(EN_WORDS) ?? []).length;
  if (pt === en) return null;
  return pt > en ? "pt" : "en";
}

async function translate(text: string, from: Lang, to: Lang): Promise<string> {
  const r = await fetch(ENDPOINT, {
    method: "POST",
    headers: { Authorization: `Bearer ${TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify({ text, source_lang: from, target_lang: to }),
  });
  const json = await r.json().catch(() => null);
  if (!r.ok || json?.success === false) throw new Error(`Workers AI ${r.status}: ${JSON.stringify(json?.errors ?? json)}`);
  const out = json?.result?.translated_text ?? json?.translated_text;
  if (typeof out !== "string") throw new Error(`Workers AI: unexpected response ${JSON.stringify(json)}`);
  return out;
}

async function translateRow(row: Row) {
  const hint = LANGS.includes(row.lang as Lang) ? (row.lang as Lang) : null;
  // emoji-only comments (reactions) have nothing to translate
  const src = /\p{L}/u.test(row.body) ? (detect(row.body) ?? detect(row.quote ?? "") ?? hint) : null;
  const out: Record<string, Piece> = {};
  if (src) {
    out[src] = { body: row.body, quote: row.quote };   // the original stays as written
    await Promise.all(LANGS.filter((to) => to !== src).map(async (to) => {
      out[to] = {
        body: await translate(row.body, src, to),
        quote: row.quote ? await translate(row.quote, src, to) : null,
      };
    }));
  }   // unknown language: store {} so the comment is not retried; the page shows the original
  const { error } = await db.from("rfc_comments").update({ translations: out, src_lang: src }).eq("id", row.id);
  if (error) throw error;
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return new Response("method not allowed", { status: 405 });
  if (!SECRET || req.headers.get("x-webhook-secret") !== SECRET) return new Response("unauthorized", { status: 401 });
  if (!ACCOUNT || !TOKEN) return new Response("CF_ACCOUNT_ID / CF_API_TOKEN are not set", { status: 500 });
  const payload = await req.json().catch(() => ({}));
  try {
    if (payload.backfill) {
      const { data, error } = await db.from("rfc_comments").select("id,body,quote,lang").is("translations", null)
        .order("created_at", { ascending: true }).limit(50);
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
